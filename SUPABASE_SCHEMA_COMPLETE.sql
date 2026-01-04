-- ============================================
-- QANOUNI-AI: Complete Supabase Schema
-- Version: 1.2 (Hybrid Architecture)
-- Date: 2026-01-04
-- ============================================

-- 1. Enable Required Extensions
-- ============================================
CREATE EXTENSION IF NOT EXISTS vector;

-- 2. Documents Table (معلومات الوثائق)
-- ============================================
CREATE TABLE IF NOT EXISTS documents (
    id BIGSERIAL PRIMARY KEY,
    filename TEXT NOT NULL,
    category TEXT DEFAULT 'law',
    upload_date TIMESTAMPTZ DEFAULT NOW(),
    total_chunks INTEGER DEFAULT 0,
    metadata JSONB DEFAULT '{}'::jsonb
);

-- 3. Chunks Table (أجزاء النصوص + الـ Embeddings)
-- ============================================
CREATE TABLE IF NOT EXISTS chunk (
    id BIGSERIAL PRIMARY KEY,
    document_id BIGINT REFERENCES documents(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    embedding VECTOR(768),  -- Google Gemini embedding dimension
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 4. Indexes for Performance
-- ============================================
-- Vector similarity search index (HNSW is faster than IVF for small datasets)
CREATE INDEX IF NOT EXISTS chunk_embedding_idx 
ON chunk USING hnsw (embedding vector_cosine_ops);

-- Text search index (for BM25 fallback - optional)
CREATE INDEX IF NOT EXISTS chunk_content_idx 
ON chunk USING gin (to_tsvector('simple', content));

-- Foreign key index
CREATE INDEX IF NOT EXISTS chunk_document_id_idx 
ON chunk (document_id);

-- 5. Vector Search Function (البحث الشعاعي)
-- ============================================
CREATE OR REPLACE FUNCTION match_documents(
    query_embedding VECTOR(768),
    match_count INT DEFAULT 10,
    filter_category TEXT DEFAULT NULL
)
RETURNS TABLE (
    id BIGINT,
    content TEXT,
    metadata JSONB,
    similarity FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        c.id,
        c.content,
        c.metadata,
        1 - (c.embedding <=> query_embedding) AS similarity
    FROM chunk c
    JOIN documents d ON c.document_id = d.id
    WHERE (filter_category IS NULL OR d.category = filter_category)
    ORDER BY c.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

-- 6. Cases Table (القضايا - للمرافعات)
-- ============================================
CREATE TABLE IF NOT EXISTS cases (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_number TEXT NOT NULL,
    case_type TEXT NOT NULL,
    court TEXT NOT NULL,
    defendant_name TEXT,
    plaintiff_name TEXT,
    charges TEXT[],
    facts TEXT,
    notes TEXT,
    status TEXT DEFAULT 'جاري',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 7. Users Table (المستخدمين - اختياري للمصادقة)
-- ============================================
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    full_name TEXT,
    email TEXT,
    role TEXT DEFAULT 'normal',  -- 'normal' or 'premium'
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 8. Permissions (صلاحيات RLS - Row Level Security)
-- ============================================
-- Enable RLS
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE chunk ENABLE ROW LEVEL SECURITY;
ALTER TABLE cases ENABLE ROW LEVEL SECURITY;

-- Allow all for anon key (for demo - tighten for production)
CREATE POLICY "Allow all for documents" ON documents FOR ALL USING (true);
CREATE POLICY "Allow all for chunks" ON chunk FOR ALL USING (true);
CREATE POLICY "Allow all for cases" ON cases FOR ALL USING (true);

-- ============================================
-- DONE! Now run the ingestion script.
-- ============================================
