"""
Migration: Add model_name and bet_amount columns to plays table

This migration:
1. Adds model_name column (default: 'pulsar_v1')
2. Adds bet_amount column (default: 10.0)
3. Updates all existing plays to be tagged as 'pulsar_v1'

Usage: python scripts/migrations/migrate_add_model_column.py
"""
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from database.db import get_session
from sqlalchemy import text


def migrate():
    """Run the migration"""
    session = get_session()

    print("=" * 60)
    print("MIGRATION: Add model_name and bet_amount columns to plays")
    print("=" * 60)

    try:
        # Check if columns already exist
        result = session.execute(text("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'plays' AND column_name = 'model_name'
        """))

        if result.fetchone():
            print("[OK] model_name column already exists")
        else:
            print("Adding model_name column...")
            session.execute(text("""
                ALTER TABLE plays
                ADD COLUMN model_name VARCHAR(50) DEFAULT 'pulsar_v1' NOT NULL
            """))
            print("[OK] Added model_name column")

        # Check if bet_amount exists
        result = session.execute(text("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'plays' AND column_name = 'bet_amount'
        """))

        if result.fetchone():
            print("[OK] bet_amount column already exists")
        else:
            print("Adding bet_amount column...")
            session.execute(text("""
                ALTER TABLE plays
                ADD COLUMN bet_amount FLOAT DEFAULT 10.0
            """))
            print("[OK] Added bet_amount column")

        # Update all existing plays to be tagged as pulsar_v1 with $10 bet
        print("\nTagging existing plays as 'pulsar_v1'...")
        result = session.execute(text("""
            UPDATE plays
            SET model_name = 'pulsar_v1', bet_amount = 10.0
            WHERE model_name IS NULL OR model_name = ''
        """))
        session.commit()

        # Count plays by model
        result = session.execute(text("""
            SELECT model_name, COUNT(*) as count
            FROM plays
            GROUP BY model_name
        """))

        print("\nPlays by model:")
        for row in result:
            print(f"  {row[0]}: {row[1]} plays")

        print("\n[OK] Migration complete!")

    except Exception as e:
        session.rollback()
        print(f"\n[ERROR] Migration failed: {e}")
        raise
    finally:
        session.close()


if __name__ == "__main__":
    migrate()
