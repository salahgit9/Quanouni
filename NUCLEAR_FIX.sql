-- NUCLEAR FIX: Recreate Chunk Table
-- =================================

-- 1. Drop the table (and its dependents)
DROP TABLE IF EXISTS chunk CASCADE;

-- 2. Recreate it with the metadata column explicitly
CREATE TABLE chunk (
    id BIGSERIAL PRIMARY KEY,
    document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    embedding VECTOR(768),
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 3. Re-enable RLS
ALTER TABLE chunk ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Allow all for chunks" ON chunk FOR ALL USING (true);

-- 4. Recreate Indexes
CREATE INDEX IF NOT EXISTS chunk_embedding_idx ON chunk USING hnsw (embedding vector_cosine_ops);
CREATE INDEX IF NOT EXISTS chunk_content_idx ON chunk USING gin (to_tsvector('simple', content));
CREATE INDEX IF NOT EXISTS chunk_document_id_idx ON chunk (document_id);

-- 5. Notify just in case
NOTIFY pgrst, 'reload config';
