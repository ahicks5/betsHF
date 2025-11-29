"""
SQLite Migration: Make game_id nullable in player_game_stats
SQLite doesn't support ALTER COLUMN, so we need to recreate the table
"""
import sqlite3
import os

DB_FILE = "props.db"

if not os.path.exists(DB_FILE):
    print(f"[ERROR] Database file {DB_FILE} not found!")
    exit(1)

conn = sqlite3.connect(DB_FILE)
cursor = conn.cursor()

print("[MIGRATION] Making game_id nullable in player_game_stats (SQLite)...")

try:
    # Step 1: Rename old table
    print("  [1/4] Renaming old table...")
    cursor.execute("ALTER TABLE player_game_stats RENAME TO player_game_stats_old")

    # Step 2: Create new table with correct schema (game_id nullable)
    print("  [2/4] Creating new table with nullable game_id...")
    cursor.execute("""
        CREATE TABLE player_game_stats (
            id INTEGER PRIMARY KEY,
            player_id INTEGER NOT NULL,
            game_id INTEGER,  -- NOW NULLABLE!
            nba_game_id VARCHAR(50) NOT NULL,
            game_date DATETIME NOT NULL,
            minutes FLOAT,
            points INTEGER,
            rebounds INTEGER,
            assists INTEGER,
            steals INTEGER,
            blocks INTEGER,
            turnovers INTEGER,
            fgm INTEGER,
            fga INTEGER,
            fg_pct FLOAT,
            fg3m INTEGER,
            fg3a INTEGER,
            fg3_pct FLOAT,
            ftm INTEGER,
            fta INTEGER,
            ft_pct FLOAT,
            season VARCHAR(10) NOT NULL,
            fetched_at DATETIME NOT NULL,
            FOREIGN KEY (player_id) REFERENCES players(id),
            FOREIGN KEY (game_id) REFERENCES games(id)
        )
    """)

    # Step 3: Copy data from old table (if any exists)
    print("  [3/4] Copying data from old table...")
    cursor.execute("""
        INSERT INTO player_game_stats
        SELECT * FROM player_game_stats_old
    """)
    rows_copied = cursor.rowcount
    print(f"      Copied {rows_copied} rows")

    # Step 4: Drop old table
    print("  [4/4] Dropping old table...")
    cursor.execute("DROP TABLE player_game_stats_old")

    conn.commit()
    print("\n[OK] Migration complete! game_id is now nullable.")

except Exception as e:
    conn.rollback()
    print(f"\n[ERROR] Migration failed: {e}")
    raise

finally:
    conn.close()
