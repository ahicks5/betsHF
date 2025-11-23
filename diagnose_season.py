"""
Diagnose what season data we're getting from NBA API
"""
from services.nba_api import NBAApiClient
from nba_api.stats.static import players

# Find John Collins
client = NBAApiClient()
player_results = players.find_players_by_full_name("John Collins")

if not player_results:
    print("Player not found")
else:
    player = player_results[0]
    print(f"Player: {player['full_name']}")
    print(f"Player ID: {player['id']}")
    print()

    # Get game log to see what season data we're getting
    print("=== Fetching 2024-25 Game Log ===")
    game_log = client.get_player_game_log(player['id'], "2024-25")

    if game_log.empty:
        print("ERROR: No games found for 2024-25 season!")
        print()
        print("Trying 2023-24 season...")
        game_log = client.get_player_game_log(player['id'], "2023-24")

    if not game_log.empty:
        print(f"Found {len(game_log)} games")
        print()
        print("First 5 games (most recent):")
        print(game_log[['GAME_DATE', 'MATCHUP', 'PTS', 'REB', 'AST', 'FG3M']].head())
        print()
        print("Season averages:")
        print(f"  PTS: {game_log['PTS'].mean():.2f}")
        print(f"  REB: {game_log['REB'].mean():.2f}")
        print(f"  AST: {game_log['AST'].mean():.2f}")
        print(f"  FG3M: {game_log['FG3M'].mean():.2f}")
        print()
        print("Last 5 games averages:")
        last_5 = game_log.head(5)
        print(f"  PTS: {last_5['PTS'].mean():.2f}")
        print(f"  REB: {last_5['REB'].mean():.2f}")
        print(f"  AST: {last_5['AST'].mean():.2f}")
        print(f"  FG3M: {last_5['FG3M'].mean():.2f}")
        print()
        print("Last 10 games averages:")
        last_10 = game_log.head(10)
        print(f"  PTS: {last_10['PTS'].mean():.2f}")
        print(f"  REB: {last_10['REB'].mean():.2f}")
        print(f"  AST: {last_10['AST'].mean():.2f}")
        print(f"  FG3M: {last_10['FG3M'].mean():.2f}")
    else:
        print("No games found!")
