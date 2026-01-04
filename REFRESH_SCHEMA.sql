-- Force PostgREST Schema Cache Reload
-- ===================================

-- Method 1: Notify channel
NOTIFY pgrst, 'reload config';

-- Method 2: Dummy comment update (triggers reload)
COMMENT ON TABLE chunk IS 'Table for document chunks with embeddings';
