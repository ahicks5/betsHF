"""
Migration: Clean up duplicate plays

This script finds and removes duplicate plays, keeping only one play per
player_name + stat_type + model_name + GAME combination.

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
from database.models import Play, PropLine, Game
from sqlalchemy import func, text


def cleanup_duplicates(dry_run=False):
    """Find and remove duplicate plays"""
    session = get_session()

    print("=" * 60)
    print("CLEANUP: Removing duplicate plays")
    print("=" * 60)

    print("\nGrouping by: player_name + stat_type + model_name + game_id")

    # Find all player + stat + model + game combinations that have duplicates
    duplicates = session.query(
        Play.player_name,
        Play.stat_type,
        Play.model_name,
        PropLine.game_id,
        func.count(Play.id).label('count')
    ).join(
        PropLine, Play.prop_line_id == PropLine.id
    ).group_by(
        Play.player_name,
        Play.stat_type,
        Play.model_name,
        PropLine.game_id
    ).having(
        func.count(Play.id) > 1
    ).all()

    if not duplicates:
        print("\nNo duplicates found!")
        session.close()
        return

    print(f"\nFound {len(duplicates)} player+stat+game combinations with duplicates")

    total_removed = 0
    plays_to_delete = []

    for player_name, stat_type, model_name, game_id, count in duplicates:
        # Get game info for display
        game = session.query(Game).filter(Game.id == game_id).first()
        game_date = game.game_date.strftime('%Y-%m-%d') if game else 'Unknown'

        # Get all plays for this combination
        plays = session.query(Play).join(
            PropLine, Play.prop_line_id == PropLine.id
        ).filter(
            Play.player_name == player_name,
            Play.stat_type == stat_type,
            Play.model_name == model_name,
            PropLine.game_id == game_id
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

        print(f"  {game_date} - {player_name} {stat_type} ({model_name}): {count} copies -> keeping ID {keep_play.id}")

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
    remaining_dups = session.query(
        Play.player_name,
        Play.stat_type,
        Play.model_name,
        PropLine.game_id,
        func.count(Play.id).label('count')
    ).join(
        PropLine, Play.prop_line_id == PropLine.id
    ).group_by(
        Play.player_name,
        Play.stat_type,
        Play.model_name,
        PropLine.game_id
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
