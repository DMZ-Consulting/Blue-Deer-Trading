print("Starting application...")

import asyncio
import logging
import os
import shutil
from contextlib import asynccontextmanager
from datetime import datetime
from typing import List, Optional
from enum import Enum

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from . import crud, models, schemas
from .bot import run_bot
from .database import get_db, engine, SessionLocal
from .models import create_tables

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Add a console handler
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

# Check if we're in a test environment
IS_TEST = os.getenv('FASTAPI_TEST') == 'true'

models.Base.metadata.create_all(bind=engine)

@asynccontextmanager
async def lifespan(app: FastAPI):
    create_tables(engine)
    try:
        asyncio.create_task(run_bot())
        if not IS_TEST:
            asyncio.create_task(backup_database())
    except Exception as e:
        logger.error(f"Failed to start the bot or backup task: {str(e)}")
    yield
    # Shutdown code here (if any)

app = FastAPI(lifespan=lifespan)



# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Add your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class SortOrder(str, Enum):
    asc = "asc"
    desc = "desc"
@app.get("/trades", response_model=List[schemas.Trade])
def read_trades(
    skip: int = Query(0, ge=0, description="Number of trades to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of trades to return"),
    status: Optional[models.TradeStatusEnum] = Query(None, description="Filter trades by status"),
    symbol: Optional[str] = Query(None, description="Filter trades by symbol"),
    tradeType: Optional[str] = Query(None, description="Filter trades by trade type"),
    sortBy: Optional[str] = Query(None, description="Field to sort trades by"),
    sortOrder: Optional[str] = Query("desc", regex="^(asc|desc)$", description="Sort order (ascending or descending)"),
    configName: Optional[str] = Query(None, description="Filter trades by configuration name"),
    weekFilter: Optional[str] = Query(None, description="Filter trades by week"),
    monthFilter: Optional[str] = Query(None, description="Filter trades by month"),
    yearFilter: Optional[str] = Query(None, description="Filter trades by year"),
    db: Session = Depends(get_db)   
):
    print("Entering read_trades function")
    try:
        trades = crud.get_trades(
            db,
            skip=skip,
            limit=limit,
            status=status,
            symbol=symbol,
            trade_type=tradeType,
            sort_by=sortBy,
            sort_order=sortOrder,
            config_name=configName,
            week_filter=weekFilter,
            month_filter=monthFilter,
            year_filter=yearFilter
        )
        print(f"Retrieved {len(trades)} trades")
        return trades
    except ValueError as e:
        print(f"Error in read_trades: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        print("Exiting read_trades function")

@app.get("/portfolio", response_model=List[schemas.PortfolioTrade])
def read_portfolio(
    skip: int = Query(0, ge=0, description="Number of trades to skip"),
    limit: int = Query(500, ge=1, le=1000, description="Maximum number of trades to return"),
    sortBy: Optional[str] = Query(None, description="Field to sort trades by"),
    sortOrder: Optional[str] = Query("desc", regex="^(asc|desc)$", description="Sort order (ascending or descending)"),
    configName: Optional[str] = Query(None, description="Filter trades by configuration name"),
    weekFilter: Optional[str] = Query(None, description="Filter trades by week"),
    db: Session = Depends(get_db)   
):
    print("Entering read_trades function")
    try:
        trades = crud.get_portfolio_trades(
            db,
            skip=skip,
            limit=limit,
            sort_by=sortBy,
            sort_order=sortOrder,
            config_name=configName,
            week_filter=weekFilter,
        )
        print(f"Retrieved {len(trades)} trades")
        return trades
    except ValueError as e:
        print(f"Error in read_trades: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        print("Exiting read_trades function")


@app.get("/trades/{trade_id}", response_model=schemas.Trade)
def read_trade(trade_id: str, db: Session = Depends(get_db)):
    db_trade = crud.get_trade(db, trade_id=trade_id)
    if db_trade is None:
        raise HTTPException(status_code=404, detail="Trade not found")
    return db_trade

@app.get("/trades/{trade_id}/transactions", response_model=List[schemas.Transaction])
def read_trade_transactions(trade_id: str, db: Session = Depends(get_db)):
    transactions = crud.get_trade_transactions(db, trade_id=trade_id)
    if not transactions:
        raise HTTPException(status_code=404, detail="Trade not found or no transactions")
    return transactions

@app.get("/performance", response_model=schemas.Performance)
def read_performance(db: Session = Depends(get_db)):
    performance = crud.get_performance(db)
    return performance

@app.get("/")
async def read_root():
    return {"Hello": "World"}

# Modify the backup_database function
async def backup_database():
    if IS_TEST:
        return  # Skip backups during tests
    while True:
        try:
            # Get the current date for the backup file name
            current_date = datetime.now().strftime("%Y-%m-%d")
            current_dir = os.path.dirname(os.path.abspath(__file__))
            source_db = os.path.join(current_dir, "../db/sql_app.db")
            
            backup_dir = os.path.join(current_dir, "../db/backups")
            backup_db = os.path.join(backup_dir, f"backup_{current_date}.db")
            
            # Create backup directory if it doesn't exist
            os.makedirs(backup_dir, exist_ok=True)
            
            # Create a copy of the database file
            shutil.copy2(source_db, backup_db)
            
            logger.info(f"Database backup created: {backup_db}")
            
            # Clean up old backups
            cleanup_old_backups(backup_dir)
            
            # Wait for 24 hours before the next backup
            await asyncio.sleep(24 * 60 * 60)
        except Exception as e:
            logger.error(f"Failed to create database backup: {str(e)}")
            # If there's an error, wait for 1 hour before trying again
            await asyncio.sleep(60 * 60)

def cleanup_old_backups(backup_dir):
    try:
        # Get all backup files
        backup_files = [f for f in os.listdir(backup_dir) if f.startswith("backup_") and f.endswith(".db")]
        
        # Sort backup files by modification time (newest first)
        backup_files.sort(key=lambda x: os.path.getmtime(os.path.join(backup_dir, x)), reverse=True)
        
        # Keep only the last 14 backups
        for old_backup in backup_files[14:]:
            os.remove(os.path.join(backup_dir, old_backup))
            logger.info(f"Removed old backup: {old_backup}")
    except Exception as e:
        logger.error(f"Failed to clean up old backups: {str(e)}")

@app.post("/trades/bto", response_model=schemas.Trade)
def create_bto_trade(trade: schemas.TradeCreate, db: Session = Depends(get_db)):
    try:
        return crud.create_trade(db, trade)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/trades/sto", response_model=schemas.Trade)
def create_sto_trade(trade: schemas.TradeCreate, db: Session = Depends(get_db)):
    try:
        return crud.create_trade(db, trade)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

@app.post("/trades/options-strategy", response_model=schemas.OptionsStrategyTrade)
def create_options_strategy(strategy: schemas.OptionsStrategyTradeCreate, db: Session = Depends(get_db)):
    return crud.create_options_strategy(db, strategy)

@app.post("/trades/{trade_id}/add", response_model=schemas.Trade)
def add_to_trade(trade_id: str, action_input: crud.TradeActionInput, db: Session = Depends(get_db)):
    return crud.add_to_trade(db, action_input)

@app.post("/trades/{trade_id}/trim", response_model=schemas.Trade)
def trim_trade(trade_id: str, action_input: crud.TradeActionInput, db: Session = Depends(get_db)):
    return crud.trim_trade(db, action_input)

@app.post("/trades/{trade_id}/exit", response_model=schemas.Trade)
def exit_trade(trade_id: str, action_input: crud.TradeActionInput, db: Session = Depends(get_db)):
    return crud.exit_trade(db, action_input)

@app.post("/trades/{trade_id}/exit-expired", response_model=schemas.Trade)
def exit_expired_trade(trade_id: str, db: Session = Depends(get_db)):
    try:
        return crud.exit_expired_trade(db, trade_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/trades/fut", response_model=schemas.Trade)
def create_future_trade(trade_input: schemas.TradeCreate, db: Session = Depends(get_db)):
    try:
        return crud.future_trade(db, trade_input)
    except ValueError as e:
        logger.error(f"Failed to create future trade: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/trades/lt", response_model=schemas.Trade)
def create_long_term_trade(trade_input: schemas.TradeCreate, db: Session = Depends(get_db)):
    try:
        return crud.long_term_trade(db, trade_input)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

# Add this endpoint to test the expired trades functionality
@app.post("/trades/check-and-exit-expired")
async def check_and_exit_expired_trades(db: Session = Depends(get_db)):
    try:
        today = datetime.now().date()
        open_trades = crud.get_trades(db, status=models.TradeStatusEnum.OPEN)
        
        exited_trades = []
        for trade in open_trades:
            if trade.expiration_date and trade.expiration_date.date() <= today:
                exited_trade = crud.exit_expired_trade(db, trade.trade_id)
                exited_trades.append(exited_trade)
        
        return {"message": f"Exited {len(exited_trades)} expired trades", "exited_trades": exited_trades}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Ignore DeprecationWarning for discord.player
import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning, module="discord.player")

@app.post("/trades/os/{strategy_id}/add", response_model=schemas.OptionsStrategyTrade)
def add_to_options_strategy(strategy_id: str, action_input: crud.StrategyTradeActionInput, db: Session = Depends(get_db)):
    try:
        return crud.os_add(db, strategy_id, action_input.net_cost, action_input.size)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/trades/os/{strategy_id}/trim", response_model=schemas.OptionsStrategyTrade)
def trim_options_strategy(strategy_id: str, action_input: crud.StrategyTradeActionInput, db: Session = Depends(get_db)):
    try:
        return crud.os_trim(db, strategy_id, action_input.net_cost, action_input.size)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/trades/os/{strategy_id}/exit", response_model=schemas.OptionsStrategyTrade)
def exit_options_strategy(strategy_id: str, action_input: crud.StrategyTradeActionInput, db: Session = Depends(get_db)):
    try:
        return crud.os_exit(db, strategy_id, action_input.net_cost)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
@app.post("/trades/{trade_id}/delete")
def delete_trade(trade_id: str, db: Session = Depends(get_db)):
    return crud.delete_trade(db, trade_id)