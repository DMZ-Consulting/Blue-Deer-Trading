import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.schema import CreateTable
import json
import time

# Add the project root to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(os.path.dirname(current_dir))
sys.path.append(backend_dir)

from backend.app.database import get_database_url, Base
from backend.app.models import (
    Trade, Transaction, TradeConfiguration, OptionsStrategyTrade,
    OptionsStrategyTransaction, VerificationConfig, Verification,
    RoleRequirement, Role, ConditionalRoleGrant, BotConfiguration,
    role_requirement_roles, conditional_role_grant_condition_roles
)

def create_tables():
    """Create tables in Supabase using SQLAlchemy models."""
    try:
        # Get the database URL for Supabase
        database_url = get_database_url()
        print(f"Connecting to database: {database_url}")
        
        # Create engine with timeout settings
        engine = create_engine(
            database_url,
            connect_args={
                "sslmode": "require",
                "connect_timeout": 30,
                "keepalives": 1,
                "keepalives_idle": 30,
                "keepalives_interval": 10,
                "keepalives_count": 5
            },
            pool_pre_ping=True,
            echo=True
        )
        
        # Test connection with timeout
        print("Testing database connection...")
        start_time = time.time()
        timeout = 30  # 30 seconds timeout
        
        while time.time() - start_time < timeout:
            try:
                with engine.connect() as conn:
                    result = conn.execute(text("SELECT 1"))
                    print("Database connection successful!")
                    break
            except Exception as e:
                print(f"Connection attempt failed: {str(e)}")
                if time.time() - start_time >= timeout:
                    raise TimeoutError("Database connection timed out")
                time.sleep(2)  # Wait 2 seconds before retrying
        
        # Models in order of dependencies
        models = [
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
            (role_requirement_roles, "role_requirement_roles"),
            (conditional_role_grant_condition_roles, "conditional_role_grant_condition_roles")
        ]
        
        # Create each table
        for model, table_name in models:
            try:
                print(f"\nCreating table: {table_name}")
                # Generate CREATE TABLE statement
                create_stmt = CreateTable(model.__table__).compile(engine)
                print(f"SQL Statement:\n{create_stmt}")
                
                # Execute the CREATE TABLE statement with timeout
                with engine.connect() as conn:
                    conn.execute(text(str(create_stmt)))
                    conn.commit()
                print(f"Successfully created table: {table_name}")
                
            except Exception as e:
                print(f"Error creating table {table_name}: {str(e)}")
                if "already exists" in str(e).lower():
                    print(f"Table {table_name} already exists, skipping...")
                    continue
                raise
        
        print("\nAll tables created successfully!")
        
    except Exception as e:
        print(f"Error setting up database: {str(e)}")
        if hasattr(e, 'orig'):
            print(f"Original error: {str(e.orig)}")
        raise

if __name__ == "__main__":
    create_tables() 