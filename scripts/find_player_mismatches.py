"""
Find Player Name Mismatches Between APIs

This script compares player names from:
1. The Odds API (betting props)
2. NBA API (official player database)

It identifies players that appear in props but don't match any NBA player,
helping us create a mapping to capture all betting opportunities.

Usage: python scripts/find_player_mismatches.py
"""
import sys
from pathlib import Path
from datetime import datetime
from difflib import SequenceMatcher

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.db import get_session
from database.models import Player, PropLine, Play
from services.odds_api import OddsApiClient
from services.nba_api import NBAApiClient


def similarity_score(a, b):
    """Calculate similarity between two strings (0-1)"""
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def find_best_match(name, candidates, threshold=0.7):
    """Find the best matching name from candidates"""
    best_match = None
    best_score = 0

    for candidate in candidates:
        score = similarity_score(name, candidate)
        if score > best_score:
            best_score = score
            best_match = candidate

    if best_score >= threshold:
        return best_match, best_score
    return None, best_score


def main():
    print("=" * 70)
    print("PLAYER NAME MISMATCH FINDER")
    print("=" * 70)
    print(f"Run time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    session = get_session()

    # Get all NBA players from database
    nba_players = session.query(Player).all()
    nba_player_names = {p.full_name for p in nba_players}
    nba_player_names_lower = {p.full_name.lower(): p.full_name for p in nba_players}

    print(f"NBA Players in database: {len(nba_player_names)}")

    # Get all unique player names from PropLines that didn't match
    # These are stored in the Play table with player_name
    plays = session.query(Play).all()
    play_player_names = {p.player_name for p in plays if p.player_name}

    print(f"Unique player names from plays: {len(play_player_names)}")
    print()

    # Now fetch live props to see current mismatches
    print("Fetching current props from Odds API...")
    try:
        odds_client = OddsApiClient()
        all_props = odds_client.get_all_todays_props()

        odds_player_names = {p['player_name'] for p in all_props if p.get('player_name')}
        print(f"Unique player names from Odds API today: {len(odds_player_names)}")
    except Exception as e:
        print(f"Could not fetch live props: {e}")
        odds_player_names = set()

    # Combine all odds player names we've seen
    all_odds_names = play_player_names | odds_player_names

    print()
    print("=" * 70)
    print("MISMATCHED PLAYERS (Props that don't match NBA database)")
    print("=" * 70)
    print()

    mismatches = []
    exact_matches = []

    for name in sorted(all_odds_names):
        # Check exact match (case insensitive)
        if name.lower() in nba_player_names_lower:
            exact_matches.append(name)
            continue

        # Check if exactly in NBA names
        if name in nba_player_names:
            exact_matches.append(name)
            continue

        # No exact match - find closest match
        best_match, score = find_best_match(name, nba_player_names)
        mismatches.append({
            'odds_name': name,
            'suggested_match': best_match,
            'similarity': score
        })

    print(f"Exact matches: {len(exact_matches)}")
    print(f"Mismatches: {len(mismatches)}")
    print()

    if mismatches:
        print("-" * 70)
        print(f"{'ODDS API NAME':<30} | {'SUGGESTED NBA MATCH':<30} | SCORE")
        print("-" * 70)

        # Sort by similarity score (highest first - most likely matches)
        for m in sorted(mismatches, key=lambda x: x['similarity'], reverse=True):
            suggested = m['suggested_match'] or "(no close match)"
            print(f"{m['odds_name'][:30]:<30} | {suggested[:30]:<30} | {m['similarity']:.2f}")

        print()
        print("=" * 70)
        print("RECOMMENDED ACTIONS")
        print("=" * 70)
        print()

        # High confidence matches (>0.85 similarity)
        high_conf = [m for m in mismatches if m['similarity'] >= 0.85]
        if high_conf:
            print("HIGH CONFIDENCE (>85% match) - Likely name variations:")
            for m in high_conf:
                print(f"  '{m['odds_name']}' -> '{m['suggested_match']}'")
            print()

        # Medium confidence matches
        med_conf = [m for m in mismatches if 0.70 <= m['similarity'] < 0.85]
        if med_conf:
            print("MEDIUM CONFIDENCE (70-85%) - Review manually:")
            for m in med_conf:
                print(f"  '{m['odds_name']}' -> '{m['suggested_match']}' ({m['similarity']:.0%})")
            print()

        # Low/no matches
        no_match = [m for m in mismatches if m['similarity'] < 0.70]
        if no_match:
            print("NO CLOSE MATCH (<70%) - May be new/traded players:")
            for m in no_match:
                print(f"  '{m['odds_name']}'")
            print()

        # Generate mapping code
        print("=" * 70)
        print("SUGGESTED NAME MAPPING (add to services/player_name_map.py)")
        print("=" * 70)
        print()
        print("PLAYER_NAME_MAP = {")
        for m in sorted(mismatches, key=lambda x: x['odds_name']):
            if m['suggested_match'] and m['similarity'] >= 0.70:
                print(f"    '{m['odds_name']}': '{m['suggested_match']}',")
        print("}")
    else:
        print("No mismatches found - all player names match!")

    print()
    print("=" * 70)
    print("STATS SUMMARY")
    print("=" * 70)
    print(f"Total unique names from Odds API: {len(all_odds_names)}")
    print(f"Exact matches: {len(exact_matches)} ({len(exact_matches)/len(all_odds_names)*100:.1f}%)")
    print(f"Mismatches: {len(mismatches)} ({len(mismatches)/len(all_odds_names)*100:.1f}%)")

    if mismatches:
        high_conf_count = len([m for m in mismatches if m['similarity'] >= 0.85])
        print(f"  - High confidence fixes: {high_conf_count}")
        print(f"  - Needs manual review: {len(mismatches) - high_conf_count}")


if __name__ == "__main__":
    main()
