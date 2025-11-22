"""
NBA API Client
Fetches player stats, game logs, and team data using nba_api
"""
from nba_api.stats.endpoints import playergamelog, leaguegamefinder, commonteamroster, playercareerstats
from nba_api.stats.static import players, teams
import pandas as pd
from datetime import datetime
import time


class NBAApiClient:
    """Client for fetching NBA stats and data"""

    def __init__(self):
        self.current_season = "2024-25"

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

        try:
            time.sleep(0.6)  # Rate limiting
            gamelog = playergamelog.PlayerGameLog(
                player_id=player_id,
                season=season
            )
            df = gamelog.get_data_frames()[0]
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
        Returns dict with opponent averages: PTS, REB, AST, FG3M
        """
        if season is None:
            season = self.current_season

        try:
            # Find team ID
            team_list = teams.find_teams_by_abbreviation(team_abbr)
            if not team_list:
                return {}

            team_id = team_list[0]['id']

            time.sleep(0.6)  # Rate limiting

            # Get games for this team
            gamefinder = leaguegamefinder.LeagueGameFinder(
                team_id_nullable=team_id,
                season_nullable=season
            )
            games_df = gamefinder.get_data_frames()[0]

            if games_df.empty:
                return {}

            # Calculate opponent averages (what defense allows)
            # Note: In LeagueGameFinder, each game appears twice (once per team)
            # We want the opponent's stats when playing against this team
            opp_stats = {
                'PTS': games_df['PTS'].mean(),  # Points allowed
                'REB': games_df['REB'].mean(),  # Rebounds allowed
                'AST': games_df['AST'].mean(),  # Assists allowed
                'FG3M': games_df['FG3M'].mean(),  # Threes allowed
                'games_played': len(games_df)
            }

            return opp_stats

        except Exception as e:
            print(f"Error fetching defense stats for {team_abbr}: {e}")
            return {}

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
