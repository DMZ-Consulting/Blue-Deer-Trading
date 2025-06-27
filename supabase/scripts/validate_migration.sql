-- Phase 1, Task 3: Data Migration Validation Script
-- This script validates the results of the data migration

-- Set up output formatting
\echo '=== Phase 1 Task 3 Migration Validation ==='
\echo ''

-- 1. Check that new tables exist
\echo '1. Checking new tables exist...'
SELECT 
    tablename, 
    CASE WHEN tablename IS NOT NULL THEN '✓ EXISTS' ELSE '✗ MISSING' END as status
FROM pg_tables 
WHERE schemaname = 'public' 
AND tablename IN ('options_strategy_legs', 'trade_types', 'trade_statuses', 'options_strategy_trades_legs_backup')
ORDER BY tablename;

\echo ''

-- 2. Check that user_id columns were added
\echo '2. Checking user_id columns were added...'
SELECT 
    table_name,
    column_name,
    is_nullable,
    data_type
FROM information_schema.columns 
WHERE table_schema = 'public' 
AND table_name IN ('trades', 'options_strategy_trades') 
AND column_name = 'user_id';

\echo ''

-- 3. Check user_id population
\echo '3. Checking user_id population...'
SELECT 
    'trades' as table_name,
    COUNT(*) as total_records,
    COUNT(user_id) as records_with_user_id,
    COUNT(*) - COUNT(user_id) as records_without_user_id
FROM public.trades
UNION ALL
SELECT 
    'options_strategy_trades' as table_name,
    COUNT(*) as total_records,
    COUNT(user_id) as records_with_user_id,
    COUNT(*) - COUNT(user_id) as records_without_user_id
FROM public.options_strategy_trades;

\echo ''

-- 4. Check options_strategy_legs table
\echo '4. Checking options_strategy_legs table structure and data...'
SELECT 
    COUNT(*) as total_strategy_legs,
    COUNT(DISTINCT strategy_id) as unique_strategies_with_legs,
    COUNT(DISTINCT trade_id) as unique_trades_linked,
    MIN(leg_sequence) as min_leg_sequence,
    MAX(leg_sequence) as max_leg_sequence
FROM public.options_strategy_legs;

\echo ''

-- 5. Check foreign key integrity
\echo '5. Checking foreign key integrity...'
-- Check for orphaned strategy_ids in options_strategy_legs
SELECT 
    'Orphaned strategy_ids' as check_type,
    COUNT(*) as count
FROM public.options_strategy_legs osl
LEFT JOIN public.options_strategy_trades ost ON osl.strategy_id = ost.strategy_id
WHERE ost.strategy_id IS NULL

UNION ALL

-- Check for orphaned trade_ids in options_strategy_legs
SELECT 
    'Orphaned trade_ids' as check_type,
    COUNT(*) as count
FROM public.options_strategy_legs osl
LEFT JOIN public.trades t ON osl.trade_id = t.trade_id
WHERE t.trade_id IS NULL;

\echo ''

-- 6. Compare before and after legs data
\echo '6. Comparing original legs data with migrated data...'
SELECT 
    'Original strategies with legs' as description,
    COUNT(*) as count
FROM public.options_strategy_trades_legs_backup
WHERE legs IS NOT NULL AND legs != ''

UNION ALL

SELECT 
    'Strategies with migrated legs' as description,
    COUNT(DISTINCT strategy_id) as count
FROM public.options_strategy_legs;

\echo ''

-- 7. Check if legs column still exists
\echo '7. Checking if legs column was removed...'
SELECT 
    CASE 
        WHEN COUNT(*) > 0 THEN '⚠ LEGS COLUMN STILL EXISTS'
        ELSE '✓ LEGS COLUMN REMOVED'
    END as status
FROM information_schema.columns 
WHERE table_schema = 'public' 
AND table_name = 'options_strategy_trades' 
AND column_name = 'legs';

\echo ''

-- 8. Sample data verification
\echo '8. Sample data verification...'
\echo 'First 5 strategy-leg relationships:'
SELECT 
    osl.strategy_id,
    osl.trade_id,
    osl.leg_sequence,
    t.symbol,
    t.trade_type,
    t.strike,
    t.option_type
FROM public.options_strategy_legs osl
JOIN public.trades t ON osl.trade_id = t.trade_id
ORDER BY osl.strategy_id, osl.leg_sequence
LIMIT 5;

\echo ''

-- 9. Data consistency checks
\echo '9. Data consistency checks...'
-- Check for strategies without legs
SELECT 
    'Strategies without legs after migration' as check_type,
    COUNT(*) as count
FROM public.options_strategy_trades ost
WHERE NOT EXISTS (
    SELECT 1 FROM public.options_strategy_legs osl 
    WHERE osl.strategy_id = ost.strategy_id
);

\echo ''

-- 10. Trigger status check
\echo '10. Checking trigger status...'
SELECT 
    schemaname,
    tablename,
    triggername,
    CASE 
        WHEN tgenabled = 'O' THEN '✓ ENABLED'
        WHEN tgenabled = 'D' THEN '⚠ DISABLED'
        ELSE '? UNKNOWN'
    END as status
FROM pg_trigger
JOIN pg_class ON pg_trigger.tgrelid = pg_class.oid
JOIN pg_namespace ON pg_class.relnamespace = pg_namespace.oid
WHERE pg_namespace.nspname = 'public'
AND pg_class.relname IN ('trades', 'transactions', 'options_strategy_trades', 'options_strategy_transactions')
AND NOT tgisinternal
ORDER BY tablename, triggername;

\echo ''
\echo '=== Validation Complete ===' 