from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
import os
import logging

Base = declarative_base()

def get_database_url():
    if os.getenv('FASTAPI_TEST') == 'true':
        return "sqlite:///./test.db"
    elif os.getenv("LOCAL_TEST", "false").lower() == "true":
        return "sqlite:///./local.db"
    else:
        return os.getenv("DATABASE_URL", "sqlite:///./sql_app.db")

def get_engine():
    database_url = get_database_url()
    return create_engine(database_url, connect_args={"check_same_thread": False})

def get_session_local():
    engine = get_engine()
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)

engine = get_engine()
SessionLocal = get_session_local()

logging.info(f"Base class created with metadata: {Base.metadata}")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()