"""
Sync NBA Player Stats Script
Runs twice daily (4 AM, 6 PM) to:
1. Fetch and cache player game stats from NBA API
2. Auto-grade any ungraded plays using fresh stats
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from data.nba_stats import sync_all_active_players, get_player_stat_distribution
from database.db import get_session
from database.models import Play, PropLine, Player, PlayerGameStats
from datetime import datetime, timedelta
import pytz


def grade_ungraded_plays():
    """
    Automatically grade plays that are ready for results
    Uses cached PlayerGameStats data
    """
    session = get_session()

    print("\n[GRADING] Checking for ungraded plays...")

    # Get ungraded plays for completed games
    # Only check plays from the last 7 days to avoid re-checking old DNP cases
    from datetime import datetime, timedelta
    seven_days_ago = datetime.utcnow() - timedelta(days=7)

    ungraded_plays = session.query(Play).filter(
        Play.was_correct == None,
        Play.recommendation != 'NO PLAY',
        Play.created_at >= seven_days_ago  # Only check recent plays
    ).all()

    if not ungraded_plays:
        print("[GRADING] No ungraded plays found")
        return 0

    print(f"[GRADING] Found {len(ungraded_plays)} ungraded plays (last 7 days)")

    graded_count = 0
    not_ready_count = 0

    for play in ungraded_plays:
        try:
            # Get the prop line
            prop_line = session.query(PropLine).filter_by(id=play.prop_line_id).first()
            if not prop_line:
                continue

            # Get the game
            from database.models import Game
            game = session.query(Game).filter_by(id=prop_line.game_id).first()
            if not game:
                continue

            # Check if game is old enough (at least 4 hours ago)
            hours_since_game = (datetime.utcnow() - game.game_date).total_seconds() / 3600
            if hours_since_game < 4:
                not_ready_count += 1
                continue

            # Get player
            player = session.query(Player).filter_by(id=prop_line.player_id).first()
            if not player:
                continue

            # Get the player's stats for this specific game
            # NOTE: We match by player + game DATE (not NBA Game ID) because:
            # - Odds API gives us one NBA game ID format (hash)
            # - NBA API gives us a different NBA game ID format (official code)
            # So we match by the date instead
            #
            # IMPORTANT: Game dates are stored in UTC, but NBA game dates are in local time
            # Convert game.game_date to Central time to get the actual game date
            from sqlalchemy import func

            utc = pytz.UTC
            central = pytz.timezone('America/Chicago')

            # Make game_date timezone-aware if it isn't already
            if game.game_date.tzinfo is None:
                game_date_utc = utc.localize(game.game_date)
            else:
                game_date_utc = game.game_date

            # Convert to Central time and extract date
            game_date_central = game_date_utc.astimezone(central)
            game_date_only = game_date_central.date()

            game_stats = session.query(PlayerGameStats).filter(
                PlayerGameStats.player_id == player.id,
                func.date(PlayerGameStats.game_date) == game_date_only
            ).first()

            if not game_stats:
                # Check if player has ANY stats (to differentiate DNP vs not synced)
                has_any_stats = session.query(PlayerGameStats).filter_by(
                    player_id=player.id
                ).count() > 0

                if has_any_stats:
                    # Player has stats for other games but not this one - likely DNP
                    print(f"  [DNP] {player.full_name} - {play.stat_type} (player did not play)")
                    # Don't grade - bet would be voided/pushed by sportsbook
                    continue
                else:
                    # No stats at all - not synced yet
                    not_ready_count += 1
                    continue

            # Map prop types to stat fields
            stat_map = {
                'points': 'points',
                'pts': 'points',
                'rebounds': 'rebounds',
                'reb': 'rebounds',
                'assists': 'assists',
                'ast': 'assists',
                'threes': 'fg3m',
                '3ptm': 'fg3m',
                'fg3m': 'fg3m',  # FIX: Add fg3m mapping
                'steals': 'steals',
                'stl': 'steals',
                'blocks': 'blocks',
                'blk': 'blocks'
            }

            stat_field = stat_map.get(play.stat_type.lower())
            if not stat_field:
                print(f"[WARNING] Unknown stat type: {play.stat_type}")
                continue

            # Get actual result
            actual_result = getattr(game_stats, stat_field)
            if actual_result is None:
                not_ready_count += 1
                continue

            # Grade the play
            was_correct = None
            if play.recommendation == 'OVER':
                was_correct = actual_result > play.line_value
            elif play.recommendation == 'UNDER':
                was_correct = actual_result < play.line_value

            if was_correct is not None:
                play.actual_result = float(actual_result)
                play.result_collected_at = datetime.utcnow()
                play.was_correct = was_correct

                result_emoji = "✅" if was_correct else "❌"
                print(f"  {result_emoji} {player.full_name} {play.stat_type.upper()} {play.recommendation} {play.line_value:.1f} → {actual_result} {'WIN' if was_correct else 'LOSS'}")

                graded_count += 1

        except Exception as e:
            print(f"[ERROR] Failed to grade play {play.id}: {e}")
            continue

    session.commit()

    print(f"\n[GRADING COMPLETE]")
    print(f"  ✓ Graded: {graded_count}")
    print(f"  ⏳ Not ready: {not_ready_count}")
    print(f"  Total: {len(ungraded_plays)}")

    return graded_count


def main():
    """
    Main sync process:
    1. Sync NBA stats for active players
    2. Grade ungraded plays
    """
    print("=" * 60)
    print("NBA STATS SYNC & AUTO-GRADING")
    print("=" * 60)
    print(f"Started at: {datetime.now()}")
    print()

    # Step 1: Sync NBA stats
    synced = sync_all_active_players()

    # Step 2: Grade plays
    graded = grade_ungraded_plays()

    print("\n" + "=" * 60)
    print(f"SYNC COMPLETE")
    print(f"  Players synced: {synced}")
    print(f"  Plays graded: {graded}")
    print(f"Finished at: {datetime.now()}")
    print("=" * 60)


if __name__ == "__main__":
    main()
