# Attribution Analysis - Implementation Plan

## Overview

**Attribution analysis** answers the critical question: "When a prop bet hits or misses, WHAT specific factor(s) caused it?"

Instead of just tracking win/loss, we want to understand **WHY** - enabling pattern recognition, risk assessment, and prediction refinement.

---

## The Problem We're Solving

### Current State
- We know: Player prop hit or missed
- We see: Final stat line vs Vegas line

### Desired State
- We understand: **Why** it hit or missed
- We identify: Specific contributing factors (minutes, efficiency, volume, etc.)
- We learn: Patterns that predict future outcomes
- We improve: Pre-game risk assessment and prediction accuracy

---

## Example Scenarios

### Scenario 1: Points UNDER
```
Player: LeBron James
Prop: Points OVER 25.5 @ -110
Result: 18 points (UNDER) ❌

Attribution Analysis:
├─ ❌ PRIMARY: Minutes (24 vs 32 avg) → -25% variance
├─ ⚠️  SECONDARY: FGA (12 vs 16 avg) → -25% variance
├─ ✅ Normal: FG% (48% vs 45% avg) → +3% variance
└─ Conclusion: "Under caused by reduced playing time & shot volume"

Context: Blowout loss, sat entire 4th quarter
```

### Scenario 2: 3-Pointers OVER
```
Player: Stephen Curry
Prop: 3PM OVER 4.5 @ -115
Result: 7 threes (OVER) ✅

Attribution Analysis:
├─ ✅ PRIMARY: 3P% (54% vs 43% avg) → +11% variance (hot shooting)
├─ ✅ SECONDARY: 3PA (13 vs 11 avg) → +18% variance
├─ ✅ Contributing: Minutes (36 vs 34 avg) → +6% variance
└─ Conclusion: "Over due to hot shooting + high volume"

Context: Close game, played full minutes
```

### Scenario 3: Rebounds UNDER
```
Player: Nikola Jokic
Prop: Rebounds OVER 11.5 @ -120
Result: 9 rebounds (UNDER) ❌

Attribution Analysis:
├─ ❌ PRIMARY: Team Pace (95 poss vs 102 avg) → -7% (slower game)
├─ ⚠️  SECONDARY: Minutes (30 vs 34 avg) → -12% variance
├─ ⚠️  Context: Opponent FG% (52% vs 46% avg) → Fewer rebound opportunities
└─ Conclusion: "Under due to slow pace + reduced minutes"
```

---

## Key Metrics to Track

### For Scoring Props (Points, 3PM, FTM)

| Metric | Description | Impact Level |
|--------|-------------|--------------|
| **Minutes** | Playing time vs season/recent avg | ⭐⭐⭐ Critical |
| **FGA / 3PA** | Shot volume vs average | ⭐⭐⭐ Critical |
| **FG% / 3P%** | Shooting efficiency vs average | ⭐⭐ High |
| **FTA** | Free throw attempts vs average | ⭐⭐ High |
| **Usage Rate** | % of team possessions used | ⭐ Medium |
| **Game Pace** | Total possessions (team + opponent) | ⭐ Medium |

### For Assists

| Metric | Impact |
|--------|--------|
| Minutes | ⭐⭐⭐ |
| Usage Rate | ⭐⭐⭐ |
| Team Pace | ⭐⭐ |
| Turnover Rate | ⭐ |

### For Rebounds

| Metric | Impact |
|--------|--------|
| Minutes | ⭐⭐⭐ |
| Team Pace | ⭐⭐⭐ |
| Opponent FG% | ⭐⭐ (more misses = more rebounds) |
| Team Rebound Rate | ⭐ |

---

## Data Requirements

### Box Score Data (NBA API)
```python
{
    "player_stats": {
        "MIN": 32,        # Minutes played
        "FGA": 15,        # Field goals attempted
        "FGM": 7,         # Field goals made
        "FG_PCT": 0.467,  # Field goal %
        "FG3A": 6,        # 3-pointers attempted
        "FG3M": 3,        # 3-pointers made
        "FG3_PCT": 0.500, # 3-point %
        "FTA": 4,         # Free throws attempted
        "FTM": 3,         # Free throws made
        "REB": 8,         # Total rebounds
        "AST": 5,         # Assists
        "PTS": 20         # Points
    },
    "team_stats": {
        "PACE": 98.5,     # Possessions per 48 min
        "USG_PCT": 28.3   # Player usage rate
    },
    "opponent_stats": {
        "FG_PCT": 0.456,  # Affects rebound opportunities
        "PACE": 102.1
    },
    "game_context": {
        "score_margin": -18,  # Blowout?
        "overtime": false,
        "back_to_back": true
    }
}
```

