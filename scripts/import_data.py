"""
Import JSON data to Heroku PostgreSQL database
"""
import sys
from pathlib import Path
import json
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.db import get_session, close_session
from database.models import Team, Player, Game, PropLine, Play

def import_data(filename='data_export.json'):
    """Import data from JSON to PostgreSQL"""
    session = get_session()
    
    print(f"Importing data from {filename}...")
    
    with open(filename, 'r') as f:
        data = json.load(f)
    
    # Import Teams
    print(f"\nImporting {len(data['teams'])} teams...")
    for team_data in data['teams']:
        team = Team(
            id=team_data['id'],
            nba_team_id=team_data['nba_team_id'],
            abbreviation=team_data['abbreviation'],
            full_name=team_data['full_name']
        )
        session.merge(team)
    session.commit()
    print(f"✓ Imported {len(data['teams'])} teams")
    
    # Import Players
    print(f"\nImporting {len(data['players'])} players...")
    for player_data in data['players']:
        player = Player(
            id=player_data['id'],
            nba_player_id=player_data['nba_player_id'],
            full_name=player_data['full_name'],
            team_id=player_data['team_id']
        )
        session.merge(player)
    session.commit()
    print(f"✓ Imported {len(data['players'])} players")
    
    # Import Games
    print(f"\nImporting {len(data['games'])} games...")
    for game_data in data['games']:
        game = Game(
            id=game_data['id'],
            nba_game_id=game_data['nba_game_id'],
            game_date=datetime.fromisoformat(game_data['game_date']) if game_data['game_date'] else None,
            home_team_id=game_data['home_team_id'],
            away_team_id=game_data['away_team_id'],
            is_completed=game_data['is_completed']
        )
        session.merge(game)
    session.commit()
    print(f"✓ Imported {len(data['games'])} games")
    
    # Import PropLines
    print(f"\nImporting {len(data['prop_lines'])} prop lines...")
    for prop_data in data['prop_lines']:
        prop = PropLine(
            id=prop_data['id'],
            game_id=prop_data['game_id'],
            player_id=prop_data['player_id'],
            prop_type=prop_data['prop_type'],
            line_value=prop_data['line_value'],
            over_odds=prop_data['over_odds'],
            under_odds=prop_data['under_odds'],
            bookmaker=prop_data['bookmaker'],
            collected_at=datetime.fromisoformat(prop_data['collected_at']) if prop_data['collected_at'] else None,
            is_latest=prop_data['is_latest']
        )
        session.merge(prop)
    session.commit()
    print(f"✓ Imported {len(data['prop_lines'])} prop lines")
    
    # Import Plays
    print(f"\nImporting {len(data['plays'])} plays...")
    for play_data in data['plays']:
        play = Play(
            id=play_data['id'],
            prop_line_id=play_data['prop_line_id'],
            player_name=play_data['player_name'],
            stat_type=play_data['stat_type'],
            line_value=play_data['line_value'],
            season_avg=play_data['season_avg'],
            last5_avg=play_data['last5_avg'],
            expected_value=play_data['expected_value'],
            std_dev=play_data['std_dev'],
            deviation=play_data['deviation'],
            z_score=play_data['z_score'],
            games_played=play_data['games_played'],
            recommendation=play_data['recommendation'],
            confidence=play_data['confidence'],
            bookmaker=play_data['bookmaker'],
            over_odds=play_data['over_odds'],
            under_odds=play_data['under_odds'],
            created_at=datetime.fromisoformat(play_data['created_at']) if play_data['created_at'] else None,
            actual_result=play_data['actual_result'],
            result_collected_at=datetime.fromisoformat(play_data['result_collected_at']) if play_data['result_collected_at'] else None,
            was_correct=play_data['was_correct']
        )
        session.merge(play)
    session.commit()
    print(f"✓ Imported {len(data['plays'])} plays")
    
    close_session()
    
    print(f"\n[OK] Data import complete!")
    print(f"Total records imported: {sum(len(v) for v in data.values())}")

if __name__ == "__main__":
    import_data()
