-- ============================================
-- AUDIT LOGGING SYSTEM (v1.5)
-- ============================================

-- 1. Create Audit Logs Table
CREATE TABLE IF NOT EXISTS audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    username TEXT, -- Denormalized username for easier reading
    action TEXT NOT NULL, -- e.g., 'SEARCH', 'CONSULT', 'LOGIN'
    resource TEXT, -- e.g., 'case:123'
    details JSONB DEFAULT '{}'::jsonb, -- Store query text here
    ip_address TEXT,
    timestamp TIMESTAMPTZ DEFAULT NOW()
);

-- 2. Indexes for Performance
CREATE INDEX IF NOT EXISTS idx_audit_user_time ON audit_logs(user_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_audit_action ON audit_logs(action);

-- 3. Row Level Security (RLS)
ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY;

-- Policy: Only Admins can VIEW logs
CREATE POLICY "Admins can view all logs" ON audit_logs
    FOR SELECT USING (
        auth.uid() IN (SELECT id FROM users WHERE role = 'admin')
    );

-- Policy: Anyone (authenticated) can INSERT logs (System uses service role usually, but this allows app usage)
-- Or better: Open for all authentified users to insert their *own* logs?
-- Actually, the backend will insert using the service role or the user's role.
-- Let's allow insert for all authenticated users for now so the API can write to it.
CREATE POLICY "Users can insert logs" ON audit_logs
    FOR INSERT WITH CHECK (true);
