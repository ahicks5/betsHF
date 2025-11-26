"""
Database connection and session management
Simple SQLite database: props.db
"""
import sys
from pathlib import Path

# Add parent directory to path for imports when run directly
if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from database.models import Base
import os

# Database configuration
DB_FILE = "props.db"
DATABASE_URL = f"sqlite:///{DB_FILE}"

# Create engine
engine = create_engine(DATABASE_URL, echo=False)

# Create session factory
SessionLocal = scoped_session(sessionmaker(bind=engine))


def init_db():
    """Initialize the database, creating all tables"""
    Base.metadata.create_all(engine)
    print(f"[OK] Database initialized: {DB_FILE}")


def get_session():
    """Get a database session"""
    return SessionLocal()


def close_session():
    """Close the scoped session"""
    SessionLocal.remove()


if __name__ == "__main__":
    # Initialize database when run directly
    init_db()
    print("Database setup complete!")
