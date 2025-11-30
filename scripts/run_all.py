"""
Run All Scripts - Manual Execution

Runs all data collection and analysis in the right order:
1. Collect today's props from Odds API
2. Sync NBA stats (player averages)
3. Generate plays for all models

Usage:
    python scripts/run_all.py              # Run everything
    python scripts/run_all.py --skip-stats # Skip stats sync (faster if already done today)
"""
import sys
import argparse
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import datetime


def main():
    parser = argparse.ArgumentParser(description='Run all data collection and analysis')
    parser.add_argument('--skip-stats', action='store_true', help='Skip NBA stats sync')

    args = parser.parse_args()

    print("=" * 60)
    print(f"RUN ALL - {datetime.now().strftime('%Y-%m-%d %I:%M %p')}")
    print("=" * 60)

    # Step 1: Initialize and collect props
    print("\n[1/3] Collecting today's props...")
    print("-" * 40)
    from database.db import init_db
    from scripts.collect_today import initialize_teams_and_players, collect_todays_games_and_props

    init_db()
    initialize_teams_and_players()
    collect_todays_games_and_props()

    # Step 2: Sync NBA stats (optional)
    if not args.skip_stats:
        print("\n[2/3] Syncing NBA stats...")
        print("-" * 40)
        from scripts.sync_nba_stats import sync_all_player_stats
        sync_all_player_stats()
    else:
        print("\n[2/3] Skipping NBA stats sync (--skip-stats)")

    # Step 3: Generate plays
    print("\n[3/3] Generating plays for all models...")
    print("-" * 40)
    from scripts.find_plays import analyze_all_props
    analyze_all_props()

    print("\n" + "=" * 60)
    print("ALL DONE!")
    print("=" * 60)


if __name__ == "__main__":
    main()
