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
