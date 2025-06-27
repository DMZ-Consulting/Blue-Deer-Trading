#!/bin/bash

# Configuration file for Phase 1 Task 3 Migration
# Set your project references here, then source this file before running scripts

# =============================================================================
# PROJECT REFERENCES - UPDATE THESE WITH YOUR ACTUAL PROJECT IDs
# =============================================================================

# Production Supabase project reference (where your live data is)
export PROD_PROJECT_REF="hsnppengoffvgtnifceo"

# Preview/Development Supabase project reference (where you'll test the migration)
export PREVIEW_PROJECT_REF="wrdcvjcglejufqhumitd"

export PREVIEW_DB_URL="postgresql://postgres.wrdcvjcglejufqhumitd:vqf0dby.zqa!gbd!JZX@aws-0-us-east-1.pooler.supabase.com:5432/postgres"
export PROD_DB_URL="postgresql://postgres.hsnppengoffvgtnifceo:vqf0dby.zqa!gbd!JZX@aws-0-us-east-1.pooler.supabase.com:5432/postgres"

# =============================================================================
# MIGRATION SETTINGS
# =============================================================================

# Which project to run the migration against (should be preview for testing)
export SUPABASE_PROJECT_REF="$PREVIEW_PROJECT_REF"

# Default user ID for existing records (NULL since no user system exists yet)
export DEFAULT_USER_ID=""

# =============================================================================
# USAGE INSTRUCTIONS
# =============================================================================
#
# 1. Update PREVIEW_PROJECT_REF above with your actual preview project reference
# 2. Source this file: source scripts/config.sh
# 3. Run the data copy script: ./scripts/copy_prod_test_data.sh
# 4. Run the migration: ./scripts/run_migration.sh
#
# Or run everything at once:
# source scripts/config.sh && ./scripts/copy_prod_test_data.sh && ./scripts/run_migration.sh
#

echo "✅ Migration configuration loaded:"
echo "   Production Project: $PROD_PROJECT_REF"
echo "   Preview Project: $PREVIEW_PROJECT_REF"
echo "   Migration Target: $SUPABASE_PROJECT_REF"
echo "   Default User ID: ${DEFAULT_USER_ID:-NULL}"
echo ""
echo "📝 Next steps:"
echo "   1. Update PREVIEW_PROJECT_REF in scripts/config.sh if needed"
echo "   2. Run: ./scripts/copy_prod_test_data.sh"
echo "   3. Run: ./scripts/run_migration.sh"
echo "" 