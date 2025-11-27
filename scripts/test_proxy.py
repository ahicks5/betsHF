#!/usr/bin/env python3
"""
Quick test for NBA API with proxy - skips all the direct connection tests
Usage: heroku run python scripts/test_proxy.py
"""
import sys
import os
import time

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def main():
    print("=" * 60)
    print(" NBA API Proxy Test")
    print("=" * 60)

    # Check proxy config
    proxy_url = os.environ.get('PROXY_URL')
    scraper_api_key = os.environ.get('SCRAPER_API_KEY')

    if proxy_url:
        if '@' in proxy_url:
            parts = proxy_url.split('@')
            print(f"Proxy: ****@{parts[1]}")
        else:
            print(f"Proxy: {proxy_url}")
    elif scraper_api_key:
        print(f"Proxy: ScraperAPI (key: {scraper_api_key[:8]}...)")
    else:
        print("ERROR: No proxy configured!")
        print("Set SCRAPER_API_KEY or PROXY_URL environment variable")
        return 1

    print()
    print("Testing NBA API with proxy...")
    print()

    try:
        from services.nba_api import NBAApiClient

        client = NBAApiClient(max_retries=2, base_delay=3.0)

        # Find LeBron
        print("Looking up LeBron James...")
        lebron = client.find_player("LeBron James")
        if not lebron:
            print("ERROR: Could not find player")
            return 1

        player_id = lebron[0]['id']
        print(f"Found: {lebron[0]['full_name']} (ID: {player_id})")
        print()

        # Fetch game log
        print("Fetching game log (this may take 30-60 seconds with proxy)...")
        start = time.time()
        df = client.get_player_game_log(player_id, '2025-26')
        elapsed = time.time() - start

        if df.empty:
            print(f"\nERROR: Got empty response after {elapsed:.1f}s")
            print("The proxy may not be working correctly.")
            return 1

        print(f"\n{'=' * 60}")
        print(f" SUCCESS! Got {len(df)} games in {elapsed:.1f}s")
        print(f"{'=' * 60}")
        print(f"\nLatest game: {df.iloc[0]['GAME_DATE']}")
        print(f"Stats: {df.iloc[0]['PTS']} PTS, {df.iloc[0]['REB']} REB, {df.iloc[0]['AST']} AST")

        return 0

    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
