"""
Check graded plays to debug win/loss count
"""
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.db import get_session, close_session
from database.models import Play

session = get_session()

# Get all plays with results (excluding NO PLAY)
graded_plays = [p for p in session.query(Play).all()
                if p.was_correct is not None and p.recommendation != 'NO PLAY']

print(f"Total graded plays: {len(graded_plays)}\n")

# Count by was_correct value
true_count = 0
false_count = 0
none_count = 0
other_count = 0

for play in graded_plays:
    if play.was_correct is True:
        true_count += 1
    elif play.was_correct is False:
        false_count += 1
    elif play.was_correct is None:
        none_count += 1
    else:
        other_count += 1
        print(f"Weird value: {play.was_correct} (type: {type(play.was_correct)})")

print(f"was_correct = True: {true_count}")
print(f"was_correct = False: {false_count}")
print(f"was_correct = None: {none_count}")
print(f"Other values: {other_count}")
print(f"\nTotal: {true_count + false_count + none_count + other_count}")

# Show some samples
print("\n=== Sample Graded Plays ===")
for play in graded_plays[:10]:
    result = "WIN" if play.was_correct else "LOSS"
    print(f"{play.player_name} {play.stat_type} {play.recommendation} {play.line_value}")
    print(f"  Actual: {play.actual_result}, was_correct: {play.was_correct} ({type(play.was_correct).__name__}), Result: {result}")

close_session()
