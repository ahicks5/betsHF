#!/usr/bin/env python3
"""
NBA API Diagnostic Script

Run this on Heroku to diagnose connectivity issues with stats.nba.com
Usage: python scripts/diagnose_nba_api.py
"""
import sys
import socket
import time
import ssl
from datetime import datetime

# Test configuration
NBA_STATS_HOST = "stats.nba.com"
NBA_STATS_PORT = 443
TEST_PLAYER_ID = 2544  # LeBron James
TEST_TIMEOUTS = [10, 30, 60, 90]


def print_header(title):
    print(f"\n{'=' * 60}")
    print(f" {title}")
    print(f"{'=' * 60}")


def test_dns_resolution():
    """Test if we can resolve stats.nba.com"""
    print_header("1. DNS Resolution Test")
    try:
        start = time.time()
        ip_addresses = socket.gethostbyname_ex(NBA_STATS_HOST)
        elapsed = time.time() - start
        print(f"✓ DNS resolved in {elapsed:.2f}s")
        print(f"  Hostname: {ip_addresses[0]}")
        print(f"  Aliases: {ip_addresses[1]}")
        print(f"  IP addresses: {ip_addresses[2]}")
        return True
    except socket.gaierror as e:
        print(f"✗ DNS resolution failed: {e}")
        return False


def test_tcp_connection():
    """Test raw TCP connection to stats.nba.com:443"""
    print_header("2. TCP Connection Test")
    try:
        start = time.time()
        sock = socket.create_connection((NBA_STATS_HOST, NBA_STATS_PORT), timeout=30)
        elapsed = time.time() - start
        sock.close()
        print(f"✓ TCP connection successful in {elapsed:.2f}s")
        return True
    except socket.error as e:
        print(f"✗ TCP connection failed: {e}")
        return False


def test_ssl_handshake():
    """Test SSL/TLS handshake"""
    print_header("3. SSL Handshake Test")
    try:
        start = time.time()
        context = ssl.create_default_context()
        sock = socket.create_connection((NBA_STATS_HOST, NBA_STATS_PORT), timeout=30)
        ssl_sock = context.wrap_socket(sock, server_hostname=NBA_STATS_HOST)
        elapsed = time.time() - start
        print(f"✓ SSL handshake successful in {elapsed:.2f}s")
        print(f"  Protocol: {ssl_sock.version()}")
        print(f"  Cipher: {ssl_sock.cipher()}")
        ssl_sock.close()
        return True
    except Exception as e:
        print(f"✗ SSL handshake failed: {e}")
        return False


def test_http_request_raw():
    """Test raw HTTP request without nba_api library"""
    print_header("4. Raw HTTP Request Test")

    import urllib.request

    headers = {
        'Host': 'stats.nba.com',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'en-US,en;q=0.5',
        'x-nba-stats-origin': 'stats',
        'x-nba-stats-token': 'true',
        'Referer': 'https://stats.nba.com/',
        'Origin': 'https://stats.nba.com',
    }

    # Simple endpoint test
    url = "https://stats.nba.com/stats/commonallplayers?IsOnlyCurrentSeason=1&LeagueID=00&Season=2025-26"

    for timeout in TEST_TIMEOUTS:
        print(f"\n  Testing with {timeout}s timeout...")
        try:
            req = urllib.request.Request(url, headers=headers)
            start = time.time()
            response = urllib.request.urlopen(req, timeout=timeout)
            elapsed = time.time() - start
            status = response.status
            content_length = len(response.read())
            print(f"  ✓ Request successful in {elapsed:.2f}s (status={status}, size={content_length} bytes)")
            return True
        except urllib.error.URLError as e:
            print(f"  ✗ Request failed with {timeout}s timeout: {e}")
        except Exception as e:
            print(f"  ✗ Request error with {timeout}s timeout: {e}")

    return False


def test_requests_library():
    """Test using requests library"""
    print_header("5. Requests Library Test")

    try:
        import requests
    except ImportError:
        print("✗ requests library not installed")
        return False

    headers = {
        'Host': 'stats.nba.com',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'x-nba-stats-origin': 'stats',
        'x-nba-stats-token': 'true',
        'Connection': 'keep-alive',
        'Referer': 'https://stats.nba.com/',
        'Origin': 'https://stats.nba.com',
    }

    url = "https://stats.nba.com/stats/commonallplayers?IsOnlyCurrentSeason=1&LeagueID=00&Season=2025-26"

    for timeout in TEST_TIMEOUTS:
        print(f"\n  Testing with {timeout}s timeout...")
        try:
            start = time.time()
            response = requests.get(url, headers=headers, timeout=timeout)
            elapsed = time.time() - start
            print(f"  ✓ Request successful in {elapsed:.2f}s (status={response.status_code}, size={len(response.content)} bytes)")
            return True
        except requests.exceptions.Timeout:
            print(f"  ✗ Timeout after {timeout}s")
        except requests.exceptions.RequestException as e:
            print(f"  ✗ Request failed: {e}")

    return False


