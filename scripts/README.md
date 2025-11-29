# Scripts Directory

## Production Scripts (Main folder)

These are the core scripts used in daily operations:

| Script | Description |
|--------|-------------|
| `collect_today.py` | Fetch today's games and player props from APIs |
| `find_plays.py` | Analyze props and generate betting recommendations |
| `collect_results.py` | Collect game results and grade plays |
| `sync_nba_stats.py` | Sync player statistics from NBA API |
| `update_player_teams.py` | Update player team assignments |
| `export_data.py` | Export database data for backup |
| `import_data.py` | Import data from backup |
| `find_player_mismatches.py` | Find player name mismatches between Odds API and NBA API |

## Debug Scripts (`debug/`)

Scripts for debugging and troubleshooting:

- `debug_grading.py` - Debug play grading issues
- `debug_devin_booker.py` - Debug specific player issues
- `debug_ungraded_play.py` - Debug ungraded plays
- `diagnose_nba_api.py` - Diagnose NBA API connection issues
- `diagnose_all_ungraded.py` - Find all ungraded plays
- `test_*.py` - Various test scripts
- `check_schema.py` - Verify database schema
- `verify_profit_calc.py` - Verify profit calculations
- `fix_sequences.py` - Fix database sequence issues

## Migration Scripts (`migrations/`)

Database migration scripts:

- `migrate_nullable_game_id.py` - Make game_id nullable
- `migrate_sqlite_nullable.py` - SQLite-specific nullable migration

## Daily Workflow

1. **Collect data**: `python scripts/collect_today.py`
2. **Generate plays**: `python scripts/find_plays.py`
3. **After games**: `python scripts/collect_results.py`
