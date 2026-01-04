-- CLEANUP LAWS DATA
-- =================

-- 1. Delete all documents categorized as 'loi' (cascades to chunks)
DELETE FROM documents WHERE category = 'loi';

-- 2. Force Schema Cache Reload (Crucial for the metadata column fix)
NOTIFY pgrst, 'reload config';
