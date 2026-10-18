-- Migration: Add entry_date column and enforce single-entry-per-day
-- Run this in your Supabase SQL editor AFTER running the main schema.sql

-- Step 1: Add entry_date column to journals (if not exists)
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'journals' AND column_name = 'entry_date'
    ) THEN
        ALTER TABLE journals ADD COLUMN entry_date DATE;
        
        -- Populate entry_date from created_at for existing records
        UPDATE journals SET entry_date = DATE(created_at) WHERE entry_date IS NULL;
        
        -- Make entry_date NOT NULL after populating
        ALTER TABLE journals ALTER COLUMN entry_date SET NOT NULL;
    END IF;
END $$;

-- Step 2: Add entry_date column to journal_embeddings (if not exists)
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'journal_embeddings' AND column_name = 'entry_date'
    ) THEN
        ALTER TABLE journal_embeddings ADD COLUMN entry_date DATE;
        
        -- Populate entry_date from journals table
        UPDATE journal_embeddings je
        SET entry_date = (
            SELECT DATE(j.created_at)
            FROM journals j
            WHERE j.id = je.journal_id
        )
        WHERE entry_date IS NULL;
        
        -- Make entry_date NOT NULL after populating
        ALTER TABLE journal_embeddings ALTER COLUMN entry_date SET NOT NULL;
    END IF;
END $$;

-- Step 3: Add unique constraint (one entry per user per day)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'journals_user_id_entry_date_key'
    ) THEN
        -- First, remove any duplicate entries (keep the most recent)
        DELETE FROM journals j1
        WHERE EXISTS (
            SELECT 1 FROM journals j2
            WHERE j2.user_id = j1.user_id
            AND DATE(j2.created_at) = DATE(j1.created_at)
            AND j2.id != j1.id
            AND j2.created_at > j1.created_at
        );
        
        ALTER TABLE journals ADD CONSTRAINT journals_user_id_entry_date_key 
            UNIQUE (user_id, entry_date);
    END IF;
END $$;

-- Step 4: Add unique constraint on embeddings (one per user per day)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'journal_embeddings_user_id_entry_date_key'
    ) THEN
        -- First, remove any duplicate embeddings (keep the most recent)
        DELETE FROM journal_embeddings je1
        WHERE EXISTS (
            SELECT 1 FROM journal_embeddings je2
            WHERE je2.user_id = je1.user_id
            AND je2.entry_date = je1.entry_date
            AND je2.id != je1.id
            AND je2.created_at > je1.created_at
        );
        
        ALTER TABLE journal_embeddings ADD CONSTRAINT journal_embeddings_user_id_entry_date_key 
            UNIQUE (user_id, entry_date);
    END IF;
END $$;

-- Step 5: Update embedding column dimension from 3072 to 1024 (for Cohere)
-- First, delete all existing embeddings (they're incompatible with new dimension)
-- They will be regenerated automatically when journals are saved
DELETE FROM journal_embeddings;

-- Change column dimension from 3072 to 1024
ALTER TABLE journal_embeddings 
ALTER COLUMN embedding TYPE vector(1024);

-- Step 6: Add indexes for entry_date
CREATE INDEX IF NOT EXISTS idx_journals_entry_date ON journals(entry_date DESC);
CREATE INDEX IF NOT EXISTS idx_journals_user_entry_date ON journals(user_id, entry_date DESC);
CREATE INDEX IF NOT EXISTS idx_journal_embeddings_entry_date ON journal_embeddings(entry_date);
CREATE INDEX IF NOT EXISTS idx_journal_embeddings_user_entry_date ON journal_embeddings(user_id, entry_date);

