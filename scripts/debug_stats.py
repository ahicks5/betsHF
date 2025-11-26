"""
Debug stats calculation - runs exact same logic as stats page
"""
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.db import get_session, close_session
from database.models import Play

session = get_session()

# EXACT same logic as stats route
all_plays = session.query(Play).all()

print(f"Total plays in database: {len(all_plays)}")

# Exclude NO PLAY from total count
actual_plays = [p for p in all_plays if p.recommendation != 'NO PLAY']
total_plays = len(actual_plays)

print(f"Actual plays (excluding NO PLAY): {total_plays}")

# Performance metrics - only plays with results (excluding NO PLAY)
graded_plays = [p for p in all_plays if p.was_correct is not None and p.recommendation != 'NO PLAY']
total_graded = len(graded_plays)

print(f"\nGraded plays: {total_graded}")

# Count wins and losses
wins = len([p for p in graded_plays if p.was_correct == True])
losses = len([p for p in graded_plays if p.was_correct == False])

print(f"Wins (was_correct == True): {wins}")
print(f"Losses (was_correct == False): {losses}")
print(f"Total (wins + losses): {wins + losses}")

# Check if there are any that don't match
other = [p for p in graded_plays if p.was_correct != True and p.was_correct != False]
print(f"\nOther (not True and not False): {len(other)}")

if other:
    print("These plays have weird values:")
    for p in other:
        print(f"  {p.player_name} - was_correct: {p.was_correct} (type: {type(p.was_correct)})")

# Show win rate calculation
win_rate = (wins / total_graded * 100) if total_graded > 0 else 0
print(f"\nWin Rate: {win_rate:.1f}%")
print(f"Display: {wins}W - {losses}L")

close_session()
