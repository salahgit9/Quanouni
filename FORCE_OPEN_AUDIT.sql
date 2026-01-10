-- ============================================
-- FORCE OPEN AUDIT LOGS (Debugging Mode)
-- ============================================

-- 1. Disable Row Level Security on audit_logs table
-- This removes ALL restrictions on who can insert/read this table.
-- Since this is a log table, we can secure it later, but priority is to get it working.
ALTER TABLE audit_logs DISABLE ROW LEVEL SECURITY;

-- 2. Grant permissions to everyone (Anon and Authenticated)
GRANT ALL ON TABLE audit_logs TO anon, authenticated, service_role;

-- 3. (Optional) If you want to keep RLS enabled but just fix it:
-- Uncomment the below lines and Comment step 1 & 2
/*
ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Allow All" ON audit_logs;
CREATE POLICY "Allow All" ON audit_logs FOR ALL TO PUBLIC USING (true) WITH CHECK (true);
*/
