"""
NBA API Client
Fetches player stats, game logs, and team data using nba_api

Note: The NBA stats API often blocks/throttles cloud provider IPs (Heroku, AWS, etc).
This client includes retry logic and custom headers to mitigate these issues.
"""
from nba_api.stats.endpoints import playergamelog, leaguegamefinder, commonteamroster, playercareerstats
from nba_api.stats.static import players, teams
import pandas as pd
from datetime import datetime
import time
import random


# Custom headers to mimic browser requests - NBA API blocks many cloud provider IPs
CUSTOM_HEADERS = {
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
    'Sec-Fetch-Dest': 'empty',
    'Sec-Fetch-Mode': 'cors',
    'Sec-Fetch-Site': 'same-origin',
}

# Increased timeout for cloud environments (default is 30s which often fails)
REQUEST_TIMEOUT = 60


class NBAApiClient:
    """Client for fetching NBA stats and data"""

    def __init__(self, max_retries=3, base_delay=2.0):
        self.current_season = "2025-26"
        self.max_retries = max_retries
        self.base_delay = base_delay

    def _request_with_retry(self, api_call_func, description="API call"):
        """
        Execute an API call with retry logic and exponential backoff.

        Args:
            api_call_func: A callable that makes the API request
            description: Description for logging purposes

        Returns:
            The result of the API call, or None on failure
        """
        last_exception = None

        for attempt in range(self.max_retries):
            try:
                # Add jitter to delay to avoid thundering herd
                delay = self.base_delay * (2 ** attempt) + random.uniform(0, 1)

                if attempt > 0:
                    print(f"  Retry {attempt}/{self.max_retries} for {description} (waiting {delay:.1f}s)...")
                    time.sleep(delay)
                else:
                    # Initial rate limiting delay
                    time.sleep(0.8 + random.uniform(0, 0.4))

                return api_call_func()

            except Exception as e:
                last_exception = e
                error_msg = str(e).lower()

                # Check if it's a timeout or connection error (worth retrying)
                if any(x in error_msg for x in ['timeout', 'timed out', 'connection', 'reset', 'refused']):
                    print(f"  {description} failed (attempt {attempt + 1}/{self.max_retries}): {e}")
                    continue
                else:
                    # Non-retryable error
                    raise

        # All retries exhausted
        print(f"  All {self.max_retries} attempts failed for {description}")
        raise last_exception

    def get_all_teams(self):
        """Get all NBA teams"""
        return teams.get_teams()

    def get_all_players(self):
        """Get all active NBA players"""
        return players.get_active_players()

    def find_player(self, player_name):
        """Find a player by name"""
        return players.find_players_by_full_name(player_name)

    def get_player_game_log(self, player_id: int, season: str = None):
        """
        Get game-by-game stats for a player
        Returns DataFrame with: PTS, REB, AST, FG3M, etc.
        """
        if season is None:
            season = self.current_season

        def make_request():
            gamelog = playergamelog.PlayerGameLog(
                player_id=player_id,
                season=season,
                headers=CUSTOM_HEADERS,
                timeout=REQUEST_TIMEOUT
            )
            return gamelog.get_data_frames()[0]

        try:
            df = self._request_with_retry(
                make_request,
                description=f"game log for player {player_id}"
            )
            return df
        except Exception as e:
            print(f"Error fetching game log for player {player_id}: {e}")
            return pd.DataFrame()

    def get_player_season_stats(self, player_id: int, season: str = None):
        """
        Get season averages for a player
        Returns dict with averages: PTS, REB, AST, FG3M
        """
        df = self.get_player_game_log(player_id, season)

        if df.empty:
            return {}

        stats = {
            'PTS': df['PTS'].mean(),
            'REB': df['REB'].mean(),
            'AST': df['AST'].mean(),
            'FG3M': df['FG3M'].mean(),
            'games_played': len(df)
        }

        return stats

    def get_player_recent_stats(self, player_id: int, num_games: int = 5):
        """
        Get recent game averages (last N games)
        Returns dict with averages: PTS, REB, AST, FG3M
        """
        df = self.get_player_game_log(player_id, self.current_season)

        if df.empty:
            return {}

        recent = df.head(num_games)

        stats = {
            'PTS': recent['PTS'].mean(),
            'REB': recent['REB'].mean(),
            'AST': recent['AST'].mean(),
            'FG3M': recent['FG3M'].mean(),
            'games_played': len(recent)
        }

        return stats

    def get_team_defense_stats(self, team_abbr: str, season: str = None):
        """
        Get what a team's defense allows (opponent averages)

        Note: NBA API doesn't provide direct opponent stats in TeamGameLog.
        Using league averages as a proxy for now (simplified approach).

        Returns dict with league average stats per game
        """
        if season is None:
            season = self.current_season

        # Return league average stats as proxy for opponent defense
        # These are 2024-25 NBA league averages per game
        league_avg_stats = {
            'PTS': 112.0,   # League average points per game
            'REB': 43.0,    # League average rebounds per game
            'AST': 27.0,    # League average assists per game
            'FG3M': 12.5,   # League average 3-pointers per game
            'games_played': 82
        }

        return league_avg_stats

    def get_todays_games(self):
        """
        Get today's NBA games
        Returns list of game matchups
        """
        # Note: nba_api doesn't have a direct "today's games" endpoint
        # This would typically use the NBA's scoreboard endpoint
        # For now, returning empty - this is better fetched from Odds API
        return []


if __name__ == "__main__":
    # Test the client
    client = NBAApiClient()

    # Test player lookup
    lebron = client.find_player("LeBron James")
    if lebron:
        print(f"Found player: {lebron[0]['full_name']}, ID: {lebron[0]['id']}")

        # Test season stats
        stats = client.get_player_season_stats(lebron[0]['id'])
        print(f"Season stats: {stats}")

        # Test recent stats
        recent = client.get_player_recent_stats(lebron[0]['id'], 5)
        print(f"Last 5 games: {recent}")
