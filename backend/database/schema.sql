-- LifeMemory AI Database Schema
-- Run this in your Supabase SQL editor to set up the database

-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Journals table (one entry per user per day)
CREATE TABLE IF NOT EXISTS journals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    entry_date DATE NOT NULL,
    content TEXT NOT NULL,
    mood TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    UNIQUE (user_id, entry_date)  -- Enforce one entry per day per user
);

-- Journal embeddings table (derived data, one per user per day)
CREATE TABLE IF NOT EXISTS journal_embeddings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    journal_id UUID NOT NULL REFERENCES journals(id) ON DELETE CASCADE,
    user_id UUID NOT NULL,
    entry_date DATE NOT NULL,
    embedding vector(1024), -- Cohere embed-v3 uses 1024 dimensions
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    UNIQUE(journal_id), -- One embedding per journal
    UNIQUE(user_id, entry_date) -- CRITICAL: Enforce one embedding per user per day
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_journals_user_id ON journals(user_id);
CREATE INDEX IF NOT EXISTS idx_journals_entry_date ON journals(entry_date DESC);
CREATE INDEX IF NOT EXISTS idx_journals_user_entry_date ON journals(user_id, entry_date DESC);
CREATE INDEX IF NOT EXISTS idx_journal_embeddings_user_id ON journal_embeddings(user_id);
CREATE INDEX IF NOT EXISTS idx_journal_embeddings_journal_id ON journal_embeddings(journal_id);
CREATE INDEX IF NOT EXISTS idx_journal_embeddings_entry_date ON journal_embeddings(entry_date);
CREATE INDEX IF NOT EXISTS idx_journal_embeddings_user_entry_date ON journal_embeddings(user_id, entry_date);

-- Enable Row Level Security (RLS)
ALTER TABLE journals ENABLE ROW LEVEL SECURITY;
ALTER TABLE journal_embeddings ENABLE ROW LEVEL SECURITY;

-- RLS Policies for journals table (simplified - one policy for all operations)
DROP POLICY IF EXISTS "Users can view own journals" ON journals;
DROP POLICY IF EXISTS "Users can insert own journals" ON journals;
DROP POLICY IF EXISTS "Users can update own journals" ON journals;
DROP POLICY IF EXISTS "Users can delete own journals" ON journals;

CREATE POLICY "user_owns_journals"
    ON journals
    FOR ALL
    USING (user_id = auth.uid())
    WITH CHECK (user_id = auth.uid());

-- RLS Policies for journal_embeddings table (simplified - one policy for all operations)
DROP POLICY IF EXISTS "Users can view own embeddings" ON journal_embeddings;
DROP POLICY IF EXISTS "Users can insert own embeddings" ON journal_embeddings;
DROP POLICY IF EXISTS "Users can update own embeddings" ON journal_embeddings;
DROP POLICY IF EXISTS "Users can delete own embeddings" ON journal_embeddings;

CREATE POLICY "user_owns_embeddings"
    ON journal_embeddings
    FOR ALL
    USING (user_id = auth.uid())
    WITH CHECK (user_id = auth.uid());

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Trigger to automatically update updated_at
DROP TRIGGER IF EXISTS update_journals_updated_at ON journals;
CREATE TRIGGER update_journals_updated_at
    BEFORE UPDATE ON journals
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
