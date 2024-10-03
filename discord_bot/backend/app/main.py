from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from . import crud, models, schemas
from .database import SessionLocal, engine
import asyncio
from .bot import run_bot
from typing import List
import logging
from fastapi.middleware.cors import CORSMiddleware
from .models import create_tables
import shutil
import os
from datetime import datetime, timedelta

models.Base.metadata.create_all(bind=engine)

app = FastAPI()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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

@app.get("/trades", response_model=List[schemas.Trade])
def read_trades(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    trades = crud.get_trades(db, skip=skip, limit=limit)
    return trades

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
    while True:
        try:
            # Get the current date for the backup file name
            current_date = datetime.now().strftime("%Y-%m-%d")
            source_db = "sql_app.db"  # Update this with your actual database file name
            backup_dir = "backups"  # Directory to store backups
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

# Modify the startup event to include the backup task
@app.on_event("startup")
async def startup_event():
    create_tables()
    try:
        asyncio.create_task(run_bot())
        asyncio.create_task(backup_database())
    except Exception as e:
        logger.error(f"Failed to start the bot or backup task: {str(e)}")