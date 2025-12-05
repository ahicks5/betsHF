# Manual Recovery Guide

When scheduled scripts haven't run for a few days (API limits, outages, etc.), use this guide to get everything back up to speed.

## Quick Recovery Commands

Run these on Heroku in order:

```bash
# 1. Grade past games that weren't graded
heroku run python scripts/collect_results.py

# 2. Clean up any duplicate plays
heroku run python scripts/migrations/cleanup_duplicate_plays.py

# 3. Collect today's props and generate picks
heroku run python scripts/run_all.py
```

## What Each Script Does

### Data Collection
| Script | Purpose | When to Run |
|--------|---------|-------------|
| `scripts/collect_today.py` | Fetches today's games and prop lines from Odds API | Before generating picks |
| `scripts/sync_nba_stats.py` | Pulls player game logs from NBA API | Once daily (morning) |

### Analysis & Picks
| Script | Purpose | When to Run |
|--------|---------|-------------|
| `scripts/find_plays.py` | Analyzes props and generates picks for all models | After collecting props |
| `scripts/run_all.py` | Runs collect + sync + find_plays in order | Convenience wrapper |

### Results & Grading
| Script | Purpose | When to Run |
|--------|---------|-------------|
| `scripts/collect_results.py` | Grades ungraded plays with actual results | After games complete |

### Maintenance
| Script | Purpose | When to Run |
|--------|---------|-------------|
| `scripts/migrations/cleanup_duplicate_plays.py` | Removes duplicate plays | After recovery/fixes |
| `scripts/migrations/migrate_add_is_locked.py` | Adds is_locked column | One-time migration |

## Play States

Plays go through these states:
- **OPEN** (`is_locked=False`, `was_correct=None`): Can be updated with better lines
- **LOCKED** (`is_locked=True`, `was_correct=None`): Game started, waiting for results
- **GRADED** (`was_correct` is not None): Has final results

## Scheduled Runner

The `scripts/scheduled_runner.py` handles automated runs via Heroku Scheduler:
- **Morning (10 AM CT)**: Collects props, syncs stats, generates picks
- **2 hours before first game**: Refreshes props and picks
- **After games**: Grades results

Force options:
```bash
heroku run python scripts/scheduled_runner.py --force-picks   # Force pick generation
heroku run python scripts/scheduled_runner.py --force-grade   # Force grading
heroku run python scripts/scheduled_runner.py --force-all     # Run everything
heroku run python scripts/scheduled_runner.py --dry-run       # Show what would run
```

## Common Issues

### "No props found"
- Odds API may not have lines yet (too early in day)
- Check API quota/limits

### Duplicate plays appearing
- Run `cleanup_duplicate_plays.py`
- Now prevented by UPSERT logic in find_plays.py

### Plays not getting graded
- Game must be completed (4+ hours after start)
- Run `collect_results.py` manually

### API rate limits
- NBA API: 0.6s delay between calls (built-in)
- Odds API: Check your plan limits
- ScraperAPI: Check your plan limits
