"""
Migration: Clean up duplicate plays

This script finds and removes duplicate plays, keeping only one play per
player_name + stat_type + model_name + DATE combination.

For duplicates, it keeps the one with results (was_correct is not None),
or the oldest one if none have results.

Usage: python scripts/migrations/cleanup_duplicate_plays.py
       python scripts/migrations/cleanup_duplicate_plays.py --dry-run
"""
import sys
import argparse
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from database.db import get_session
from database.models import Play
from sqlalchemy import func, text, cast, Date


def has_model_name_column(session):
    """Check if model_name column exists in plays table"""
    try:
        # Try to query the column - if it fails, column doesn't exist
        session.execute(text("SELECT model_name FROM plays LIMIT 1"))
        return True
    except Exception:
        session.rollback()
        return False


def cleanup_duplicates(dry_run=False):
    """Find and remove duplicate plays"""
    session = get_session()

    print("=" * 60)
    print("CLEANUP: Removing duplicate plays")
    print("=" * 60)

    # Check if model_name column exists
    has_model = has_model_name_column(session)

    if has_model:
        print("\nGrouping by: player_name + stat_type + model_name + date")
        # Find all player + stat + model + date combinations that have duplicates
        duplicates = session.query(
            Play.player_name,
            Play.stat_type,
            Play.model_name,
            cast(Play.created_at, Date).label('play_date'),
            func.count(Play.id).label('count')
        ).group_by(
            Play.player_name,
            Play.stat_type,
            Play.model_name,
            cast(Play.created_at, Date)
        ).having(
            func.count(Play.id) > 1
        ).all()
    else:
        print("\nGrouping by: player_name + stat_type + date only (model_name column not found)")
        # Find all player + stat + date combinations that have duplicates
        duplicates = session.query(
            Play.player_name,
            Play.stat_type,
            cast(Play.created_at, Date).label('play_date'),
            func.count(Play.id).label('count')
        ).group_by(
            Play.player_name,
            Play.stat_type,
            cast(Play.created_at, Date)
        ).having(
            func.count(Play.id) > 1
        ).all()

    if not duplicates:
        print("\nNo duplicates found!")
        session.close()
        return

    print(f"\nFound {len(duplicates)} player+stat+date combinations with duplicates")

    total_removed = 0
    plays_to_delete = []

    for dup_row in duplicates:
        if has_model:
            player_name, stat_type, model_name, play_date, count = dup_row
            # Get all plays for this combination on this date
            plays = session.query(Play).filter(
                Play.player_name == player_name,
                Play.stat_type == stat_type,
                Play.model_name == model_name,
                cast(Play.created_at, Date) == play_date
            ).order_by(Play.created_at).all()
        else:
            player_name, stat_type, play_date, count = dup_row
            model_name = "N/A"
            # Get all plays for this player + stat on this date
            plays = session.query(Play).filter(
                Play.player_name == player_name,
                Play.stat_type == stat_type,
                cast(Play.created_at, Date) == play_date
            ).order_by(Play.created_at).all()

        # Determine which one to keep:
        # 1. Prefer one with results (was_correct is not None)
        # 2. Otherwise keep the oldest one
        keep_play = None
        for play in plays:
            if play.was_correct is not None:
                keep_play = play
                break

        if keep_play is None:
            keep_play = plays[0]  # Keep oldest

        # Mark others for deletion
        for play in plays:
            if play.id != keep_play.id:
                plays_to_delete.append(play)
                total_removed += 1

        print(f"  {play_date} - {player_name} {stat_type} ({model_name}): {count} copies -> keeping 1")

    print(f"\nTotal plays to remove: {total_removed}")

    if dry_run:
        print("\n[DRY RUN] No changes made")
        session.close()
        return

    # Delete duplicates
    print("\nDeleting duplicates...")
    for play in plays_to_delete:
        session.delete(play)

    session.commit()
    print(f"[OK] Removed {total_removed} duplicate plays")

    # Verify
    if has_model:
        remaining_dups = session.query(
            Play.player_name,
            Play.stat_type,
            Play.model_name,
            cast(Play.created_at, Date),
            func.count(Play.id).label('count')
        ).group_by(
            Play.player_name,
            Play.stat_type,
            Play.model_name,
            cast(Play.created_at, Date)
        ).having(
            func.count(Play.id) > 1
        ).count()
    else:
        remaining_dups = session.query(
            Play.player_name,
            Play.stat_type,
            cast(Play.created_at, Date),
            func.count(Play.id).label('count')
        ).group_by(
            Play.player_name,
            Play.stat_type,
            cast(Play.created_at, Date)
        ).having(
            func.count(Play.id) > 1
        ).count()

    print(f"\nRemaining duplicates: {remaining_dups}")

    session.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Clean up duplicate plays')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be deleted without doing it')

    args = parser.parse_args()
    cleanup_duplicates(dry_run=args.dry_run)
