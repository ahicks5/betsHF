# Daily Run Guide

## Quick Start - Run This Every Day

```bash
# Step 1: Collect today's data
python scripts/collect_today.py

# Step 2: Analyze and find plays
python scripts/find_plays.py

# Step 3: View results in browser (optional)
python app.py
```

Then open your browser to `http://localhost:5000`

---

## What Each Step Does

### Step 1: `collect_today.py`
- Fetches today's NBA games
- Loads all player props from sportsbooks
- Stores data in `props.db` database
- **Time:** ~2-3 minutes
- **API calls:** ~15-20 (The Odds API)

### Step 2: `find_plays.py`
- Analyzes all props using NBA stats
- Calculates expected values and z-scores
- Identifies betting opportunities
- Saves plays to database with timestamps
- Exports CSV report
- **Time:** ~3-5 minutes
- **API calls:** ~100-200 (NBA API, cached)

### Step 3: `app.py` (Web Interface)
- View today's plays in browser
- Filter by confidence, stat type, player
- See historical play results
- **No API calls** - reads from database

---

## Automation Setup (For Future Hosting)

### Option 1: Linux Cron Job

```bash
# Edit crontab
crontab -e

# Add this line to run daily at 10 AM ET
0 10 * * * cd /path/to/betsHF && /usr/bin/python3 scripts/collect_today.py && /usr/bin/python3 scripts/find_plays.py
```

### Option 2: Heroku Scheduler

```bash
# Install Heroku CLI
heroku login

# Add scheduler addon
heroku addons:create scheduler:standard

# Configure job in dashboard:
# - Command: python scripts/collect_today.py && python scripts/find_plays.py
# - Frequency: Daily at 10 AM ET
```

### Option 3: GitHub Actions

Create `.github/workflows/daily_analysis.yml`:

```yaml
name: Daily Analysis
on:
  schedule:
    - cron: '0 14 * * *'  # 10 AM ET (2 PM UTC)
  workflow_dispatch:  # Allow manual trigger

jobs:
  analyze:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      - run: pip install -r requirements.txt
      - run: python scripts/collect_today.py
        env:
          ODDS_API_KEY: ${{ secrets.ODDS_API_KEY }}
      - run: python scripts/find_plays.py
```

### Option 4: AWS Lambda

```bash
# Package dependencies
pip install -r requirements.txt -t lambda/

# Deploy using AWS CLI or Serverless Framework
# Configure CloudWatch Events to trigger daily
```

---

## Best Time to Run

**Recommended: 10 AM ET / 7 AM PT**

Why:
- NBA games usually scheduled the night before
- Odds lines posted by morning
- Gives you time to review before afternoon games
- Most bookmakers have lines up by 10 AM

---

## Output Files

After running, you'll find:

1. **Database:** `props.db`
   - All games, props, and plays
   - Queryable with SQL

2. **CSV Export:** `analysis_details_YYYYMMDD_HHMMSS.csv`
   - Full calculation details
   - Import to Excel/Sheets

3. **Web Dashboard:** `http://localhost:5000`
   - Today's plays
   - Historical results (when implemented)

---

## Environment Variables

Required in `.env`:

```bash
ODDS_API_KEY=your_key_here
```

Optional:

```bash
FLASK_ENV=development  # or 'production'
DATABASE_URL=sqlite:///props.db
```

---

## Monitoring

### Check if it ran successfully:

```bash
# View latest plays
sqlite3 props.db "SELECT * FROM plays WHERE DATE(created_at) = DATE('now') ORDER BY z_score DESC LIMIT 10;"

# Count today's props
sqlite3 props.db "SELECT COUNT(*) FROM prop_lines WHERE DATE(created_at) = DATE('now');"

# Check CSV exists
ls -lh analysis_details_*.csv | tail -1
```

### Common Issues:

**No games found:**
- Check if NBA is in season
- Verify it's a game day

**API quota exceeded:**
- Odds API free tier = 500 requests/month
- ~15 requests/day × 30 days = 450/month
- Upgrade at https://the-odds-api.com/

**Stale data:**
- Run `collect_today.py` first
- Check `created_at` timestamps in database

---

## Quick Database Queries

```bash
# Today's high-confidence plays
sqlite3 props.db "SELECT player_name, stat_type, recommendation, z_score, confidence FROM plays WHERE DATE(created_at) = DATE('now') AND confidence = 'High' ORDER BY ABS(z_score) DESC;"

# Games today
sqlite3 props.db "SELECT home_team_id, away_team_id, game_date FROM games WHERE DATE(game_date) = DATE('now');"

# Prop count by bookmaker
sqlite3 props.db "SELECT bookmaker, COUNT(*) FROM prop_lines WHERE is_latest = 1 GROUP BY bookmaker;"
```

---

## Next Steps

1. ✅ Run daily workflow manually for a week
2. ✅ Track results to validate strategy
3. ✅ Set up automation on preferred platform
4. ✅ Configure email/Slack notifications for plays
5. ✅ Build historical analysis after collecting data

---

## Support

- Issues: Check logs in console output
- API docs: https://the-odds-api.com/liveapi/guides/v4/
- NBA API: https://github.com/swar/nba_api
