#!/bin/bash

# Script to copy test data from production to preview branch
# This version works with current Supabase CLI (no db shell command)

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

print_message "$YELLOW" "Step 1: Creating sample data SQL files..."

# Create SQL files to extract sample data
cat > "$TEMP_DIR/extract_trades.sql" << 'EOF'
\copy (
    SELECT * FROM public.trades 
    WHERE created_at >= NOW() - INTERVAL '30 days'
    ORDER BY created_at DESC 
    LIMIT 50
) TO 'trades_sample.csv' WITH CSV HEADER;
EOF

cat > "$TEMP_DIR/extract_options_strategy_trades.sql" << 'EOF'
\copy (
    SELECT * FROM public.options_strategy_trades 
    WHERE legs IS NOT NULL AND legs != ''
    ORDER BY created_at DESC 
    LIMIT 20
) TO 'options_strategy_trades_sample.csv' WITH CSV HEADER;
EOF

cat > "$TEMP_DIR/extract_options_strategy_transactions.sql" << 'EOF'
\copy (
    SELECT ost.* FROM public.options_strategy_transactions ost
    JOIN public.options_strategy_trades ostrades ON ost.strategy_id = ostrades.strategy_id
    WHERE ostrades.legs IS NOT NULL AND ostrades.legs != ''
    ORDER BY ost.created_at DESC 
    LIMIT 100
) TO 'options_strategy_transactions_sample.csv' WITH CSV HEADER;
EOF

cat > "$TEMP_DIR/extract_transactions.sql" << 'EOF'
\copy (
    SELECT t.* FROM public.transactions t
    JOIN public.trades tr ON t.trade_id = tr.trade_id
    WHERE tr.created_at >= NOW() - INTERVAL '30 days'
    ORDER BY t.created_at DESC 
    LIMIT 200
) TO 'transactions_sample.csv' WITH CSV HEADER;
EOF

print_message "$GREEN" "✓ SQL extraction files created"
echo ""

# Method 1: Try using db dump with --data-only for specific tables
print_message "$YELLOW" "Step 2: Extracting sample data using Supabase CLI..."

# First, we need to get the connection strings
print_message "$YELLOW" "Getting database connection details..."

# Method 2: Use a simpler approach - create a manual data extraction script
print_message "$YELLOW" "Creating manual extraction approach..."

cat > "$TEMP_DIR/manual_extract.py" << 'EOF'
#!/usr/bin/env python3
import psycopg2
import csv
import os

