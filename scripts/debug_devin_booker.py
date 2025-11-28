"""
Debug Devin Booker's ungraded play on Heroku
Check exactly what's happening with the 11/26 game
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.db import get_session
from database.models import Play, PropLine, Player, Game, PlayerGameStats
from datetime import datetime
import pytz

session = get_session()

print("\n" + "="*80)
print("DEBUGGING DEVIN BOOKER - PTS OVER 33.5")
print("="*80 + "\n")

# Current times
utc_now = datetime.utcnow()
central = pytz.timezone('America/Chicago')
central_now = datetime.now(central)

print(f"Current UTC time: {utc_now}")
print(f"Current Central time: {central_now}")
print(f"Target game date: 11/26/2025 (Central Time)")
print()

# Find Devin Booker
player = session.query(Player).filter(Player.full_name.like('%Devin Booker%')).first()
if not player:
    print("[ERROR] Devin Booker not found in database!")
    sys.exit(1)

print(f"Player: {player.full_name}")
print(f"Player ID: {player.id}")
print(f"NBA Player ID: {player.nba_player_id}")
print()

# Find the play
play = session.query(Play).filter(
    Play.player_name.like('%Booker%'),
    Play.stat_type.in_(['PTS', 'points']),
    Play.line_value == 33.5,
    Play.was_correct == None
).first()

if not play:
    print("[ERROR] No ungraded Devin Booker PTS 33.5 play found!")
    print("\nSearching for ANY Booker plays:")
    all_booker_plays = session.query(Play).filter(Play.player_name.like('%Booker%')).all()
    for p in all_booker_plays:
        print(f"  - {p.player_name} {p.stat_type} {p.recommendation} {p.line_value} | Graded: {p.was_correct is not None}")
    sys.exit(1)

print(f"[FOUND] Play ID: {play.id}")
print(f"  Player: {play.player_name}")
print(f"  Stat: {play.stat_type} {play.recommendation} {play.line_value}")
print(f"  Confidence: {play.confidence}")
print(f"  Created: {play.created_at}")
print()

# Get PropLine
prop_line = session.query(PropLine).filter_by(id=play.prop_line_id).first()
if not prop_line:
    print("[ERROR] PropLine not found!")
    sys.exit(1)

print(f"PropLine ID: {prop_line.id}")
print(f"  Bookmaker: {prop_line.bookmaker}")
print(f"  Collected: {prop_line.collected_at}")
print()

# Get Game
game = session.query(Game).filter_by(id=prop_line.game_id).first()
if not game:
    print("[ERROR] Game not found!")
    sys.exit(1)

print(f"Game ID: {game.id}")
print(f"  NBA Game ID: {game.nba_game_id}")
print(f"  Game Date (stored in DB): {game.game_date}")
print(f"  Game Date type: {type(game.game_date)}")

# Check if game date is timezone-aware
if game.game_date.tzinfo:
    print(f"  Game Date timezone: {game.game_date.tzinfo}")
else:
    print(f"  Game Date timezone: None (naive datetime)")

# Calculate hours since game
hours_since = (utc_now - game.game_date).total_seconds() / 3600
print(f"  Hours since game: {hours_since:.1f}")
print(f"  Is old enough (>4 hours)? {hours_since >= 4}")
print()

# Check for PlayerGameStats
print("CHECKING FOR PLAYER GAME STATS:")
print(f"  Looking for player_id={player.id}, nba_game_id='{game.nba_game_id}'")
print()

game_stats = session.query(PlayerGameStats).filter_by(
    player_id=player.id,
    nba_game_id=game.nba_game_id
).first()

if game_stats:
    print("[FOUND] Game stats exist!")
    print(f"  Game Date: {game_stats.game_date}")
    print(f"  Points: {game_stats.points}")
    print(f"  Rebounds: {game_stats.rebounds}")
    print(f"  Assists: {game_stats.assists}")
    print(f"  Minutes: {game_stats.minutes}")
    print(f"  Fetched At: {game_stats.fetched_at}")
    print()

    # Check if we can grade it
    if game_stats.points is not None:
        print(f"GRADING CHECK:")
        print(f"  Line: {play.line_value}")
        print(f"  Actual: {game_stats.points}")
        print(f"  Recommendation: {play.recommendation}")

        if play.recommendation == 'OVER':
            would_win = game_stats.points > play.line_value
        else:
            would_win = game_stats.points < play.line_value

        print(f"  Result: {'WIN' if would_win else 'LOSS'}")
        print(f"\n>>> THIS PLAY SHOULD BE GRADED! <<<")
    else:
        print("[ERROR] Points is NULL - cannot grade")
else:
    print("[NOT FOUND] No game stats for this game!")
    print("\nChecking what stats we DO have for Devin Booker:")

    all_stats = session.query(PlayerGameStats).filter_by(
        player_id=player.id
    ).order_by(PlayerGameStats.game_date.desc()).limit(10).all()

    print(f"\nFound {len(all_stats)} total games for Devin Booker:")
    for i, stat in enumerate(all_stats, 1):
        print(f"  {i}. {stat.game_date} | NBA Game ID: {stat.nba_game_id} | PTS: {stat.points}")

    print(f"\n>>> PROBLEM: Stats for game {game.nba_game_id} not fetched! <<<")

print("\n" + "="*80)
print("DIAGNOSIS COMPLETE")
print("="*80)
