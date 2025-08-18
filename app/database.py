"""Database configuration and setup."""

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Database URL - using SQLite for simplicity
DATABASE_URL = "sqlite:///./duty_tracker.db"

# Create engine
engine = create_engine(
    DATABASE_URL, 
    connect_args={"check_same_thread": False}  # Only needed for SQLite
)

# Create SessionLocal class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create Base class
Base = declarative_base()


def get_db():
    """Get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables():
    """Create all database tables."""
    from app.models import Base
    Base.metadata.create_all(bind=engine)
