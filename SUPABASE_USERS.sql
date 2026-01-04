-- ============================================
-- QANOUNI-AI: User Management & Multi-tenancy
-- ============================================

-- 1. Create Users Table
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    full_name TEXT,
    email TEXT,
    role TEXT DEFAULT 'normal', -- 'normal', 'premium', 'admin'
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_login TIMESTAMPTZ
);

-- 2. Link Cases to Users
-- Add user_id column to existing cases table
DO $$ 
BEGIN 
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'cases' AND column_name = 'user_id') THEN
        ALTER TABLE cases ADD COLUMN user_id UUID REFERENCES users(id) ON DELETE CASCADE;
        CREATE INDEX cases_user_id_idx ON cases(user_id);
    END IF;
END $$;

-- 3. Update RLS Policies (Security)
-- Enable RLS on users
ALTER TABLE users ENABLE ROW LEVEL SECURITY;

-- Policy: Users can see only their own profile
DROP POLICY IF EXISTS "Users can see own profile" ON users;
CREATE POLICY "Users can see own profile" ON users
    FOR SELECT USING (auth.uid() = id);

-- Policy: Cases are private to the user
-- Note: usage of auth.uid() assumes we use Supabase Auth or simulate it. 
-- Since we use custom auth in Python, RLS is a second layer of defense.
-- We will enforce filtering in the API (Python) level primarily.
