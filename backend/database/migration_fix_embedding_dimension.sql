-- Migration: Fix embedding dimension from 3072 to 1024 (for Cohere)
-- Run this if you see "expected 3072 dimensions, not 1024" error
-- This is a standalone fix that can be run independently

-- Step 1: Delete all existing embeddings (they're incompatible with new dimension)
-- WARNING: This will delete all embeddings. They will be regenerated automatically 
-- when you save journal entries (background task will recreate them).
DELETE FROM journal_embeddings;

-- Step 2: Change column dimension from 3072 to 1024
ALTER TABLE journal_embeddings 
ALTER COLUMN embedding TYPE vector(1024);

-- Step 3: Verify the change
DO $$
DECLARE
    current_dim INTEGER;
BEGIN
    -- Get the dimension from pg_attribute
    SELECT (atttypmod - 4) / 4 INTO current_dim
    FROM pg_attribute 
    WHERE attrelid = 'journal_embeddings'::regclass 
    AND attname = 'embedding';
    
    IF current_dim = 1024 THEN
        RAISE NOTICE 'Successfully updated embedding column to vector(1024)';
    ELSE
        RAISE WARNING 'Embedding dimension is still % (expected 1024)', current_dim;
    END IF;
END $$;