def extract_data():
    # You'll need to set these environment variables with your database URLs
    prod_url = os.getenv('PROD_DB_URL')
    preview_url = os.getenv('PREVIEW_DB_URL')
    
    if not prod_url or not preview_url:
        print("Error: PROD_DB_URL and PREVIEW_DB_URL environment variables are required")
        print("Get these from your Supabase dashboard > Settings > Database")
        return False
    
    try:
        # Connect to production
        print("Connecting to production database...")
        prod_conn = psycopg2.connect(prod_url)
        prod_cur = prod_conn.cursor()
        
        # Connect to preview
        print("Connecting to preview database...")
        preview_conn = psycopg2.connect(preview_url)
        preview_cur = preview_conn.cursor()
        
        # First, we need to copy in the right order to maintain FK relationships
        # Step 1: Copy reference/lookup tables
        print("Step 1: Copying reference tables...")
        
        # Copy trade_configurations first
        prod_cur.execute("SELECT * FROM public.trade_configurations ORDER BY id")
        columns = [desc[0] for desc in prod_cur.description]
        rows = prod_cur.fetchall()
        if rows:
            preview_cur.execute("TRUNCATE TABLE public.trade_configurations CASCADE")
            placeholders = ','.join(['%s'] * len(columns))
            insert_query = f"INSERT INTO public.trade_configurations ({','.join(columns)}) VALUES ({placeholders})"
            preview_cur.executemany(insert_query, rows)
            preview_conn.commit()
            print(f"✓ Copied {len(rows)} records to trade_configurations")
        
        # Step 2: Copy main tables and collect their IDs
        print("Step 2: Copying main tables...")
        
        # Copy trades and collect trade_ids
        prod_cur.execute("""
            SELECT * FROM public.trades 
            WHERE created_at >= NOW() - INTERVAL '30 days'
            ORDER BY created_at DESC 
            LIMIT 50
        """)
        columns = [desc[0] for desc in prod_cur.description]
        trade_rows = prod_cur.fetchall()
        trade_ids = []
        
        if trade_rows:
            preview_cur.execute("TRUNCATE TABLE public.trades CASCADE")
            placeholders = ','.join(['%s'] * len(columns))
            insert_query = f"INSERT INTO public.trades ({','.join(columns)}) VALUES ({placeholders})"
            preview_cur.executemany(insert_query, trade_rows)
            preview_conn.commit()
            
            # Collect trade_ids for later use
            trade_id_index = columns.index('trade_id')
            trade_ids = [row[trade_id_index] for row in trade_rows]
            print(f"✓ Copied {len(trade_rows)} records to trades")
        
        # Copy options_strategy_trades and collect strategy_ids
        prod_cur.execute("""
            SELECT * FROM public.options_strategy_trades 
            WHERE legs IS NOT NULL AND legs != ''
            ORDER BY created_at DESC 
            LIMIT 20
        """)
        columns = [desc[0] for desc in prod_cur.description]
        strategy_rows = prod_cur.fetchall()
        strategy_ids = []
        
        if strategy_rows:
            preview_cur.execute("TRUNCATE TABLE public.options_strategy_trades CASCADE")
            placeholders = ','.join(['%s'] * len(columns))
            insert_query = f"INSERT INTO public.options_strategy_trades ({','.join(columns)}) VALUES ({placeholders})"
            preview_cur.executemany(insert_query, strategy_rows)
            preview_conn.commit()
            
            # Collect strategy_ids for later use
            strategy_id_index = columns.index('strategy_id')
            strategy_ids = [row[strategy_id_index] for row in strategy_rows]
            print(f"✓ Copied {len(strategy_rows)} records to options_strategy_trades")
        
        # Step 3: Copy transactions only for the trades/strategies we've copied
        print("Step 3: Copying related transactions...")
        
        # Copy transactions only for our copied trades
        if trade_ids:
            trade_ids_str = "', '".join(trade_ids)
            prod_cur.execute(f"""
                SELECT * FROM public.transactions 
                WHERE trade_id IN ('{trade_ids_str}')
                ORDER BY created_at DESC
            """)
            columns = [desc[0] for desc in prod_cur.description]
            transaction_rows = prod_cur.fetchall()
            
            if transaction_rows:
                preview_cur.execute("TRUNCATE TABLE public.transactions CASCADE")
                placeholders = ','.join(['%s'] * len(columns))
                insert_query = f"INSERT INTO public.transactions ({','.join(columns)}) VALUES ({placeholders})"
                preview_cur.executemany(insert_query, transaction_rows)
                preview_conn.commit()
                print(f"✓ Copied {len(transaction_rows)} records to transactions")
        
        # Copy options_strategy_transactions only for our copied strategies
        if strategy_ids:
            strategy_ids_str = "', '".join(strategy_ids)
            prod_cur.execute(f"""
                SELECT * FROM public.options_strategy_transactions 
                WHERE strategy_id IN ('{strategy_ids_str}')
                ORDER BY created_at DESC
            """)
            columns = [desc[0] for desc in prod_cur.description]
            strategy_transaction_rows = prod_cur.fetchall()
            
            if strategy_transaction_rows:
                preview_cur.execute("TRUNCATE TABLE public.options_strategy_transactions CASCADE")
                placeholders = ','.join(['%s'] * len(columns))
                insert_query = f"INSERT INTO public.options_strategy_transactions ({','.join(columns)}) VALUES ({placeholders})"
                preview_cur.executemany(insert_query, strategy_transaction_rows)
                preview_conn.commit()
                print(f"✓ Copied {len(strategy_transaction_rows)} records to options_strategy_transactions")
        
                 # Close connections
         prod_cur.close()
         prod_conn.close()
         preview_cur.close()
         preview_conn.close()
         
         print("\n✅ Data copy completed successfully!")
         return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    extract_data()
EOF

chmod +x "$TEMP_DIR/manual_extract.py"

print_message "$GREEN" "✓ Created Python extraction script"
echo ""

print_message "$BLUE" "=== Next Steps ==="
print_message "$YELLOW" "The automated extraction requires database connection strings."
print_message "$YELLOW" "Please follow these steps:"
echo ""
print_message "$YELLOW" "1. Get your database connection strings from Supabase dashboard:"
print_message "$YELLOW" "   - Go to Settings > Database"
print_message "$YELLOW" "   - Copy the 'URI' connection string for both projects"
echo ""
print_message "$YELLOW" "2. Set environment variables and run the Python script:"
echo ""
print_message "$GREEN" "export PROD_DB_URL='postgresql://...your_prod_connection_string'"
print_message "$GREEN" "export PREVIEW_DB_URL='postgresql://...your_preview_connection_string'"
print_message "$GREEN" "cd temp_prod_data && python3 manual_extract.py"
echo ""
print_message "$YELLOW" "3. After data is copied, you can run the migration:"
print_message "$GREEN" "./scripts/run_migration.sh"
echo ""

print_message "$BLUE" "Alternative: Manual approach using Supabase dashboard"
print_message "$YELLOW" "1. Export data from production using dashboard SQL editor"
print_message "$YELLOW" "2. Import the data into preview branch"
print_message "$YELLOW" "3. Run the migration script"
echo "" 