import io
import json
from pathlib import Path
import tempfile
import unittest
import zipfile
from unittest.mock import patch

from backend import rag_store
import admin_server as admin


class FakeAdapter:
    def __init__(self): self.calls=[]; self.semantic=[]; self.lexical=[]
    def upsert(self, site_id, document, chunks): self.calls.append(('upsert', site_id, document, chunks))
    def delete(self, site_id, document_id): self.calls.append(('delete', site_id, document_id))
    def semantic_search(self, site_id, vector, limit): self.calls.append(('semantic', site_id, vector, limit)); return self.semantic
    def lexical_search(self, site_id, query, limit): self.calls.append(('lexical', site_id, query, limit)); return self.lexical

class FakeEmbedding:
    dimension=3; model='fake'
    def embed(self, texts): return [[1.0,0.0,0.0] for _ in texts]

class RagStoreTests(unittest.TestCase):
    def test_semantic_paraphrase_beats_keyword_mismatch_and_tenant_is_scoped(self):
        db=FakeAdapter(); db.semantic=[{'chunk_id':'meaning','text':'We handle move-out cleaning','title':'Moving','url':'/moving','semantic_score':.99}]
        db.lexical=[{'chunk_id':'words','text':'relocation relocation','title':'Words','url':'/words','lexical_score':.8}]
        store=rag_store.HybridRagStore(db,FakeEmbedding())
        result=store.search('tenant-a','clean my empty apartment after relocating',limit=2)
        self.assertEqual(result[0]['chunk_id'],'meaning')
        self.assertTrue(all(call[1]=='tenant-a' for call in db.calls))
        self.assertGreater(result[0]['relevance_score'], .8)
    def test_irrelevant_vector_only_candidate_is_filtered(self):
        db=FakeAdapter(); db.semantic=[{'chunk_id':'noise','text':'Unrelated gardening advice','semantic_score':.12}]
        self.assertEqual(rag_store.HybridRagStore(db,FakeEmbedding()).search('tenant','office cleaning prices'),[])
    def test_semantic_paraphrase_survives_conservative_threshold(self):
        db=FakeAdapter(); db.semantic=[{'chunk_id':'match','text':'We clean empty homes after tenants leave','semantic_score':.91}]
        result=rag_store.HybridRagStore(db,FakeEmbedding()).search('tenant','move-out service',3)
        self.assertEqual([row['chunk_id'] for row in result],['match'])
    def test_embedding_failure_falls_back(self):
        class Broken:
            dimension=3; model='bad'
            def embed(self,texts): raise rag_store.EmbeddingError('offline')
        fallback=lambda site,q,n:[{'chunk_id':'fallback','text':'offline answer','title':'JSON','url':'/json'}]
        result=rag_store.HybridRagStore(FakeAdapter(),Broken(),fallback).search('s','question',3)
        self.assertEqual(result[0]['chunk_id'],'fallback')
    def test_dimension_mismatch_rejected(self):
        db=FakeAdapter(); store=rag_store.HybridRagStore(db,FakeEmbedding(),dimension=1536)
        with self.assertRaises(rag_store.DimensionMismatch): store.ingest('s',{'document_id':'d','content':'hello'})
    def test_document_title_is_chunk_title_fallback(self):
        db=FakeAdapter(); store=rag_store.HybridRagStore(db,FakeEmbedding())
        chunks=store.ingest('s',{'document_id':'d','title':'Document title','content':'hello','chunks':[{'text':'hello'}]})
        self.assertEqual(chunks[0]['title'],'Document title')

