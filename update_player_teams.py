"""
Update Player Teams

This script assigns teams to players that don't have them yet.
Uses NBA API to get current team information.
"""
from database.db import get_session, close_session
from database.models import Player, Team
from nba_api.stats.endpoints import commonplayerinfo
import time


def update_player_teams():
    """Update teams for all players without team assignments"""
    session = get_session()

    # Get all players without teams
    players_without_teams = session.query(Player).filter_by(team_id=None).all()

    print(f"Found {len(players_without_teams)} players without team assignments")
    print("Updating player teams from NBA API...\n")

    updated = 0
    errors = 0

    for i, player in enumerate(players_without_teams, 1):
        try:
            # Rate limiting
            time.sleep(0.6)

            # Get player info from NBA API
            player_info = commonplayerinfo.CommonPlayerInfo(player_id=player.nba_player_id)
            info_df = player_info.get_data_frames()[0]

            if not info_df.empty:
                team_abbr = info_df['TEAM_ABBREVIATION'].iloc[0]

                # Find matching team in database
                team = session.query(Team).filter_by(abbreviation=team_abbr).first()

                if team:
                    player.team_id = team.id
                    updated += 1
                    if i % 50 == 0:
                        print(f"Processed {i}/{len(players_without_teams)} players...")
                        session.commit()  # Commit periodically

        except Exception as e:
            errors += 1
            if errors < 10:  # Only print first 10 errors
                print(f"Error updating {player.full_name}: {e}")

    # Final commit
    session.commit()
    close_session()

    print(f"\n[OK] Updated {updated} players")
    print(f"Errors: {errors}")


if __name__ == "__main__":
    print("=== Updating Player Teams ===\n")
    update_player_teams()
    print("\n=== Update Complete ===")
