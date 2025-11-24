from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# The URL format: postgresql://user:password@address:port/dbname
DATABASE_URL = "postgresql://admin:password123@localhost:5432/polyphonic_db"

# Create the engine (the connection)
engine = create_engine(DATABASE_URL)

# Create a Session factory (this allows us to open 'conversations' with the DB)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# The Base class (all our models will inherit from this)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()