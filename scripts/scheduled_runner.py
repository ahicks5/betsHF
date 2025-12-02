"""
Smart Scheduled Runner for NBA Props

This script intelligently runs the right tasks based on time of day and game schedule.
Run this hourly via Heroku Scheduler and it will determine what needs to be done.

Schedule Logic:
- GRADE RESULTS: 2 hours after first game start through 2 hours after last game, plus morning
- GENERATE PICKS: Morning (10am) + 2 hours before first game
- COLLECT PROPS: Same as generate picks (props needed for picks)
- SYNC STATS: Morning only (stats don't change during day)

Usage:
    python scripts/scheduled_runner.py           # Auto-detect what to run
    python scripts/scheduled_runner.py --force-picks    # Force pick generation
    python scripts/scheduled_runner.py --force-grade    # Force grading
    python scripts/scheduled_runner.py --force-all      # Run everything
    python scripts/scheduled_runner.py --dry-run        # Show what would run without doing it
"""
import sys
import argparse
from pathlib import Path
from datetime import datetime, timedelta

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytz

# Configuration
LOCAL_TIMEZONE = pytz.timezone('America/Chicago')  # Central Time

# Time windows (in local time)
MORNING_PICKS_HOUR = 10  # 10 AM - morning pick generation
HOURS_BEFORE_GAME_FOR_PICKS = 2  # Generate picks 2 hours before first game
HOURS_AFTER_GAME_FOR_GRADING = 2  # Grade results 2 hours after game start
MORNING_GRADE_HOUR = 9  # 9 AM - morning grading run


def get_local_now():
    """Get current time in local timezone"""
    return datetime.now(LOCAL_TIMEZONE)


def get_todays_game_times():
    """Get today's game start times from database"""
    from database.db import get_session
    from database.models import Game

    session = get_session()
    now = get_local_now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1)

    # Convert to UTC for query
    today_start_utc = today_start.astimezone(pytz.utc).replace(tzinfo=None)
    today_end_utc = today_end.astimezone(pytz.utc).replace(tzinfo=None)

    games = session.query(Game).filter(
        Game.game_date >= today_start_utc,
        Game.game_date < today_end_utc
    ).order_by(Game.game_date).all()

    # Convert to local times
    game_times = []
    for game in games:
        if game.game_date.tzinfo is None:
            game_time = pytz.utc.localize(game.game_date)
        else:
            game_time = game.game_date
        game_times.append(game_time.astimezone(LOCAL_TIMEZONE))

    session.close()
    return game_times


def should_generate_picks(now, game_times, force=False):
    """
    Determine if we should generate picks now

    Conditions:
    1. Morning run (10 AM)
    2. 2 hours before first game
    """
    if force:
        return True, "Forced pick generation"

    current_hour = now.hour

    # Morning run
    if current_hour == MORNING_PICKS_HOUR:
        return True, f"Morning pick generation ({MORNING_PICKS_HOUR}:00)"

    # 2 hours before first game
    if game_times:
        first_game = game_times[0]
        hours_until_first = (first_game - now).total_seconds() / 3600

        if 1.5 <= hours_until_first <= 2.5:  # Window around 2 hours
            return True, f"2 hours before first game ({first_game.strftime('%I:%M %p')})"

    return False, "Not in pick generation window"


def should_grade_results(now, game_times, force=False):
    """
    Determine if we should grade results now

    Conditions:
    1. Morning run (9 AM) - catch overnight results
    2. 2 hours after any game start through 2 hours after last game
    """
    if force:
        return True, "Forced grading"

    current_hour = now.hour

    # Morning run
    if current_hour == MORNING_GRADE_HOUR:
        return True, f"Morning grading run ({MORNING_GRADE_HOUR}:00)"

    # During/after games window
    if game_times:
        first_game = game_times[0]
        last_game = game_times[-1]

        # Grading window: 2 hours after first game start through 2 hours after last game
        grade_window_start = first_game + timedelta(hours=HOURS_AFTER_GAME_FOR_GRADING)
        grade_window_end = last_game + timedelta(hours=HOURS_AFTER_GAME_FOR_GRADING + 3)  # Extra buffer

        if grade_window_start <= now <= grade_window_end:
            return True, f"In grading window ({grade_window_start.strftime('%I:%M %p')} - {grade_window_end.strftime('%I:%M %p')})"

    return False, "Not in grading window"


def should_sync_stats(now, force=False):
    """
    Determine if we should sync NBA stats

    Conditions:
    1. Morning only (same as morning picks)
    """
    if force:
        return True, "Forced stats sync"

    current_hour = now.hour

    if current_hour == MORNING_PICKS_HOUR:
        return True, f"Morning stats sync ({MORNING_PICKS_HOUR}:00)"

    return False, "Not in stats sync window"


