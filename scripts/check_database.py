"""
Database Diagnostic Tool

Check what's in the database and when plays were created
"""
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.db import get_session, close_session
from database.models import Play, Game
from datetime import datetime
import pytz

# Import timezone from app
from app import LOCAL_TIMEZONE, utc_to_local


def check_database():
    """Show what's in the database"""
    session = get_session()

    print("=== DATABASE DIAGNOSTIC ===\n")

    # Get all plays
    all_plays = session.query(Play).order_by(Play.created_at.desc()).all()

    if not all_plays:
        print("NO PLAYS IN DATABASE")
        close_session()
        return

    print(f"Total plays in database: {len(all_plays)}\n")

    # Get current time
    now_local = datetime.now(LOCAL_TIMEZONE)
    today_local = now_local.date()

    # Group by local date
    plays_by_date = {}
    for play in all_plays:
        local_dt = utc_to_local(play.created_at)
        date = local_dt.date()
        if date not in plays_by_date:
            plays_by_date[date] = []
        plays_by_date[date].append(play)

    print(f"Plays grouped by date (in {LOCAL_TIMEZONE}):\n")

    for date in sorted(plays_by_date.keys(), reverse=True):
        plays = plays_by_date[date]
        is_today = (date == today_local)
        date_label = "TODAY" if is_today else "PAST"

        # Count plays with results
        with_results = len([p for p in plays if p.actual_result is not None])
        wins = len([p for p in plays if p.was_correct == True])
        losses = len([p for p in plays if p.was_correct == False])

        print(f"  [{date_label}] {date}: {len(plays)} plays")
        print(f"           Results: {with_results}/{len(plays)} graded")
        if with_results > 0:
            print(f"           Win/Loss: {wins}W - {losses}L")
        print()

    # Check games
    print("\n=== GAMES ===\n")
    all_games = session.query(Game).order_by(Game.game_date.desc()).all()

    if not all_games:
        print("NO GAMES IN DATABASE")
    else:
        print(f"Total games: {len(all_games)}\n")

        games_by_status = {
            'completed': len([g for g in all_games if g.is_completed]),
            'not_completed': len([g for g in all_games if not g.is_completed])
        }

        print(f"Completed: {games_by_status['completed']}")
        print(f"Not completed: {games_by_status['not_completed']}\n")

        # Show recent games
        print("Recent games:")
        for game in all_games[:5]:
            game_time_local = utc_to_local(game.game_date)
            status = "DONE" if game.is_completed else "PENDING"
            print(f"  [{status}] {game.nba_game_id} at {game_time_local}")

    # Check what history page would show
    print("\n=== HISTORY PAGE ANALYSIS ===\n")

    past_plays = [p for date, plays in plays_by_date.items() if date < today_local for p in plays]

    if past_plays:
        print(f"History page SHOULD show {len(past_plays)} plays from previous days")

        # Group by date
        past_by_date = {}
        for play in past_plays:
            local_dt = utc_to_local(play.created_at)
            date = local_dt.date()
            if date not in past_by_date:
                past_by_date[date] = []
            past_by_date[date].append(play)

        for date in sorted(past_by_date.keys(), reverse=True):
            plays = past_by_date[date]
            with_results = len([p for p in plays if p.actual_result is not None])
            print(f"  {date}: {len(plays)} plays ({with_results} with results)")
    else:
        print("History page would be EMPTY (no plays from previous days)")
        print("All plays are from today!")

    close_session()


if __name__ == "__main__":
    check_database()
