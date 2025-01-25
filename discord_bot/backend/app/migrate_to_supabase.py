import os
import sys
import argparse
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
    
    # Create engine with SQLite-specific connect args
    engine = create_engine(
        sqlite_url,
        connect_args={"check_same_thread": False}
    )
    
    # Create all tables (this is safe to call even if tables exist)
    Base.metadata.create_all(bind=engine)
    
    # Create session factory
    Session = sessionmaker(
        bind=engine,
        autocommit=False,
        autoflush=False
    )
    
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
        if 'average_price' not in record_dict:
            record_dict['average_price'] = record_dict.get('entry_price')
        if 'average_exit_price' not in record_dict:
            record_dict['average_exit_price'] = None
        if 'profit_loss' not in record_dict:
            record_dict['profit_loss'] = None
        if 'win_loss' not in record_dict:
            record_dict['win_loss'] = None
        if 'is_day_trade' not in record_dict:
            record_dict['is_day_trade'] = False
    
    # Handle tables with unique constraints
    if table_name == 'verifications':
        # For duplicate verifications, we'll append a timestamp to make them unique
        if 'user_id' in record_dict:
            record_dict['user_id'] = f"{record_dict['user_id']}_{record_dict.get('timestamp', '')}"
    
    if table_name == 'roles':
        # For duplicate roles, we'll skip them in the insert_records_safely function
        pass
    
    return record_dict

def insert_records_safely(supabase, table_name, records):
    """Insert records one by one to handle errors gracefully."""
    successful = 0
    failed = 0
    
    for record in records:
        try:
            # Transform record before insertion
            transformed_record = transform_record(record, table_name)
            
            # For roles table, check if record already exists before inserting
            if table_name == 'roles':
                try:
                    existing = supabase.table(table_name)\
                        .select('*')\
                        .eq('role_id', record['role_id'])\
                        .eq('guild_id', record['guild_id'])\
                        .execute()
                    if existing.data:
                        print(f"Skipping duplicate role: {record['role_id']}")
                        continue
                except Exception as e:
                    print(f"Error checking existing role: {str(e)}")
            
            response = supabase.table(table_name).insert(transformed_record).execute()
            successful += 1
        except Exception as e:
            print(f"Failed to insert record: {record}")
            print(f"Error: {str(e)}")
            failed += 1
            continue
    
    return successful, failed

def migrate_table_data(supabase, sqlite_session, model, table_name, skip_existence_check=False):
    print(f"Migrating {table_name}...")
    try:
        # Use all() to get all records from the model
        records = sqlite_session.query(model).all()
        
        if not records:
            print(f"No records found in {table_name}")
            return
        
        print(f"Found {len(records)} records in {table_name}")
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
            
            # Only check for existing records if we're not skipping the check
            if not skip_existence_check and check_existing_record(supabase, table_name, record_dict, model):
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

def clean_supabase_tables(supabase):
    """Delete all records from Supabase tables in reverse order of dependencies."""
    # Order matters due to foreign key constraints - delete children before parents
    table_configs = [
        # First delete dependent tables
        {"name": "transactions", "pk": "id"},
        {"name": "options_strategy_transactions", "pk": "id"},
        # Then delete main tables
        {"name": "trades", "pk": "trade_id"},
        {"name": "options_strategy_trades", "pk": "id"},
        # Then delete junction tables
        {"name": "role_requirement_roles", "pk": None, "where": True},  
        {"name": "conditional_role_grant_condition_roles", "pk": None, "where": True},
        # Then delete remaining tables
        {"name": "verifications", "pk": "id"},
        {"name": "verification_configs", "pk": "id"},
        {"name": "role_requirements", "pk": "id"},
        {"name": "roles", "pk": "id"},
        {"name": "conditional_role_grants", "pk": "id"},
        {"name": "bot_configurations", "pk": "id"},
        {"name": "trade_configurations", "pk": "id"}
    ]
    
    failed_tables = []
    for table in table_configs:
        try:
            print(f"Cleaning table {table['name']}...")
            
            if table.get('where', False):
                # For tables requiring WHERE clause
                response = supabase.table(table['name']).delete().eq('id', 'id').execute()
            elif table['pk'] is None:
                # For junction tables without WHERE requirement
                response = supabase.table(table['name']).delete().execute()
            else:
                # For regular tables, delete using their primary key
                response = supabase.table(table['name']).delete().neq(table['pk'], -1).execute()
            
            # Verify the table is empty
            check = supabase.table(table['name']).select('*').execute()
            if len(check.data) > 0:
                print(f"Warning: Table {table['name']} still has {len(check.data)} records after cleaning")
                # Try a more aggressive approach for tables that failed initial delete
                try:
                    print(f"Attempting forced delete on {table['name']}...")
                    response = supabase.table(table['name']).delete().execute()
                    check = supabase.table(table['name']).select('*').execute()
                    if len(check.data) > 0:
                        failed_tables.append(table['name'])
                    else:
                        print(f"Successfully cleaned {table['name']} on second attempt")
                except Exception as e:
                    print(f"Error on forced delete: {str(e)}")
                    failed_tables.append(table['name'])
            else:
                print(f"Successfully cleaned {table['name']}")
        except Exception as e:
            print(f"Error cleaning table {table['name']}: {str(e)}")
            failed_tables.append(table['name'])
    
    if failed_tables:
        tables_str = ", ".join(failed_tables)
        raise Exception(f"Failed to clean the following tables: {tables_str}")
    
    return True

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Migrate data from SQLite to Supabase')
    parser.add_argument('--clean', action='store_true', help='Clean Supabase tables before migration')
    args = parser.parse_args()
    
    try:
        # Get database connections
        sqlite_session = get_sqlite_session()
        supabase = get_supabase()
        
        if args.clean:
            print("Cleaning Supabase tables...")
            try:
                clean_supabase_tables(supabase)
                print("Successfully cleaned all tables")
            except Exception as e:
                print(f"Error during cleaning: {str(e)}")
                print("Aborting migration to prevent partial data state")
                sys.exit(1)
        
        # Define models and their corresponding table names in reverse order of deletion
        # This ensures parent records exist before child records are inserted
        models_to_migrate = [
            (TradeConfiguration, "trade_configurations"),
            (BotConfiguration, "bot_configurations"),
            (VerificationConfig, "verification_configs"),
            (Verification, "verifications"),
            (Role, "roles"),
            (ConditionalRoleGrant, "conditional_role_grants"),
            (RoleRequirement, "role_requirements"),
            (Trade, "trades"),
            (Transaction, "transactions"),
            (OptionsStrategyTrade, "options_strategy_trades"),
            (OptionsStrategyTransaction, "options_strategy_transactions")
        ]
        
        # Junction tables that don't have models - these will need to be handled separately
        junction_tables = [
            "role_requirement_roles",
            "conditional_role_grant_condition_roles"
        ]
        
        print("Note: Junction tables will be skipped as they don't have SQLAlchemy models:", junction_tables)
        
        # Migrate each table
        for model, table_name in models_to_migrate:
            migrate_table_data(supabase, sqlite_session, model, table_name, skip_existence_check=args.clean)
            
        # Handle junction tables if needed
        for table_name in junction_tables:
            print(f"Skipping junction table {table_name} - handle these manually if needed")
            
        print("Migration completed successfully!")
        
    except Exception as e:
        print(f"Migration failed: {str(e)}")
        sys.exit(1)
    finally:
        sqlite_session.close() 