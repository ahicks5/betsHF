"""
Database Migration: Make game_id nullable in player_game_stats table
This is safe - it doesn't drop any data, just relaxes the constraint
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.db import get_session
from sqlalchemy import text

def migrate():
    """Make game_id nullable in player_game_stats table"""
    session = get_session()

    print("[MIGRATION] Making game_id nullable in player_game_stats table...")

    try:
        # PostgreSQL: ALTER TABLE to drop NOT NULL constraint
        session.execute(text("""
            ALTER TABLE player_game_stats
            ALTER COLUMN game_id DROP NOT NULL;
        """))
        session.commit()

        print("[OK] Migration complete! game_id is now nullable.")
        print("[OK] All existing data preserved.")

    except Exception as e:
        session.rollback()
        print(f"[ERROR] Migration failed: {e}")
        print("\nIf you see 'column does not exist' error, the table hasn't been created yet.")
        print("In that case, just run: python database/db.py")
        raise

    finally:
        session.close()

if __name__ == "__main__":
    migrate()