### Baseline Comparison Values
- **Season Average** - Full season stats
- **L5 Average** - Last 5 games (recent form)
- **L10 Average** - Last 10 games (trend)
- **Expected Minutes** - Projected playing time

---

## Value Propositions

### 1. Pattern Recognition
**Discover actionable insights:**
- "Player A hits OVER 75% when minutes > 32, but only 40% when < 28"
- "Player B always underperforms on back-to-backs (-15% efficiency)"
- "3PM props miss 60% of the time when 3PA < season average"

### 2. Risk Assessment
**Pre-game warnings:**
```
⚠️ RISK FACTORS DETECTED:
├─ Player on injury report (minutes uncertain)
├─ Historical pattern: -8 min on back-to-backs
└─ Recommendation: Reduce confidence by 20%
```

### 3. Prediction Refinement
**Feed insights back into model:**
- Weight predictions by expected minutes reliability
- Adjust for pace matchups
- Factor in recent efficiency trends
- Identify when Vegas line accounts for context we're missing

### 4. Portfolio Optimization
**Aggregate analysis:**
- "35% of our UNDERs are caused by low minutes"
- "High-efficiency players hitting overs at 68%"
- "Slow-pace games underperform expectations by 12%"

---

## Implementation Phases

## Phase 1: Data Collection & Display (MVP)

**Goal:** Collect box score data and display alongside results

### Tasks
1. Extend `collect_results.py` to fetch box scores via NBA API
2. Add columns to `Play` model:
   ```python
   actual_minutes = Column(Float)
   actual_fga = Column(Integer)
   actual_fg_pct = Column(Float)
   actual_3pa = Column(Integer)
   actual_3p_pct = Column(Float)
   season_avg_minutes = Column(Float)
   season_avg_fga = Column(Float)
   # etc...
   ```
3. Display on history page:
   ```
   Player: LeBron James - 18 PTS (Line: 25.5)
   Box Score: 24 MIN (avg: 32) | 12 FGA (avg: 16) | 48% FG (avg: 45%)
   ```

### Effort
- **Time:** 4-6 hours
- **Complexity:** Low
- **Value:** Medium (manual pattern recognition)

---

## Phase 2: Attribution Engine

**Goal:** Automated analysis identifying primary/secondary factors

### Logic
```python
def analyze_attribution(play, box_score, averages):
    factors = []

    # Calculate variances
    min_variance = (box_score.MIN - averages.MIN) / averages.MIN
    fga_variance = (box_score.FGA - averages.FGA) / averages.FGA
    fg_pct_variance = box_score.FG_PCT - averages.FG_PCT

    # Weight by impact (for points props)
    if abs(min_variance) > 0.15:  # >15% variance
        impact = abs(min_variance) * MINUTES_WEIGHT  # e.g., 0.4
        factors.append({
            'metric': 'Minutes',
            'variance': min_variance,
            'impact': impact,
            'severity': 'primary' if impact > 0.3 else 'secondary'
        })

    # Similar for FGA, FG%, etc.

    # Rank by impact
    factors.sort(key=lambda x: x['impact'], reverse=True)

    return {
        'primary_factor': factors[0] if factors else None,
        'contributing_factors': factors[1:3],
        'summary': generate_summary(factors, play.recommendation)
    }
```

### Display
```
Attribution Analysis:
├─ ❌ PRIMARY: Minutes (-8, 35% impact)
├─ ⚠️  SECONDARY: FGA (-4, 25% impact)
├─ ✅ Normal: FG% (+3%, 10% impact)
└─ Summary: "Under primarily caused by reduced playing time"
```

### Effort
- **Time:** 8-12 hours
- **Complexity:** Medium
- **Value:** High (automated insights)

---

## Phase 3: Aggregate Analytics & Risk Assessment

**Goal:** Surface patterns and provide pre-game warnings

### Features

#### Aggregate Attribution Dashboard
```
Attribution Breakdown (Last 30 Days):
├─ Unders caused by low minutes: 35% (21/60)
├─ Overs from high efficiency: 28% (17/60)
├─ Misses from low volume: 22% (13/60)
└─ Other factors: 15% (9/60)

Best Predictors of Success:
1. Minutes > 90% of average: 68% win rate (51 plays)
2. FG% regression to mean: 62% win rate (38 plays)
3. High usage + normal pace: 71% win rate (24 plays)
```

