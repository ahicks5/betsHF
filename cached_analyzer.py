"""
Cached Stats-Based NBA Props Analyzer

Uses database cache for player stats - NO API calls during analysis
Stats are pre-fetched by sync_nba_stats.py
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from database.db import get_session
from database.models import Player
from data.nba_stats import get_player_averages, get_player_stat_distribution
import numpy as np


class CachedPropAnalyzer:
    """Analyze player props using pre-cached database stats"""

    def __init__(self):
        self.session = get_session()
        self.player_id_map = {}  # Map NBA API player IDs to internal database IDs

    def get_internal_player_id(self, nba_player_id):
        """Convert NBA API player ID to internal database player ID"""
        if nba_player_id not in self.player_id_map:
            player = self.session.query(Player).filter_by(nba_player_id=nba_player_id).first()
            if player:
                self.player_id_map[nba_player_id] = player.id
            else:
                return None
        return self.player_id_map.get(nba_player_id)

    def get_cached_player_stats(self, nba_player_id):
        """
        Get player stats from database cache

        Returns same format as old version for compatibility
        """
        # Get internal player ID
        internal_id = self.get_internal_player_id(nba_player_id)
        if not internal_id:
            # Return empty stats if player not found
            return {
                'season': {},
                'recent': {},
                'std_devs': {},
                'games_played': 0
            }

        # Map prop stat names to database column names
        stat_map = {
            'PTS': 'points',
            'REB': 'rebounds',
            'AST': 'assists',
            'FG3M': 'fg3m',
            'STL': 'steals',
            'BLK': 'blocks'
        }

        # Get season averages
        season_avgs = get_player_averages(internal_id)

        # Get recent (last 5 games) averages
        recent_avgs = get_player_averages(internal_id, last_n_games=5)

        # Build response in old format
        season_stats = {}
        recent_stats = {}
        std_devs = {}

        for nba_stat, db_stat in stat_map.items():
            season_stats[nba_stat] = season_avgs.get(db_stat, 0) or 0
            recent_stats[nba_stat] = recent_avgs.get(db_stat, 0) or 0
            std_devs[nba_stat] = season_avgs.get(f'{db_stat}_std', 0) or 0

        games_played = season_avgs.get('points_games', 0)  # Use points games as proxy

        return {
            'season': season_stats,
            'recent': recent_stats,
            'std_devs': std_devs,
            'games_played': games_played
        }

    def get_cached_team_defense(self, team_abbr):
        """
        Get team defense stats (currently not used)
        Placeholder for future enhancement
        """
        return {}

    def calculate_expected_value(self, player_id, stat_type, opponent_abbr):
        """
        Calculate expected stat value using weighted average from cached data

        Formula: 50% season avg + 50% L5 avg

        Note: Opponent defense component removed because NBA API doesn't provide
        reliable player-level opponent stats (only team totals available)

        Returns: (expected_value, std_dev, components_dict)
        """
        # Get cached player stats (from database, not API)
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
            'players_cached': len(self.player_id_map),
            'teams_cached': 0  # Team caching not currently implemented
        }
