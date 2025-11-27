"""
Cached Stats-Based NBA Props Analyzer

Caches player and team stats to avoid redundant API calls
"""
from services.nba_api import NBAApiClient
import pandas as pd
import numpy as np


class CachedPropAnalyzer:
    """Analyze player props with caching to minimize API calls"""

    def __init__(self):
        self.nba_client = NBAApiClient()
        self.player_cache = {}  # Cache player stats
        self.team_cache = {}    # Cache team defense stats

    def get_cached_player_stats(self, player_id):
        """Get player stats with caching"""
        if player_id not in self.player_cache:
            # Fetch season and recent stats
            season_stats = self.nba_client.get_player_season_stats(player_id)
            recent_stats = self.nba_client.get_player_recent_stats(player_id, 5)
            game_log = self.nba_client.get_player_game_log(player_id)

            # Calculate standard deviations for each stat
            std_devs = {}
            games_played = 0
            if not game_log.empty:
                games_played = len(game_log)
                for stat in ['PTS', 'REB', 'AST', 'FG3M']:
                    if stat in game_log.columns:
                        std_devs[stat] = game_log[stat].std()

            self.player_cache[player_id] = {
                'season': season_stats,
                'recent': recent_stats,
                'std_devs': std_devs,
                'games_played': games_played
            }

        return self.player_cache[player_id]

    def get_cached_team_defense(self, team_abbr):
        """Get team defense stats with caching"""
        if team_abbr not in self.team_cache:
            defense = self.nba_client.get_team_defense_stats(team_abbr)
            self.team_cache[team_abbr] = defense

        return self.team_cache[team_abbr]

    def calculate_expected_value(self, player_id, stat_type, opponent_abbr):
        """
        Calculate expected stat value using weighted average with caching

        Formula: 50% season avg + 50% L5 avg

        Note: Opponent defense component removed because NBA API doesn't provide
        reliable player-level opponent stats (only team totals available)

        Returns: (expected_value, std_dev, components_dict)
        """
        # Get cached player stats
        player_stats = self.get_cached_player_stats(player_id)

        season_avg = player_stats['season'].get(stat_type, 0)
        recent_avg = player_stats['recent'].get(stat_type, 0)
        std_dev = player_stats['std_devs'].get(stat_type, 0)
        games_played = player_stats.get('games_played', 0)

        # Weighted average: 50% season, 50% recent (L5)
        # This balances long-term performance with recent form
        expected = (season_avg * 0.5) + (recent_avg * 0.5)

        components = {
            'season_avg': season_avg,
            'recent_avg': recent_avg,
            'std_dev': std_dev,
            'games_played': games_played
        }

        return expected, std_dev, components

    def analyze_prop(self, player_id, player_name, stat_type, line_value, opponent_abbr):
        """
        Analyze a single prop line

        Returns analysis with:
        - Expected value
        - Deviation from line
        - Z-score
        - Recommendation
        - Confidence level
        """
        expected, std_dev, components = self.calculate_expected_value(
            player_id, stat_type, opponent_abbr
        )

        # Calculate deviation
        deviation = line_value - expected

        # Calculate z-score (how many standard deviations away)
        z_score = 0
        if std_dev > 0:
            z_score = deviation / std_dev

        # Determine recommendation based on z-score
        # Theory: Follow the deviation - if line is way off, Vegas knows something
        abs_z = abs(z_score)

        if abs_z < 0.5:
            # Line is close to expected - no strong signal
            recommendation = "NO PLAY"
            confidence = "N/A"
        elif abs_z < 1.0:
            # Moderate deviation
            recommendation = "UNDER" if deviation < 0 else "OVER"
            confidence = "Medium"
        else:
            # Strong deviation
            recommendation = "UNDER" if deviation < 0 else "OVER"
            confidence = "High"

        # Apply sample size penalty for players with limited games
        games_played = components.get('games_played', 0)

        if games_played > 0 and confidence != "N/A":
            if games_played < 3:
                # Very limited sample - downgrade significantly
                if confidence == "High":
                    confidence = "Medium"
                elif confidence == "Medium":
                    recommendation = "NO PLAY"
                    confidence = "N/A"
            elif games_played < 5:
                # Limited sample - downgrade High confidence only
                if confidence == "High":
                    confidence = "Medium"

        analysis = {
            'player_name': player_name,
            'stat_type': stat_type,
            'line_value': line_value,
            'expected_value': round(expected, 2),
            'deviation': round(deviation, 2),
            'z_score': round(z_score, 2),
            'recommendation': recommendation,
            'confidence': confidence,
            'season_avg': round(components['season_avg'], 2),
            'recent_avg': round(components['recent_avg'], 2),
            'std_dev': round(components['std_dev'], 2),
            'games_played': games_played
        }

        return analysis

    def get_cache_stats(self):
        """Get cache statistics"""
        return {
            'players_cached': len(self.player_cache),
            'teams_cached': len(self.team_cache)
        }
