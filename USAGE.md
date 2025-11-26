# NBA Props Analyzer - Usage Guide

## Timezone Configuration

The project uses **Central Time (America/Chicago)** by default. All plays and dates are displayed in your local timezone.

### Changing Your Timezone

Edit `app.py` line 16:

```python
LOCAL_TIMEZONE = pytz.timezone('America/Chicago')  # Change to your timezone
```

Common timezones:
- `'America/New_York'` - Eastern Time
- `'America/Chicago'` - Central Time (default)
- `'America/Denver'` - Mountain Time
- `'America/Los_Angeles'` - Pacific Time

### How Timezone Works

- **Database**: Stores all timestamps in UTC (universal standard)
- **Display**: Converts to your local timezone for viewing
- **Front Page**: Shows plays created "today" in your local timezone
- **History Page**: Shows plays from previous days (excludes today)

## Daily Workflow

### 1. Collect Today's Props (Morning)

Run this around 10 AM ET / 7 AM PT when betting lines are posted:

```bash
python scripts/collect_today.py
```

This fetches:
- Today's NBA games
- All available player prop betting lines
- Updates player team assignments

### 2. Analyze and Generate Plays

```bash
python scripts/find_plays.py
```

This:
- Analyzes all props using statistical model
- Calculates expected values and z-scores
- Generates recommendations (OVER/UNDER)
- Saves plays to database
- Exports detailed CSV analysis

### 3. View Plays in Browser

```bash
python app.py
```

Open http://localhost:5000

**Front Page** (`/plays/today`):
- Shows today's plays only
- Default filter: "Active" (upcoming and live games)
- Filter by confidence, stat type, recommendation
- Shows game status and time until game

**History Page** (`/plays/history`):
- Shows past plays (excludes today)
- Grouped by date
- Adjustable date range (default: last 7 days)

**Stats Page** (`/stats`):
- Overall win rate and profit/loss
- Win rate by confidence level
- Win rate by stat type
- Days tracked and total plays

### 4. Collect Results (Next Day)

After games complete, collect actual results:

```bash
# Collect results for yesterday
python scripts/collect_results.py

# Or specify a date
python scripts/collect_results.py --date 2025-11-25

# Or go back N days
python scripts/collect_results.py --days-back 2
```

This:
- Fetches actual player stats from completed games
- Updates plays with actual results
- Marks plays as correct/incorrect
- Shows win rate for that date

## Understanding the System

### Recommendation Logic

The system **follows Vegas deviations**, not predictions:

- **Expected Value** = (50% × Season Avg) + (50% × Last 5 Games)
- **Deviation** = Line Value - Expected Value
- **Z-Score** = Deviation / Standard Deviation

**When line is significantly different from expected:**
- **OVER** recommendation: Line is LOW → Vegas expects player to exceed
- **UNDER** recommendation: Line is HIGH → Vegas expects player to underperform

### Confidence Levels

- **High**: |z-score| ≥ 1.0 (line is 1+ standard deviations off)
- **Medium**: 0.5 ≤ |z-score| < 1.0
- **NO PLAY**: |z-score| < 0.5 (line matches expectations)

### Game Status Filters

- **Active** (default): Upcoming and live games (not completed)
- **Upcoming**: Games that haven't started
- **Live**: Games in progress (started within last 3 hours, not marked complete)
- **All**: Everything including completed games

## Tracking Performance

### Win Rate Calculation

Win rate is calculated only for graded plays (those with actual results):

```
Win Rate = (Correct Plays / Total Graded Plays) × 100%
```

### Profit/Loss Calculation

Assumes $100 bet per play:

**Win:**
- Negative odds (e.g., -110): Win $100
- Positive odds (e.g., +150): Win $150

**Loss:**
- Always lose $100

**ROI:**
```
ROI = (Total Profit / Total Amount Wagered) × 100%
```

### Viewing Historical Performance

1. Go to http://localhost:5000/stats
2. View overall metrics
3. See breakdown by confidence level and stat type

## Tips

1. **Run collection daily** around 10 AM ET when lines are posted
2. **Collect results next day** after games complete (usually by midnight)
3. **Focus on High confidence plays** for better accuracy
4. **Track performance over time** to validate the strategy
5. **Adjust timezone** if you're not in Central Time

## Troubleshooting

### Plays not showing on front page

- Check timezone setting in `app.py`
- Verify plays were created "today" in your local time
- Try changing game status filter from "Active" to "All"

### No results after running collect_results.py

- Games must be marked as completed (happens automatically 4+ hours after game time)
- Date format must be YYYY-MM-DD
- NBA API rate limits may cause delays (script has built-in 0.6s delays)

### Different results in history vs stats

- History page uses local timezone for grouping
- Stats page shows cumulative data across all time
- Both should be consistent after timezone fixes
