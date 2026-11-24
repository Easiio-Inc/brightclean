CREATE EXTENSION IF NOT EXISTS vector;
CREATE TABLE IF NOT EXISTS rag_documents (
 site_id text NOT NULL, document_id text NOT NULL, title text NOT NULL DEFAULT '', source_url text NOT NULL DEFAULT '',
 original_filename text NOT NULL DEFAULT '', stored_filename text NOT NULL DEFAULT '', mime_type text NOT NULL DEFAULT '',
 content_hash text NOT NULL, metadata jsonb NOT NULL DEFAULT '{}'::jsonb, created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now(),
 PRIMARY KEY(site_id,document_id)
);
CREATE TABLE IF NOT EXISTS rag_chunks (
 site_id text NOT NULL, document_id text NOT NULL, chunk_id text NOT NULL, chunk_index integer NOT NULL,
 title text NOT NULL DEFAULT '', content text NOT NULL, content_hash text NOT NULL, embedding vector(1536) NOT NULL,
 embedding_model text NOT NULL, metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
 search_vector tsvector GENERATED ALWAYS AS (to_tsvector('english',coalesce(title,'')||' '||content)) STORED,
 PRIMARY KEY(site_id,chunk_id), FOREIGN KEY(site_id,document_id) REFERENCES rag_documents(site_id,document_id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS rag_chunks_search_idx ON rag_chunks USING gin(search_vector);
CREATE INDEX IF NOT EXISTS rag_chunks_embedding_idx ON rag_chunks USING hnsw(embedding vector_cosine_ops);
CREATE INDEX IF NOT EXISTS rag_chunks_tenant_document_idx ON rag_chunks(site_id,document_id);
