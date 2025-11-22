"""
The Odds API Client
Fetches betting lines and player props from sportsbooks
"""
import requests
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()


class OddsApiClient:
    """Client for fetching betting odds and player props"""

    def __init__(self, api_key=None):
        self.api_key = api_key or os.getenv("ODDS_API_KEY")
        self.base_url = "https://api.the-odds-api.com/v4"

        if not self.api_key:
            raise ValueError("ODDS_API_KEY not found in environment variables")

    def get_nba_games(self):
        """
        Get today's NBA games with event IDs
        Returns list of games with matchup info
        """
        url = f"{self.base_url}/sports/basketball_nba/odds"

        params = {
            'apiKey': self.api_key,
            'regions': 'us',
            'markets': 'h2h',
            'oddsFormat': 'american'
        }

        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            games = response.json()

            print(f"[OK] Found {len(games)} NBA games")
            return games

        except requests.exceptions.RequestException as e:
            print(f"Error fetching NBA games: {e}")
            return []

    def get_player_props(self, event_id: str):
        """
        Get player props for a specific game
        Returns prop lines for points, rebounds, assists, threes
        """
        url = f"{self.base_url}/sports/basketball_nba/events/{event_id}/odds"

        params = {
            'apiKey': self.api_key,
            'regions': 'us',
            'markets': 'player_points,player_rebounds,player_assists,player_threes',
            'oddsFormat': 'american'
        }

        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()

            return self._parse_props(data)

        except requests.exceptions.RequestException as e:
            print(f"Error fetching props for event {event_id}: {e}")
            return []

    def _parse_props(self, data):
        """
        Parse the props response into a clean format
        Returns list of prop dictionaries
        """
        props = []

        if not data.get('bookmakers'):
            return props

        for bookmaker in data['bookmakers']:
            bookmaker_name = bookmaker['key']

            for market in bookmaker.get('markets', []):
                market_type = market['key']

                # Map market types to our prop types
                prop_type_mapping = {
                    'player_points': 'PTS',
                    'player_rebounds': 'REB',
                    'player_assists': 'AST',
                    'player_threes': 'FG3M'
                }

                prop_type = prop_type_mapping.get(market_type)
                if not prop_type:
                    continue

                for outcome in market.get('outcomes', []):
                    player_name = outcome.get('description')

                    if outcome['name'] == 'Over':
                        line_value = outcome.get('point')
                        over_odds = outcome.get('price')

                        # Find corresponding under
                        under_odds = None
                        for under_outcome in market.get('outcomes', []):
                            if under_outcome.get('description') == player_name and under_outcome['name'] == 'Under':
                                under_odds = under_outcome.get('price')
                                break

                        props.append({
                            'player_name': player_name,
                            'prop_type': prop_type,
                            'line_value': line_value,
                            'over_odds': over_odds,
                            'under_odds': under_odds,
                            'bookmaker': bookmaker_name
                        })

        return props

    def get_all_todays_props(self):
        """
        Get all player props for today's games
        Returns comprehensive list of all props
        """
        all_props = []

        games = self.get_nba_games()

        for game in games:
            event_id = game['id']
            home_team = game['home_team']
            away_team = game['away_team']

            print(f"Fetching props for {away_team} @ {home_team}...")

            props = self.get_player_props(event_id)

            # Add game context to each prop
            for prop in props:
                prop['event_id'] = event_id
                prop['home_team'] = home_team
                prop['away_team'] = away_team
                prop['game_time'] = game.get('commence_time')

            all_props.extend(props)

        print(f"\n[OK] Total props collected: {len(all_props)}")
        return all_props


if __name__ == "__main__":
    # Test the client
    client = OddsApiClient()

    # Test fetching games
    games = client.get_nba_games()
    print(f"Found {len(games)} games")

    if games:
        # Test fetching props for first game
        event_id = games[0]['id']
        print(f"\nFetching props for event: {event_id}")
        props = client.get_player_props(event_id)
        print(f"Found {len(props)} props")

        if props:
            print("\nSample prop:")
            print(props[0])
