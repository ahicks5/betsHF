"""
Verify profit/loss calculations are correct
Shows example calculations with different odds scenarios
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.db import get_session
from database.models import Play

def calculate_profit(odds, bet_amount=10, won=True):
    """Calculate profit/loss for American odds"""
    if not won:
        return -bet_amount

    if odds < 0:
        # Negative odds: risk |odds| to win $100
        # Profit = bet_amount * (100 / |odds|)
        profit = bet_amount * (100 / abs(odds))
    else:
        # Positive odds: risk $100 to win odds
        # Profit = bet_amount * (odds / 100)
        profit = bet_amount * (odds / 100)

    return profit


print("\n" + "="*80)
print("PROFIT/LOSS CALCULATION VERIFICATION")
print("="*80)
print(f"\nBet Size: $10 per play\n")

print("AMERICAN ODDS EXPLAINED:")
print("-" * 80)
print("Negative odds (e.g., -110): You risk MORE to win $100")
print("  Example: -110 means risk $110 to win $100")
print("  On a $10 bet: profit = $10 * (100/110) = $9.09")
print()
print("Positive odds (e.g., +200): You risk $100 to win THAT amount")
print("  Example: +200 means risk $100 to win $200")
print("  On a $10 bet: profit = $10 * (200/100) = $20.00")
print()

print("EXAMPLE CALCULATIONS:")
print("-" * 80)

examples = [
    (-110, "Favorite (slight)"),
    (-150, "Favorite (moderate)"),
    (-200, "Heavy favorite"),
    (+100, "Even odds"),
    (+150, "Underdog (moderate)"),
    (+200, "Underdog (good value)"),
    (+300, "Big underdog"),
]

for odds, description in examples:
    win_profit = calculate_profit(odds, 10, won=True)
    loss_amount = calculate_profit(odds, 10, won=False)

    print(f"\nOdds: {odds:+4d} ({description})")
    print(f"  If WIN:  +${win_profit:.2f} profit")
    print(f"  If LOSS: ${loss_amount:.2f}")
    print(f"  Risk/Reward Ratio: ${abs(loss_amount):.2f} to win ${win_profit:.2f}")


print("\n" + "="*80)
print("VERIFY AGAINST ACTUAL GRADED PLAYS")
print("="*80)

session = get_session()

# Get some graded plays
graded_plays = session.query(Play).filter(
    Play.was_correct != None,
    Play.recommendation != 'NO PLAY'
).limit(10).all()

if graded_plays:
    print(f"\nShowing first 10 graded plays:\n")

    for play in graded_plays:
        # Get the odds for the recommendation
        if play.recommendation == 'OVER':
            odds = play.over_odds
        elif play.recommendation == 'UNDER':
            odds = play.under_odds
        else:
            continue

        if odds is None:
            continue

        # Calculate profit
        if play.was_correct:
            if odds < 0:
                profit = 10 * (100 / abs(odds))
            else:
                profit = 10 * (odds / 100)
            result_str = f"+${profit:.2f}"
            outcome = "WIN"
        else:
            result_str = f"-$10.00"
            outcome = "LOSS"

        print(f"{play.player_name:20s} {play.stat_type:6s} {play.recommendation:5s} {odds:+5d} -> {outcome:4s} {result_str:>9s}")

else:
    print("\nNo graded plays found yet!")

print("\n" + "="*80)
print("KEY INSIGHTS:")
print("-" * 80)
print("• Big underdogs (+200, +300) can yield BIG profits when they hit!")
print("• A single +200 win (+$20) offsets TWO losses (-$10 each)")
print("• Even at 40% win rate, you can be profitable with good odds")
print("• This is why Vegas gives good odds on 'sharp' plays - they know")
print("  the public will bet the other side")
print("="*80 + "\n")
