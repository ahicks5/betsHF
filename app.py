"""
Flask Web App for NBA Props Analyzer
Simple interface to view plays and results
"""
from flask import Flask, render_template, request
from database.db import get_session
from database.models import Play, PropLine, Player, Game, Team
from sqlalchemy import func, desc
from datetime import datetime, timedelta
import pytz

app = Flask(__name__)

# Timezone configuration - change this to your local timezone
LOCAL_TIMEZONE = pytz.timezone('America/Chicago')  # Central Time


def utc_to_local(utc_dt):
    """Convert UTC datetime to local timezone"""
    if utc_dt is None:
        return None
    if utc_dt.tzinfo is None:
        # Assume UTC if no timezone info
        utc_dt = pytz.utc.localize(utc_dt)
    return utc_dt.astimezone(LOCAL_TIMEZONE)


def get_local_now():
    """Get current time in local timezone"""
    return datetime.now(LOCAL_TIMEZONE)


@app.route('/')
def index():
    """Home page - redirect to today's plays"""
    return today_plays()


@app.route('/plays/today')
def today_plays():
    """Show today's plays"""
    session = get_session()

    # Get today's plays with game info - join with PropLine and Game
    today = datetime.utcnow().date()
    plays_query = session.query(Play, Game).join(
        PropLine, Play.prop_line_id == PropLine.id
    ).join(
        Game, PropLine.game_id == Game.id
    ).filter(
        func.date(Play.created_at) == today
    ).order_by(desc(func.abs(Play.z_score)))

    # Get all results
    results = plays_query.all()

    # Create list of (play, game) tuples
    plays_with_games = [(play, game) for play, game in results]

    # Filter options
    confidence_filter = request.args.get('confidence', 'all')
    stat_filter = request.args.get('stat', 'all')
    recommendation_filter = request.args.get('recommendation', 'all')
    game_status_filter = request.args.get('game_status', 'all')

    if confidence_filter != 'all':
        plays_with_games = [(p, g) for p, g in plays_with_games if p.confidence == confidence_filter]

    if stat_filter != 'all':
        plays_with_games = [(p, g) for p, g in plays_with_games if p.stat_type == stat_filter]

    if recommendation_filter != 'all':
        plays_with_games = [(p, g) for p, g in plays_with_games if p.recommendation == recommendation_filter]

    # Filter by game status
    now = get_local_now()
    if game_status_filter == 'upcoming':
        plays_with_games = [(p, g) for p, g in plays_with_games if utc_to_local(g.game_date) > now]
    elif game_status_filter == 'live':
        # Games started in last 3 hours and not completed
        three_hours_ago = now - timedelta(hours=3)
        plays_with_games = [(p, g) for p, g in plays_with_games
                          if three_hours_ago <= utc_to_local(g.game_date) <= now and not g.is_completed]
    elif game_status_filter == 'completed':
        plays_with_games = [(p, g) for p, g in plays_with_games if g.is_completed]

    # Get unique values for filters (from original plays)
    all_plays = [p for p, g in results]
    all_stats = sorted(set(p.stat_type for p in all_plays)) if all_plays else []
    all_confidences = sorted(set(p.confidence for p in all_plays if p.confidence)) if all_plays else []
    all_recommendations = sorted(set(p.recommendation for p in all_plays)) if all_plays else []

    return render_template('today.html',
                         plays_with_games=plays_with_games,
                         date=today,
                         now=now,
                         confidence_filter=confidence_filter,
                         stat_filter=stat_filter,
                         recommendation_filter=recommendation_filter,
                         game_status_filter=game_status_filter,
                         all_stats=all_stats,
                         all_confidences=all_confidences,
                         all_recommendations=all_recommendations)


@app.route('/plays/history')
def plays_history():
    """Show historical plays"""
    session = get_session()

    # Get date range
    days = int(request.args.get('days', 7))
    start_date = datetime.utcnow().date() - timedelta(days=days)

    plays = session.query(Play).filter(
        func.date(Play.created_at) >= start_date
    ).order_by(desc(Play.created_at), desc(func.abs(Play.z_score))).all()

    # Group by date
    plays_by_date = {}
    for play in plays:
        date = play.created_at.date()
        if date not in plays_by_date:
            plays_by_date[date] = []
        plays_by_date[date].append(play)

    return render_template('history.html',
                         plays_by_date=plays_by_date,
                         days=days)


