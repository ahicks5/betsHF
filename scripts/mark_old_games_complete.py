"""
Mark Old Games as Completed

Simple utility to mark games that started more than 4 hours ago as completed.
Run this to clean up your database.
"""
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.db import get_session, close_session
from database.models import Game
from datetime import datetime, timedelta
import pytz


def mark_old_games_complete():
    """Mark all games that started more than 4 hours ago as completed"""
    session = get_session()

    # Get current time
    now_utc = datetime.now(pytz.utc)
    four_hours_ago = now_utc - timedelta(hours=4)

    # Find games that started more than 4 hours ago and aren't marked complete
    old_games = session.query(Game).filter(
        Game.game_date < four_hours_ago.replace(tzinfo=None),
        Game.is_completed == False
    ).all()

    if not old_games:
        print("No old games to mark as completed")
        close_session()
        return

    print(f"Found {len(old_games)} old games to mark as completed:\n")

    for game in old_games:
        game.is_completed = True
        game_time = pytz.utc.localize(game.game_date) if game.game_date.tzinfo is None else game.game_date
        hours_ago = (now_utc - game_time).total_seconds() / 3600
        print(f"  - Game {game.nba_game_id} from {game.game_date} ({hours_ago:.1f} hours ago)")

    session.commit()
    print(f"\n[OK] Marked {len(old_games)} games as completed")
    close_session()


if __name__ == "__main__":
    mark_old_games_complete()