#### Pre-Game Risk Assessment
```python
def assess_pregame_risk(player, prop_type):
    risks = []

    # Check injury report
    if player.is_questionable():
        risks.append({
            'type': 'minutes_uncertainty',
            'severity': 'high',
            'message': 'Player on injury report - minutes uncertain'
        })

    # Check back-to-back
    if is_back_to_back(player, today):
        historical_impact = calculate_b2b_impact(player)
        risks.append({
            'type': 'back_to_back',
            'severity': 'medium',
            'message': f'B2B game, historical avg: {historical_impact} min'
        })

    # Check pace matchup
    opponent_pace = get_opponent_pace(player.next_game)
    if opponent_pace < player.team.avg_pace * 0.9:
        risks.append({
            'type': 'slow_pace',
            'severity': 'low',
            'message': 'Opponent plays slow pace (fewer possessions)'
        })

    return risks
```

### Display on Today's Plays
```
⚠️ RISK FACTORS:
├─ [HIGH] Minutes uncertainty - player questionable (ankle)
├─ [MED] Back-to-back game (historical: -6 min, -15% FGA)
└─ Adjusted Confidence: High → Medium
```

### Effort
- **Time:** 12-16 hours
- **Complexity:** High
- **Value:** Very High (proactive risk management)

---

## Phase 4: Machine Learning Integration

**Goal:** Predict which factors will vary before the game

### Approach
- Train model on historical attribution data
- Features: Player, opponent, home/away, rest days, injury status, recent trends
- Prediction: Expected minutes, usage, efficiency variance
- Output: Confidence adjustment before placing bet

### Example
```
Prediction for LeBron James - PTS O/U 25.5:
├─ Expected Minutes: 31 (±3)  [90% confidence]
├─ Expected FGA: 15 (±2)      [85% confidence]
├─ Expected FG%: 47% (±5%)    [70% confidence]
└─ Model Adjustment: -10% confidence (high minute variance risk)
```

### Effort
- **Time:** 20-30 hours
- **Complexity:** Very High
- **Value:** Exceptional (predictive edge)

---

## Database Schema Extensions

### New Tables

```sql
-- Store box score data
CREATE TABLE player_box_scores (
    id SERIAL PRIMARY KEY,
    play_id INTEGER REFERENCES plays(id),
    game_id INTEGER REFERENCES games(id),
    player_id INTEGER REFERENCES players(id),

    -- Counting stats
    minutes FLOAT,
    fga INTEGER,
    fgm INTEGER,
    fg_pct FLOAT,
    fg3a INTEGER,
    fg3m INTEGER,
    fg3_pct FLOAT,
    fta INTEGER,
    ftm INTEGER,
    rebounds INTEGER,
    assists INTEGER,
    points INTEGER,

    -- Advanced stats
    usage_rate FLOAT,
    pace FLOAT,

    -- Comparison baselines
    season_avg_minutes FLOAT,
    season_avg_fga FLOAT,
    season_avg_fg_pct FLOAT,
    l5_avg_minutes FLOAT,
    l5_avg_fga FLOAT,

    created_at TIMESTAMP DEFAULT NOW()
);

-- Store attribution analysis
CREATE TABLE play_attributions (
    id SERIAL PRIMARY KEY,
    play_id INTEGER REFERENCES plays(id),

    primary_factor VARCHAR(50),      -- 'minutes', 'fga', 'efficiency', etc.
    primary_variance FLOAT,          -- -0.25 = 25% below average
    primary_impact FLOAT,            -- 0.35 = 35% impact score

    secondary_factors JSONB,         -- [{factor, variance, impact}, ...]

    summary TEXT,                    -- Human-readable explanation

    created_at TIMESTAMP DEFAULT NOW()
);

-- Store risk assessments
CREATE TABLE pregame_risk_assessments (
    id SERIAL PRIMARY KEY,
    player_id INTEGER REFERENCES players(id),
    game_id INTEGER REFERENCES games(id),

    risk_factors JSONB,              -- [{type, severity, message}, ...]
    confidence_adjustment FLOAT,     -- -0.20 = reduce confidence by 20%

    created_at TIMESTAMP DEFAULT NOW()
);
```

---

## API Endpoints Needed

### NBA API - Box Scores
```python
from nba_api.stats.endpoints import boxscoretraditionalv2

def get_box_score(game_id, player_id):
    boxscore = boxscoretraditionalv2.BoxScoreTraditionalV2(game_id=game_id)
    stats = boxscore.get_data_frames()[0]  # Player stats
    player_stats = stats[stats['PLAYER_ID'] == player_id].iloc[0]

    return {
        'minutes': player_stats['MIN'],
        'fga': player_stats['FGA'],
        'fgm': player_stats['FGM'],
        'fg_pct': player_stats['FG_PCT'],
        # ... etc
    }
```

