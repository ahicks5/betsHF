"""
Debug ANY ungraded play - pass player name and stat type as arguments
Usage: python scripts/debug_ungraded_play.py "Player Name" "STAT_TYPE"
Example: python scripts/debug_ungraded_play.py "Precious Achiuwa" "FG3M"
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.db import get_session
from database.models import Play, PropLine, Player, Game, PlayerGameStats, Team
from datetime import datetime
import pytz
from sqlalchemy.orm import aliased

if len(sys.argv) < 2:
    print("Usage: python scripts/debug_ungraded_play.py \"Player Name\" [STAT_TYPE]")
    print('Example: python scripts/debug_ungraded_play.py "Precious Achiuwa" "FG3M"')
    sys.exit(1)

player_name = sys.argv[1]
stat_type = sys.argv[2] if len(sys.argv) > 2 else None

session = get_session()

print("\n" + "="*80)
print(f"DEBUGGING UNGRADED PLAYS FOR: {player_name.upper()}")
if stat_type:
    print(f"Stat Type: {stat_type}")
print("="*80 + "\n")

# Current times
utc_now = datetime.utcnow()
central = pytz.timezone('America/Chicago')
central_now = datetime.now(central)

print(f"Current UTC time: {utc_now}")
print(f"Current Central time: {central_now}")
print()

# Find the player
player = session.query(Player).filter(Player.full_name.like(f'%{player_name}%')).first()
if not player:
    print(f"[ERROR] Player '{player_name}' not found in database!")
    print("\nSearching for similar names:")
    similar = session.query(Player).filter(Player.full_name.like(f'%{player_name.split()[0]}%')).limit(5).all()
    for p in similar:
        print(f"  - {p.full_name}")
    sys.exit(1)

print(f"Player: {player.full_name}")
print(f"Player ID: {player.id}")
print(f"NBA Player ID: {player.nba_player_id}")
print()

# Find ungraded plays for this player
query = session.query(Play).filter(
    Play.player_name.like(f'%{player.full_name.split()[-1]}%'),  # Match by last name
    Play.was_correct == None,
    Play.recommendation != 'NO PLAY'
)

if stat_type:
    query = query.filter(Play.stat_type == stat_type)

ungraded_plays = query.all()

if not ungraded_plays:
    print(f"[INFO] No ungraded plays found for {player.full_name}")
    if stat_type:
        print(f"      with stat type {stat_type}")
    sys.exit(0)

print(f"[FOUND] {len(ungraded_plays)} ungraded play(s)\n")

# Debug each play
for i, play in enumerate(ungraded_plays, 1):
    print(f"\n{'='*80}")
    print(f"PLAY #{i}: {play.player_name} {play.stat_type} {play.recommendation} {play.line_value}")
    print(f"{'='*80}")
    print(f"Play ID: {play.id}")
    print(f"Created: {play.created_at}")
    print(f"Confidence: {play.confidence}")
    print()

    # Get PropLine
    prop_line = session.query(PropLine).filter_by(id=play.prop_line_id).first()
    if not prop_line:
        print("[ERROR] PropLine not found!")
        continue

    print(f"PropLine ID: {prop_line.id}")
    print(f"  Bookmaker: {prop_line.bookmaker}")
    print()

    # Get Game
    game = session.query(Game).filter_by(id=prop_line.game_id).first()
    if not game:
        print("[ERROR] Game not found!")
        continue

    # Get team names
    away_team = session.query(Team).filter_by(id=game.away_team_id).first()
    home_team = session.query(Team).filter_by(id=game.home_team_id).first()
    matchup = f"{away_team.abbreviation} @ {home_team.abbreviation}" if away_team and home_team else "Unknown"

    print(f"Game: {matchup}")
    print(f"  Game ID: {game.id}")
    print(f"  NBA Game ID: {game.nba_game_id}")
    print(f"  Game Date (UTC): {game.game_date}")

    # Convert to Central time
    utc = pytz.UTC
    if game.game_date.tzinfo is None:
        game_date_utc = utc.localize(game.game_date)
    else:
        game_date_utc = game.game_date

    game_date_central = game_date_utc.astimezone(central)
    game_date_only = game_date_central.date()

    print(f"  Game Date (Central): {game_date_central}")
    print(f"  Game Date (date only): {game_date_only}")

    # Calculate hours since game
    hours_since = (utc_now - game.game_date).total_seconds() / 3600
    print(f"  Hours since game: {hours_since:.1f}")
    print(f"  Is old enough (>4 hours)? {hours_since >= 4}")
    print()

    # Check for PlayerGameStats
    print("CHECKING FOR PLAYER GAME STATS:")
    print(f"  Player ID: {player.id}")
    print(f"  Looking for game date: {game_date_only}")
    print()

    # Try matching by date (the fixed logic)
    from sqlalchemy import func
    game_stats = session.query(PlayerGameStats).filter(
        PlayerGameStats.player_id == player.id,
        func.date(PlayerGameStats.game_date) == game_date_only
    ).first()

    if game_stats:
        print("[FOUND] Game stats exist!")
        print(f"  Game Date: {game_stats.game_date}")
        print(f"  NBA Game ID: {game_stats.nba_game_id}")
        print(f"  Points: {game_stats.points}")
        print(f"  Rebounds: {game_stats.rebounds}")
        print(f"  Assists: {game_stats.assists}")
        print(f"  3PM (FG3M): {game_stats.fg3m}")
        print(f"  Fetched At: {game_stats.fetched_at}")
        print()

        # Check if we can grade it
        stat_map = {
            'points': 'points', 'pts': 'points',
            'rebounds': 'rebounds', 'reb': 'rebounds',
            'assists': 'assists', 'ast': 'assists',
            'threes': 'fg3m', '3ptm': 'fg3m', 'fg3m': 'fg3m',
            'steals': 'steals', 'stl': 'steals',
            'blocks': 'blocks', 'blk': 'blocks'
        }

        stat_field = stat_map.get(play.stat_type.lower())
        if stat_field:
            actual = getattr(game_stats, stat_field)
            if actual is not None:
                print(f"GRADING CHECK:")
                print(f"  Stat Type: {play.stat_type} -> {stat_field}")
                print(f"  Line: {play.line_value}")
                print(f"  Actual: {actual}")
                print(f"  Recommendation: {play.recommendation}")

                if play.recommendation == 'OVER':
                    would_win = actual > play.line_value
                else:
                    would_win = actual < play.line_value

                print(f"  Result: {'WIN' if would_win else 'LOSS'}")
                print(f"\n>>> THIS PLAY SHOULD BE GRADED! <<<")
            else:
                print(f"[ERROR] {stat_field} is NULL - cannot grade")
        else:
            print(f"[ERROR] Unknown stat type mapping: {play.stat_type}")
    else:
        print("[NOT FOUND] No game stats for this game date!")

        # Check what stats we DO have for this player
        all_stats = session.query(PlayerGameStats).filter_by(
            player_id=player.id
        ).order_by(PlayerGameStats.game_date.desc()).limit(10).all()

        print(f"\nRecent games for {player.full_name} ({len(all_stats)} total):")
        for j, stat in enumerate(all_stats, 1):
            print(f"  {j}. {stat.game_date} | NBA Game ID: {stat.nba_game_id} | PTS: {stat.points} | 3PM: {stat.fg3m}")

        print(f"\n>>> PROBLEM: Stats for {game_date_only} not fetched! <<<")
        print(f"    The player may not have played in this game")
        print(f"    Or the sync didn't fetch this specific game")

print("\n" + "="*80)
print("DIAGNOSIS COMPLETE")
print("="*80)
