import ast
from pathlib import Path
import sys
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]


class SelfContainedBackendTests(unittest.TestCase):
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
