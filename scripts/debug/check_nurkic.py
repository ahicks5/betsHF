"""
Debug script to check Nurkic plays specifically
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from database.db import get_session
from database.models import Play, PropLine, Game
from sqlalchemy import desc

session = get_session()

print("=" * 80)
print("ALL NURKIC PLAYS IN DATABASE")
print("=" * 80)

plays = session.query(Play).filter(
    Play.player_name.ilike('%nurki%')
).order_by(desc(Play.created_at)).all()

print(f"\nFound {len(plays)} Nurkic plays:\n")

for p in plays:
    print(f"ID: {p.id}")
    print(f"  Created:     {p.created_at}")
    print(f"  Model:       {p.model_name}")
    print(f"  Stat:        {p.stat_type}")
    print(f"  Line:        {p.line_value}")
    print(f"  Expected:    {p.expected_value}")
    print(f"  Actual:      {p.actual_result}")
    print(f"  Rec:         {p.recommendation}")
    print(f"  Was Correct: {p.was_correct}")
    print(f"  PropLine ID: {p.prop_line_id}")

    # Get the prop line and game info
    if p.prop_line_id:
        prop = session.query(PropLine).filter(PropLine.id == p.prop_line_id).first()
        if prop and prop.game_id:
            game = session.query(Game).filter(Game.id == prop.game_id).first()
            if game:
                print(f"  Game Date:   {game.game_date}")
                print(f"  Game ID:     {game.id}")
    print()

print("=" * 80)
session.close()
