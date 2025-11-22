"""
Diagnostic script to check defense stats and prop data
"""
from services.nba_api import NBAApiClient
from database.db import get_session
from database.models import PropLine, Player
import sys

print("=== Checking Opponent Defense Stats ===\n")

# Test opponent defense
nba_client = NBAApiClient()
print("Testing LAC defense stats...")
defense = nba_client.get_team_defense_stats("LAC")
print(f"Result: {defense}")
print()

# Check what columns are actually in TeamGameLog
print("Checking TeamGameLog columns...")
from nba_api.stats.endpoints import teamgamelog
from nba_api.stats.static import teams
import time

all_teams = teams.get_teams()
lac = [t for t in all_teams if t['abbreviation'] == 'LAC'][0]

time.sleep(0.6)
gamelog = teamgamelog.TeamGameLog(team_id=lac['id'], season="2024-25")
df = gamelog.get_data_frames()[0]

if not df.empty:
    print(f"Available columns: {list(df.columns)}")
    print(f"\nSample row:")
    print(df.iloc[0])
else:
    print("DataFrame is empty!")

print("\n\n=== Checking James Harden Props ===\n")

session = get_session()
harden = session.query(Player).filter(Player.full_name.like("%Harden%")).first()

if harden:
    print(f"Found: {harden.full_name}")
    props = session.query(PropLine).filter_by(player_id=harden.id, is_latest=True).all()

    print(f"\nAll {len(props)} props:")
    for prop in props:
        print(f"  {prop.prop_type}: {prop.line_value} ({prop.bookmaker})")

session.close()
