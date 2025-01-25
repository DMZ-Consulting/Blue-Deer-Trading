import os
import sys
from sqlalchemy import create_engine, text, UniqueConstraint
from sqlalchemy.orm import sessionmaker
import json
from datetime import datetime
from typing import Dict, Any

# Add the project root to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(os.path.dirname(current_dir))
sys.path.append(backend_dir)

from backend.app.database import get_supabase, Base
from backend.app.models import (
    Trade, Transaction, TradeConfiguration, OptionsStrategyTrade,
    OptionsStrategyTransaction, VerificationConfig, Verification,
    RoleRequirement, Role, ConditionalRoleGrant, BotConfiguration
)

def serialize_datetime(obj: Any) -> Any:
    if isinstance(obj, datetime):
        return obj.isoformat()
    return obj

def get_sqlite_session():
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    db_path = os.path.join(base_dir, 'db', 'sql_app.db')
    
    if not os.path.exists(db_path):
        raise FileNotFoundError(f"SQLite database not found at {db_path}")
        
    sqlite_url = f"sqlite:///{db_path}"
    print(f"SQLite URL: {sqlite_url}")
    engine = create_engine(sqlite_url)
    Session = sessionmaker(bind=engine)
    return Session()

def get_unique_constraints(model):
    """Get all unique constraints for a model."""
    constraints = []
    
    # Add primary key columns
    pk_cols = [col.name for col in model.__table__.columns if col.primary_key]
    if pk_cols:
        constraints.append(pk_cols)
    
    # Add unique constraints
    for constraint in model.__table__.constraints:
        if isinstance(constraint, UniqueConstraint):
            constraint_cols = [col.name for col in constraint.columns]
            if constraint_cols not in constraints:
                constraints.append(constraint_cols)
    
    return constraints

def check_existing_record(supabase, table_name, record_dict, model):
    """Check if a record already exists in Supabase using all unique constraints."""
    constraints = get_unique_constraints(model)
    
    for constraint_cols in constraints:
        # Skip if any constraint column is missing from the record
        if not all(col in record_dict for col in constraint_cols):
            continue
            
        try:
            # Build query for this constraint
            query = supabase.table(table_name).select("*")
            for col in constraint_cols:
                query = query.eq(col, record_dict[col])
            
            response = query.execute()
            existing_records = response.data
            
            if len(existing_records) > 0:
                constraint_values = {col: record_dict[col] for col in constraint_cols}
                print(f"Found existing record with constraint {constraint_values}")
                return True
                
        except Exception as e:
            print(f"Error checking existing record: {str(e)}")
            return False
    
    return False

def transform_record(record_dict: Dict[str, Any], table_name: str) -> Dict[str, Any]:
    """Transform record values based on table-specific rules."""
    
    # Capitalize status and transaction_type fields
    if 'status' in record_dict:
        record_dict['status'] = record_dict['status'].upper()
    if 'transaction_type' in record_dict:
        record_dict['transaction_type'] = record_dict['transaction_type'].upper()
    
    # Handle new columns for specific tables
    if table_name == 'trades':
        # New columns in Supabase trades table
        record_dict.setdefault('average_price', record_dict.get('entry_price'))
        record_dict.setdefault('average_exit_price', None)
        record_dict.setdefault('profit_loss', None)
        record_dict.setdefault('win_loss', None)
        record_dict.setdefault('is_day_trade', False)
    
    if table_name == 'transactions':
        # New columns in Supabase transactions table
        record_dict.setdefault('net_cost', None)
    
    return record_dict

def insert_records_safely(supabase, table_name, records):
    """Insert records one by one to handle errors gracefully."""
    successful = 0
    failed = 0
    
    for record in records:
        try:
            # Transform record before insertion
            transformed_record = transform_record(record, table_name)
            response = supabase.table(table_name).insert(transformed_record).execute()
            successful += 1
        except Exception as e:
            print(f"Failed to insert record: {record}")
            print(f"Error: {str(e)}")
            failed += 1
            continue
    
    return successful, failed

def migrate_table_data(supabase, sqlite_session, model, table_name):
    print(f"Migrating {table_name}...")
    try:
        records = sqlite_session.query(model).all()
        
        if not records:
            print(f"No records found in {table_name}")
            return
        
        # Convert SQLAlchemy objects to dictionaries
        data = []
        skipped = 0
        for record in records:
            record_dict = {}
            for column in model.__table__.columns:
                value = getattr(record, column.name)
                # Handle enum types
                if hasattr(value, 'value'):
                    value = value.value
                # Handle datetime objects
                elif isinstance(value, datetime):
                    value = value.isoformat()
                record_dict[column.name] = value
            
            # Check if record already exists using all unique constraints
            if check_existing_record(supabase, table_name, record_dict, model):
                skipped += 1
                continue
                
            data.append(record_dict)
        
        if not data:
            print(f"All records already exist in {table_name}, skipped {skipped} records")
            return
            
        print(f"Prepared {len(data)} new records for {table_name} (skipped {skipped} existing records)")
        print("Sample data:", json.dumps(data[0] if data else {}, indent=2, default=str))
        
        # Insert records safely one by one
        successful, failed = insert_records_safely(supabase, table_name, data)
        print(f"Migration results for {table_name}:")
        print(f"- Successfully inserted: {successful}")
        print(f"- Failed to insert: {failed}")
        print(f"- Skipped (already exist): {skipped}")
        
        if failed > 0:
            print("Some records failed to insert, but continuing with migration...")
        
    except Exception as e:
        print(f"Error migrating {table_name}: {str(e)}")
        raise

def migrate_to_supabase():
    sqlite_session = None
    try:
        # Initialize connections
        print("Initializing Supabase connection...")
        supabase = get_supabase()
        
        print("Initializing SQLite connection...")
        sqlite_session = get_sqlite_session()
        
        # Migration order based on dependencies
        migrations = [
            (TradeConfiguration, "trade_configurations"),
            (BotConfiguration, "bot_configurations"),
            (Role, "roles"),
            (RoleRequirement, "role_requirements"),
            (ConditionalRoleGrant, "conditional_role_grants"),
            (VerificationConfig, "verification_configs"),
            (Verification, "verifications"),
            (OptionsStrategyTrade, "options_strategy_trades"),
            (Trade, "trades"),
            (Transaction, "transactions"),
            (OptionsStrategyTransaction, "options_strategy_transactions"),
        ]
        
        # Execute migrations
        for model, table_name in migrations:
            migrate_table_data(supabase, sqlite_session, model, table_name)
        
        print("Migration completed successfully!")
        
    except FileNotFoundError as e:
        print(f"Database error: {str(e)}")
        print("Please make sure your SQLite database exists and is accessible.")
    except Exception as e:
        print(f"Migration failed: {str(e)}")
        print("Please check your Supabase credentials and database permissions.")
        if hasattr(e, 'response'):
            print(f"Response details: {e.response.text if hasattr(e.response, 'text') else e.response}")
    finally:
        if sqlite_session:
            sqlite_session.close()

if __name__ == "__main__":
    migrate_to_supabase() 