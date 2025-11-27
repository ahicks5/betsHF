"""
Export local SQLite data to JSON for migration to Heroku Postgres
"""
import sys
from pathlib import Path
import json
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.db import get_session, close_session
from database.models import Team, Player, Game, PropLine, Play

def datetime_handler(obj):
    """JSON serializer for datetime objects"""
    if isinstance(obj, datetime):
        return obj.isoformat()
    return str(obj)

def export_data():
    """Export all data from SQLite to JSON"""
    session = get_session()
    
    data = {
        'teams': [],
        'players': [],
        'games': [],
        'prop_lines': [],
        'plays': []
    }
    
    print("Exporting data from local SQLite database...")
    
    # Export Teams
    teams = session.query(Team).all()
    for team in teams:
        data['teams'].append({
            'id': team.id,
            'nba_team_id': team.nba_team_id,
            'abbreviation': team.abbreviation,
            'full_name': team.full_name
        })
    print(f"✓ Exported {len(data['teams'])} teams")
    
    # Export Players
    players = session.query(Player).all()
    for player in players:
        data['players'].append({
            'id': player.id,
            'nba_player_id': player.nba_player_id,
            'full_name': player.full_name,
            'team_id': player.team_id
        })
    print(f"✓ Exported {len(data['players'])} players")
    
    # Export Games
    games = session.query(Game).all()
    for game in games:
        data['games'].append({
            'id': game.id,
            'nba_game_id': game.nba_game_id,
            'game_date': game.game_date.isoformat() if game.game_date else None,
            'home_team_id': game.home_team_id,
            'away_team_id': game.away_team_id,
            'is_completed': game.is_completed
        })
    print(f"✓ Exported {len(data['games'])} games")
    
    # Export PropLines
    prop_lines = session.query(PropLine).all()
    for prop in prop_lines:
        data['prop_lines'].append({
            'id': prop.id,
            'game_id': prop.game_id,
            'player_id': prop.player_id,
            'prop_type': prop.prop_type,
            'line_value': prop.line_value,
            'over_odds': prop.over_odds,
            'under_odds': prop.under_odds,
            'bookmaker': prop.bookmaker,
            'collected_at': prop.collected_at.isoformat() if prop.collected_at else None,
            'is_latest': prop.is_latest
        })
    print(f"✓ Exported {len(data['prop_lines'])} prop lines")
    
    # Export Plays
    plays = session.query(Play).all()
    for play in plays:
        data['plays'].append({
            'id': play.id,
            'prop_line_id': play.prop_line_id,
            'player_name': play.player_name,
            'stat_type': play.stat_type,
            'line_value': play.line_value,
            'season_avg': play.season_avg,
            'last5_avg': play.last5_avg,
            'expected_value': play.expected_value,
            'std_dev': play.std_dev,
            'deviation': play.deviation,
            'z_score': play.z_score,
            'games_played': play.games_played,
            'recommendation': play.recommendation,
            'confidence': play.confidence,
            'bookmaker': play.bookmaker,
            'over_odds': play.over_odds,
            'under_odds': play.under_odds,
            'created_at': play.created_at.isoformat() if play.created_at else None,
            'actual_result': play.actual_result,
            'result_collected_at': play.result_collected_at.isoformat() if play.result_collected_at else None,
            'was_correct': play.was_correct
        })
    print(f"✓ Exported {len(data['plays'])} plays")
    
    close_session()
    
    # Write to JSON file
    filename = 'data_export.json'
    with open(filename, 'w') as f:
        json.dump(data, f, indent=2, default=datetime_handler)
    
    print(f"\n[OK] Data exported to {filename}")
    print(f"Total records: {sum(len(v) for v in data.values())}")
    
    return filename

if __name__ == "__main__":
    export_data()
