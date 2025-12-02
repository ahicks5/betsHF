"""
Collect Actual Results for Completed Games

Fetches actual player stats for completed games and updates plays
with actual results and whether the bet was correct.
"""
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.db import get_session, close_session
from database.models import Play, PropLine, Game, Player
from services.nba_api import NBAApiClient
from datetime import datetime, timedelta
import time


def collect_results_for_date(target_date=None, days_back=1):
    """
    Collect actual results for plays that need grading

    Args:
        target_date: Date to collect results for (optional - if None, gets all ungraded plays)
        days_back: How many days back to look (default 1 for yesterday)
    """
    session = get_session()
    nba_client = NBAApiClient()

    from app import LOCAL_TIMEZONE
    import pytz

    # If no target date specified, get ALL plays that need results
    if target_date is None:
        print(f"=== Collecting Results for ALL Ungraded Plays ===\n")

        # Get all plays without results where the game is completed or old
        now_utc = datetime.now(pytz.utc)
        four_hours_ago = now_utc - timedelta(hours=4)

        plays = session.query(Play).join(
            PropLine, Play.prop_line_id == PropLine.id
        ).join(
            Game, PropLine.game_id == Game.id
        ).filter(
            Play.was_correct == None,  # No results yet
            (Game.is_completed == True) | (Game.game_date < four_hours_ago.replace(tzinfo=None))  # Game is done
        ).all()

        target_date_str = "all completed games"
    else:
        # Get plays from specific date
        print(f"=== Collecting Results for {target_date} ===\n")

        target_start = LOCAL_TIMEZONE.localize(datetime.combine(target_date, datetime.min.time()))
        target_end = LOCAL_TIMEZONE.localize(datetime.combine(target_date, datetime.max.time()))
        target_start_utc = target_start.astimezone(pytz.utc).replace(tzinfo=None)
        target_end_utc = target_end.astimezone(pytz.utc).replace(tzinfo=None)

        plays = session.query(Play).filter(
            Play.created_at >= target_start_utc,
            Play.created_at <= target_end_utc,
            Play.was_correct == None  # Only get plays without results
        ).all()

        target_date_str = str(target_date)

    if not plays:
        print(f"No ungraded plays found for {target_date_str}")
        close_session()
        return

    print(f"Found {len(plays)} plays to grade\n")

    updated_count = 0
    skipped_count = 0
    error_count = 0

    for play in plays:
        try:
            # Get the prop line to find the game
            prop_line = session.query(PropLine).filter_by(id=play.prop_line_id).first()
            if not prop_line:
                print(f"[SKIP] No prop line found for play {play.id}")
                skipped_count += 1
                continue

            # Get the game
            game = session.query(Game).filter_by(id=prop_line.game_id).first()
            if not game:
                print(f"[SKIP] No game found for play {play.id}")
                skipped_count += 1
                continue

            # Check if game is completed
            if not game.is_completed:
                # Check if game date was more than 4 hours ago (game should be done)
                game_time = game.game_date
                if game_time.tzinfo is None:
                    game_time = pytz.utc.localize(game_time)

                hours_since_game = (datetime.now(pytz.utc) - game_time).total_seconds() / 3600

                if hours_since_game > 4:
                    # Game should be done, mark it as completed
                    game.is_completed = True
                    session.commit()
                else:
                    print(f"[SKIP] Game not completed yet: {play.player_name}")
                    skipped_count += 1
                    continue

            # Get player
            player = session.query(Player).filter_by(id=prop_line.player_id).first()
            if not player:
                print(f"[SKIP] No player found for play {play.id}")
                skipped_count += 1
                continue

            # Fetch actual game stats for the player on the game date
            # Map prop types to NBA API column names
            stat_map = {
                'points': 'PTS',
                'rebounds': 'REB',
                'assists': 'AST',
                'threes': 'FG3M',
                # Also handle if already in NBA format
                'PTS': 'PTS',
                'REB': 'REB',
                'AST': 'AST',
                'FG3M': 'FG3M',
                # Handle variations
                'pts': 'PTS',
                'reb': 'REB',
                'ast': 'AST',
                'fg3m': 'FG3M'
            }

            stat_column = stat_map.get(play.stat_type)
            if not stat_column:
                print(f"[SKIP] Unknown stat type: {play.stat_type}")
                skipped_count += 1
                continue

            # Get game log for the specific game date
            # Convert UTC game date to local time for NBA API lookup
            from app import utc_to_local
            game_date_local = utc_to_local(game.game_date)

            # NBA API uses format like "Nov 25, 2025" not "2025-11-25"
            game_date_str_nba = game_date_local.strftime('%b %d, %Y')  # "Nov 25, 2025"
            game_date_str_display = game_date_local.strftime('%Y-%m-%d')  # For display

            print(f"Fetching stats for {player.full_name} on {game_date_str_display}...")
            time.sleep(0.6)  # Rate limiting

            # Try current season first, then previous season
            game_logs_df = nba_client.get_player_game_log(
                player_id=player.nba_player_id,
                season='2025-26'
            )

            # If no games in current season, try previous season
            if game_logs_df.empty:
                game_logs_df = nba_client.get_player_game_log(
                    player_id=player.nba_player_id,
                    season='2024-25'
                )

            # Find the game on the specific date (DataFrame)
            actual_value = None
            if not game_logs_df.empty:
                for _, log in game_logs_df.iterrows():
                    log_date = log.get('GAME_DATE', '')
                    # Match NBA API format: "Nov 25, 2025"
                    if log_date == game_date_str_nba:
                        actual_value = log.get(stat_column, 0)
                        if actual_value is None:
                            actual_value = 0
                        actual_value = float(actual_value)
                        break

            if actual_value is None:
                print(f"[SKIP] No game log found for {player.full_name} on {game_date_str_display}")
                skipped_count += 1
                continue

            # Determine if the bet was correct
            line_value = play.line_value
            recommendation = play.recommendation

            was_correct = None
            if recommendation == 'OVER':
                was_correct = actual_value > line_value
            elif recommendation == 'UNDER':
                was_correct = actual_value < line_value
            elif recommendation == 'NO PLAY':
                # For NO PLAY, record the result but don't mark as correct/incorrect
                was_correct = None
            else:
                print(f"[SKIP] Unknown recommendation: {recommendation}")
                skipped_count += 1
                continue

            # Update the play
            play.actual_result = actual_value
            play.was_correct = was_correct
            play.result_collected_at = datetime.utcnow()

            # Lock the play since we now have results
            if not play.is_locked:
                play.is_locked = True
                play.locked_at = datetime.utcnow()

            if was_correct is None:
                result_str = "SKIP"
            else:
                result_str = "WIN" if was_correct else "LOSS"
            print(f"[{result_str}] {player.full_name} {play.stat_type} {recommendation} {line_value} (Actual: {actual_value})")

            updated_count += 1

        except Exception as e:
            print(f"[ERROR] Failed to process play {play.id}: {e}")
            error_count += 1
            continue

    # Commit all updates
    session.commit()

    print(f"\n=== Summary ===")
    print(f"Updated: {updated_count}")
    print(f"Skipped: {skipped_count}")
    print(f"Errors: {error_count}")

    if updated_count > 0:
        # Show win rate for the graded plays BY MODEL
        graded_plays = [p for p in plays if p.was_correct is not None]
        if graded_plays:
            print(f"\n=== Results by Model ===")

            # Group by model
            model_results = {}
            for p in graded_plays:
                model = p.model_name or 'pulsar_v1'  # Default for old plays
                if model not in model_results:
                    model_results[model] = {'wins': 0, 'losses': 0, 'total': 0}
                model_results[model]['total'] += 1
                if p.was_correct:
                    model_results[model]['wins'] += 1
                else:
                    model_results[model]['losses'] += 1

            for model, stats in model_results.items():
                win_rate = (stats['wins'] / stats['total'] * 100) if stats['total'] > 0 else 0
                print(f"{model}: {stats['wins']}/{stats['total']} ({win_rate:.1f}%)")

    close_session()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Collect actual results for completed games')
    parser.add_argument('--date', type=str, help='Date to collect results for (YYYY-MM-DD). If not specified, collects ALL ungraded plays.', default=None)
    parser.add_argument('--days-back', type=int, help='How many days back to look (only used with --date)', default=1)

    args = parser.parse_args()

    target_date = None
    if args.date:
        target_date = datetime.strptime(args.date, '%Y-%m-%d').date()
    # If no date specified, target_date stays None and script will get ALL ungraded plays

    collect_results_for_date(target_date, args.days_back)
