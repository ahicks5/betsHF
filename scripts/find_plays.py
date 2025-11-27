"""
Find Today's Best Plays

Analyzes all collected props and shows recommendations
Sorted by strongest deviation (highest z-score)
"""
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.db import get_session, close_session
from database.models import PropLine, Player, Game, Team, Play
from cached_analyzer import CachedPropAnalyzer
from tabulate import tabulate
import csv
from datetime import datetime


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


def export_detailed_csv(analyses, filename=None):
    """
    Export all analysis details to CSV showing calculation steps

    This helps diagnose issues by showing exactly how expected values are calculated
    """
    if filename is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"analysis_details_{timestamp}.csv"

    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = [
            'Player',
            'Stat',
            'Line',
            'Season_Avg',
            'L5_Avg',
            'Formula',
            'Expected',
            'Std_Dev',
            'Games_Played',
            'Deviation',
            'Z_Score',
            'Recommendation',
            'Confidence',
            'Bookmaker',
            'Over_Odds',
            'Under_Odds'
        ]

        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

        for a in analyses:
            # Show the formula calculation
            formula = f"({a['season_avg']} × 0.5) + ({a['recent_avg']} × 0.5) = {a['expected_value']}"

            writer.writerow({
                'Player': a['player_name'],
                'Stat': a['stat_type'],
                'Line': a['line_value'],
                'Season_Avg': a['season_avg'],
                'L5_Avg': a['recent_avg'],
                'Formula': formula,
                'Expected': a['expected_value'],
                'Std_Dev': a['std_dev'],
                'Games_Played': a.get('games_played', 'N/A'),
                'Deviation': a['deviation'],
                'Z_Score': a['z_score'],
                'Recommendation': a['recommendation'],
                'Confidence': a['confidence'],
                'Bookmaker': a['bookmaker'],
                'Over_Odds': a.get('over_odds', ''),
                'Under_Odds': a.get('under_odds', '')
            })

    return filename


def save_plays_to_db(session, analyses_with_props):
    """Save analyzed plays to the database"""
    saved_count = 0

    for item in analyses_with_props:
        analysis = item['analysis']
        prop = item['prop']

        try:
            play = Play(
                prop_line_id=prop.id,
                player_name=analysis['player_name'],
                stat_type=analysis['stat_type'],
                line_value=analysis['line_value'],
                season_avg=analysis['season_avg'],
                last5_avg=analysis['recent_avg'],
                expected_value=analysis['expected_value'],
                std_dev=analysis['std_dev'],
                deviation=analysis['deviation'],
                z_score=analysis['z_score'],
                games_played=analysis.get('games_played', 0),
                recommendation=analysis['recommendation'],
                confidence=analysis['confidence'],
                bookmaker=analysis['bookmaker'],
                over_odds=analysis.get('over_odds'),
                under_odds=analysis.get('under_odds')
            )

            session.add(play)
            saved_count += 1

        except Exception as e:
            print(f"Error saving play for {analysis['player_name']}: {e}")
            continue

    session.commit()
    return saved_count


def analyze_all_props():
    """Analyze all latest props and display results"""
    session = get_session()
    analyzer = CachedPropAnalyzer()

    print("=== Analyzing Today's Props ===\n")

    # Clear out only UNGRADED plays to avoid duplicates
    # Keep historical plays that have results (was_correct is not None)
    ungraded_plays = session.query(Play).filter(Play.was_correct == None).all()
    for play in ungraded_plays:
        session.delete(play)
    session.commit()
    print(f"[OK] Cleared {len(ungraded_plays)} ungraded plays from database\n")

    # Get all latest props
    props = session.query(PropLine).filter_by(is_latest=True).all()

    if not props:
        print("No props found. Run collect_today.py first.")
        close_session()
        return

    print(f"Found {len(props)} props to analyze\n")

    analyses = []
    all_analyses = []  # Track everything
    all_analyses_with_props = []  # Track analyses with their prop references
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
            all_analyses_with_props.append({'analysis': analysis, 'prop': prop})

            # Only include plays with recommendations
            if analysis['recommendation'] != "NO PLAY":
                analyses.append(analysis)

        except Exception as e:
            print(f"Error analyzing {player.full_name} {prop.prop_type}: {e}")
            errors += 1
            continue

    # Deduplicate props - keep only ONE prop per player+stat
    # Pick the play with the STRONGEST SIGNAL (highest absolute z-score)
    player_stat_best = {}
    player_stat_best_with_props = {}

    for item in all_analyses_with_props:
        analysis = item['analysis']
        key = (analysis['player_name'], analysis['stat_type'])

        if key not in player_stat_best:
            player_stat_best[key] = analysis
            player_stat_best_with_props[key] = item
        else:
            current = player_stat_best[key]

            # Keep the play with the highest absolute z-score (strongest signal)
            if abs(analysis['z_score']) > abs(current['z_score']):
                player_stat_best[key] = analysis
                player_stat_best_with_props[key] = item

    # Convert back to lists
    all_analyses = list(player_stat_best.values())
    all_analyses_with_props = list(player_stat_best_with_props.values())
    analyses = [a for a in all_analyses if a['recommendation'] != "NO PLAY"]

    # Save all plays to database
    saved_count = save_plays_to_db(session, all_analyses_with_props)
    print(f"[OK] Saved {saved_count} plays to database")
    print()

    close_session()

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

    # Export detailed CSV for diagnostics
    csv_filename = export_detailed_csv(all_analyses)
    print(f"[OK] Exported detailed analysis to: {csv_filename}")
    print()

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
        print(f"   Expected: {a['expected_value']} (Season: {a['season_avg']}, L5: {a['recent_avg']})")
        print(f"   Deviation: {a['deviation']} (Z-Score: {a['z_score']})")
        print(f"   Confidence: {a['confidence']}")
        print(f"   Bookmaker: {a['bookmaker']}")
        print()


if __name__ == "__main__":
    analyze_all_props()
