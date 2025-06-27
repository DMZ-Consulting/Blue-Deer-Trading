-- Phase 1, Task 3: Rollback Script
-- This script rolls back the data migration changes if needed
-- WARNING: This will delete migrated data. Use with caution!

\echo '=== Phase 1 Task 3 Migration Rollback ==='
\echo 'WARNING: This will undo the migration and may result in data loss!'
\echo 'Make sure you have a backup before proceeding.'
\echo ''

-- Step 1: Restore the legs column if it was removed
\echo 'Step 1: Restoring legs column...'
DO $$
BEGIN
    -- Check if legs column exists
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'options_strategy_trades' 
        AND column_name = 'legs'
    ) THEN
        -- Add the legs column back
        ALTER TABLE public.options_strategy_trades ADD COLUMN legs text;
        RAISE NOTICE 'Added legs column back to options_strategy_trades';
    ELSE
        RAISE NOTICE 'Legs column already exists';
    END IF;
END $$;

-- Step 2: Restore legs data from backup
\echo 'Step 2: Restoring legs data from backup...'
UPDATE public.options_strategy_trades ost
SET legs = backup.legs
FROM public.options_strategy_trades_legs_backup backup
WHERE ost.strategy_id = backup.strategy_id;

-- Check how many records were restored
SELECT 
    COUNT(*) as records_restored
FROM public.options_strategy_trades 
WHERE legs IS NOT NULL AND legs != '';

-- Step 3: Drop the options_strategy_legs table
\echo 'Step 3: Dropping options_strategy_legs table...'
DROP TABLE IF EXISTS public.options_strategy_legs CASCADE;

-- Step 4: Remove user_id columns (optional - only if they were added in this migration)
\echo 'Step 4: Removing user_id columns...'
-- Uncomment the following lines if you want to remove user_id columns
-- ALTER TABLE public.trades DROP COLUMN IF EXISTS user_id;
-- ALTER TABLE public.options_strategy_trades DROP COLUMN IF EXISTS user_id;

-- Step 5: Drop lookup tables (optional)
\echo 'Step 5: Dropping lookup tables...'
-- Uncomment the following lines if you want to remove lookup tables
-- DROP TABLE IF EXISTS public.trade_types CASCADE;
-- DROP TABLE IF EXISTS public.trade_statuses CASCADE;

-- Step 6: Drop helper functions
\echo 'Step 6: Dropping helper functions...'
DROP FUNCTION IF EXISTS public.generate_strategy_leg_id() CASCADE;

-- Step 7: Clean up backup table (optional)
\echo 'Step 7: Cleaning up backup table...'
-- Uncomment the following line if you want to remove the backup table
-- DROP TABLE IF EXISTS public.options_strategy_trades_legs_backup CASCADE;

-- Step 8: Verification
\echo 'Step 8: Rollback verification...'
SELECT 
    'options_strategy_trades with legs' as description,
    COUNT(*) as count
FROM public.options_strategy_trades 
WHERE legs IS NOT NULL AND legs != '';

-- Check that options_strategy_legs table is gone
SELECT 
    CASE 
        WHEN COUNT(*) = 0 THEN '✓ options_strategy_legs table removed'
        ELSE '⚠ options_strategy_legs table still exists'
    END as status
FROM information_schema.tables 
WHERE table_schema = 'public' 
AND table_name = 'options_strategy_legs';

-- Check that legs column is restored
SELECT 
    CASE 
        WHEN COUNT(*) > 0 THEN '✓ legs column restored'
        ELSE '⚠ legs column missing'
    END as status
FROM information_schema.columns 
WHERE table_schema = 'public' 
AND table_name = 'options_strategy_trades' 
AND column_name = 'legs';

\echo ''
\echo '=== Rollback Complete ==='
\echo 'Please verify that your data has been restored correctly.' 