def test_nba_api_library():
    """Test the nba_api library directly"""
    print_header("6. nba_api Library Test")

    try:
        from nba_api.stats.endpoints import playergamelog
        from nba_api.stats.static import players
    except ImportError:
        print("✗ nba_api library not installed")
        return False

    headers = {
        'Host': 'stats.nba.com',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'en-US,en;q=0.5',
        'x-nba-stats-origin': 'stats',
        'x-nba-stats-token': 'true',
        'Referer': 'https://stats.nba.com/',
        'Origin': 'https://stats.nba.com',
    }

    print(f"\n  Testing player lookup (static data, no API call)...")
    try:
        lebron = players.find_players_by_full_name("LeBron James")
        if lebron:
            print(f"  ✓ Found player: {lebron[0]['full_name']} (ID: {lebron[0]['id']})")
            player_id = lebron[0]['id']
        else:
            player_id = TEST_PLAYER_ID
            print(f"  Using default player ID: {player_id}")
    except Exception as e:
        print(f"  ✗ Player lookup failed: {e}")
        player_id = TEST_PLAYER_ID

    for timeout in TEST_TIMEOUTS:
        print(f"\n  Testing PlayerGameLog with {timeout}s timeout...")
        try:
            start = time.time()
            gamelog = playergamelog.PlayerGameLog(
                player_id=player_id,
                season='2025-26',
                headers=headers,
                timeout=timeout
            )
            df = gamelog.get_data_frames()[0]
            elapsed = time.time() - start
            print(f"  ✓ PlayerGameLog successful in {elapsed:.2f}s")
            print(f"    Got {len(df)} games")
            if not df.empty:
                print(f"    Latest game: {df.iloc[0]['GAME_DATE']} vs {df.iloc[0]['MATCHUP']}")
                print(f"    Stats: {df.iloc[0]['PTS']} PTS, {df.iloc[0]['REB']} REB, {df.iloc[0]['AST']} AST")
            return True
        except Exception as e:
            print(f"  ✗ PlayerGameLog failed with {timeout}s timeout: {e}")

    return False


def test_our_client():
    """Test our custom NBAApiClient"""
    print_header("7. Custom NBAApiClient Test")

    try:
        sys.path.insert(0, str(__file__).replace('/scripts/diagnose_nba_api.py', ''))
        from services.nba_api import NBAApiClient
    except ImportError as e:
        print(f"✗ Could not import NBAApiClient: {e}")
        return False

    print("\n  Testing with retry logic enabled...")
    try:
        client = NBAApiClient(max_retries=3, base_delay=2.0)
        lebron = client.find_player("LeBron James")
        if lebron:
            player_id = lebron[0]['id']
            print(f"  Found player: {lebron[0]['full_name']} (ID: {player_id})")

            start = time.time()
            df = client.get_player_game_log(player_id, '2025-26')
            elapsed = time.time() - start

            if not df.empty:
                print(f"  ✓ get_player_game_log successful in {elapsed:.2f}s")
                print(f"    Got {len(df)} games")
                return True
            else:
                print(f"  ✗ get_player_game_log returned empty DataFrame")
                return False
    except Exception as e:
        print(f"  ✗ NBAApiClient test failed: {e}")
        return False


def get_system_info():
    """Print system information"""
    print_header("System Information")
    print(f"  Python version: {sys.version}")
    print(f"  Platform: {sys.platform}")
    print(f"  Timestamp: {datetime.now().isoformat()}")

    # Check if running on Heroku
    import os
    if os.environ.get('DYNO'):
        print(f"  Heroku dyno: {os.environ.get('DYNO')}")
        print(f"  Running on Heroku: YES")
    else:
        print(f"  Running on Heroku: NO (local environment)")

    # Check proxy configuration
    proxy_url = os.environ.get('PROXY_URL')
    scraper_api_key = os.environ.get('SCRAPER_API_KEY')
    if proxy_url:
        # Mask credentials in output
        if '@' in proxy_url:
            parts = proxy_url.split('@')
            print(f"  Proxy configured: ****@{parts[1]}")
        else:
            print(f"  Proxy configured: {proxy_url}")
    elif scraper_api_key:
        print(f"  Proxy configured: ScraperAPI (key: {scraper_api_key[:8]}...)")
    else:
        print(f"  Proxy configured: NO")
        print(f"    → Set SCRAPER_API_KEY or PROXY_URL to enable proxy")

    # Get external IP if possible
    try:
        import urllib.request
        external_ip = urllib.request.urlopen('https://api.ipify.org', timeout=5).read().decode('utf8')
        print(f"  External IP: {external_ip}")
    except:
        print(f"  External IP: (could not determine)")


def main():
    print("\n" + "=" * 60)
    print(" NBA API Diagnostic Script")
    print(" Testing connectivity to stats.nba.com")
    print("=" * 60)

    get_system_info()

    results = {}

    # Run all tests
    results['DNS'] = test_dns_resolution()
    results['TCP'] = test_tcp_connection()
    results['SSL'] = test_ssl_handshake()
    results['HTTP_Raw'] = test_http_request_raw()
    results['Requests'] = test_requests_library()
    results['nba_api'] = test_nba_api_library()
    results['NBAApiClient'] = test_our_client()

    # Summary
    print_header("Summary")
    all_passed = True
    for test_name, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"  {test_name}: {status}")
        if not passed:
            all_passed = False

    print()
    if all_passed:
        print("All tests passed! NBA API connectivity is working.")
    else:
        print("Some tests failed. See above for details.")
        print("\nRecommendations:")
        if not results.get('DNS'):
            print("  - DNS resolution failed. Check network connectivity.")
        if not results.get('TCP'):
            print("  - TCP connection failed. Firewall may be blocking port 443.")
        if not results.get('SSL'):
            print("  - SSL handshake failed. TLS/SSL issues.")
        if results.get('HTTP_Raw') and not results.get('nba_api'):
            print("  - Raw HTTP works but nba_api fails. Library configuration issue.")
        if not results.get('HTTP_Raw') and not results.get('nba_api'):
            print("  - stats.nba.com is blocking this IP (common with cloud providers).")
            print("")
            print("  To fix this, configure a proxy:")
            print("    1. Sign up for ScraperAPI (free tier: 1000 requests/month)")
            print("       https://www.scraperapi.com/")
            print("")
            print("    2. Set the environment variable on Heroku:")
            print("       heroku config:set SCRAPER_API_KEY=your_api_key")
            print("")
            print("    3. Run this diagnostic again to verify it works")

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