@app.route('/plays/<int:play_id>')
def play_detail(play_id):
    """Show detailed analysis for a single play"""
    session = get_session()
    play = session.query(Play).filter_by(id=play_id).first()

    if not play:
        return "Play not found", 404

    # Get the prop line details
    prop_line = session.query(PropLine).filter_by(id=play.prop_line_id).first()

    # Get game details if prop line exists
    game = None
    if prop_line:
        game = session.query(Game).filter_by(id=prop_line.game_id).first()

    return render_template('play_detail.html',
                         play=play,
                         prop_line=prop_line,
                         game=game)


@app.route('/stats')
def stats():
    """Show overall statistics"""
    session = get_session()

    # Get all plays
    all_plays = session.query(Play).all()

    # Calculate stats
    total_plays = len(all_plays)
    high_confidence = len([p for p in all_plays if p.confidence == 'High'])
    medium_confidence = len([p for p in all_plays if p.confidence == 'Medium'])

    # Group by stat type
    stat_counts = {}
    for play in all_plays:
        stat_counts[play.stat_type] = stat_counts.get(play.stat_type, 0) + 1

    # Group by recommendation
    rec_counts = {}
    for play in all_plays:
        rec_counts[play.recommendation] = rec_counts.get(play.recommendation, 0) + 1

    # Average z-scores
    avg_z_score = sum(abs(p.z_score) for p in all_plays) / total_plays if total_plays > 0 else 0

    # Days tracked
    if all_plays:
        dates = [p.created_at.date() for p in all_plays]
        days_tracked = len(set(dates))
        first_date = min(dates)
        last_date = max(dates)
    else:
        days_tracked = 0
        first_date = None
        last_date = None

    return render_template('stats.html',
                         total_plays=total_plays,
                         high_confidence=high_confidence,
                         medium_confidence=medium_confidence,
                         stat_counts=stat_counts,
                         rec_counts=rec_counts,
                         avg_z_score=avg_z_score,
                         days_tracked=days_tracked,
                         first_date=first_date,
                         last_date=last_date)


def get_game_status(game, now=None):
    """Get game status: upcoming, live, or completed"""
    if now is None:
        now = get_local_now()

    # Convert game date to local time for comparison
    game_local = utc_to_local(game.game_date)

    if game.is_completed:
        return 'completed'

    if game_local > now:
        return 'upcoming'

    # Game has started but not completed (within last 3 hours)
    three_hours_ago = now - timedelta(hours=3)
    if three_hours_ago <= game_local <= now:
        return 'live'

    # Game started more than 3 hours ago but not marked complete
    return 'completed'


@app.template_filter('format_odds')
def format_odds(odds):
    """Format American odds for display"""
    if odds is None:
        return '-'
    if odds > 0:
        return f'+{odds}'
    return str(odds)


@app.template_filter('format_float')
def format_float(value, decimals=2):
    """Format float to specified decimals"""
    if value is None:
        return '-'
    return f"{value:.{decimals}f}"


@app.template_filter('game_status')
def game_status_filter(game):
    """Get game status for template"""
    return get_game_status(game)


@app.template_filter('time_until')
def time_until(game_time):
    """Get human-readable time until game"""
    if game_time is None:
        return '-'

    # Convert to local time
    game_local = utc_to_local(game_time)
    now = get_local_now()

    if game_local < now:
        return 'Started'

    diff = game_local - now
    hours = diff.total_seconds() / 3600

    if hours < 1:
        minutes = int(diff.total_seconds() / 60)
        return f'{minutes}m'
    elif hours < 24:
        return f'{int(hours)}h'
    else:
        days = int(hours / 24)
        return f'{days}d'


@app.template_filter('to_local')
def to_local_filter(utc_time):
    """Convert UTC time to local timezone"""
    return utc_to_local(utc_time)


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
