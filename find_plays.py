"""
Find Today's Best Plays

Analyzes all collected props and shows recommendations
Sorted by strongest deviation (highest z-score)
"""
from database.db import get_session, close_session
from database.models import PropLine, Player, Game, Team
from cached_analyzer import CachedPropAnalyzer
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
    analyzer = CachedPropAnalyzer()

    print("=== Analyzing Today's Props ===\n")

    # Get all latest props
    props = session.query(PropLine).filter_by(is_latest=True).all()

    if not props:
        print("No props found. Run collect_today.py first.")
        close_session()
        return

    print(f"Found {len(props)} props to analyze\n")

    analyses = []
    all_analyses = []  # Track everything
    skipped_no_team = 0
    errors = 0

    for prop in props:
        player = prop.player
        game = prop.game

        # Get opponent
        opponent_abbr = get_opponent_abbr(session, game, player)

        if not opponent_abbr:
            skipped_no_team += 1
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

            # Track all analyses
            all_analyses.append(analysis)

            # Only include plays with recommendations
            if analysis['recommendation'] != "NO PLAY":
                analyses.append(analysis)

        except Exception as e:
            print(f"Error analyzing {player.full_name} {prop.prop_type}: {e}")
            errors += 1
            continue

    close_session()

    # Deduplicate props - keep only ONE prop per player+stat (the one with highest z-score)
    player_stat_best = {}

    for analysis in all_analyses:
        key = (analysis['player_name'], analysis['stat_type'])
        abs_z = abs(analysis['z_score'])

        # Keep the one with highest absolute z-score
        if key not in player_stat_best or abs_z > abs(player_stat_best[key]['z_score']):
            player_stat_best[key] = analysis

    # Convert back to lists
    all_analyses = list(player_stat_best.values())
    analyses = [a for a in all_analyses if a['recommendation'] != "NO PLAY"]

    # Print cache statistics
    cache_stats = analyzer.get_cache_stats()
    print(f"Cache Stats: {cache_stats['players_cached']} players, {cache_stats['teams_cached']} teams cached")
    print()

    # Print summary statistics
    print(f"Analysis Summary:")
    print(f"  Total props in database: {len(props)}")
    print(f"  Successfully analyzed (before dedup): {len(all_analyses) + len(props) - len(all_analyses)}")
    print(f"  Unique props (after dedup): {len(all_analyses)}")
    print(f"  Skipped (no team assigned): {skipped_no_team}")
    print(f"  Errors: {errors}")
    print(f"  Plays with recommendations: {len(analyses)}")
    print()

    # Sort by absolute z-score (strongest deviation first)
    analyses.sort(key=lambda x: abs(x['z_score']), reverse=True)
    all_analyses.sort(key=lambda x: abs(x['z_score']), reverse=True)

    # Display top 20 props regardless of recommendation
    print("=== Top 20 Props by Z-Score (All Props) ===\n")

    top_20 = all_analyses[:20]
    table_data = []

    for a in top_20:
        if a['recommendation'] == "OVER":
            odds = a['over_odds']
        elif a['recommendation'] == "UNDER":
            odds = a['under_odds']
        else:
            odds = "-"

        table_data.append([
            a['player_name'][:20],  # Truncate long names
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
    print()

    # Display results for strong plays only
    if not analyses:
        print("No plays with z-score > 0.5 found.")
        print("\nNote: To see plays, props need z-score > 0.5 (Medium) or > 1.0 (High)")
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
