"""Optional PostgreSQL/pgvector hybrid RAG storage.

No dependency is imported until a PostgreSQL URL is configured, preserving the
standard-library classroom mode. All repository operations require a site_id.
"""
from __future__ import annotations
import hashlib
import json
import os
import math
import logging
import urllib.request
from typing import Any, Callable

class RagError(RuntimeError): pass
class EmbeddingError(RagError): pass
class DimensionMismatch(RagError): pass

class OpenAIEmbeddingClient:
    def __init__(self, api_key=None, base_url=None, model=None, dimension=None, timeout=15):
        self.api_key=api_key or os.getenv('EASIIO_RAG_EMBEDDING_API_KEY') or os.getenv('OPENAI_API_KEY') or ''
        self.base_url=(base_url or os.getenv('EASIIO_RAG_EMBEDDING_BASE_URL') or 'https://api.openai.com/v1').rstrip('/')
        self.model=model or os.getenv('EASIIO_RAG_EMBEDDING_MODEL') or 'text-embedding-3-small'
        self.dimension=int(dimension or os.getenv('EASIIO_RAG_EMBEDDING_DIMENSION','1536'))
        self.timeout=float(timeout)
    def embed(self,texts):
        if not self.api_key: raise EmbeddingError('embedding API key is not configured')
        body={'model':self.model,'input':list(texts),'dimensions':self.dimension}
        req=urllib.request.Request(self.base_url+'/embeddings',data=json.dumps(body).encode(),method='POST',headers={'Authorization':'Bearer '+self.api_key,'Content-Type':'application/json'})
        try:
            with urllib.request.urlopen(req,timeout=self.timeout) as response: result=json.loads(response.read())
            vectors=[row['embedding'] for row in sorted(result['data'],key=lambda x:x['index'])]
        except Exception as exc: raise EmbeddingError('embedding request failed') from exc
        if len(vectors)!=len(texts) or any(len(v)!=self.dimension for v in vectors): raise DimensionMismatch('embedding response dimension mismatch')
        return vectors

class PsycopgAdapter:
    def __init__(self,database_url):
        self.database_url=database_url
    def _connect(self):
        try: import psycopg
        except ImportError as exc: raise RagError('install requirements-rag.txt for PostgreSQL RAG') from exc
        return psycopg.connect(self.database_url)
    def upsert(self,site_id,document,chunks):
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute("""INSERT INTO rag_documents(site_id,document_id,title,source_url,original_filename,stored_filename,mime_type,content_hash,metadata)
            VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb) ON CONFLICT(site_id,document_id) DO UPDATE SET title=excluded.title,source_url=excluded.source_url,original_filename=excluded.original_filename,stored_filename=excluded.stored_filename,mime_type=excluded.mime_type,content_hash=excluded.content_hash,metadata=excluded.metadata,updated_at=now()""",
            (site_id,document['document_id'],document.get('title',''),document.get('source_url',''),document.get('original_filename',''),document.get('stored_filename',''),document.get('mime_type',''),document['content_hash'],json.dumps(document.get('metadata',{}))))
            cur.execute('DELETE FROM rag_chunks WHERE site_id=%s AND document_id=%s',(site_id,document['document_id']))
            for c in chunks:
                cur.execute("INSERT INTO rag_chunks(site_id,document_id,chunk_id,chunk_index,title,content,content_hash,embedding,embedding_model,metadata) VALUES(%s,%s,%s,%s,%s,%s,%s,%s::vector,%s,%s::jsonb)",(site_id,document['document_id'],c['chunk_id'],c['chunk_index'],c.get('title',''),c['text'],c['content_hash'],'['+','.join(map(str,c['embedding']))+']',c['embedding_model'],json.dumps(c.get('metadata',{}))))
    def delete(self,site_id,document_id):
        with self._connect() as conn, conn.cursor() as cur: cur.execute('DELETE FROM rag_documents WHERE site_id=%s AND document_id=%s',(site_id,document_id))
    def semantic_search(self,site_id,vector,limit):
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute("SELECT chunk_id,content AS text,title,COALESCE(metadata->>'source_url','') AS url,metadata,1-(embedding <=> %s::vector) semantic_score FROM rag_chunks WHERE site_id=%s ORDER BY embedding <=> %s::vector LIMIT %s",('['+','.join(map(str,vector))+']',site_id,'['+','.join(map(str,vector))+']',limit))
            return [dict(zip([d.name for d in cur.description],r)) for r in cur.fetchall()]
    def lexical_search(self,site_id,query,limit):
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute("SELECT chunk_id,content AS text,title,COALESCE(metadata->>'source_url','') AS url,metadata,ts_rank(search_vector,websearch_to_tsquery('english',%s)) lexical_score FROM rag_chunks WHERE site_id=%s AND search_vector @@ websearch_to_tsquery('english',%s) ORDER BY lexical_score DESC LIMIT %s",(query,site_id,query,limit))
            return [dict(zip([d.name for d in cur.description],r)) for r in cur.fetchall()]
    def exact_search(self,site_id,query,limit):
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute("SELECT chunk_id,content AS text,title,COALESCE(metadata->>'source_url','') AS url,metadata FROM rag_chunks WHERE site_id=%s AND position(lower(%s) in lower(content))>0 ORDER BY length(content) LIMIT %s",(site_id,query,limit))
            return [dict(zip([d.name for d in cur.description],r)) for r in cur.fetchall()]