class ParsingTests(unittest.TestCase):
    CONTENT_TYPES='<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">{}</Types>'
    def zipped(self, members):
        out=io.BytesIO()
        with zipfile.ZipFile(out,'w') as z:
            for name,value in members.items(): z.writestr(name,value)
        return out.getvalue()
    def test_txt_docx_pptx_and_chunk_stability(self):
        self.assertEqual(admin.parse_knowledge_file('note.txt',b'Heading\nUseful text')[0],'Heading\nUseful text')
        docx=self.zipped({'[Content_Types].xml':self.CONTENT_TYPES.format('<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'),'word/document.xml':'<w:document xmlns:w="w"><w:p><w:r><w:t>Doc heading</w:t></w:r></w:p><w:p><w:r><w:t>Body</w:t></w:r></w:p></w:document>'})
        self.assertIn('Doc heading',admin.parse_knowledge_file('x.docx',docx)[0])
        pptx=self.zipped({'[Content_Types].xml':self.CONTENT_TYPES.format('<Override PartName="/ppt/presentation.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml"/>'),'ppt/slides/slide1.xml':'<p:sld xmlns:p="p" xmlns:a="a"><a:t>Slide title</a:t><a:t>Detail</a:t></p:sld>'})
        text,meta=admin.parse_knowledge_file('x.pptx',pptx); self.assertIn('Slide 1',text); self.assertEqual(meta['pages'],1)
        first=admin.chunk_document('d',text); second=admin.chunk_document('d',text)
        self.assertEqual([x['chunk_id'] for x in first],[x['chunk_id'] for x in second])
    def test_invalid_text_corrupt_zip_and_zip_bomb_rejected(self):
        with self.assertRaises(admin.Problem): admin.parse_knowledge_file('../malware.exe',b'x')
        with self.assertRaises(admin.Problem): admin.parse_knowledge_file('x.txt',b'\xff\x00')
        with self.assertRaises(admin.Problem): admin.parse_knowledge_file('x.docx',b'not zip')
        bomb=self.zipped({f'word/x{i}.xml':'x' for i in range(admin.MAX_ZIP_MEMBERS+1)})
        with self.assertRaises(admin.Problem): admin.parse_knowledge_file('x.docx',bomb)
    def test_pdf_missing_or_no_text_is_actionable(self):
        with patch.dict('sys.modules',{'fitz':None}):
            with self.assertRaisesRegex(admin.Problem,'PyMuPDF'): admin.parse_knowledge_file('x.pdf',b'%PDF-1.4')
    def test_office_extension_spoof_is_rejected_by_content_type(self):
        spoof=self.zipped({'[Content_Types].xml':self.CONTENT_TYPES.format('<Override PartName="/ppt/presentation.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml"/>'),'word/document.xml':'<w:document xmlns:w="w"><w:p><w:r><w:t>Fake</w:t></w:r></w:p></w:document>'})
        with self.assertRaisesRegex(admin.Problem,'content type'):
            admin.parse_knowledge_file('spoof.docx',spoof)

class UploadStorageTests(unittest.TestCase):
    def test_upload_is_atomic_download_scoped_and_delete_removes_original(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); (root/'data').mkdir(); (root/'data/rag-content.json').write_text('{"sites":{}}')
            app=admin.Application(root,'u',admin.hash_password('p'))
            result=app.upload_knowledge(admin.SITE,'evil.txt',b'Title\n\nUseful knowledge')
            self.assertNotIn('stored_path',result)
            stored=root/'data/knowledge-files'/admin.SITE/(result['upload_id']+'.txt')
            data,name,mime=app.download_upload(admin.SITE,result['upload_id']); self.assertIn(b'Useful',data); self.assertEqual(name,'evil.txt')
            with self.assertRaises(admin.Problem): app.download_upload('other',result['upload_id'])
            app.delete_upload(admin.SITE,result['upload_id']); self.assertFalse(stored.exists())
    def test_failed_parse_leaves_no_files_or_rag(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); (root/'data').mkdir(); (root/'data/rag-content.json').write_text('{"sites":{}}')
            app=admin.Application(root,'u',admin.hash_password('p'))
            with self.assertRaises(admin.Problem): app.upload_knowledge(admin.SITE,'bad.docx',b'bad')
            self.assertFalse((root/'data/knowledge-files').exists())
            self.assertEqual(json.loads((root/'data/rag-content.json').read_text()),{'sites':{}})

class UIUploadTests(unittest.TestCase):
    def test_upload_controls_status_and_source_link_exist(self):
        root=Path(__file__).resolve().parents[1]
        html=(root/'admin/index.html').read_text(); js=(root/'admin/app.js').read_text()
        for token in ['knowledge-upload','accept=".pdf,.docx,.pptx,.txt"','upload-status']: self.assertIn(token,html)
        self.assertIn('/api/uploads',js); self.assertIn('source_link',js)
        self.assertIn('result.indexed',js); self.assertIn('result.index_warning',js)
        self.assertIn('JSON search only',js)

