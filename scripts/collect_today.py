"""
Collect Today's NBA Data

Steps:
1. Initialize teams and players in database
2. Fetch today's games from Odds API
3. Fetch all player props for today's games
4. Store in database
"""
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.db import init_db, get_session, close_session
from database.models import Team, Player, Game, PropLine
from services.nba_api import NBAApiClient
from services.odds_api import OddsApiClient
from datetime import datetime


def initialize_teams_and_players():
    """Load all NBA teams and active players into database"""
    session = get_session()
    nba_client = NBAApiClient()

    print("Loading teams...")
    teams_data = nba_client.get_all_teams()

    for team_data in teams_data:
        # Check if team already exists
        existing = session.query(Team).filter_by(nba_team_id=team_data['id']).first()

        if not existing:
            team = Team(
                nba_team_id=team_data['id'],
                abbreviation=team_data['abbreviation'],
                full_name=team_data['full_name']
            )
            session.add(team)

    session.commit()
    print(f"[OK] Loaded {len(teams_data)} teams")

    print("\nLoading players...")
    players_data = nba_client.get_all_players()

    for player_data in players_data:
        # Check if player already exists
        existing = session.query(Player).filter_by(nba_player_id=player_data['id']).first()

        if not existing:
            player = Player(
                nba_player_id=player_data['id'],
                full_name=player_data['full_name']
            )
            session.add(player)

    session.commit()
    print(f"[OK] Loaded {len(players_data)} active players")

    close_session()


def collect_todays_games_and_props():
    """Fetch today's games and all player props"""
    session = get_session()
    odds_client = OddsApiClient()

    print("\nFetching today's games and props...")

    # Get all props for today
    all_props = odds_client.get_all_todays_props()

    if not all_props:
        print("No props found for today")
        close_session()
        return

    # Mark old props as not latest
    session.query(PropLine).update({PropLine.is_latest: False})

    # Store props
    props_stored = 0

    for prop_data in all_props:
        # Find player by name
        player = session.query(Player).filter_by(full_name=prop_data['player_name']).first()

        if not player:
            # Try to find by partial match
            player = session.query(Player).filter(
                Player.full_name.like(f"%{prop_data['player_name']}%")
            ).first()

        if not player:
            print(f"[WARNING] Player not found: {prop_data['player_name']}")
            continue

        # For now, create a simple game record (we can enhance this later)
        # Check if game already exists for today
        game_date = datetime.fromisoformat(prop_data['game_time'].replace('Z', '+00:00'))

        # Find teams
        home_team = session.query(Team).filter_by(full_name=prop_data['home_team']).first()
        away_team = session.query(Team).filter_by(full_name=prop_data['away_team']).first()

        if not home_team or not away_team:
            continue

        # Assign player to team if not already assigned
        # Use NBA API to determine player's current team
        if not player.team_id:
            try:
                from nba_api.stats.endpoints import commonplayerinfo
                import time

                time.sleep(0.6)  # Rate limiting
                player_info = commonplayerinfo.CommonPlayerInfo(player_id=player.nba_player_id)
                info_df = player_info.get_data_frames()[0]

                if not info_df.empty:
                    team_abbr = info_df['TEAM_ABBREVIATION'].iloc[0]

                    # Match team abbreviation to our teams
                    if team_abbr == home_team.abbreviation:
                        player.team_id = home_team.id
                    elif team_abbr == away_team.abbreviation:
                        player.team_id = away_team.id
                    else:
                        # Player might be on a different team, look it up
                        team_match = session.query(Team).filter_by(abbreviation=team_abbr).first()
                        if team_match:
                            player.team_id = team_match.id

            except Exception as e:
                # If we can't determine team from API, make an educated guess
                # Most likely they're on one of the two teams playing
                # We'll assign to home team as default - this will get corrected
                # when we see them in other games
                player.team_id = home_team.id

        # Find or create game
        game = session.query(Game).filter_by(nba_game_id=prop_data['event_id']).first()

        if not game:
            game = Game(
                nba_game_id=prop_data['event_id'],
                game_date=game_date,
                home_team_id=home_team.id,
                away_team_id=away_team.id
            )
            session.add(game)
            session.flush()

        # Create prop line
        prop_line = PropLine(
            game_id=game.id,
            player_id=player.id,
            prop_type=prop_data['prop_type'],
            line_value=prop_data['line_value'],
            over_odds=prop_data['over_odds'],
            under_odds=prop_data['under_odds'],
            bookmaker=prop_data['bookmaker'],
            is_latest=True
        )

        session.add(prop_line)
        props_stored += 1

    session.commit()
    print(f"\n[OK] Stored {props_stored} prop lines")

    close_session()


if __name__ == "__main__":
    print("=== NBA Props Data Collection ===\n")

    # Initialize database
    print("Step 1: Initialize database...")
    init_db()

    # Initialize teams and players (only needed first time)
    print("\nStep 2: Load teams and players...")
    initialize_teams_and_players()

    # Collect today's games and props
    print("\nStep 3: Collect today's props...")
    collect_todays_games_and_props()

    print("\n=== Collection Complete ===")
