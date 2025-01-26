from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
import os
import logging
from supabase import create_client
from supabase.lib.client_options import ClientOptions
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

Base = declarative_base()

def get_supabase_url():
    return os.getenv("SUPABASE_URL")

def get_supabase_key():
    return os.getenv("SUPABASE_KEY")

def get_database_url():
    """Get the database URL for Supabase PostgreSQL connection."""
    if os.getenv('FASTAPI_TEST') == 'true':
        return f"sqlite:///./test.db"  # Keep SQLite for tests
    
    # Get Supabase credentials
    db_host = os.getenv("SUPABASE_DB_HOST")
    db_password = os.getenv("SUPABASE_DB_PASSWORD")
    db_name = os.getenv("SUPABASE_DB_NAME", "postgres")
    db_port = os.getenv("SUPABASE_DB_PORT", "5432")
    db_user = os.getenv("SUPABASE_DB_USER", "postgres")
    
    if not all([db_host, db_password]):
        raise ValueError("Missing required Supabase database credentials")
    
    # Construct PostgreSQL connection URL with additional parameters
    params = {
        "sslmode": "require",
        "connect_timeout": "30",
        "target_session_attrs": "read-write"
    }
    param_str = "&".join(f"{k}={v}" for k, v in params.items())
    
    # Use the host directly without modification
    return f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}?{param_str}"

def get_engine():
    database_url = get_database_url()
    #print(f"Database URL: {database_url}")
    connect_args = {
        "check_same_thread": False
    } if database_url.startswith("sqlite") else {
        "sslmode": "require",
        "connect_timeout": 30,
        "target_session_attrs": "read-write"
    }
    return create_engine(
        database_url,
        connect_args=connect_args,
        pool_size=5,
        max_overflow=10,
        pool_timeout=30,
        pool_pre_ping=True,
        echo=True  # Enable SQL logging
    )

def get_session_local():
    engine = get_engine()
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_supabase():
    """Initialize Supabase client with version 2.10.0."""
    supabase_url = get_supabase_url()
    supabase_key = get_supabase_key()
    if not supabase_url or not supabase_key:
        raise ValueError("Supabase environment variables not set")
    
    options = ClientOptions(
        schema="public",
        headers={"Authorization": f"Bearer {supabase_key}"},
        auto_refresh_token=True,
        persist_session=True
    )
    
    return create_client(supabase_url, supabase_key, options=options)

engine = get_engine()
SessionLocal = get_session_local()

logging.info(f"Base class created with metadata: {Base.metadata}")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()