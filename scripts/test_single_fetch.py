"""
Test fetching stats for a single player to diagnose the issue
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.db import get_session
from database.models import Player, PlayerGameStats
from data.nba_stats import fetch_player_game_log

session = get_session()

# Get Devin Booker (from the ungraded plays)
player = session.query(Player).filter_by(full_name='Devin Booker').first()

if not player:
    print("Player not found! Searching for any player...")
    player = session.query(Player).first()

if not player:
    print("No players in database at all!")
    sys.exit(1)

print(f"\n{'='*80}")
print(f"Testing NBA stats fetch for: {player.full_name}")
print(f"Player ID: {player.id}")
print(f"NBA Player ID: {player.nba_player_id}")
print(f"{'='*80}\n")

# Try to fetch game log
print("Attempting to fetch game log from NBA API...")
stats = fetch_player_game_log(player.id, season="2025-26", force_refresh=True)

print(f"\nResult: {len(stats)} games fetched")

if stats:
    print("\nFirst game:")
    first_game = stats[0]
    print(f"  Date: {first_game.game_date}")
    print(f"  NBA Game ID: {first_game.nba_game_id}")
    print(f"  Points: {first_game.points}")
    print(f"  Rebounds: {first_game.rebounds}")
    print(f"  Assists: {first_game.assists}")
else:
    print("\n[ERROR] No stats were fetched!")
    print("This is why grading isn't working - the NBA API fetch is failing")

# Check what's in the database
count = session.query(PlayerGameStats).filter_by(player_id=player.id).count()
print(f"\nPlayerGameStats in DB for this player: {count}")
