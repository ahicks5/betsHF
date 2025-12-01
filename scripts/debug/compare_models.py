"""
Debug script to compare what plays each model has for today
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from database.db import get_session
from database.models import Play

session = get_session()

print("=" * 60)
print("COMPARING TODAY'S PLAYS BETWEEN MODELS")
print("=" * 60)

# Get today's plays for each model
pulsar_plays = session.query(Play).filter(
    Play.model_name == 'pulsar_v1',
    Play.was_correct == None
).all()

sentinel_plays = session.query(Play).filter(
    Play.model_name == 'sentinel_v1',
    Play.was_correct == None
).all()

# Create sets of (player, stat) for comparison
pulsar_set = {(p.player_name, p.stat_type) for p in pulsar_plays}
sentinel_set = {(p.player_name, p.stat_type) for p in sentinel_plays}

# Find differences
only_pulsar = pulsar_set - sentinel_set
only_sentinel = sentinel_set - pulsar_set
both = pulsar_set & sentinel_set

print(f"\nPulsar only: {len(only_pulsar)} plays")
print(f"Sentinel only: {len(only_sentinel)} plays")
print(f"Both models: {len(both)} plays")

print("\n--- PLAYS ONLY IN PULSAR ---")
for player, stat in sorted(only_pulsar)[:10]:
    play = next(p for p in pulsar_plays if p.player_name == player and p.stat_type == stat)
    print(f"  {player} {stat} {play.recommendation} (z={play.z_score:.2f})")

print("\n--- PLAYS ONLY IN SENTINEL ---")
for player, stat in sorted(only_sentinel)[:20]:
    play = next(p for p in sentinel_plays if p.player_name == player and p.stat_type == stat)
    print(f"  {player} {stat} {play.recommendation} (z={play.z_score:.2f})")

# Check for same player/stat with different recommendations
print("\n--- SAME PLAYER/STAT, CHECKING RECOMMENDATIONS ---")
for player, stat in sorted(both)[:10]:
    p_play = next(p for p in pulsar_plays if p.player_name == player and p.stat_type == stat)
    s_play = next(p for p in sentinel_plays if p.player_name == player and p.stat_type == stat)
    match = "MATCH" if p_play.recommendation == s_play.recommendation else "DIFF!"
    print(f"  {player} {stat}: Pulsar={p_play.recommendation}, Sentinel={s_play.recommendation} [{match}]")

session.close()
