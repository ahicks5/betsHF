"""
Simple Stats-Based NBA Props Analyzer

Strategy:
1. Player's season average
2. Player's last 5 games average
3. Opponent's defense (what they allow)

Weighted formula: 40% season + 40% recent + 20% opponent defense

Theory: Whatever current lines are MOST deviant from the 'normal'
        = vegas knows something. Follow the deviation.
"""
from services.nba_api import NBAApiClient
import pandas as pd
import numpy as np


class PropAnalyzer:
    """Analyze player props using simple stats-based approach"""

    def __init__(self):
        self.nba_client = NBAApiClient()

    def calculate_expected_value(self, player_id, stat_type, opponent_abbr):
        """
        Calculate expected stat value using weighted average

        Formula: 40% season avg + 40% L5 avg + 20% opponent defense

        Returns: (expected_value, std_dev, components_dict)
        """
        # Get season average
        season_stats = self.nba_client.get_player_season_stats(player_id)
        season_avg = season_stats.get(stat_type, 0)

        # Get recent 5 games average
        recent_stats = self.nba_client.get_player_recent_stats(player_id, 5)
        recent_avg = recent_stats.get(stat_type, 0)

        # Get opponent defense (what they allow)
        opp_defense = self.nba_client.get_team_defense_stats(opponent_abbr)
        opp_avg = opp_defense.get(stat_type, 0)

        # Weighted average: 40/40/20
        expected = (season_avg * 0.4) + (recent_avg * 0.4) + (opp_avg * 0.2)

        # Calculate standard deviation from player's game log
        game_log = self.nba_client.get_player_game_log(player_id)
        std_dev = 0

        if not game_log.empty and stat_type in game_log.columns:
            std_dev = game_log[stat_type].std()

        components = {
            'season_avg': season_avg,
            'recent_avg': recent_avg,
            'opponent_avg': opp_avg,
            'std_dev': std_dev
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
            'opponent_avg': round(components['opponent_avg'], 2),
            'std_dev': round(components['std_dev'], 2)
        }

        return analysis

    def find_player_id(self, player_name):
        """Find NBA player ID by name"""
        results = self.nba_client.find_player(player_name)

        if results:
            return results[0]['id']

        return None


if __name__ == "__main__":
    # Test the analyzer
    analyzer = PropAnalyzer()

    # Test with LeBron James
    player_id = analyzer.find_player_id("LeBron James")

    if player_id:
        print(f"Testing analyzer with LeBron James (ID: {player_id})")

        # Analyze a sample prop
        analysis = analyzer.analyze_prop(
            player_id=player_id,
            player_name="LeBron James",
            stat_type="PTS",
            line_value=25.5,
            opponent_abbr="GSW"
        )

        print("\nAnalysis Results:")
        for key, value in analysis.items():
            print(f"{key}: {value}")
