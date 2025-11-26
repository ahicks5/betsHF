"""
Flask Web App for NBA Props Analyzer
Simple interface to view plays and results
"""
from flask import Flask, render_template, request
from database.db import get_session
from database.models import Play, PropLine, Player, Game, Team
from sqlalchemy import func, desc
from datetime import datetime, timedelta

app = Flask(__name__)


@app.route('/')
def index():
    """Home page - redirect to today's plays"""
    return today_plays()


@app.route('/plays/today')
def today_plays():
    """Show today's plays"""
    session = get_session()

    # Get today's plays
    today = datetime.utcnow().date()
    plays = session.query(Play).filter(
        func.date(Play.created_at) == today
    ).order_by(desc(func.abs(Play.z_score))).all()

    # Filter options
    confidence_filter = request.args.get('confidence', 'all')
    stat_filter = request.args.get('stat', 'all')
    recommendation_filter = request.args.get('recommendation', 'all')

    if confidence_filter != 'all':
        plays = [p for p in plays if p.confidence == confidence_filter]

    if stat_filter != 'all':
        plays = [p for p in plays if p.stat_type == stat_filter]

    if recommendation_filter != 'all':
        plays = [p for p in plays if p.recommendation == recommendation_filter]

    # Get unique values for filters
    all_stats = sorted(set(p.stat_type for p in plays)) if plays else []
    all_confidences = sorted(set(p.confidence for p in plays if p.confidence)) if plays else []
    all_recommendations = sorted(set(p.recommendation for p in plays)) if plays else []

    return render_template('today.html',
                         plays=plays,
                         date=today,
                         confidence_filter=confidence_filter,
                         stat_filter=stat_filter,
                         recommendation_filter=recommendation_filter,
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


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
