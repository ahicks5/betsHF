# NBA Props Analyzer - Hedge Fund for Sports Betting

A simple, stats-based NBA player props analyzer that identifies betting opportunities by detecting deviations between Vegas lines and expected values.

## Strategy

The analyzer uses a straightforward approach:

1. **Player's Season Average** - What the player typically does all season
2. **Player's Last 5 Games** - Recent form and trends

### Weighted Formula

```
Expected Value = (50% × Season Avg) + (50% × L5 Avg)
```

**Note:** Opponent defense component was removed because NBA API only provides team-level defensive stats (not player-level). Mixing team totals with individual player stats created inaccurate results.

### Theory

**"Whatever current lines are MOST deviant from the normal = Vegas knows something"**

We don't try to predict outcomes. Instead, we:
- Calculate what we expect based on simple stats
- Compare to the Vegas line
- **Follow the deviation** - if the line is way off, there's likely information we don't have
- The bigger the deviation (z-score), the stronger the signal

## Project Structure

```
betsHF/
├── database/
│   ├── models.py          # Team, Player, Game, PropLine, Play models
│   └── db.py              # SQLite connection (props.db)
├── services/
│   ├── nba_api.py         # NBA API client for stats
│   └── odds_api.py        # Odds API client for props
├── scripts/
│   ├── collect_today.py   # Data collection script
│   ├── find_plays.py      # Play finder and analyzer (saves to DB)
│   └── update_player_teams.py  # Team assignment utility
├── templates/             # Flask HTML templates
│   ├── base.html          # Base template with navigation
│   ├── today.html         # Today's plays view
│   ├── history.html       # Historical plays view
│   ├── play_detail.html   # Detailed play analysis
│   └── stats.html         # Overall statistics
├── app.py                 # Flask web application
├── cached_analyzer.py     # Core stats analyzer with caching
├── requirements.txt       # Python dependencies
├── .env                   # API keys (not committed)
├── DAILY_RUN.md          # Daily workflow and automation guide
└── README.md              # This file
```

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

Or install individually:
```bash
pip install nba_api requests python-dotenv sqlalchemy pandas numpy tabulate flask
```

### 2. Configure API Keys

Copy `.env.example` to `.env` and add your Odds API key:

```bash
cp .env.example .env
```

Edit `.env`:
```
ODDS_API_KEY=your_key_here
```

Get your free API key at: https://the-odds-api.com/

### 3. Initialize Database

```bash
python database/db.py
```

This creates the `props.db` SQLite database with all necessary tables.

## Usage

### Quick Start - Daily Workflow

See [DAILY_RUN.md](DAILY_RUN.md) for detailed daily run instructions and automation setup.

**Step 1: Collect Today's Data**

```bash
python scripts/collect_today.py
```

This will:
- Load all NBA teams (30 teams)
- Load all active players (~500 players)
- Fetch today's NBA games from Odds API
- Fetch all available player props
- Store everything in the database

**Step 2: Find Plays**

```bash
python scripts/find_plays.py
```

This will:
- Analyze all collected props
- Calculate expected values using our formula
- Compute z-scores (deviation strength)
- Show recommendations sorted by strongest signal
- **Save all plays to database with timestamps**
- Export detailed CSV with calculation steps for diagnostics

**Step 3: View in Browser (Optional)**

```bash
python app.py
```

Then open `http://localhost:5000` to:
- View today's plays in a clean web interface
- Filter by confidence, stat type, or recommendation
- See detailed analysis for each play
- Browse historical plays
- View overall statistics

### Sample Output

```
=== Found 42 Plays ===

┌─────────────────┬──────┬────────┬──────────┬───────────┬─────────┬──────────────┬────────────┬──────┐
│ Player          │ Stat │ Line   │ Expected │ Deviation │ Z-Score │ Play         │ Confidence │ Odds │
├─────────────────┼──────┼────────┼──────────┼───────────┼─────────┼──────────────┼────────────┼──────┤
│ LeBron James    │ PTS  │ 25.5   │ 28.3     │ -2.8      │ -1.2    │ UNDER        │ High       │ -110 │
│ Stephen Curry   │ FG3M │ 4.5    │ 5.8      │ -1.3      │ -0.9    │ UNDER        │ Medium     │ -105 │
└─────────────────┴──────┴────────┴──────────┴───────────┴─────────┴──────────────┴────────────┴──────┘

=== Top 5 Plays (Details) ===

1. LeBron James - PTS UNDER 25.5
   Expected: 28.3 (Season: 27.5, L5: 30.2)
   Deviation: -2.8 (Z-Score: -1.2)
   Confidence: High
   Bookmaker: draftkings
```

