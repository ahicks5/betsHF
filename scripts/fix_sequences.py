"""
Fix PostgreSQL Sequences
Resets auto-increment sequences to correct values after migrations
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.db import get_session
from sqlalchemy import text

def fix_sequences():
    """Reset all PostgreSQL sequences to correct values"""
    session = get_session()

    print("[FIX] Resetting PostgreSQL sequences...")

    try:
        # List of tables with auto-increment IDs
        tables = [
            'teams',
            'players',
            'games',
            'prop_lines',
            'plays',
            'player_game_stats',
            'api_call_logs'
        ]

        for table in tables:
            # Get the max ID from the table
            result = session.execute(text(f"SELECT MAX(id) FROM {table}"))
            max_id = result.scalar()

            if max_id is None:
                max_id = 0

            # Reset the sequence to max_id + 1
            sequence_name = f"{table}_id_seq"
            session.execute(text(f"SELECT setval('{sequence_name}', {max_id + 1}, false)"))

            print(f"  [OK] {table}: sequence set to {max_id + 1}")

        session.commit()
        print("\n[OK] All sequences fixed!")

    except Exception as e:
        session.rollback()
        print(f"[ERROR] Failed to fix sequences: {e}")
        raise

    finally:
        session.close()

if __name__ == "__main__":
    fix_sequences()
