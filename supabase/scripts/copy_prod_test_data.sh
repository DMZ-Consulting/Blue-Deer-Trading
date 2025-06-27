#!/bin/bash

# Script to copy test data from production to preview branch
# This helps test the migration scripts with real data structure

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_message() {
    local color=$1
    local message=$2
    echo -e "${color}${message}${NC}"
}

# Configuration
PROD_PROJECT_REF="${PROD_PROJECT_REF:-hsnppengoffvgtnifceo}"
PREVIEW_PROJECT_REF="${PREVIEW_PROJECT_REF:-}"
TEMP_DIR="./temp_prod_data"

print_message "$BLUE" "=== Copying Test Data from Production ==="
echo ""

# Check if preview project ref is provided
if [[ -z "$PREVIEW_PROJECT_REF" ]]; then
    print_message "$RED" "Error: PREVIEW_PROJECT_REF environment variable is required"
    print_message "$YELLOW" "Set it with: export PREVIEW_PROJECT_REF=your_preview_project_ref"
    exit 1
fi

print_message "$YELLOW" "Production Project: $PROD_PROJECT_REF"
print_message "$YELLOW" "Preview Project: $PREVIEW_PROJECT_REF"
echo ""

# Create temp directory
mkdir -p "$TEMP_DIR"

# Tables to copy (with limited data for testing)
TABLES=("trades" "options_strategy_trades" "options_strategy_transactions" "transactions")

print_message "$YELLOW" "Step 1: Extracting test data from production..."

for table in "${TABLES[@]}"; do
    print_message "$YELLOW" "Extracting sample data from $table..."
    
    case $table in
        "trades")
            # Get a representative sample of trades
            supabase db shell --project-ref "$PROD_PROJECT_REF" --command "
                \copy (
                    SELECT * FROM public.trades 
                    WHERE created_at >= NOW() - INTERVAL '30 days'
                    ORDER BY created_at DESC 
                    LIMIT 50
                ) TO STDOUT WITH CSV HEADER
            " > "$TEMP_DIR/${table}_sample.csv"
            ;;
        "options_strategy_trades")
            # Get options strategies with legs data
            supabase db shell --project-ref "$PROD_PROJECT_REF" --command "
                \copy (
                    SELECT * FROM public.options_strategy_trades 
                    WHERE legs IS NOT NULL AND legs != ''
                    ORDER BY created_at DESC 
                    LIMIT 20
                ) TO STDOUT WITH CSV HEADER
            " > "$TEMP_DIR/${table}_sample.csv"
            ;;
        "options_strategy_transactions")
            # Get related strategy transactions
            supabase db shell --project-ref "$PROD_PROJECT_REF" --command "
                \copy (
                    SELECT ost.* FROM public.options_strategy_transactions ost
                    JOIN public.options_strategy_trades ostrades ON ost.strategy_id = ostrades.strategy_id
                    WHERE ostrades.legs IS NOT NULL AND ostrades.legs != ''
                    ORDER BY ost.created_at DESC 
                    LIMIT 100
                ) TO STDOUT WITH CSV HEADER
            " > "$TEMP_DIR/${table}_sample.csv"
            ;;
        "transactions")
            # Get related transactions
            supabase db shell --project-ref "$PROD_PROJECT_REF" --command "
                \copy (
                    SELECT t.* FROM public.transactions t
                    JOIN public.trades tr ON t.trade_id = tr.trade_id
                    WHERE tr.created_at >= NOW() - INTERVAL '30 days'
                    ORDER BY t.created_at DESC 
                    LIMIT 200
                ) TO STDOUT WITH CSV HEADER
            " > "$TEMP_DIR/${table}_sample.csv"
            ;;
    esac
    
    if [[ -f "$TEMP_DIR/${table}_sample.csv" ]] && [[ -s "$TEMP_DIR/${table}_sample.csv" ]]; then
        RECORD_COUNT=$(tail -n +2 "$TEMP_DIR/${table}_sample.csv" | wc -l)
        print_message "$GREEN" "✓ Extracted $RECORD_COUNT records from $table"
    else
        print_message "$YELLOW" "⚠ No data extracted for $table"
    fi
done

echo ""
print_message "$YELLOW" "Step 2: Loading test data into preview branch..."

# Load data into preview branch
for table in "${TABLES[@]}"; do
    if [[ -f "$TEMP_DIR/${table}_sample.csv" ]] && [[ -s "$TEMP_DIR/${table}_sample.csv" ]]; then
        print_message "$YELLOW" "Loading data into preview $table..."
        
        # Create a SQL script to load the data
        cat > "$TEMP_DIR/load_${table}.sql" << EOF
-- Clear existing data first
TRUNCATE TABLE public.$table CASCADE;

-- Load the CSV data
\copy public.$table FROM '$PWD/$TEMP_DIR/${table}_sample.csv' WITH CSV HEADER;
EOF
        
        supabase db shell --project-ref "$PREVIEW_PROJECT_REF" < "$TEMP_DIR/load_${table}.sql"
        
        if [[ $? -eq 0 ]]; then
            print_message "$GREEN" "✓ Loaded $table data into preview"
        else
            print_message "$RED" "✗ Failed to load $table data"
        fi
    fi
done

echo ""
print_message "$YELLOW" "Step 3: Verifying data in preview branch..."

# Verify the data was loaded
supabase db shell --project-ref "$PREVIEW_PROJECT_REF" --command "
SELECT 
    'trades' as table_name,
    COUNT(*) as record_count
FROM public.trades
UNION ALL
SELECT 
    'options_strategy_trades' as table_name,
    COUNT(*) as record_count
FROM public.options_strategy_trades
UNION ALL
SELECT 
    'options_strategy_transactions' as table_name,
    COUNT(*) as record_count
FROM public.options_strategy_transactions
UNION ALL
SELECT 
    'transactions' as table_name,
    COUNT(*) as record_count
FROM public.transactions;
"

echo ""
print_message "$YELLOW" "Sample legs data from preview branch:"
supabase db shell --project-ref "$PREVIEW_PROJECT_REF" --command "
SELECT 
    strategy_id,
    LEFT(legs, 100) || '...' as legs_sample
FROM public.options_strategy_trades 
WHERE legs IS NOT NULL AND legs != ''
LIMIT 3;
"

# Cleanup temp files
print_message "$YELLOW" "Cleaning up temporary files..."
rm -rf "$TEMP_DIR"

echo ""
print_message "$GREEN" "=== Test Data Copy Complete ==="
print_message "$YELLOW" "Your preview branch now has sample data to test the migration!"
print_message "$YELLOW" "You can now run: ./scripts/run_migration.sh"
echo "" 