## Understanding the Output

### Z-Score Thresholds

- **< 0.5**: No play - line is close to expected
- **0.5 - 1.0**: Medium confidence play
- **> 1.0**: High confidence play (strong deviation)

### Recommendation Logic

- **NO PLAY**: Line matches expected value (z-score < 0.5)
- **OVER**: Line is significantly below expected (follow Vegas up)
- **UNDER**: Line is significantly above expected (follow Vegas down)

## Customization

### Adjust Weighted Formula

Edit `cached_analyzer.py`, line 70:

```python
# Current: 50/50
expected = (season_avg * 0.5) + (recent_avg * 0.5)

# More weight on season average: 60/40
expected = (season_avg * 0.6) + (recent_avg * 0.4)

# More weight on recent form: 40/60
expected = (season_avg * 0.4) + (recent_avg * 0.6)
```

### Change Recent Games Window

Edit `cached_analyzer.py`, line 24:

```python
# Current: Last 5 games
recent_stats = self.nba_client.get_player_recent_stats(player_id, 5)

# Last 10 games instead
recent_stats = self.nba_client.get_player_recent_stats(player_id, 10)
```

### Adjust Z-Score Thresholds

Edit `cached_analyzer.py`, lines 108-119:

```python
# Current thresholds
if abs_z < 0.5:
    recommendation = "NO PLAY"
    confidence = "N/A"
elif abs_z < 1.0:
    recommendation = "UNDER" if deviation < 0 else "OVER"
    confidence = "Medium"
else:
    recommendation = "UNDER" if deviation < 0 else "OVER"
    confidence = "High"

# More conservative (only strong signals)
if abs_z < 1.0:
    recommendation = "NO PLAY"
    confidence = "N/A"
else:
    recommendation = "UNDER" if deviation < 0 else "OVER"
    confidence = "High"
```

## Database Schema

### Tables

- **teams** - NBA teams (30 teams)
- **players** - Active NBA players (~500)
- **games** - Today's games
- **prop_lines** - Player prop lines from sportsbooks
- **plays** - Analyzed plays with recommendations, z-scores, and all analysis data (timestamped for tracking)

### Querying the Database

```python
from database.db import get_session
from database.models import PropLine, Player, Play

session = get_session()

# Get all latest props
props = session.query(PropLine).filter_by(is_latest=True).all()

# Find a specific player
player = session.query(Player).filter_by(full_name="LeBron James").first()

# Get today's high-confidence plays
from sqlalchemy import func
from datetime import datetime
today = datetime.utcnow().date()
plays = session.query(Play).filter(
    func.date(Play.created_at) == today,
    Play.confidence == 'High'
).all()
```

## Web Interface

The Flask web app provides a user-friendly interface to view and analyze plays:

- **Today's Plays**: View all plays for today with filtering options
- **History**: Browse historical plays by date range
- **Play Details**: Deep dive into individual play analysis with formulas and interpretation
- **Statistics**: Overall metrics and breakdowns by stat type and recommendation

Start the web server:

```bash
python app.py
```

Access at `http://localhost:5000`

## API Rate Limits

### NBA API
- Rate limit: ~1 request per 0.6 seconds
- Automatically handled in `services/nba_api.py`

### The Odds API
- Free tier: 500 requests/month
- Each game = 1 request for props
- Typical day: ~10-15 games = 10-15 requests

## Troubleshooting

### "No props found"
- Check if there are NBA games today
- Verify your ODDS_API_KEY in `.env`
- Check API quota at https://the-odds-api.com/account

### "Player not found"
- Some player names don't match exactly between APIs
- The script tries partial matching
- Check database: `SELECT full_name FROM players WHERE full_name LIKE '%Player%'`

### Database errors
- Delete `props.db` and run `python database/db.py` to reinitialize

## Philosophy

This is **not** a machine learning system. It's intentionally simple:

- No complex models
- No predictions
- Just basic stats and deviation detection
- Follow Vegas when they move the line

The goal is to identify when Vegas knows something we don't, and follow their lead.

## License

MIT

## Disclaimer

This tool is for educational purposes. Sports betting involves risk. Bet responsibly.
