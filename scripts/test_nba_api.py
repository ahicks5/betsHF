"""
Test NBA API to see what game log data looks like
"""
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.nba_api import NBAApiClient
from nba_api.stats.static import players

# Test with LeBron James
client = NBAApiClient()

lebron = players.find_players_by_full_name("LeBron James")
if lebron:
    player_id = lebron[0]['id']
    print(f"Testing with LeBron James (ID: {player_id})\n")

    print(f"Current season set to: {client.current_season}\n")

    # Get game logs
    print("Fetching game logs...")
    df = client.get_player_game_log(player_id, season='2024-25')  # Try 2024-25 season

    if df.empty:
        print("ERROR: No game logs returned!")
        print("Trying 2025-26 season instead...")
        df = client.get_player_game_log(player_id, season='2025-26')

    if df.empty:
        print("ERROR: Still no game logs!")
    else:
        print(f"Found {len(df)} games\n")
        print("Recent games (first 5):")
        print(df[['GAME_DATE', 'MATCHUP', 'PTS', 'REB', 'AST', 'FG3M']].head())
        print("\n")
        print("Date format sample:")
        if len(df) > 0:
            print(f"  First game GAME_DATE: '{df.iloc[0]['GAME_DATE']}'")
            print(f"  Type: {type(df.iloc[0]['GAME_DATE'])}")
else:
    print("Could not find LeBron James")
