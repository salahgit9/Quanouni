-- ============================================
-- QANOUNI-AI: Cases Management Schema
-- Purpose: Store legal cases for "Advocate Mode"
-- ============================================

-- Create Cases Table
CREATE TABLE IF NOT EXISTS cases (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_number TEXT NOT NULL,
    case_type TEXT NOT NULL,
    court TEXT NOT NULL,
    status TEXT DEFAULT 'جاري',
    
    -- Structured Data
    defendant_name TEXT,
    plaintiff_name TEXT,
    charges TEXT[],
    facts TEXT, -- Summary facts
    
    -- Rich Data (JSONB for flexibility)
    parties JSONB DEFAULT '{}'::jsonb,      -- Detailed parties info (lawyer, victim...)
    evidence JSONB DEFAULT '{}'::jsonb,     -- Prosecution vs Defense evidence
    timeline JSONB DEFAULT '[]'::jsonb,     -- Events chronological order
    defense_strategy JSONB DEFAULT '{}'::jsonb, -- Arguments, articles, jurisprudence
    
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Metadata
    source_file TEXT -- Original JSON filename
);

-- Indexes
CREATE INDEX IF NOT EXISTS cases_case_number_idx ON cases(case_number);
CREATE INDEX IF NOT EXISTS cases_defendant_idx ON cases(defendant_name);

-- RLS (Row Level Security)
ALTER TABLE cases ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Enable all access for demo" ON cases FOR ALL USING (true);
