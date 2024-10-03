from app.database import Base, engine
from app.models import Trade, Transaction

def init_db():
    Base.metadata.create_all(bind=engine)

if __name__ == "__main__":
    init_db()
    print("Database initialized successfully.")