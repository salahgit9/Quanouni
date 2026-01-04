-- FORCE SCHEMA CACHE REFRESH (The Hard Way)
-- ===========================================

-- 1. Add a dummy column (Forces schema update)
ALTER TABLE chunk ADD COLUMN IF NOT EXISTS _force_refresh_cache TEXT;

-- 2. Drop the dummy column (Forces schema update again)
ALTER TABLE chunk DROP COLUMN IF EXISTS _force_refresh_cache;

-- 3. Notify again just in case
NOTIFY pgrst, 'reload config';
