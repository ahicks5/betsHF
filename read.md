nba-props-simple/
├── database/
│   ├── models.py          # Just: Team, Player, Game, PropLine
│   └── db.py              # SQLite connection
├── services/
│   ├── nba_api.py         # Fetch player stats
│   └── odds_api.py        # Fetch prop lines
├── analyzer.py            # Simple stats analyzer (season avg, L5, opponent)
├── collect_today.py       # Fetch today's data
├── find_plays.py          # Analyze and show picks
├── .env                   # API keys
└── props.db              # Single database