class HybridRagStore:
    def __init__(self,adapter,embedding,fallback:Callable|None=None,dimension=None,min_relevance=None):
        self.adapter,self.embedding,self.fallback=adapter,embedding,fallback; self.dimension=int(dimension or embedding.dimension); self.last_warning=''
        self.min_relevance=float(min_relevance if min_relevance is not None else os.getenv('EASIIO_RAG_MIN_RELEVANCE','0.65'))
        if not 0 <= self.min_relevance <= 1: raise ValueError('min_relevance must be between 0 and 1')
    def _validate(self,vectors):
        if any(len(v)!=self.dimension or any(type(x) not in (int,float) or not math.isfinite(x) for x in v) for v in vectors): raise EmbeddingError('embedding response contains invalid values or dimensions')
    def ingest(self,site_id,document,batch_size=32):
        text=document.get('content',''); raw_chunks=document.get('chunks') or [{'text':text}]; vectors=[]
        for i in range(0,len(raw_chunks),batch_size): vectors.extend(self.embedding.embed([c['text'] for c in raw_chunks[i:i+batch_size]]))
        if any(len(v)!=self.dimension for v in vectors): raise DimensionMismatch(f'expected {self.dimension}-dimensional embeddings')
        self._validate(vectors); chunks=[]
        for i,(raw,vector) in enumerate(zip(raw_chunks,vectors)):
            content=raw['text']; digest=hashlib.sha256(content.encode()).hexdigest()
            metadata={**document.get('metadata',{}),**raw.get('metadata',{}),'document_id':document['document_id'],'upload_id':document.get('upload_id',''),'source_url':document.get('source_url',''),'original_filename':document.get('original_filename','')}
            chunks.append({**raw,'title':raw.get('title') or document.get('title',''),'chunk_id':raw.get('chunk_id') or f"{document['document_id']}:{i}:{digest[:12]}",'chunk_index':i,'content_hash':digest,'embedding':vector,'embedding_model':self.embedding.model,'metadata':metadata})
        doc={**document,'content_hash':document.get('content_hash') or hashlib.sha256(text.encode()).hexdigest()}
        self.adapter.upsert(site_id,doc,chunks); return chunks
    def delete(self,site_id,document_id): self.adapter.delete(site_id,document_id)
    def search(self,site_id,query,limit=5):
        try:
            vector=self.embedding.embed([query])[0]
            if len(vector)!=self.dimension: raise DimensionMismatch('query embedding dimension mismatch')
            self._validate([vector]); count=max(limit*4,10)
            exact_search=getattr(self.adapter,'exact_search',lambda _site,_query,_count: [])
            groups=[self.adapter.semantic_search(site_id,vector,count),self.adapter.lexical_search(site_id,query,count),exact_search(site_id,query,count)]
            merged={}
            for group_index,(weight,rows) in enumerate(zip((1,1,2),groups)):
                for rank,row in enumerate(rows):
                    entry=merged.setdefault(row['chunk_id'],[dict(row),0,[]]); entry[1]+=weight/(61+rank)
                    if group_index==0: evidence=max(0.0,min(1.0,float(row.get('semantic_score') or 0)))
                    elif group_index==1:
                        lexical=max(0.0,float(row.get('lexical_score') or 0)); evidence=lexical/(lexical+0.1) if lexical else 0.0
                    else: evidence=1.0
                    entry[2].append(evidence)
            result=[]
            for row,score,evidence in sorted(merged.values(),key=lambda x:x[1],reverse=True):
                relevance=min(1.0,max(evidence,default=0.0)+(0.05 if sum(x>0 for x in evidence)>1 else 0.0))
                if relevance < self.min_relevance: continue
                row['rrf_score']=score; row['relevance_score']=relevance; result.append(row)
                if len(result)>=limit: break
            self.last_warning=''; return result
        except Exception:
            self.last_warning='Vector retrieval unavailable; fallback search used.'; logging.getLogger(__name__).warning(self.last_warning)
            return self.fallback(site_id,query,limit) if self.fallback else []

def configured_store(fallback=None):
    url=os.getenv('EASIIO_RAG_DATABASE_URL','')
    if not url: return None
    embedding=OpenAIEmbeddingClient(); return HybridRagStore(PsycopgAdapter(url),embedding,fallback)
