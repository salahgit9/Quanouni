-- FIX: Allow Insertion on Data Tables for Ingestion Script
-- ========================================================

-- Enable INSERT for 'documents' table
DROP POLICY IF EXISTS "Allow insert documents" ON documents;
CREATE POLICY "Allow insert documents" ON documents
    FOR INSERT 
    WITH CHECK (true);

-- Enable INSERT for 'chunk' table
DROP POLICY IF EXISTS "Allow insert chunks" ON chunk;
CREATE POLICY "Allow insert chunks" ON chunk
    FOR INSERT 
    WITH CHECK (true);

-- Ensure we can select them too (for search)
DROP POLICY IF EXISTS "Allow public select documents" ON documents;
CREATE POLICY "Allow public select documents" ON documents
    FOR SELECT 
    USING (true);

DROP POLICY IF EXISTS "Allow public select chunks" ON chunk;
CREATE POLICY "Allow public select chunks" ON chunk
    FOR SELECT 
    USING (true);