### NBA API - Season Averages
```python
from nba_api.stats.endpoints import playergamelog

def get_season_averages(player_id, season='2024-25'):
    gamelog = playergamelog.PlayerGameLog(
        player_id=player_id,
        season=season
    )
    df = gamelog.get_data_frames()[0]

    return {
        'avg_minutes': df['MIN'].mean(),
        'avg_fga': df['FGA'].mean(),
        'avg_fg_pct': df['FG_PCT'].mean(),
        # ... etc
    }
```

---

## Success Metrics

### Phase 1
- ✅ Box score data collected for 100% of graded plays
- ✅ Data displayed on history page
- ✅ Manual insights documented

### Phase 2
- ✅ Attribution analysis runs for all graded plays
- ✅ Primary factor identified with >80% confidence
- ✅ Summary makes sense to human review

### Phase 3
- ✅ 5+ actionable patterns discovered
- ✅ Risk assessments reduce losses by 10%+
- ✅ Confidence adjustments improve ROI

### Phase 4
- ✅ ML model accuracy >70% on minute prediction
- ✅ Variance predictions reduce unexpected outcomes by 15%
- ✅ Overall win rate improves by 3-5%

---

## Example Insights (What We Might Learn)

### Player-Specific Patterns
```
LeBron James:
├─ Back-to-back games: -8 min avg, -15% FGA (avoid unders)
├─ vs Top-10 defense: -2.5 PPG avg (avoid overs)
└─ Home games: +3 min avg (prefer overs)

Stephen Curry:
├─ High 3PA (>10): 65% over rate on 3PM
├─ Low 3PA (<8): 32% over rate on 3PM
└─ Conclusion: Volume is primary predictor, not efficiency
```

### Situational Patterns
```
Back-to-Back Games:
├─ Players >30 years old: -12% minutes avg
├─ Players <25 years old: -3% minutes avg
└─ Strategy: Reduce confidence on aging vets

Slow Pace Matchups (<95 poss/game):
├─ Assist props: 42% hit rate (below expectation)
├─ Rebound props: 38% hit rate
└─ Strategy: Avoid volume-dependent props
```

### Vegas Tells
```
When Vegas Line is 2+ std devs from our EV:
├─ Vegas knows minutes will be limited: 68% accuracy
├─ Vegas knows matchup advantage: 61% accuracy
└─ Strategy: Respect sharp lines, investigate context
```

---

## Technical Challenges

### 1. Data Availability Timing
- **Problem:** Box scores available 30-60 min after game ends
- **Solution:** Run attribution analysis in batch, not real-time

### 2. Baseline Calculation
- **Problem:** What's the "right" average? Season? L5? L10? vs opponent?
- **Solution:** Test multiple baselines, see which predicts best

### 3. Correlation vs Causation
- **Problem:** Low minutes might be RESULT of blowout, not CAUSE of under
- **Solution:** Add game context (score margin, foul trouble, injury)

### 4. Sample Size
- **Problem:** Need enough data to establish patterns
- **Solution:** Start simple, expand as data grows

### 5. API Rate Limits
- **Problem:** NBA API has rate limits (especially for box scores)
- **Solution:** Cache data, batch requests, respect limits

---

## Future Enhancements

### Advanced Attribution
- **Defensive matchup impact** - Track opponent's defensive rating
- **Lineup combinations** - Performance with specific teammates
- **Referee tendencies** - Foul rates affecting FTA, minutes

### Predictive Features
- **Injury probability model** - Predict load management / rest games
- **Minutes projection** - ML model for expected playing time
- **Efficiency regression** - Predict bounce-back games

### Portfolio Optimization
- **Kelly Criterion** - Optimal bet sizing based on confidence
- **Hedge recommendations** - When to hedge based on live attribution
- **Parlay builder** - Find correlated attributions

---

## Conclusion

Attribution analysis transforms betting from "did it hit?" to "why did it hit?" - unlocking:

- **Deeper insights** into what actually drives outcomes
- **Risk mitigation** through pre-game assessment
- **Prediction refinement** by feeding learnings back into model
- **Professional edge** used by sharp bettors

Start with Phase 1 (data collection), learn patterns manually, then automate and scale.

This is the difference between recreational and professional sports analytics.
