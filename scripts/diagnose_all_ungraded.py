"""
Diagnose ALL ungraded plays and categorize why they can't be graded
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.db import get_session
from database.models import Play, PropLine, Player, Game, PlayerGameStats, Team
from datetime import datetime
import pytz
from sqlalchemy import func

session = get_session()

print("\n" + "="*80)
print("COMPREHENSIVE UNGRADED PLAYS DIAGNOSIS")
print("="*80 + "\n")

# Get ALL ungraded plays
ungraded = session.query(Play, PropLine, Game).join(
    PropLine, Play.prop_line_id == PropLine.id
).join(
    Game, PropLine.game_id == Game.id
).filter(
    Play.was_correct == None,
    Play.recommendation != 'NO PLAY'
).all()

print(f"Total ungraded plays: {len(ungraded)}\n")

if not ungraded:
    print("All plays are graded! ✓")
    sys.exit(0)

# Categorize issues
categories = {
    'game_too_recent': [],      # Game < 4 hours ago
    'no_stats_player_dnp': [],  # Player didn't play (DNP, injured, etc.)
    'no_stats_not_synced': [],  # Stats not fetched for this player
    'stats_exist_should_grade': []  # Stats exist but not graded (BUG!)
}

utc_now = datetime.utcnow()
central = pytz.timezone('America/Chicago')
utc = pytz.UTC

for play, prop_line, game in ungraded:
    # Get player
    player = session.query(Player).join(
        PropLine, PropLine.player_id == Player.id
    ).filter(PropLine.id == play.prop_line_id).first()

    if not player:
        continue

    # Check game age
    hours_since = (utc_now - game.game_date).total_seconds() / 3600

    if hours_since < 4:
        categories['game_too_recent'].append({
            'play': play,
            'game': game,
            'player': player,
            'hours': hours_since
        })
        continue

    # Convert game date to date-only for matching
    if game.game_date.tzinfo is None:
        game_date_utc = utc.localize(game.game_date)
    else:
        game_date_utc = game.game_date

    game_date_central = game_date_utc.astimezone(central)
    game_date_only = game_date_central.date()

    # Check for stats
    game_stats = session.query(PlayerGameStats).filter(
        PlayerGameStats.player_id == player.id,
        func.date(PlayerGameStats.game_date) == game_date_only
    ).first()

    if game_stats:
        # Stats exist but play not graded - this is a bug!
        categories['stats_exist_should_grade'].append({
            'play': play,
            'game': game,
            'player': player,
            'stats': game_stats,
            'date': game_date_only
        })
    else:
        # No stats - check if player has ANY stats (to differentiate DNP vs not synced)
        any_stats = session.query(PlayerGameStats).filter_by(
            player_id=player.id
        ).count()

        if any_stats > 0:
            # Has other stats but not this game - likely DNP
            categories['no_stats_player_dnp'].append({
                'play': play,
                'game': game,
                'player': player,
                'date': game_date_only
            })
        else:
            # No stats at all - not synced
            categories['no_stats_not_synced'].append({
                'play': play,
                'game': game,
                'player': player,
                'date': game_date_only
            })

# Print results
print("="*80)
print("CATEGORY 1: GAME TOO RECENT (< 4 hours)")
print("="*80)
if categories['game_too_recent']:
    for item in categories['game_too_recent']:
        print(f"  • {item['player'].full_name} - {item['play'].stat_type} - {item['hours']:.1f}h ago")
else:
    print("  (None)")

print("\n" + "="*80)
print("CATEGORY 2: PLAYER DNP / DIDN'T PLAY")
print("="*80)
print("These players have stats for other games but not this specific game")
print("Likely: DNP (rest), injury, traded, or game stats not available yet")
if categories['no_stats_player_dnp']:
    for item in categories['no_stats_player_dnp']:
        away_team = session.query(Team).filter_by(id=item['game'].away_team_id).first()
        home_team = session.query(Team).filter_by(id=item['game'].home_team_id).first()
        matchup = f"{away_team.abbreviation} @ {home_team.abbreviation}" if away_team and home_team else "???"

        print(f"  • {item['player'].full_name:25s} {item['play'].stat_type:6s} - {matchup} - {item['date']}")
else:
    print("  (None)")

print("\n" + "="*80)
print("CATEGORY 3: PLAYER NOT SYNCED")
print("="*80)
print("These players have ZERO stats in database - need to run sync for them")
if categories['no_stats_not_synced']:
    for item in categories['no_stats_not_synced']:
        print(f"  • {item['player'].full_name:25s} (Player ID: {item['player'].id})")
else:
    print("  (None)")

print("\n" + "="*80)
print("CATEGORY 4: STATS EXIST BUT NOT GRADED (BUG!)")
print("="*80)
print("These SHOULD be graded - there's a bug if any appear here!")
if categories['stats_exist_should_grade']:
    for item in categories['stats_exist_should_grade']:
        stat_map = {
            'points': 'points', 'pts': 'points',
            'rebounds': 'rebounds', 'reb': 'rebounds',
            'assists': 'assists', 'ast': 'assists',
            'threes': 'fg3m', '3ptm': 'fg3m', 'fg3m': 'fg3m',
            'steals': 'steals', 'stl': 'steals',
            'blocks': 'blocks', 'blk': 'blocks'
        }

        stat_field = stat_map.get(item['play'].stat_type.lower())
        if stat_field:
            actual = getattr(item['stats'], stat_field)
            print(f"  • {item['player'].full_name:25s} {item['play'].stat_type:6s} {item['play'].recommendation:5s} {item['play'].line_value:.1f}")
            print(f"    Actual: {actual}, Should be: {'WIN' if (actual > item['play'].line_value and item['play'].recommendation == 'OVER') or (actual < item['play'].line_value and item['play'].recommendation == 'UNDER') else 'LOSS'}")
else:
    print("  (None) ✓")

print("\n" + "="*80)
print("SUMMARY")
print("="*80)
print(f"  Game too recent:       {len(categories['game_too_recent'])}")
print(f"  Player DNP/Injured:    {len(categories['no_stats_player_dnp'])}")
print(f"  Player not synced:     {len(categories['no_stats_not_synced'])}")
print(f"  Should be graded:      {len(categories['stats_exist_should_grade'])} ← FIX THESE!")
print("="*80)

# Recommendations
print("\nRECOMMENDATIONS:")
if categories['no_stats_not_synced']:
    print(f"  1. Run sync for {len(categories['no_stats_not_synced'])} players who have no stats")
    print(f"     → heroku run python scripts/sync_nba_stats.py")

if categories['no_stats_player_dnp']:
    print(f"  2. {len(categories['no_stats_player_dnp'])} players likely DNP - verify manually")
    print(f"     → Check if they played in that game on basketball-reference.com")

if categories['stats_exist_should_grade']:
    print(f"  3. ⚠️ {len(categories['stats_exist_should_grade'])} plays have stats but aren't graded!")
    print(f"     → This is a BUG - run sync again or investigate grading logic")

print()
