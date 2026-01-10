-- ============================================
-- FIX: AUDIT LOGS PERMISSIONS
-- ============================================

-- 1. Remove old policies that might be conflicting or too restrictive
DROP POLICY IF EXISTS "Users can insert logs" ON audit_logs;
DROP POLICY IF EXISTS "Allow anon insert" ON audit_logs;

-- 2. Create a Permissive INSERT Policy
-- This allows both 'anon' (unauthenticated backend calls) and 'authenticated' users to insert logs.
-- Essential for logging "Login Failed" events.
CREATE POLICY "Allow All Insert" ON audit_logs
FOR INSERT
TO PUBLIC
WITH CHECK (true);

-- 3. Verify RLS is enabled (should be, but just in case)
ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY;
