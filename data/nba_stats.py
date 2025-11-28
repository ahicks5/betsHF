"""
NBA Stats Caching Module
Fetches player game stats from NBA API and caches in database
Provides efficient access to player averages and game logs
Uses existing NBAApiClient with ScraperAPI support
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.nba_api import NBAApiClient
from database.db import get_session
from database.models import Player, Game, Team, PlayerGameStats, APICallLog
from datetime import datetime, timedelta
import time
import numpy as np


def log_api_call(api_name, endpoint=None, player_id=None, season=None, cache_hit=False):
    """Log API call for monitoring"""
    session = get_session()
    log = APICallLog(
        api_name=api_name,
        endpoint=endpoint,
        player_id=player_id,
        season=season,
        cache_hit=cache_hit
    )
    session.add(log)
    session.commit()


def get_current_season():
    """Get current NBA season (e.g., '2025-26')"""
    return "2025-26"


def fetch_player_game_log(player_id, season=None, force_refresh=False):
    """
    Fetch player game log from NBA API or cache

    Args:
        player_id: Internal database player ID
        season: NBA season (e.g., '2024-25'), defaults to current
        force_refresh: If True, fetch from API even if cached

    Returns:
        List of PlayerGameStats objects
    """
    session = get_session()

    if season is None:
        season = get_current_season()

    # Get player info
    player = session.query(Player).filter_by(id=player_id).first()
    if not player:
        print(f"[ERROR] Player ID {player_id} not found in database")
        return []

    # Check cache first (unless force refresh)
    if not force_refresh:
        # Get cached stats for this player/season
        cached_stats = session.query(PlayerGameStats).filter_by(
            player_id=player_id,
            season=season
        ).order_by(PlayerGameStats.game_date).all()

        # If we have cache data from the last 12 hours, use it
        if cached_stats:
            most_recent = max(cached_stats, key=lambda x: x.fetched_at)
            if most_recent.fetched_at > datetime.utcnow() - timedelta(hours=12):
                # Filter out marker records (where all stats are None)
                real_stats = [s for s in cached_stats if s.minutes is not None or s.points is not None]

                log_api_call('nba_api', 'playergamelog', player_id, season, cache_hit=True)
                print(f"[CACHE HIT] {player.full_name} - {len(real_stats)} games (last updated {most_recent.fetched_at})")
                return real_stats

    # Fetch from NBA API using existing client (with ScraperAPI support)
    print(f"[NBA API] Fetching game log for {player.full_name} ({season})...")
    log_api_call('nba_api', 'playergamelog', player_id, season, cache_hit=False)

    try:
        # Use existing NBAApiClient (has ScraperAPI, retry logic, proper headers)
        nba_client = NBAApiClient()
        df = nba_client.get_player_game_log(player.nba_player_id, season)

        if df.empty:
            print(f"[WARNING] No games found for {player.full_name} in {season}")
            # Don't create marker records - just return empty list
            # This avoids database constraint errors for players with no games
            return []

        # Store in database
        stats_objects = []
        for _, row in df.iterrows():
            game_date = datetime.strptime(row['GAME_DATE'], '%b %d, %Y')
            nba_game_id = row['Game_ID']

            # Check if we already have this game stat
            existing = session.query(PlayerGameStats).filter_by(
                player_id=player_id,
                nba_game_id=nba_game_id
            ).first()

            if existing:
                # Update existing record
                stats_obj = existing
            else:
                # Create new record
                stats_obj = PlayerGameStats(player_id=player_id)

            # Get or create game record
            game = session.query(Game).filter_by(nba_game_id=nba_game_id).first()
            if game:
                stats_obj.game_id = game.id

            # Update stats
            stats_obj.nba_game_id = nba_game_id
            stats_obj.game_date = game_date
            stats_obj.minutes = float(row['MIN']) if row['MIN'] else None
            stats_obj.points = int(row['PTS']) if row['PTS'] is not None else None
            stats_obj.rebounds = int(row['REB']) if row['REB'] is not None else None
            stats_obj.assists = int(row['AST']) if row['AST'] is not None else None
            stats_obj.steals = int(row['STL']) if row['STL'] is not None else None
            stats_obj.blocks = int(row['BLK']) if row['BLK'] is not None else None
            stats_obj.turnovers = int(row['TOV']) if row['TOV'] is not None else None
            stats_obj.fgm = int(row['FGM']) if row['FGM'] is not None else None
            stats_obj.fga = int(row['FGA']) if row['FGA'] is not None else None
            stats_obj.fg_pct = float(row['FG_PCT']) if row['FG_PCT'] is not None else None
            stats_obj.fg3m = int(row['FG3M']) if row['FG3M'] is not None else None
            stats_obj.fg3a = int(row['FG3A']) if row['FG3A'] is not None else None
            stats_obj.fg3_pct = float(row['FG3_PCT']) if row['FG3_PCT'] is not None else None
            stats_obj.ftm = int(row['FTM']) if row['FTM'] is not None else None
            stats_obj.fta = int(row['FTA']) if row['FTA'] is not None else None
            stats_obj.ft_pct = float(row['FT_PCT']) if row['FT_PCT'] is not None else None
            stats_obj.season = season
            stats_obj.fetched_at = datetime.utcnow()

            if not existing:
                session.add(stats_obj)

            stats_objects.append(stats_obj)

        session.commit()
        print(f"[OK] Cached {len(stats_objects)} games for {player.full_name}")
        return stats_objects

    except Exception as e:
        print(f"[ERROR] Failed to fetch game log for {player.full_name}: {e}")
        session.rollback()
        return []


def get_player_averages(player_id, stat_types=None, last_n_games=None, season=None):
    """
    Calculate player averages from cached stats

    Args:
        player_id: Internal database player ID
        stat_types: List of stats to calculate (e.g., ['points', 'rebounds'])
        last_n_games: If provided, only use last N games
        season: NBA season, defaults to current

    Returns:
        Dictionary of stat averages
    """
    # Get cached game stats
    games = fetch_player_game_log(player_id, season)

    if not games:
        return {}

    # Sort by date (most recent first)
    games = sorted(games, key=lambda x: x.game_date, reverse=True)

    # Limit to last N games if specified
    if last_n_games:
        games = games[:last_n_games]

    if not games:
        return {}

    # Default stat types
    if stat_types is None:
        stat_types = ['points', 'rebounds', 'assists', 'steals', 'blocks', 'turnovers', 'fg3m']

    averages = {}

    for stat in stat_types:
        values = [getattr(g, stat) for g in games if getattr(g, stat) is not None]
        if values:
            averages[stat] = np.mean(values)
            averages[f'{stat}_std'] = np.std(values)
            averages[f'{stat}_games'] = len(values)
        else:
            averages[stat] = None
            averages[f'{stat}_std'] = None
            averages[f'{stat}_games'] = 0

    return averages


def get_player_stat_distribution(player_id, stat_type, season=None):
    """
    Get detailed distribution for a specific stat

    Returns:
        {
            'mean': float,
            'std': float,
            'min': float,
            'max': float,
            'median': float,
            'games_played': int,
            'values': list
        }
    """
    games = fetch_player_game_log(player_id, season)

    if not games:
        return None

    values = [getattr(g, stat_type) for g in games if getattr(g, stat_type) is not None]

    if not values:
        return None

    return {
        'mean': np.mean(values),
        'std': np.std(values),
        'min': min(values),
        'max': max(values),
        'median': np.median(values),
        'games_played': len(values),
        'values': values
    }


def sync_all_active_players(season=None):
    """
    Sync stats for all players who have prop lines
    This is the main function run 2x/day

    Returns:
        Number of players synced
    """
    session = get_session()

    if season is None:
        season = get_current_season()

    print(f"\n[SYNC] Starting sync for season {season}...")
    print(f"[SYNC] Time: {datetime.now()}")

    # Get all unique players from recent prop lines (last 7 days)
    from database.models import PropLine
    from sqlalchemy import distinct, func

    cutoff = datetime.utcnow() - timedelta(days=7)
    active_player_ids = session.query(distinct(PropLine.player_id)).filter(
        PropLine.collected_at >= cutoff
    ).all()

    active_player_ids = [pid[0] for pid in active_player_ids]

    print(f"[SYNC] Found {len(active_player_ids)} active players")

    synced_count = 0
    error_count = 0

    for player_id in active_player_ids:
        try:
            player = session.query(Player).filter_by(id=player_id).first()
            if not player:
                continue

            # Fetch and cache stats (force_refresh=True to get latest)
            stats = fetch_player_game_log(player_id, season, force_refresh=True)
            if stats:
                synced_count += 1
                print(f"[{synced_count}/{len(active_player_ids)}] ✓ {player.full_name}")

        except Exception as e:
            error_count += 1
            print(f"[ERROR] Failed to sync {player_id}: {e}")
            continue

    print(f"\n[SYNC COMPLETE]")
    print(f"  ✓ Synced: {synced_count}")
    print(f"  ✗ Errors: {error_count}")
    print(f"  Total: {len(active_player_ids)}")

    return synced_count


if __name__ == "__main__":
    # Test the module
    print("Testing NBA stats caching...")
    sync_all_active_players()
