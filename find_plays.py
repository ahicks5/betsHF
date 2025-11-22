"""
Find Today's Best Plays

Analyzes all collected props and shows recommendations
Sorted by strongest deviation (highest z-score)
"""
from database.db import get_session, close_session
from database.models import PropLine, Player, Game, Team
from analyzer import PropAnalyzer
from tabulate import tabulate


def get_opponent_abbr(session, game, player):
    """Determine opponent abbreviation for a player in a game"""
    # Find player's team
    player_team = player.team

    if not player_team:
        return None

    # If player's team is home team, opponent is away team
    if game.home_team_id == player_team.id:
        return game.away_team.abbreviation
    else:
        return game.home_team.abbreviation


def analyze_all_props():
    """Analyze all latest props and display results"""
    session = get_session()
    analyzer = PropAnalyzer()

    print("=== Analyzing Today's Props ===\n")

    # Get all latest props
    props = session.query(PropLine).filter_by(is_latest=True).all()

    if not props:
        print("No props found. Run collect_today.py first.")
        close_session()
        return

    print(f"Found {len(props)} props to analyze\n")

    analyses = []

    for prop in props:
        player = prop.player
        game = prop.game

        # Get opponent
        opponent_abbr = get_opponent_abbr(session, game, player)

        if not opponent_abbr:
            continue

        # Analyze the prop
        try:
            analysis = analyzer.analyze_prop(
                player_id=player.nba_player_id,
                player_name=player.full_name,
                stat_type=prop.prop_type,
                line_value=prop.line_value,
                opponent_abbr=opponent_abbr
            )

            # Add odds info
            analysis['over_odds'] = prop.over_odds
            analysis['under_odds'] = prop.under_odds
            analysis['bookmaker'] = prop.bookmaker

            # Only include plays with recommendations
            if analysis['recommendation'] != "NO PLAY":
                analyses.append(analysis)

        except Exception as e:
            print(f"Error analyzing {player.full_name} {prop.prop_type}: {e}")
            continue

    close_session()

    # Sort by absolute z-score (strongest deviation first)
    analyses.sort(key=lambda x: abs(x['z_score']), reverse=True)

    # Display results
    if not analyses:
        print("No strong plays found today.")
        return

    print(f"=== Found {len(analyses)} Plays ===\n")

    # Prepare table
    table_data = []

    for a in analyses:
        # Determine which odds to show based on recommendation
        if a['recommendation'] == "OVER":
            odds = a['over_odds']
        else:
            odds = a['under_odds']

        table_data.append([
            a['player_name'],
            a['stat_type'],
            a['line_value'],
            a['expected_value'],
            a['deviation'],
            a['z_score'],
            a['recommendation'],
            a['confidence'],
            odds
        ])

    headers = [
        "Player",
        "Stat",
        "Line",
        "Expected",
        "Deviation",
        "Z-Score",
        "Play",
        "Confidence",
        "Odds"
    ]

    print(tabulate(table_data, headers=headers, tablefmt="grid"))

    # Show top 5 details
    print("\n=== Top 5 Plays (Details) ===\n")

    for i, a in enumerate(analyses[:5], 1):
        print(f"{i}. {a['player_name']} - {a['stat_type']} {a['recommendation']} {a['line_value']}")
        print(f"   Expected: {a['expected_value']} (Season: {a['season_avg']}, L5: {a['recent_avg']}, Opp: {a['opponent_avg']})")
        print(f"   Deviation: {a['deviation']} (Z-Score: {a['z_score']})")
        print(f"   Confidence: {a['confidence']}")
        print(f"   Bookmaker: {a['bookmaker']}")
        print()


if __name__ == "__main__":
    analyze_all_props()
