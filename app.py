"""
Flask Web App for NBA Props Analyzer
Simple interface to view plays and results
"""
from flask import Flask, render_template, request
from database.db import get_session
from database.models import Play, PropLine, Player, Game, Team
from sqlalchemy import func, desc
from sqlalchemy.orm import aliased
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

    # Get today's plays with game info - join with PropLine, Game, and Teams
    # Use aliases for Team table since we join it twice (away and home)
    away_team = aliased(Team)
    home_team = aliased(Team)

    # Get all recent plays (last 3 days) - we'll filter by game status below
    now_local = get_local_now()
    today_local = now_local.date()
    three_days_ago = (now_local - timedelta(days=3)).astimezone(pytz.utc).replace(tzinfo=None)

    plays_query = session.query(Play, Game, away_team, home_team).join(
        PropLine, Play.prop_line_id == PropLine.id
    ).join(
        Game, PropLine.game_id == Game.id
    ).join(
        away_team, Game.away_team_id == away_team.id
    ).join(
        home_team, Game.home_team_id == home_team.id
    ).filter(
        Play.created_at >= three_days_ago  # Get recent plays
    ).order_by(desc(func.abs(Play.z_score)))

    # Get all results - (play, game, away_team, home_team)
    results = plays_query.all()

    # Create list of (play, game, matchup) tuples
    plays_with_games = [(play, game, f"{away.abbreviation} @ {home.abbreviation}")
                        for play, game, away, home in results]

    # Filter options
    confidence_filter = request.args.get('confidence', 'all')
    stat_filter = request.args.get('stat', 'all')
    recommendation_filter = request.args.get('recommendation', 'all')
    game_status_filter = request.args.get('game_status', 'active')  # Default to 'active' instead of 'all'

    if confidence_filter != 'all':
        plays_with_games = [(p, g, m) for p, g, m in plays_with_games if p.confidence == confidence_filter]

    if stat_filter != 'all':
        plays_with_games = [(p, g, m) for p, g, m in plays_with_games if p.stat_type == stat_filter]

    if recommendation_filter != 'all':
        plays_with_games = [(p, g, m) for p, g, m in plays_with_games if p.recommendation == recommendation_filter]

    # Filter by game status
    now = get_local_now()
    four_hours_ago = now - timedelta(hours=4)

    if game_status_filter == 'active':
        # Default: show only upcoming and live games (not completed or old)
        # Exclude completed games OR games that started more than 4 hours ago
        plays_with_games = [(p, g, m) for p, g, m in plays_with_games
                          if not g.is_completed and utc_to_local(g.game_date) >= four_hours_ago]
    elif game_status_filter == 'upcoming':
        plays_with_games = [(p, g, m) for p, g, m in plays_with_games
                          if not g.is_completed and utc_to_local(g.game_date) > now]
    elif game_status_filter == 'live':
        # Games started in last 4 hours and not completed
        plays_with_games = [(p, g, m) for p, g, m in plays_with_games
                          if not g.is_completed and four_hours_ago <= utc_to_local(g.game_date) <= now]
    # 'all' - no filtering

    # Get unique values for filters (from original plays)
    all_plays = [p for p, g, away, home in results]
    all_stats = sorted(set(p.stat_type for p in all_plays)) if all_plays else []
    all_confidences = sorted(set(p.confidence for p in all_plays if p.confidence)) if all_plays else []
    all_recommendations = sorted(set(p.recommendation for p in all_plays)) if all_plays else []

    return render_template('today.html',
                         plays_with_games=plays_with_games,
                         date=today_local,
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
    """Show completed games with results"""
    session = get_session()

    # Get date range
    days = int(request.args.get('days', 7))
    now_local = get_local_now()
    cutoff_date = now_local - timedelta(days=days)
    cutoff_utc = cutoff_date.astimezone(pytz.utc).replace(tzinfo=None)

    # Get plays where the game is completed OR started more than 4 hours ago
    four_hours_ago = (now_local - timedelta(hours=4)).astimezone(pytz.utc).replace(tzinfo=None)

    # Join with PropLine and Game to check game status
    from database.models import PropLine

    plays = session.query(Play).join(
        PropLine, Play.prop_line_id == PropLine.id
    ).join(
        Game, PropLine.game_id == Game.id
    ).filter(
        Play.created_at >= cutoff_utc,  # Within date range
        (Game.is_completed == True) | (Game.game_date < four_hours_ago)  # Game is done
    ).order_by(desc(Play.created_at), desc(func.abs(Play.z_score))).all()

    # Group by date (convert to local timezone first)
    plays_by_date = {}
    for play in plays:
        # Convert UTC to local timezone before extracting date
        local_dt = utc_to_local(play.created_at)
        date = local_dt.date()
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
    """Show overall statistics including performance metrics"""
    session = get_session()

    # Get all plays
    all_plays = session.query(Play).all()

    # Calculate basic stats - exclude NO PLAY from total count
    actual_plays = [p for p in all_plays if p.recommendation != 'NO PLAY']
    total_plays = len(actual_plays)
    high_confidence = len([p for p in actual_plays if p.confidence == 'High'])
    medium_confidence = len([p for p in actual_plays if p.confidence == 'Medium'])

    # Performance metrics - only plays with results (excluding NO PLAY)
    graded_plays = [p for p in all_plays if p.was_correct is not None and p.recommendation != 'NO PLAY']
    total_graded = len(graded_plays)
    wins = len([p for p in graded_plays if p.was_correct == True])
    losses = len([p for p in graded_plays if p.was_correct == False])
    win_rate = (wins / total_graded * 100) if total_graded > 0 else 0

    # DEBUG: Print to console
    print(f"DEBUG STATS: Graded={total_graded}, Wins={wins}, Losses={losses}, WinRate={win_rate:.1f}%")

    # Calculate profit/loss based on American odds ($10 bets)
    bet_amount = 10
    total_profit = 0
    for play in graded_plays:
        if play.was_correct == True:
            # Win
            odds = play.over_odds if play.recommendation == 'OVER' else play.under_odds
            if odds and odds < 0:
                # Negative odds: profit = bet_amount * (100 / |odds|)
                profit = bet_amount * (100 / abs(odds))
            elif odds and odds > 0:
                # Positive odds: profit = bet_amount * (odds / 100)
                profit = bet_amount * (odds / 100)
            else:
                profit = bet_amount  # Default
            total_profit += profit
        elif play.was_correct == False:
            # Loss - lose the bet amount
            total_profit -= bet_amount

    roi = (total_profit / (total_graded * bet_amount) * 100) if total_graded > 0 else 0

    # Win rate and profit by confidence
    win_rate_by_conf = {}
    profit_by_conf = {}
    for conf in ['High', 'Medium']:
        conf_plays = [p for p in graded_plays if p.confidence == conf]
        if conf_plays:
            conf_wins = len([p for p in conf_plays if p.was_correct == True])
            win_rate_by_conf[conf] = {
                'rate': (conf_wins / len(conf_plays) * 100),
                'wins': conf_wins,
                'total': len(conf_plays)
            }

            # Calculate profit for this confidence level
            conf_profit = 0
            for play in conf_plays:
                if play.was_correct == True:
                    odds = play.over_odds if play.recommendation == 'OVER' else play.under_odds
                    if odds and odds < 0:
                        profit = bet_amount * (100 / abs(odds))
                    elif odds and odds > 0:
                        profit = bet_amount * (odds / 100)
                    else:
                        profit = bet_amount
                    conf_profit += profit
                elif play.was_correct == False:
                    conf_profit -= bet_amount
            profit_by_conf[conf] = conf_profit
        else:
            win_rate_by_conf[conf] = {'rate': 0, 'wins': 0, 'total': 0}
            profit_by_conf[conf] = 0

    # Win rate and profit by stat type
    win_rate_by_stat = {}
    profit_by_stat = {}
    for play in graded_plays:
        stat = play.stat_type
        if stat not in win_rate_by_stat:
            win_rate_by_stat[stat] = {'wins': 0, 'total': 0}
            profit_by_stat[stat] = 0

        win_rate_by_stat[stat]['total'] += 1
        if play.was_correct == True:
            win_rate_by_stat[stat]['wins'] += 1
            # Calculate profit
            odds = play.over_odds if play.recommendation == 'OVER' else play.under_odds
            if odds and odds < 0:
                profit = bet_amount * (100 / abs(odds))
            elif odds and odds > 0:
                profit = bet_amount * (odds / 100)
            else:
                profit = bet_amount
            profit_by_stat[stat] += profit
        elif play.was_correct == False:
            profit_by_stat[stat] -= bet_amount

    # Convert to percentages
    for stat in win_rate_by_stat:
        stat_total = win_rate_by_stat[stat]['total']
        stat_wins = win_rate_by_stat[stat]['wins']
        win_rate_by_stat[stat]['rate'] = (stat_wins / stat_total * 100) if stat_total > 0 else 0

    # Group by stat type (exclude NO PLAY)
    stat_counts = {}
    for play in actual_plays:
        stat_counts[play.stat_type] = stat_counts.get(play.stat_type, 0) + 1

    # Group by recommendation (exclude NO PLAY)
    rec_counts = {}
    for play in actual_plays:
        rec_counts[play.recommendation] = rec_counts.get(play.recommendation, 0) + 1

    # Average z-scores
    avg_z_score = sum(abs(p.z_score) for p in all_plays) / total_plays if total_plays > 0 else 0

    # Days tracked (convert to local timezone)
    if all_plays:
        dates = [utc_to_local(p.created_at).date() for p in all_plays]
        days_tracked = len(set(dates))
        first_date = min(dates)
        last_date = max(dates)
    else:
        days_tracked = 0
        first_date = None
        last_date = None

    # DEBUG: Print right before rendering
    print(f"DEBUG BEFORE RENDER: wins={wins}, losses={losses}")
    print(f"DEBUG win_rate_by_conf: {win_rate_by_conf}")

    return render_template('stats.html',
                         total_plays=total_plays,
                         high_confidence=high_confidence,
                         medium_confidence=medium_confidence,
                         total_graded=total_graded,
                         wins=wins,
                         losses=losses,
                         win_rate=win_rate,
                         total_profit=total_profit,
                         roi=roi,
                         win_rate_by_conf=win_rate_by_conf,
                         profit_by_conf=profit_by_conf,
                         win_rate_by_stat=win_rate_by_stat,
                         profit_by_stat=profit_by_stat,
                         stat_counts=stat_counts,
                         rec_counts=rec_counts,
                         avg_z_score=avg_z_score,
                         days_tracked=days_tracked,
                         first_date=first_date,
                         last_date=last_date,
                         bet_amount=bet_amount)


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


@app.template_filter('z_to_confidence')
def z_to_confidence(z_score):
    """
    Convert z-score to confidence percentage
    Higher |z| = more unusual line = higher confidence Vegas knows something

    Mapping:
    |z| = 0.5 → 60%
    |z| = 1.0 → 70%
    |z| = 1.5 → 80%
    |z| = 2.0 → 90%
    |z| = 2.5+ → 95%+
    """
    if z_score is None:
        return '-'

    abs_z = abs(z_score)
    # Linear mapping: 50% base + 20% per z-score unit
    confidence = 50 + (abs_z * 20)
    # Cap at 99%
    confidence = min(confidence, 99)

    return f"{int(confidence)}%"


@app.template_filter('calculate_profit')
def calculate_profit(play, bet_amount=10):
    """
    Calculate profit/loss for a play based on American odds

    Args:
        play: Play object with recommendation, was_correct, over_odds, under_odds
        bet_amount: Amount bet (default $10)

    Returns:
        Formatted string showing profit/loss (e.g., "+$15.00" or "-$10.00")
    """
    if play.was_correct is None or play.recommendation == 'NO PLAY':
        return '-'

    # Get the odds for the recommendation
    if play.recommendation == 'OVER':
        odds = play.over_odds
    elif play.recommendation == 'UNDER':
        odds = play.under_odds
    else:
        return '-'

    if odds is None:
        return '-'

    if play.was_correct:
        # Win - calculate profit based on American odds
        if odds < 0:
            # Negative odds: risk |odds| to win $100
            # Profit = bet_amount * (100 / |odds|)
            profit = bet_amount * (100 / abs(odds))
        else:
            # Positive odds: risk $100 to win odds
            # Profit = bet_amount * (odds / 100)
            profit = bet_amount * (odds / 100)
        return f'<span style="color: #27ae60; font-weight: bold;">+${profit:.2f}</span>'
    else:
        # Loss - lose the bet amount
        return f'<span style="color: #e74c3c; font-weight: bold;">-${bet_amount:.2f}</span>'


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