class BlockingReviewTests(unittest.TestCase):
    def make_app(self,root):
        (root/'data').mkdir(); (root/'data/rag-content.json').write_text('{"sites":{}}')
        return admin.Application(root,'u',admin.hash_password('p'))
    def test_huge_paragraph_chunk_bounds_and_overlap(self):
        chunks=admin.chunk_document('d','x'*5000,size=1000,overlap=100)
        self.assertGreater(len(chunks),1); self.assertTrue(all(len(c['text'])<=1000 for c in chunks))
        self.assertEqual(chunks[0]['text'][-100:],chunks[1]['text'][:100])
    def test_filename_rejected_full_text_hashes_and_no_path_exposure(self):
        with tempfile.TemporaryDirectory() as tmp:
            app=self.make_app(Path(tmp))
            with self.assertRaises(admin.Problem): app.upload_knowledge(admin.SITE,'../x.txt',b'x')
            result=app.upload_knowledge(admin.SITE,'x.txt',b'a'*60000)
            self.assertNotIn('stored_path',result)
            item=json.loads((Path(tmp)/'data/rag-content.json').read_text())['sites'][admin.SITE][0]
            self.assertEqual(len(item['content']),60000)
            self.assertIn('file_sha256',item); self.assertIn('content_sha256',item)
            with self.assertRaisesRegex(admin.Problem,'/api/uploads/'): app.rag('DELETE',item['content_id'],{})
    def test_failed_index_is_explicit_and_safe(self):
        with tempfile.TemporaryDirectory() as tmp:
            app=self.make_app(Path(tmp))
            class Broken:
                def ingest(self,*a,**k): raise RuntimeError('password=secret')
            with patch('backend.rag_store.configured_store',return_value=Broken()): result=app.upload_knowledge(admin.SITE,'x.txt',b'x')
            self.assertFalse(result['indexed']); self.assertNotIn('secret',result['index_warning'])
    def test_vector_delete_failure_preserves_all_local_upload_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); app=self.make_app(root)
            result=app.upload_knowledge(admin.SITE,'keep.txt',b'keep this knowledge')
            target=root/'data/rag-content.json'; manifest=app._upload_manifest()
            stored=root/'data/knowledge-files'/admin.SITE/(result['upload_id']+'.txt')
            before=(target.read_bytes(),manifest.read_bytes(),stored.read_bytes())
            class Broken:
                def delete(self,*args): raise RuntimeError('postgres password=secret')
            with patch('backend.rag_store.configured_store',return_value=Broken()):
                with self.assertRaisesRegex(admin.Problem,'Vector index deletion failed') as caught:
                    app.delete_upload(admin.SITE,result['upload_id'])
            self.assertNotIn('secret',str(caught.exception))
            self.assertEqual((target.read_bytes(),manifest.read_bytes(),stored.read_bytes()),before)
    def test_write_failure_rolls_back_and_cleans_temps(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); app=self.make_app(root); original=(root/'data/rag-content.json').read_bytes(); real=admin.atomic_json; count=[0]
            def injected(path,data):
                count[0]+=1
                if count[0]==2: raise OSError('injected')
                return real(path,data)
            with patch.object(admin,'atomic_json',side_effect=injected):
                with self.assertRaises(OSError): app.upload_knowledge(admin.SITE,'x.txt',b'hello')
            self.assertEqual((root/'data/rag-content.json').read_bytes(),original)
            self.assertEqual(list(root.rglob('*.tmp')),[])
    def test_hybrid_exact_rrf_and_embedding_validation(self):
        class Adapter(FakeAdapter):
            def exact_search(self,site_id,query,limit): self.calls.append(('exact',site_id,query,limit)); return []
        db=Adapter(); db.semantic=[{'chunk_id':'c','text':'x','metadata':{},'semantic_score':.9}]
        result=rag_store.HybridRagStore(db,FakeEmbedding()).search('tenant','phrase',1)
        self.assertGreater(result[0]['rrf_score'],0); self.assertTrue(any(x[0]=='exact' and x[1]=='tenant' for x in db.calls))
        class Bad(FakeEmbedding):
            def embed(self,texts): return [[True,0,float('nan')] for _ in texts]
        with self.assertRaises(rag_store.EmbeddingError): rag_store.HybridRagStore(db,Bad()).ingest('s',{'document_id':'d','content':'x'})

if __name__=='__main__': unittest.main()