def run_collect_props():
    """Run prop collection"""
    print("\n" + "=" * 60)
    print("COLLECTING TODAY'S PROPS")
    print("=" * 60)

    from scripts.collect_today import initialize_teams_and_players, collect_todays_games_and_props
    from database.db import init_db

    init_db()
    initialize_teams_and_players()
    collect_todays_games_and_props()


def run_sync_stats():
    """Run NBA stats sync"""
    print("\n" + "=" * 60)
    print("SYNCING NBA STATS")
    print("=" * 60)

    from scripts.sync_nba_stats import sync_all_player_stats
    sync_all_player_stats()


def run_find_plays():
    """Run play generation for all models"""
    print("\n" + "=" * 60)
    print("GENERATING PLAYS FOR ALL MODELS")
    print("=" * 60)

    from scripts.find_plays import analyze_all_props
    analyze_all_props()


def run_lock_started_games():
    """Lock plays for games that have started"""
    print("\n" + "=" * 60)
    print("LOCKING PLAYS FOR STARTED GAMES")
    print("=" * 60)

    from database.db import get_session
    from database.models import Play, PropLine, Game

    session = get_session()
    now = datetime.now(pytz.utc)

    # Find all unlocked plays where the game has started
    plays_to_lock = session.query(Play).join(
        PropLine, Play.prop_line_id == PropLine.id
    ).join(
        Game, PropLine.game_id == Game.id
    ).filter(
        Play.is_locked == False,  # Not yet locked
        Game.game_date < now  # Game has started (game_date is in the past)
    ).all()

    if not plays_to_lock:
        print("No plays to lock")
        session.close()
        return

    locked_count = 0
    for play in plays_to_lock:
        play.is_locked = True
        play.locked_at = datetime.utcnow()
        locked_count += 1

    session.commit()
    print(f"[OK] Locked {locked_count} plays")
    session.close()


def run_grade_results():
    """Run result grading"""
    print("\n" + "=" * 60)
    print("GRADING RESULTS")
    print("=" * 60)

    # First lock any plays that should be locked
    run_lock_started_games()

    from scripts.collect_results import collect_results_for_date
    collect_results_for_date()  # None = all ungraded


def main():
    parser = argparse.ArgumentParser(description='Smart scheduled runner for NBA props')
    parser.add_argument('--force-picks', action='store_true', help='Force pick generation')
    parser.add_argument('--force-grade', action='store_true', help='Force grading')
    parser.add_argument('--force-all', action='store_true', help='Run everything')
    parser.add_argument('--dry-run', action='store_true', help='Show what would run without doing it')

    args = parser.parse_args()

    now = get_local_now()
    print(f"Scheduled Runner - {now.strftime('%Y-%m-%d %I:%M %p %Z')}")
    print("=" * 60)

    # Get today's games
    try:
        game_times = get_todays_game_times()
        if game_times:
            print(f"\nToday's games: {len(game_times)}")
            print(f"  First game: {game_times[0].strftime('%I:%M %p')}")
            print(f"  Last game:  {game_times[-1].strftime('%I:%M %p')}")
        else:
            print("\nNo games found for today")
    except Exception as e:
        print(f"\nCouldn't fetch game times: {e}")
        game_times = []

    # Determine what to run
    tasks_to_run = []

    # Check picks
    should_picks, picks_reason = should_generate_picks(now, game_times, args.force_picks or args.force_all)
    print(f"\nPick generation: {'YES' if should_picks else 'NO'} - {picks_reason}")
    if should_picks:
        tasks_to_run.append(('picks', run_find_plays))

    # Check grading
    should_grade, grade_reason = should_grade_results(now, game_times, args.force_grade or args.force_all)
    print(f"Result grading:  {'YES' if should_grade else 'NO'} - {grade_reason}")
    if should_grade:
        tasks_to_run.append(('grade', run_grade_results))

    # Check stats sync (only if we're generating picks)
    should_stats, stats_reason = should_sync_stats(now, args.force_all)
    print(f"Stats sync:      {'YES' if should_stats else 'NO'} - {stats_reason}")
    if should_stats:
        tasks_to_run.insert(0, ('stats', run_sync_stats))  # Stats first

    # Check prop collection (only if we're generating picks)
    if should_picks:
        print(f"Prop collection: YES - Required for picks")
        tasks_to_run.insert(0, ('props', run_collect_props))  # Props first

    if not tasks_to_run:
        print("\n[OK] Nothing to run at this time")
        return

    if args.dry_run:
        print(f"\n[DRY RUN] Would run: {', '.join(t[0] for t in tasks_to_run)}")
        return

    # Run tasks
    print(f"\n[RUNNING] Tasks: {', '.join(t[0] for t in tasks_to_run)}")

    for task_name, task_func in tasks_to_run:
        try:
            task_func()
            print(f"\n[OK] {task_name} completed")
        except Exception as e:
            print(f"\n[ERROR] {task_name} failed: {e}")

    print("\n" + "=" * 60)
    print("SCHEDULED RUN COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()
