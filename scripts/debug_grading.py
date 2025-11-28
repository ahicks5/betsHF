"""
Debug script to figure out why plays aren't being graded
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.db import get_session
from database.models import Play, PropLine, Player, Game, PlayerGameStats
from datetime import datetime, timedelta
import pytz

session = get_session()

# Get ungraded plays
ungraded_plays = session.query(Play).filter(
    Play.was_correct == None,
    Play.recommendation != 'NO PLAY'
).all()

print(f"\n{'='*80}")
print(f"DEBUGGING {len(ungraded_plays)} UNGRADED PLAYS")
print(f"{'='*80}\n")
print(f"Current UTC time: {datetime.utcnow()}")
print(f"Current local time: {datetime.now()}")

central = pytz.timezone('America/Chicago')
print(f"Current Central time: {datetime.now(central)}")

for i, play in enumerate(ungraded_plays[:5], 1):  # Only check first 5
    print(f"\n{'-'*80}")
    print(f"PLAY #{i}: {play.player_name} {play.stat_type.upper()} {play.recommendation} {play.line_value}")
    print(f"{'-'*80}")

    # Get prop line
    prop_line = session.query(PropLine).filter_by(id=play.prop_line_id).first()
    if not prop_line:
        print("[ERROR] PropLine not found!")
        continue

    # Get game
    game = session.query(Game).filter_by(id=prop_line.game_id).first()
    if not game:
        print("[ERROR] Game not found!")
        continue

    print(f"Game ID: {game.id}")
    print(f"NBA Game ID: {game.nba_game_id}")
    print(f"Game Date (stored): {game.game_date}")
    print(f"Game Date type: {type(game.game_date)}")

    # Check hours since game
    hours_since = (datetime.utcnow() - game.game_date).total_seconds() / 3600
    print(f"Hours since game: {hours_since:.1f} hours")

    if hours_since < 4:
        print(f"[SKIP] Game too recent (< 4 hours) - SKIPPING")
        continue
    else:
        print(f"[OK] Game old enough ({hours_since:.1f} hours)")

    # Get player
    player = session.query(Player).filter_by(id=prop_line.player_id).first()
    if not player:
        print("[ERROR] Player not found!")
        continue

    print(f"Player: {player.full_name} (ID: {player.id}, NBA ID: {player.nba_player_id})")

    # Check if we have stats for this game
    game_stats = session.query(PlayerGameStats).filter_by(
        player_id=player.id,
        nba_game_id=game.nba_game_id
    ).first()

    if not game_stats:
        print(f"[ERROR] NO STATS FOUND for this game!")

        # Check what stats we DO have for this player
        all_player_stats = session.query(PlayerGameStats).filter_by(
            player_id=player.id
        ).order_by(PlayerGameStats.game_date.desc()).limit(5).all()

        print(f"\n   Recent games for {player.full_name}:")
        for gs in all_player_stats:
            print(f"   - {gs.game_date} | NBA Game ID: {gs.nba_game_id} | PTS: {gs.points}")

        print(f"\n   Looking for NBA Game ID: {game.nba_game_id}")
        print(f"   ^^^ THIS IS THE PROBLEM - Stats not fetched for this game yet!")

    else:
        print(f"[OK] Stats found!")
        print(f"   Points: {game_stats.points}")
        print(f"   Rebounds: {game_stats.rebounds}")
        print(f"   Assists: {game_stats.assists}")
        print(f"   3PM: {game_stats.fg3m}")
        print(f"   Game Date: {game_stats.game_date}")
        print(f"   Fetched At: {game_stats.fetched_at}")

        # Try to grade it
        stat_map = {
            'points': 'points', 'pts': 'points',
            'rebounds': 'rebounds', 'reb': 'rebounds',
            'assists': 'assists', 'ast': 'assists',
            'threes': 'fg3m', '3ptm': 'fg3m'
        }

        stat_field = stat_map.get(play.stat_type.lower())
        if stat_field:
            actual = getattr(game_stats, stat_field)
            print(f"\n   Stat Type: {play.stat_type} → {stat_field}")
            print(f"   Line: {play.line_value}")
            print(f"   Actual: {actual}")
            print(f"   Recommendation: {play.recommendation}")

            if play.recommendation == 'OVER':
                result = actual > play.line_value
            else:
                result = actual < play.line_value

            print(f"   Result: {'WIN' if result else 'LOSS'}")
        else:
            print(f"   [ERROR] Unknown stat type: {play.stat_type}")

print(f"\n{'='*80}")
print("DEBUG COMPLETE")
print(f"{'='*80}\n")
