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
    """Home page - redirect to upcoming plays"""
    return upcoming_plays()


@app.route('/plays/upcoming')
@app.route('/plays/today')  # Keep old route for backwards compatibility
def upcoming_plays():
    """Show upcoming plays (today + tomorrow)"""
    session = get_session()

    # Get upcoming plays with game info - join with PropLine, Game, and Teams
    # Use aliases for Team table since we join it twice (away and home)
    away_team = aliased(Team)
    home_team = aliased(Team)

    # Get recent plays (last 3 days) through future games
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
        Play.created_at >= three_days_ago,  # Get recent plays
        Play.recommendation != 'NO PLAY'  # Hide NO PLAY recommendations
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
    game_status_filter = request.args.get('game_status', 'upcoming')  # Default to 'upcoming' to show all future games

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

    return render_template('upcoming.html',
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

    now_local = get_local_now()

    # Get filter parameters
    days_param = request.args.get('days', '')
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')
    confidence_filter = request.args.get('confidence', 'all')
    stat_filter = request.args.get('stat', 'all')
    recommendation_filter = request.args.get('recommendation', 'all')
    outcome_filter = request.args.get('outcome', 'all')

    # Determine date range
    if days_param:
        days = int(days_param)
        cutoff_date = now_local - timedelta(days=days)
        cutoff_utc = cutoff_date.astimezone(pytz.utc).replace(tzinfo=None)
        end_utc = None  # No end limit when using days
    elif date_from or date_to:
        days = None
        if date_from:
            from_date = datetime.strptime(date_from, '%Y-%m-%d')
            cutoff_utc = LOCAL_TIMEZONE.localize(from_date).astimezone(pytz.utc).replace(tzinfo=None)
        else:
            cutoff_utc = None
        if date_to:
            to_date = datetime.strptime(date_to, '%Y-%m-%d') + timedelta(days=1)  # Include the entire day
            end_utc = LOCAL_TIMEZONE.localize(to_date).astimezone(pytz.utc).replace(tzinfo=None)
        else:
            end_utc = None
    else:
        # Default to last 7 days
        days = 7
        cutoff_date = now_local - timedelta(days=days)
        cutoff_utc = cutoff_date.astimezone(pytz.utc).replace(tzinfo=None)
        end_utc = None

    # Get plays where the game is completed OR started more than 4 hours ago
    four_hours_ago = (now_local - timedelta(hours=4)).astimezone(pytz.utc).replace(tzinfo=None)

    # Join with PropLine, Game, and Teams to get full info
    away_team = aliased(Team)
    home_team = aliased(Team)

    query = session.query(Play, Game, away_team, home_team).join(
        PropLine, Play.prop_line_id == PropLine.id
    ).join(
        Game, PropLine.game_id == Game.id
    ).join(
        away_team, Game.away_team_id == away_team.id
    ).join(
        home_team, Game.home_team_id == home_team.id
    ).filter(
        Play.recommendation != 'NO PLAY',  # Hide NO PLAY recommendations
        (Game.is_completed == True) | (Game.game_date < four_hours_ago)  # Game is done
    )

    # Apply date filters
    if cutoff_utc:
        query = query.filter(Play.created_at >= cutoff_utc)
    if end_utc:
        query = query.filter(Play.created_at < end_utc)

    # Apply other filters at database level
    if confidence_filter != 'all':
        query = query.filter(Play.confidence == confidence_filter)
    if stat_filter != 'all':
        query = query.filter(Play.stat_type == stat_filter)
    if recommendation_filter != 'all':
        query = query.filter(Play.recommendation == recommendation_filter)
    if outcome_filter == 'win':
        query = query.filter(Play.was_correct == True)
    elif outcome_filter == 'loss':
        query = query.filter(Play.was_correct == False)
    elif outcome_filter == 'pending':
        query = query.filter(Play.was_correct == None)

    results = query.order_by(desc(Game.game_date), desc(func.abs(Play.z_score))).all()

    # Create flat list of (play, game, matchup) tuples
    all_plays = []
    for play, game, away, home in results:
        matchup = f"{away.abbreviation} @ {home.abbreviation}"
        all_plays.append((play, game, matchup))

    # Get unique values for filter dropdowns (from all data, not just filtered)
    all_results_for_filters = session.query(Play).join(
        PropLine, Play.prop_line_id == PropLine.id
    ).join(
        Game, PropLine.game_id == Game.id
    ).filter(
        Play.recommendation != 'NO PLAY',
        (Game.is_completed == True) | (Game.game_date < four_hours_ago)
    ).all()

    all_stats = sorted(set(p.stat_type for p in all_results_for_filters if p.stat_type))
    all_confidences = sorted(set(p.confidence for p in all_results_for_filters if p.confidence))
    all_recommendations = sorted(set(p.recommendation for p in all_results_for_filters if p.recommendation))

    return render_template('history.html',
                         all_plays=all_plays,
                         days=days,
                         date_from=date_from,
                         date_to=date_to,
                         confidence_filter=confidence_filter,
                         stat_filter=stat_filter,
                         recommendation_filter=recommendation_filter,
                         outcome_filter=outcome_filter,
                         all_stats=all_stats,
                         all_confidences=all_confidences,
                         all_recommendations=all_recommendations)


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

    # ===== NEW ADVANCED ANALYTICS =====

    # Average odds for wins vs losses
    winning_odds = []
    losing_odds = []
    for play in graded_plays:
        odds = play.over_odds if play.recommendation == 'OVER' else play.under_odds
        if odds:
            if play.was_correct == True:
                winning_odds.append(odds)
            else:
                losing_odds.append(odds)

    avg_winning_odds = sum(winning_odds) / len(winning_odds) if winning_odds else 0
    avg_losing_odds = sum(losing_odds) / len(losing_odds) if losing_odds else 0

    # Over vs Under performance
    over_plays = [p for p in graded_plays if p.recommendation == 'OVER']
    under_plays = [p for p in graded_plays if p.recommendation == 'UNDER']

    over_wins = len([p for p in over_plays if p.was_correct == True])
    under_wins = len([p for p in under_plays if p.was_correct == True])

    over_win_rate = (over_wins / len(over_plays) * 100) if over_plays else 0
    under_win_rate = (under_wins / len(under_plays) * 100) if under_plays else 0

    # Calculate profit for Over vs Under
    over_profit = 0
    under_profit = 0
    for play in over_plays:
        if play.was_correct == True:
            odds = play.over_odds
            if odds and odds < 0:
                over_profit += bet_amount * (100 / abs(odds))
            elif odds and odds > 0:
                over_profit += bet_amount * (odds / 100)
            else:
                over_profit += bet_amount
        else:
            over_profit -= bet_amount

    for play in under_plays:
        if play.was_correct == True:
            odds = play.under_odds
            if odds and odds < 0:
                under_profit += bet_amount * (100 / abs(odds))
            elif odds and odds > 0:
                under_profit += bet_amount * (odds / 100)
            else:
                under_profit += bet_amount
        else:
            under_profit -= bet_amount

    # Player performance rankings
    player_stats = {}
    for play in graded_plays:
        name = play.player_name
        if name not in player_stats:
            player_stats[name] = {'wins': 0, 'total': 0, 'profit': 0}

        player_stats[name]['total'] += 1
        if play.was_correct == True:
            player_stats[name]['wins'] += 1
            odds = play.over_odds if play.recommendation == 'OVER' else play.under_odds
            if odds and odds < 0:
                player_stats[name]['profit'] += bet_amount * (100 / abs(odds))
            elif odds and odds > 0:
                player_stats[name]['profit'] += bet_amount * (odds / 100)
            else:
                player_stats[name]['profit'] += bet_amount
        else:
            player_stats[name]['profit'] -= bet_amount

    # Calculate win rate for each player
    for name in player_stats:
        player_stats[name]['win_rate'] = (player_stats[name]['wins'] / player_stats[name]['total'] * 100)

    # Sort by profit
    top_players = sorted(player_stats.items(), key=lambda x: x[1]['profit'], reverse=True)[:10]
    worst_players = sorted(player_stats.items(), key=lambda x: x[1]['profit'])[:10]

    # Bookmaker analysis
    bookmaker_stats = {}
    for play in graded_plays:
        bookie = play.bookmaker or 'Unknown'
        if bookie not in bookmaker_stats:
            bookmaker_stats[bookie] = {'wins': 0, 'total': 0, 'profit': 0}

        bookmaker_stats[bookie]['total'] += 1
        if play.was_correct == True:
            bookmaker_stats[bookie]['wins'] += 1
            odds = play.over_odds if play.recommendation == 'OVER' else play.under_odds
            if odds and odds < 0:
                bookmaker_stats[bookie]['profit'] += bet_amount * (100 / abs(odds))
            elif odds and odds > 0:
                bookmaker_stats[bookie]['profit'] += bet_amount * (odds / 100)
            else:
                bookmaker_stats[bookie]['profit'] += bet_amount
        else:
            bookmaker_stats[bookie]['profit'] -= bet_amount

    for bookie in bookmaker_stats:
        bookmaker_stats[bookie]['win_rate'] = (bookmaker_stats[bookie]['wins'] / bookmaker_stats[bookie]['total'] * 100)

    # Z-score effectiveness (do higher z-scores win more?)
    z_score_ranges = {
        '0.5-0.75': [],
        '0.75-1.0': [],
        '1.0-1.5': [],
        '1.5+': []
    }

    for play in graded_plays:
        abs_z = abs(play.z_score) if play.z_score else 0
        if 0.5 <= abs_z < 0.75:
            z_score_ranges['0.5-0.75'].append(play)
        elif 0.75 <= abs_z < 1.0:
            z_score_ranges['0.75-1.0'].append(play)
        elif 1.0 <= abs_z < 1.5:
            z_score_ranges['1.0-1.5'].append(play)
        elif abs_z >= 1.5:
            z_score_ranges['1.5+'].append(play)

    z_score_performance = {}
    profit_by_z_score_range = {}
    for range_name, plays_list in z_score_ranges.items():
        if plays_list:
            range_wins = len([p for p in plays_list if p.was_correct == True])
            z_score_performance[range_name] = {
                'win_rate': (range_wins / len(plays_list) * 100),
                'total': len(plays_list),
                'wins': range_wins
            }

            # Calculate profit for this z-score range
            range_profit = 0
            for play in plays_list:
                if play.was_correct == True:
                    odds = play.over_odds if play.recommendation == 'OVER' else play.under_odds
                    if odds and odds < 0:
                        range_profit += bet_amount * (100 / abs(odds))
                    elif odds and odds > 0:
                        range_profit += bet_amount * (odds / 100)
                    else:
                        range_profit += bet_amount
                elif play.was_correct == False:
                    range_profit -= bet_amount
            profit_by_z_score_range[range_name] = range_profit
        else:
            z_score_performance[range_name] = {'win_rate': 0, 'total': 0, 'wins': 0}
            profit_by_z_score_range[range_name] = 0

    # Cumulative profit over time (for charting)
    plays_by_date = sorted(graded_plays, key=lambda x: x.created_at)
    cumulative_profit_data = []
    running_profit = 0

    for play in plays_by_date:
        if play.was_correct == True:
            odds = play.over_odds if play.recommendation == 'OVER' else play.under_odds
            if odds and odds < 0:
                running_profit += bet_amount * (100 / abs(odds))
            elif odds and odds > 0:
                running_profit += bet_amount * (odds / 100)
            else:
                running_profit += bet_amount
        else:
            running_profit -= bet_amount

        cumulative_profit_data.append({
            'date': utc_to_local(play.created_at).strftime('%Y-%m-%d'),
            'profit': round(running_profit, 2)
        })

    # Daily profit breakdown
    daily_profit = {}
    for play in graded_plays:
        date_str = utc_to_local(play.created_at).strftime('%Y-%m-%d')
        if date_str not in daily_profit:
            daily_profit[date_str] = 0

        if play.was_correct == True:
            odds = play.over_odds if play.recommendation == 'OVER' else play.under_odds
            if odds and odds < 0:
                daily_profit[date_str] += bet_amount * (100 / abs(odds))
            elif odds and odds > 0:
                daily_profit[date_str] += bet_amount * (odds / 100)
            else:
                daily_profit[date_str] += bet_amount
        else:
            daily_profit[date_str] -= bet_amount

    # Sort by date
    daily_profit_sorted = sorted(daily_profit.items(), key=lambda x: x[0], reverse=True)[:30]  # Last 30 days

    # ===== HEDGE FUND RISK METRICS =====

    # Current streak (W/L streak based on most recent plays)
    current_streak = 0
    if plays_by_date:
        # Start from most recent play
        for play in reversed(plays_by_date):
            if current_streak == 0:
                # First play sets the direction
                if play.was_correct == True:
                    current_streak = 1
                elif play.was_correct == False:
                    current_streak = -1
            elif current_streak > 0 and play.was_correct == True:
                # Continuing win streak
                current_streak += 1
            elif current_streak < 0 and play.was_correct == False:
                # Continuing loss streak
                current_streak -= 1
            else:
                # Streak broken
                break

    # Longest win streak
    longest_win_streak = 0
    current_win_streak = 0
    for play in plays_by_date:
        if play.was_correct == True:
            current_win_streak += 1
            longest_win_streak = max(longest_win_streak, current_win_streak)
        else:
            current_win_streak = 0

    # Max drawdown (biggest peak-to-trough decline)
    max_drawdown = 0
    if cumulative_profit_data:
        peak = cumulative_profit_data[0]['profit']
        for data_point in cumulative_profit_data:
            current_profit = data_point['profit']
            # Update peak if we're at a new high
            if current_profit > peak:
                peak = current_profit
            # Calculate drawdown from peak
            drawdown = peak - current_profit
            # Update max drawdown
            max_drawdown = max(max_drawdown, drawdown)

    # Average win amount and average loss amount
    win_amounts = []
    loss_amounts = []
    for play in graded_plays:
        if play.was_correct == True:
            odds = play.over_odds if play.recommendation == 'OVER' else play.under_odds
            if odds and odds < 0:
                win_amount = bet_amount * (100 / abs(odds))
            elif odds and odds > 0:
                win_amount = bet_amount * (odds / 100)
            else:
                win_amount = bet_amount
            win_amounts.append(win_amount)
        elif play.was_correct == False:
            loss_amounts.append(bet_amount)

    avg_win_amount = sum(win_amounts) / len(win_amounts) if win_amounts else 0
    avg_loss_amount = sum(loss_amounts) / len(loss_amounts) if loss_amounts else 0

    # Total winnings and total losses (for profit factor)
    total_winnings = sum(win_amounts)
    total_losses = sum(loss_amounts)

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
                         bet_amount=bet_amount,
                         # New advanced analytics
                         avg_winning_odds=avg_winning_odds,
                         avg_losing_odds=avg_losing_odds,
                         over_win_rate=over_win_rate,
                         under_win_rate=under_win_rate,
                         over_profit=over_profit,
                         under_profit=under_profit,
                         over_total=len(over_plays),
                         under_total=len(under_plays),
                         top_players=top_players,
                         worst_players=worst_players,
                         bookmaker_stats=bookmaker_stats,
                         z_score_performance=z_score_performance,
                         profit_by_z_score_range=profit_by_z_score_range,
                         cumulative_profit_data=cumulative_profit_data,
                         daily_profit=daily_profit_sorted,
                         # Hedge fund risk metrics
                         current_streak=current_streak,
                         longest_win_streak=longest_win_streak,
                         max_drawdown=max_drawdown,
                         avg_win_amount=avg_win_amount,
                         avg_loss_amount=avg_loss_amount,
                         total_winnings=total_winnings,
                         total_losses=total_losses)


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


@app.template_filter('format_line')
def format_line(value):
    """Format line value to always show 1 decimal"""
    if value is None:
        return '-'
    return f"{value:.1f}"


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
