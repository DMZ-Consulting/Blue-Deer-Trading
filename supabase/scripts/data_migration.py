#!/usr/bin/env python3
"""
Phase 1, Task 3: Data Migration Strategy
This script migrates existing options strategy legs data to the new normalized schema.
"""

import psycopg2
import json
import uuid
import os
import sys
from typing import Dict, List, Any, Optional
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'migration_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

class DatabaseMigrator:
    def __init__(self, db_url: str, default_user_id: str = None):
        self.db_url = db_url
        self.default_user_id = default_user_id
        self.connection = None
        self.cursor = None
        
    def connect(self):
        """Establish database connection"""
        try:
            self.connection = psycopg2.connect(self.db_url)
            self.cursor = self.connection.cursor()
            logger.info("Database connection established")
            return True
        except psycopg2.Error as e:
            logger.error(f"Failed to connect to database: {e}")
            return False
    
    def disconnect(self):
        """Close database connection"""
        if self.cursor:
            self.cursor.close()
        if self.connection:
            self.connection.close()
        logger.info("Database connection closed")
    
    def disable_triggers(self):
        """Disable triggers that might interfere with the migration"""
        triggers_to_disable = [
            ("transactions", "transaction_before_insert_update"),
            ("transactions", "transaction_before_delete"),
            ("options_strategy_trades", "set_options_strategy_trade_id"),
            ("options_strategy_transactions", "set_options_strategy_transaction_id"),
            ("options_strategy_transactions", "options_strategy_transaction_before_change"),
        ]
        
        logger.info("Disabling triggers...")
        for table, trigger in triggers_to_disable:
            try:
                self.cursor.execute(f"ALTER TABLE public.{table} DISABLE TRIGGER {trigger}")
                logger.info(f"Disabled trigger {trigger} on table {table}")
            except psycopg2.Error as e:
                logger.warning(f"Could not disable trigger {trigger} on {table}: {e}")
        
        self.connection.commit()
    
    def enable_triggers(self):
        """Re-enable triggers after migration"""
        triggers_to_enable = [
            ("transactions", "transaction_before_insert_update"),
            ("transactions", "transaction_before_delete"),
            ("options_strategy_trades", "set_options_strategy_trade_id"),
            ("options_strategy_transactions", "set_options_strategy_transaction_id"),
            ("options_strategy_transactions", "options_strategy_transaction_before_change"),
        ]
        
        logger.info("Re-enabling triggers...")
        for table, trigger in triggers_to_enable:
            try:
                self.cursor.execute(f"ALTER TABLE public.{table} ENABLE TRIGGER {trigger}")
                logger.info(f"Enabled trigger {trigger} on table {table}")
            except psycopg2.Error as e:
                logger.warning(f"Could not enable trigger {trigger} on {table}: {e}")
        
        self.connection.commit()
    
    def assign_default_user_ids(self):
        """Assign default user_id to existing records"""
        if self.default_user_id is None:
            logger.info("Leaving user_id as NULL for existing records (no user system implemented yet)")
            return
            
        logger.info(f"Assigning default user_id '{self.default_user_id}' to existing records...")
        
        # Update trades table
        self.cursor.execute("UPDATE public.trades SET user_id = %s WHERE user_id IS NULL", 
                          (self.default_user_id,))
        trades_updated = self.cursor.rowcount
        
        # Update options_strategy_trades table
        self.cursor.execute("UPDATE public.options_strategy_trades SET user_id = %s WHERE user_id IS NULL", 
                          (self.default_user_id,))
        strategies_updated = self.cursor.rowcount
        
        self.connection.commit()
        logger.info(f"Updated {trades_updated} trades and {strategies_updated} strategy trades with default user_id")
    
    def parse_legs_data(self, legs_text: str) -> List[Dict[str, Any]]:
        """Parse the legs data from the text field"""
        if not legs_text or legs_text.strip() == '':
            return []
        
        try:
            # Try to parse as JSON first
            legs_data = json.loads(legs_text)
            if isinstance(legs_data, list):
                return legs_data
            elif isinstance(legs_data, dict):
                return [legs_data]  # Single leg
            else:
                logger.warning(f"Unexpected legs data format: {type(legs_data)}")
                return []
        except json.JSONDecodeError:
            logger.warning(f"Could not parse legs as JSON: {legs_text[:100]}...")
            # Try to parse as a simple format or return empty
            return []
    
    def create_trade_from_leg(self, leg_data: Dict[str, Any], strategy_id: str, user_id: str) -> str:
        """Create a new trade record from leg data"""
        trade_id = f"trade_{uuid.uuid4().hex[:8]}_{int(datetime.now().timestamp())}"
        
        # Extract leg information with defaults based on your legs format
        symbol = leg_data.get('symbol', 'UNKNOWN')
        trade_type = leg_data.get('trade_type', 'Option')  # Use BTO/STO/etc. from leg
        status = 'OPEN'  # Default to open
        entry_price = float(leg_data.get('entry_price', 0.0))
        size = str(leg_data.get('multiplier', 1))  # Use multiplier as size
        strike = leg_data.get('strike')
        expiration_date = leg_data.get('expiration_date')
        option_type = leg_data.get('option_type')  # P or C
        
        # Insert the trade
        insert_query = """
            INSERT INTO public.trades (
                trade_id, symbol, trade_type, status, entry_price, size, 
                created_at, is_contract, strike, expiration_date, option_type, user_id
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (trade_id) DO NOTHING
        """
        
        self.cursor.execute(insert_query, (
            trade_id,
            symbol,
            trade_type,
            status,
            entry_price,
            size,
            datetime.now(),
            True,  # is_contract for options
            strike,
            expiration_date,
            option_type,
            user_id
        ))
        
        return trade_id
    
    def link_strategy_leg(self, strategy_id: str, trade_id: str, leg_sequence: int):
        """Create a link between strategy and trade in options_strategy_legs table"""
        strategy_leg_id = f"leg_{uuid.uuid4().hex[:8]}_{int(datetime.now().timestamp())}"
        
        insert_query = """
            INSERT INTO public.options_strategy_legs (
                strategy_leg_id, strategy_id, trade_id, leg_sequence
            ) VALUES (%s, %s, %s, %s)
        """
        
        self.cursor.execute(insert_query, (strategy_leg_id, strategy_id, trade_id, leg_sequence))
    
    def migrate_options_strategies(self):
        """Main migration logic for options strategies"""
        logger.info("Starting options strategy legs migration...")
        
        # Fetch all options strategies with legs data
        self.cursor.execute("""
            SELECT strategy_id, legs, user_id 
            FROM public.options_strategy_trades 
            WHERE legs IS NOT NULL AND legs != ''
        """)
        
        strategies = self.cursor.fetchall()
        logger.info(f"Processing {len(strategies)} options strategies...")
        
        total_legs_processed = 0
        strategies_processed = 0
        
        for strategy_id, legs_text, user_id in strategies:
            try:
                legs_data = self.parse_legs_data(legs_text)
                
                if not legs_data:
                    logger.warning(f"No valid legs data found for strategy {strategy_id}")
                    continue
                
                logger.info(f"Processing strategy {strategy_id} with {len(legs_data)} legs")
                
                for leg_sequence, leg in enumerate(legs_data, 1):
                    try:
                        # Create trade record for the leg
                        trade_id = self.create_trade_from_leg(leg, strategy_id, user_id)
                        
                        # Link the trade to the strategy
                        self.link_strategy_leg(strategy_id, trade_id, leg_sequence)
                        
                        total_legs_processed += 1
                        
                    except psycopg2.Error as e:
                        logger.error(f"Error processing leg {leg_sequence} for strategy {strategy_id}: {e}")
                        self.connection.rollback()
                        continue
                
                strategies_processed += 1
                
                # Commit after each strategy to avoid losing progress
                self.connection.commit()
                
            except Exception as e:
                logger.error(f"Error processing strategy {strategy_id}: {e}")
                self.connection.rollback()
                continue
        
        logger.info(f"Migration completed: {strategies_processed} strategies processed, {total_legs_processed} legs migrated")
    
    def cleanup_legs_column(self):
        """Remove the legs column after successful migration"""
        logger.info("Removing the 'legs' column from options_strategy_trades...")
        self.cursor.execute("ALTER TABLE public.options_strategy_trades DROP COLUMN legs")
        self.connection.commit()
        logger.info("'legs' column removed successfully")
    
    def validate_migration(self):
        """Validate the migration results"""
        logger.info("Validating migration results...")
        
        # Check that all strategies have corresponding legs
        self.cursor.execute("""
            SELECT COUNT(*) FROM public.options_strategy_trades ost
            WHERE EXISTS (
                SELECT 1 FROM public.options_strategy_legs osl 
                WHERE osl.strategy_id = ost.strategy_id
            )
        """)
        strategies_with_legs = self.cursor.fetchone()[0]
        
        self.cursor.execute("SELECT COUNT(*) FROM public.options_strategy_trades")
        total_strategies = self.cursor.fetchone()[0]
        
        self.cursor.execute("SELECT COUNT(*) FROM public.options_strategy_legs")
        total_legs = self.cursor.fetchone()[0]
        
        logger.info(f"Validation results:")
        logger.info(f"  Total strategies: {total_strategies}")
        logger.info(f"  Strategies with legs: {strategies_with_legs}")
        logger.info(f"  Total legs created: {total_legs}")
        
    def run_migration(self, skip_cleanup: bool = False):
        """Run the complete migration process"""
        if not self.connect():
            return False
        
        try:
            logger.info("Starting Phase 1 Task 3 data migration...")
            
            # Step 1: Disable triggers
            self.disable_triggers()
            
            # Step 2: Assign default user IDs
            self.assign_default_user_ids()
            
            # Step 3: Migrate options strategy legs
            self.migrate_options_strategies()
            
            # Step 4: Validate migration
            self.validate_migration()
            
            # Step 5: Cleanup (optional)
            if not skip_cleanup:
                response = input("Do you want to remove the 'legs' column? (y/N): ")
                if response.lower() == 'y':
                    self.cleanup_legs_column()
            
            # Step 6: Re-enable triggers
            self.enable_triggers()
            
            logger.info("Migration completed successfully!")
            return True
            
        except Exception as e:
            logger.error(f"Migration failed: {e}")
            self.connection.rollback()
            return False
        finally:
            self.disconnect()

def main():
    # Get database URL from environment
    db_url = os.getenv('PREVIEW_DB_URL')
    if not db_url:
        logger.error("PREVIEW_DB_URL environment variable is required")
        sys.exit(1)
    
    # Get default user ID from environment (None means leave as NULL)
    default_user_id = os.getenv('DEFAULT_USER_ID')
    
    # Parse command line arguments
    skip_cleanup = '--skip-cleanup' in sys.argv
    
    # Run migration
    migrator = DatabaseMigrator(db_url, default_user_id)
    success = migrator.run_migration(skip_cleanup)
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main() 