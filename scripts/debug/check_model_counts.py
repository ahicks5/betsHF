"""
Debug script to check play counts by model
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from database.db import get_session
from database.models import Play
from sqlalchemy import func
from datetime import datetime, timedelta
import pytz

session = get_session()

# Today's date range (UTC)
LOCAL_TZ = pytz.timezone('America/Chicago')
now = datetime.now(LOCAL_TZ)
today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
today_start_utc = today_start.astimezone(pytz.utc).replace(tzinfo=None)

print("=" * 60)
print("PLAY COUNTS BY MODEL")
print("=" * 60)

# Total plays by model
print("\n1. TOTAL PLAYS (all time):")
counts = session.query(
    Play.model_name,
    func.count(Play.id)
).group_by(Play.model_name).all()

for model, total in counts:
    print(f"   {model}: {total}")

# Today's plays by model
print("\n2. TODAY'S PLAYS (ungraded):")
ungraded = session.query(
    Play.model_name,
    func.count(Play.id)
).filter(
    Play.was_correct == None
).group_by(Play.model_name).all()

for model, count in ungraded:
    print(f"   {model}: {count}")

# Breakdown by recommendation type for today
print("\n3. TODAY'S BREAKDOWN BY TYPE:")
for model_name in ['pulsar_v1', 'sentinel_v1']:
    plays = session.query(Play).filter(
        Play.model_name == model_name,
        Play.was_correct == None
    ).all()

    overs = len([p for p in plays if p.recommendation == 'OVER'])
    unders = len([p for p in plays if p.recommendation == 'UNDER'])

    print(f"   {model_name}: {len(plays)} total ({overs} OVER, {unders} UNDER)")

print("\n" + "=" * 60)
session.close()
