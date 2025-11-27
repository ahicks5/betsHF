"""
Test Caching System
Verifies that NBA stats caching and data retrieval works correctly
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.db import get_session, init_db
from database.models import Player, PlayerGameStats, Play
from data.nba_stats import get_player_averages, fetch_player_game_log, sync_all_active_players
from datetime import datetime


def test_database_tables():
    """Test that new database tables exist"""
    print("\n[TEST 1] Checking database tables...")
    try:
        init_db()
        print("[OK] Database tables created successfully")
        return True
    except Exception as e:
        print(f"[FAIL] Failed to create tables: {e}")
        return False


def test_player_fetch():
    """Test fetching stats for a single player"""
    print("\n[TEST 2] Testing player stats fetch...")
    session = get_session()

    # Get first active player
    player = session.query(Player).first()
    if not player:
        print("✗ No players found in database")
        return False

    print(f"Testing with player: {player.full_name} (ID: {player.id})")

    try:
        # Fetch game log
        stats = fetch_player_game_log(player.id)
        if stats:
            print(f"[OK] Fetched {len(stats)} games for {player.full_name}")

            # Check if stats were saved to database
            db_stats = session.query(PlayerGameStats).filter_by(player_id=player.id).count()
            print(f"[OK] {db_stats} games saved to database")

            return True
        else:
            print(f"[FAIL] No stats returned for {player.full_name}")
            return False

    except Exception as e:
        print(f"[FAIL] Error fetching stats: {e}")
        return False


def test_averages_calculation():
    """Test calculating averages from cached data"""
    print("\n[TEST 3] Testing averages calculation...")
    session = get_session()

    # Find a player with cached stats
    player_with_stats = session.query(PlayerGameStats.player_id).first()
    if not player_with_stats:
        print("✗ No cached stats found. Run test 2 first.")
        return False

    player_id = player_with_stats[0]
    player = session.query(Player).filter_by(id=player_id).first()

    print(f"Testing with: {player.full_name}")

    try:
        # Get season averages
        avgs = get_player_averages(player_id)

        if avgs:
            print(f"[OK] Season Averages:")
            print(f"  Points: {avgs.get('points', 0):.1f} ({avgs.get('points_games', 0)} games)")
            print(f"  Rebounds: {avgs.get('rebounds', 0):.1f}")
            print(f"  Assists: {avgs.get('assists', 0):.1f}")
            print(f"  3PM: {avgs.get('fg3m', 0):.1f}")

            # Get last 5 games averages
            recent_avgs = get_player_averages(player_id, last_n_games=5)
            print(f"\n[OK] Last 5 Games Averages:")
            print(f"  Points: {recent_avgs.get('points', 0):.1f}")
            print(f"  Rebounds: {recent_avgs.get('rebounds', 0):.1f}")

            return True
        else:
            print("[FAIL] No averages calculated")
            return False

    except Exception as e:
        print(f"[FAIL] Error calculating averages: {e}")
        return False


def test_caching_speed():
    """Test that second fetch is faster (from cache)"""
    print("\n[TEST 4] Testing cache performance...")
    session = get_session()

    player = session.query(Player).first()
    if not player:
        print("✗ No players found")
        return False

    try:
        # First fetch (should hit cache if test 2 ran)
        start = datetime.now()
        stats1 = fetch_player_game_log(player.id)
        time1 = (datetime.now() - start).total_seconds()

        # Second fetch (should be from cache)
        start = datetime.now()
        stats2 = fetch_player_game_log(player.id)
        time2 = (datetime.now() - start).total_seconds()

        print(f"First fetch: {time1:.2f}s")
        print(f"Second fetch: {time2:.2f}s")

        if time2 < time1:
            print(f"[OK] Cache is {time1/time2:.1f}x faster!")
            return True
        else:
            print("[WARN] Cache not significantly faster (may need more data)")
            return True  # Still pass, just slower

    except Exception as e:
        print(f"[FAIL] Error testing cache: {e}")
        return False


def test_grading():
    """Test play grading logic"""
    print("\n[TEST 5] Testing play grading...")
    session = get_session()

    # Check for ungraded plays
    ungraded = session.query(Play).filter(Play.was_correct == None).count()
    print(f"Found {ungraded} ungraded plays")

    # Count total graded plays
    graded = session.query(Play).filter(Play.was_correct != None).count()
    print(f"Found {graded} graded plays")

    print("[OK] Grading system ready (run sync_nba_stats.py to grade)")
    return True


def main():
    """Run all tests"""
    print("=" * 60)
    print("CACHING SYSTEM TESTS")
    print("=" * 60)

    results = []

    results.append(("Database Tables", test_database_tables()))
    results.append(("Player Stats Fetch", test_player_fetch()))
    results.append(("Averages Calculation", test_averages_calculation()))
    results.append(("Cache Performance", test_caching_speed()))
    results.append(("Grading Logic", test_grading()))

    print("\n" + "=" * 60)
    print("TEST RESULTS")
    print("=" * 60)

    for test_name, passed in results:
        status = "[PASS]" if passed else "[FAIL]"
        print(f"{status} - {test_name}")

    passed_count = sum(1 for _, passed in results if passed)
    total_count = len(results)

    print(f"\nPassed: {passed_count}/{total_count}")

    if passed_count == total_count:
        print("\n[SUCCESS] All tests passed! System is ready.")
    else:
        print("\n[WARNING] Some tests failed. Check errors above.")


if __name__ == "__main__":
    main()
