from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.database import Base
import logging

SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

def create_test_database():
    Base.metadata.create_all(bind=engine)
    logging.info("Test database created")

def drop_test_database():
    Base.metadata.drop_all(bind=engine)
    with engine.connect() as conn:
        table_names = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table';")).fetchall()
    logging.info(f"Tables remaining in test database: {table_names}")
