# Phase 1 Task 3: Data Migration Strategy

This directory contains all the scripts and documentation needed to execute the Phase 1 Task 3 data migration for the Blue Deer Trading Supabase database.

## Overview

This migration restructures how options strategy legs are stored by:
1. Adding `user_id` columns to `trades` and `options_strategy_trades` tables
2. Creating a new `options_strategy_legs` table to link individual trades to strategies
3. Parsing the `legs` text column from `options_strategy_trades` and creating normalized trade records
4. Creating lookup tables for trade types and statuses (optional)

## Files Created

### Migration Files
- `migrations/20250117000001_phase1_task3_schema_migration.sql` - Schema changes
- `scripts/data_migration.py` - Python script for data migration
- `scripts/backup_database.sh` - Database backup script
- `scripts/validate_migration.sql` - Validation queries
- `scripts/rollback_migration.sql` - Rollback script (emergency use)
- `scripts/run_migration.sh` - Master orchestration script

## Prerequisites

1. **Supabase CLI** installed and configured
2. **Python 3** with `psycopg2` package
3. **Database backup** (automatically created by the scripts)
4. **Preview branch access** to your Supabase database

## Quick Start

### Step 0: Set Up Test Data (Required for Preview Branch)

Since you're working on a preview branch with no data, first copy some test data from production:

```bash
cd supabase
export PREVIEW_PROJECT_REF="your_preview_project_ref"
chmod +x scripts/copy_prod_test_data.sh
./scripts/copy_prod_test_data.sh
```

### Option 1: Automated Migration (Recommended)

Run the master script that handles everything:

```bash
cd supabase
export SUPABASE_PROJECT_REF="your_preview_project_ref"  # Use preview branch
chmod +x scripts/run_migration.sh
./scripts/run_migration.sh
```

### Option 2: Manual Step-by-Step

If you prefer to run each step manually:

```bash
cd supabase

# 1. Create backup
chmod +x scripts/backup_database.sh
./scripts/backup_database.sh

# 2. Apply schema migration
supabase db push --project-ref YOUR_PROJECT_REF

# 3. Run data migration
export DATABASE_URL="your_database_connection_string"
export DEFAULT_USER_ID="default_user"
cd scripts
python3 data_migration.py
cd ..

# 4. Validate results
supabase db shell --project-ref YOUR_PROJECT_REF < scripts/validate_migration.sql
```

## Configuration

### Environment Variables

- `SUPABASE_PROJECT_REF` - Your Supabase project reference (default: hsnppengoffvgtnifceo)
- `DEFAULT_USER_ID` - Default user ID for existing records (default: NULL, since no user system exists yet)
- `DATABASE_URL` - PostgreSQL connection string (auto-detected if not set)

### Customization

Before running the migration, you may want to customize:

1. **Default User ID**: Since no user system exists yet, user_id will remain NULL for existing records
2. **Legs Data Format**: The script is configured for your JSON legs format: `[{"symbol": "SPXW", "strike": 5875, ...}, ...]`
3. **Preview Branch Setup**: Use the `copy_prod_test_data.sh` script to populate your preview branch with test data

## Migration Process Details

### Step 1: Schema Changes
- Adds `user_id` columns to existing tables
- Creates `options_strategy_legs` junction table
- Creates lookup tables for trade types and statuses
- Creates backup table for original legs data

### Step 2: Data Migration
- Assigns default user IDs to existing records
- Parses `legs` column from `options_strategy_trades`
- Creates individual trade records for each leg
- Links trades to strategies via `options_strategy_legs` table
- Preserves leg sequence order

### Step 3: Validation
- Verifies table structure
- Checks data integrity
- Validates foreign key relationships
- Compares before/after data counts

## Safety Features

1. **Automatic Backup**: Full database backup created before migration
2. **Transaction Safety**: Each strategy processed in its own transaction
3. **Rollback Script**: Complete rollback capability
4. **Validation**: Comprehensive post-migration validation
5. **Trigger Management**: Temporarily disables triggers during migration

## Post-Migration Tasks

After successful migration:

1. **Test Your Application**: Verify all functionality works with the new schema
2. **Update Application Code**: Modify queries to use the new `options_strategy_legs` table
3. **Remove Backup Data**: Once confident, you can drop the backup tables
4. **Update Documentation**: Update your API documentation and ERD

## Schema Changes Summary

### New Tables

```sql
-- Junction table for strategy-leg relationships
CREATE TABLE options_strategy_legs (
    strategy_leg_id VARCHAR PRIMARY KEY,
    strategy_id TEXT REFERENCES options_strategy_trades(strategy_id),
    trade_id VARCHAR REFERENCES trades(trade_id),
    leg_sequence INTEGER,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Lookup tables (optional)
CREATE TABLE trade_types (
    id SERIAL PRIMARY KEY,
    type_name VARCHAR UNIQUE
);

CREATE TABLE trade_statuses (
    id SERIAL PRIMARY KEY,
    status_name VARCHAR UNIQUE
);
```

### Modified Tables

```sql
-- Added to trades table
ALTER TABLE trades ADD COLUMN user_id VARCHAR;

-- Added to options_strategy_trades table  
ALTER TABLE options_strategy_trades ADD COLUMN user_id VARCHAR;

-- The 'legs' column will be removed after successful migration
```

## Querying the New Schema

### Get all legs for a strategy
```sql
SELECT t.* 
FROM options_strategy_legs osl
JOIN trades t ON osl.trade_id = t.trade_id
WHERE osl.strategy_id = 'your_strategy_id'
ORDER BY osl.leg_sequence;
```

### Get strategy for a specific trade
```sql
SELECT ost.*
FROM options_strategy_trades ost
JOIN options_strategy_legs osl ON ost.strategy_id = osl.strategy_id
WHERE osl.trade_id = 'your_trade_id';
```

## Troubleshooting

### Common Issues

1. **Connection Issues**: Ensure you're linked to the correct Supabase project
2. **Permission Errors**: Make sure your database user has sufficient privileges
3. **Data Format Issues**: Check the format of your `legs` column data
4. **Trigger Conflicts**: The script handles trigger management automatically

### Recovery

If something goes wrong:

```bash
# Run the rollback script
supabase db shell --project-ref YOUR_PROJECT_REF < scripts/rollback_migration.sql

# Restore from backup if needed
supabase db push --project-ref YOUR_PROJECT_REF < backups/TIMESTAMP/full_backup.sql
```

### Log Files

- Migration logs are saved as `migration_TIMESTAMP.log` in the scripts directory
- Check these files for detailed error information

## Validation Queries

The validation script checks:
- ✅ New tables exist
- ✅ Columns added correctly  
- ✅ Data migrated successfully
- ✅ Foreign key integrity
- ✅ Trigger status
- ✅ No orphaned records

## Support

If you encounter issues:

1. Check the log files for detailed error messages
2. Run the validation script to identify specific problems
3. Use the rollback script if you need to revert changes
4. Ensure your `legs` data format matches expectations

## Next Steps

After this migration, you'll be ready for:
- Enhanced multi-user support
- More flexible options strategy modeling
- Better data normalization and querying
- Simplified application code for strategy management 