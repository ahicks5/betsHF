"""
Migration: Add is_locked and locked_at columns to plays table

This migration adds play state tracking:
- is_locked (Boolean): Whether the play is locked (game started)
- locked_at (DateTime): When the play was locked

Play states:
- OPEN: is_locked=False, was_correct=None (can update with better lines)
- LOCKED: is_locked=True, was_correct=None (game started, waiting for results)
- GRADED: was_correct is not None (has results)

This migration also sets is_locked=True for all existing plays that have
actual_result (meaning the game finished) or was_correct is not None.

Usage: python scripts/migrations/migrate_add_is_locked.py
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
    print("MIGRATION: Add is_locked and locked_at columns to plays")
    print("=" * 60)

    try:
        # Check if is_locked column already exists
        result = session.execute(text("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'plays' AND column_name = 'is_locked'
        """))

        if result.fetchone():
            print("[OK] is_locked column already exists")
        else:
            print("Adding is_locked column...")
            session.execute(text("""
                ALTER TABLE plays
                ADD COLUMN is_locked BOOLEAN DEFAULT FALSE NOT NULL
            """))
            print("[OK] Added is_locked column")

        # Check if locked_at column already exists
        result = session.execute(text("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'plays' AND column_name = 'locked_at'
        """))

        if result.fetchone():
            print("[OK] locked_at column already exists")
        else:
            print("Adding locked_at column...")
            session.execute(text("""
                ALTER TABLE plays
                ADD COLUMN locked_at TIMESTAMP
            """))
            print("[OK] Added locked_at column")

        session.commit()

        # Lock all plays that have results or actual_result
        print("\nLocking plays that are already graded or have results...")
        result = session.execute(text("""
            UPDATE plays
            SET is_locked = TRUE, locked_at = result_collected_at
            WHERE (was_correct IS NOT NULL OR actual_result IS NOT NULL)
            AND is_locked = FALSE
        """))
        session.commit()

        # Count plays by state
        print("\nPlay states after migration:")

        # GRADED: was_correct is not None
        result = session.execute(text("""
            SELECT COUNT(*) FROM plays WHERE was_correct IS NOT NULL
        """))
        graded_count = result.fetchone()[0]
        print(f"  GRADED (has result): {graded_count}")

        # LOCKED: is_locked=True but was_correct is None
        result = session.execute(text("""
            SELECT COUNT(*) FROM plays
            WHERE is_locked = TRUE AND was_correct IS NULL
        """))
        locked_count = result.fetchone()[0]
        print(f"  LOCKED (waiting for results): {locked_count}")

        # OPEN: is_locked=False and was_correct is None
        result = session.execute(text("""
            SELECT COUNT(*) FROM plays
            WHERE is_locked = FALSE AND was_correct IS NULL
        """))
        open_count = result.fetchone()[0]
        print(f"  OPEN (can still update): {open_count}")

        print("\n[OK] Migration complete!")

    except Exception as e:
        session.rollback()
        print(f"\n[ERROR] Migration failed: {e}")
        raise
    finally:
        session.close()


if __name__ == "__main__":
    migrate()
