import ast
from pathlib import Path
import sys
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]


class SelfContainedBackendTests(unittest.TestCase):
    def test_semantic_candidate_survives_reranking_for_a_paraphrase(self):
        from backend import chatbot_app
        semantic={'chunk':{'chunk_id':'semantic','text':'Our cleaners bring all products and equipment.','title':'FAQ','section':'Supplies'},'score':.403,'reasons':['pgvector_hybrid']}
        lexical={'chunk':{'chunk_id':'lexical','text':'Cleaning homes throughout San Jose.','title':'Cleaning'},'score':.44,'reasons':['original_overlap']}
        ranked=chatbot_app.rerank_rag_candidates('Do I need to provide materials?', [lexical,semantic], keep=1)
        self.assertEqual(ranked[0]['chunk']['chunk_id'],'semantic')

    def test_grounding_accepts_cited_bullets_but_rejects_new_claims(self):
        from backend import chatbot_app
        chunks=[{'text':'Standard cleaning starts at $149. Our cleaners bring all cleaning products and equipment.'}]
        valid='- Pricing starts at $149 for standard cleaning. [Source 1]\n- Supplies and equipment are provided. [Source 1]'
        self.assertTrue(chatbot_app.verify_grounded_answer(valid,chunks,'What does it cost and who supplies materials?')['supported'])
        self.assertFalse(chatbot_app.verify_grounded_answer('Standard cleaning costs $199.',chunks,'What does it cost?')['supported'])
        self.assertFalse(chatbot_app.verify_grounded_answer('Every booking includes carpet repair and window replacement.',chunks,'What is included?')['supported'])

    def test_grounded_llm_prices_and_supplies_keep_llm_source(self):
        from backend import chatbot_app
        rows={
            'price':{'chunk_id':'price','text':'Standard cleaning starts at $149.','title':'Pricing','relevance_score':.538},
            'supplies':{'chunk_id':'supplies','text':'Our cleaners bring all cleaning products and equipment.','title':'FAQ','relevance_score':.412},
        }
        store=mock.Mock()
        with (
            mock.patch.object(chatbot_app,'refresh_manual_rag_index'),
            mock.patch.object(chatbot_app,'rag_chunks_for_site',return_value=[]),
            mock.patch.object(chatbot_app,'retrieve_rag_candidates',side_effect=lambda *args,**kwargs: []),
            mock.patch('backend.rag_store.configured_store',return_value=store),
        ):
            for kind,question,answer in (
                ('price','How much does a standard visit cost?','Standard cleaning starts at $149. [Source 1]'),
                ('supplies','Do I need to provide materials?','No. Cleaners bring all cleaning products and equipment. [Source 1]'),
            ):
                with self.subTest(kind=kind):
                    store.search.return_value=[rows[kind]]
                    with mock.patch.object(chatbot_app,'call_llm_answer_formatter',return_value=answer):
                        result=chatbot_app.answer_from_site_rag('test-site',question)
                    self.assertEqual(result['reply'],answer)
                    self.assertEqual(result['answer_source'],'website_rag_llm')

    def test_count_answer_is_offered_to_llm_before_deterministic_fallback(self):
        from backend import chatbot_app
        chunks=[{'chunk_id':'one','text':'The course has 12 lessons. Lesson 1 Setup.','title':'Curriculum','url':'https://example.test'}]
        with (
            mock.patch.object(chatbot_app,'refresh_manual_rag_index'),
            mock.patch.object(chatbot_app,'rag_chunks_for_site',return_value=chunks),
            mock.patch.object(chatbot_app,'call_llm_answer_formatter',return_value='LLM polished: twelve classes.') as formatter,
        ):
            result=chatbot_app.answer_from_site_rag('test-site','How many classes are there?')
        self.assertEqual(result['reply'],'LLM polished: twelve classes.')
        self.assertEqual(result['answer_source'],'website_rag_llm')
        formatter.assert_called_once()

    def test_public_server_uses_only_repository_local_backend(self):
        source = (ROOT / "public_server.py").read_text(encoding="utf-8")
        self.assertNotIn("/home/jianl/.hermes", source)
        self.assertNotIn("website_chatbot/backend/app.py", source)
        self.assertTrue((ROOT / "backend" / "chatbot_app.py").is_file())
        self.assertTrue((ROOT / "backend" / "crm_core.py").is_file())

        tree = ast.parse(source)
        backend_paths = [
            node.args[1]
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "spec_from_file_location"
            and len(node.args) >= 2
        ]
        self.assertTrue(backend_paths, "public_server must explicitly load its backend")
        assignments = {
            target.id: ast.unparse(node.value)
            for node in ast.walk(tree)
            if isinstance(node, ast.Assign)
            for target in node.targets
            if isinstance(target, ast.Name)
        }
        path_expression = ast.unparse(backend_paths[0])
        if path_expression in assignments:
            path_expression = assignments[path_expression]
        self.assertIn("ROOT", path_expression)
        self.assertIn("backend", path_expression)
        self.assertIn("chatbot_app.py", path_expression)

    def test_public_runtime_invokes_repository_pgvector_hook(self):
        # Exercise the module exactly as the public process loads it by file
        # spec. Patching the package-qualified module also guards against a
        # second, top-level ``rag_store`` module being imported accidentally.
        sys.path.insert(0, str(ROOT))
        try:
            import public_server
            import backend.rag_store as repository_rag_store

            vector_store = mock.Mock()
            vector_store.search.return_value = []
            fake_server = mock.Mock()
            with (
                mock.patch.object(repository_rag_store, "configured_store", return_value=vector_store) as configured,
                mock.patch.object(
                    public_server,
                    "ThreadingHTTPServer",
                    side_effect=lambda _address, handler: setattr(fake_server, "RequestHandlerClass", handler) or fake_server,
                ),
            ):
                server = public_server.chatbot_server()
                loaded_backend = server.RequestHandlerClass.__mro__[1].__module__
                chatbot = sys.modules[loaded_backend]
                chatbot.answer_from_site_rag("integration-pgvector-site", "hybrid retrieval probe")

            configured.assert_called_once_with()
            vector_store.search.assert_called_once_with(
                "integration-pgvector-site", "hybrid retrieval probe", chatbot.RAG_MAX_SELECTED
            )
        finally:
            if sys.path[0] == str(ROOT):
                sys.path.pop(0)


if __name__ == "__main__":
    unittest.main()
