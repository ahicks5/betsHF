"""
Database connection and session management
Supports both SQLite (local) and PostgreSQL (Heroku)
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
# Use Heroku's DATABASE_URL if available (PostgreSQL), otherwise use SQLite locally
DATABASE_URL = os.getenv('DATABASE_URL')

if DATABASE_URL:
    # Heroku PostgreSQL
    # Heroku uses postgres:// but SQLAlchemy needs postgresql://
    if DATABASE_URL.startswith('postgres://'):
        DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)
    print("[OK] Using PostgreSQL (Heroku)")
else:
    # Local SQLite
    DB_FILE = "props.db"
    DATABASE_URL = f"sqlite:///{DB_FILE}"
    print("[OK] Using SQLite (Local)")

# Create engine
engine = create_engine(DATABASE_URL, echo=False)

# Create session factory
SessionLocal = scoped_session(sessionmaker(bind=engine))


def init_db():
    """Initialize the database, creating all tables"""
    Base.metadata.create_all(engine)
    db_type = "PostgreSQL" if os.getenv('DATABASE_URL') else "SQLite"
    print(f"[OK] Database initialized ({db_type})")


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
