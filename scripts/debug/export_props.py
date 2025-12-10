"""
Export Prop Data for Investigation

Shows all prop lines in the database to understand:
- How many lines exist per player/stat
- Which bookmakers we have
- Line value variations
- Odds variations

Usage:
    python scripts/debug/export_props.py              # Export to CSV
    python scripts/debug/export_props.py --today      # Only today's props
    python scripts/debug/export_props.py --player "LeBron James"
"""
import sys
from pathlib import Path
import csv
from datetime import datetime, timedelta

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from database.db import get_session, close_session
from database.models import PropLine, Player, Game, Team
from sqlalchemy import func
import argparse


def export_props(output_file=None, today_only=False, player_filter=None):
    """Export all prop lines to CSV for investigation"""
    session = get_session()

    # Build query
    query = session.query(
        PropLine,
        Player.full_name,
        Player.nba_player_id,
        Game.game_date,
        Game.nba_game_id
    ).join(
        Player, PropLine.player_id == Player.id
    ).join(
        Game, PropLine.game_id == Game.id
    )

    if today_only:
        from app import LOCAL_TIMEZONE
        import pytz
        now_local = datetime.now(LOCAL_TIMEZONE)
        today_start = LOCAL_TIMEZONE.localize(datetime.combine(now_local.date(), datetime.min.time()))
        today_end = today_start + timedelta(days=2)  # Include tomorrow too
        today_start_utc = today_start.astimezone(pytz.utc).replace(tzinfo=None)
        today_end_utc = today_end.astimezone(pytz.utc).replace(tzinfo=None)
        query = query.filter(Game.game_date >= today_start_utc, Game.game_date < today_end_utc)

    if player_filter:
        query = query.filter(Player.full_name.ilike(f'%{player_filter}%'))

    # Order by player, stat, then collected_at
    query = query.order_by(Player.full_name, PropLine.prop_type, PropLine.collected_at.desc())

    results = query.all()

    if not results:
        print("No props found matching criteria")
        close_session()
        return

    # Prepare data
    rows = []
    for prop, player_name, nba_player_id, game_date, nba_game_id in results:
        rows.append({
            'player_name': player_name,
            'nba_player_id': nba_player_id,
            'stat_type': prop.prop_type,
            'line_value': prop.line_value,
            'over_odds': prop.over_odds,
            'under_odds': prop.under_odds,
            'bookmaker': prop.bookmaker,
            'is_latest': prop.is_latest,
            'collected_at': prop.collected_at.strftime('%Y-%m-%d %H:%M:%S') if prop.collected_at else '',
            'game_date': game_date.strftime('%Y-%m-%d %H:%M') if game_date else '',
            'game_id': nba_game_id,
            'prop_line_id': prop.id
        })

    # Print summary first
    print(f"\n=== Prop Data Summary ===")
    print(f"Total prop lines: {len(rows)}")

    # Count by is_latest
    latest_count = sum(1 for r in rows if r['is_latest'])
    old_count = len(rows) - latest_count
    print(f"Latest (is_latest=True): {latest_count}")
    print(f"Historical (is_latest=False): {old_count}")

    # Count unique player/stat combinations
    unique_player_stats = set((r['player_name'], r['stat_type']) for r in rows)
    print(f"Unique player+stat combinations: {len(unique_player_stats)}")

    # Count by bookmaker
    bookmaker_counts = {}
    for r in rows:
        bookie = r['bookmaker'] or 'Unknown'
        bookmaker_counts[bookie] = bookmaker_counts.get(bookie, 0) + 1

    print(f"\nBy Bookmaker:")
    for bookie, count in sorted(bookmaker_counts.items(), key=lambda x: -x[1]):
        print(f"  {bookie}: {count}")

    # Find players with multiple lines for same stat (latest only)
    latest_rows = [r for r in rows if r['is_latest']]
    player_stat_lines = {}
    for r in latest_rows:
        key = (r['player_name'], r['stat_type'])
        if key not in player_stat_lines:
            player_stat_lines[key] = []
        player_stat_lines[key].append(r)

    multi_line_cases = {k: v for k, v in player_stat_lines.items() if len(v) > 1}

    if multi_line_cases:
        print(f"\n=== Players with MULTIPLE 'latest' lines for same stat ===")
        print(f"Found {len(multi_line_cases)} cases:\n")

        for (player, stat), lines in sorted(multi_line_cases.items())[:20]:  # Show first 20
            print(f"{player} - {stat}:")
            for line in lines:
                print(f"  Line: {line['line_value']} | Over: {line['over_odds']} | Under: {line['under_odds']} | Book: {line['bookmaker']}")
            print()

    # Export to CSV
    if output_file is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"prop_data_export_{timestamp}.csv"

    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    print(f"\n[OK] Exported {len(rows)} rows to: {output_file}")

    close_session()
    return rows


def show_line_variations():
    """Show how lines vary across bookmakers for the same player/stat"""
    session = get_session()

    # Get only latest props
    query = session.query(
        Player.full_name,
        PropLine.prop_type,
        func.count(PropLine.id).label('num_lines'),
        func.min(PropLine.line_value).label('min_line'),
        func.max(PropLine.line_value).label('max_line'),
        func.avg(PropLine.line_value).label('avg_line')
    ).join(
        Player, PropLine.player_id == Player.id
    ).filter(
        PropLine.is_latest == True
    ).group_by(
        Player.full_name, PropLine.prop_type
    ).having(
        func.count(PropLine.id) > 1  # Only show where there are multiple lines
    ).order_by(
        (func.max(PropLine.line_value) - func.min(PropLine.line_value)).desc()
    )

    results = query.limit(30).all()

    print(f"\n=== Line Variations (Latest Props Only) ===")
    print(f"Showing player/stats with multiple bookmaker lines:\n")
    print(f"{'Player':<25} {'Stat':<6} {'Lines':<6} {'Min':<8} {'Max':<8} {'Spread':<8}")
    print("-" * 70)

    for player, stat, num_lines, min_line, max_line, avg_line in results:
        spread = max_line - min_line
        print(f"{player[:24]:<25} {stat:<6} {num_lines:<6} {min_line:<8.1f} {max_line:<8.1f} {spread:<8.1f}")

    close_session()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Export prop data for investigation')
    parser.add_argument('--today', action='store_true', help='Only export today/tomorrow props')
    parser.add_argument('--player', type=str, help='Filter by player name')
    parser.add_argument('--output', '-o', type=str, help='Output CSV filename')
    parser.add_argument('--variations', action='store_true', help='Show line variations across bookmakers')

    args = parser.parse_args()

    if args.variations:
        show_line_variations()
    else:
        export_props(
            output_file=args.output,
            today_only=args.today,
            player_filter=args.player
        )
