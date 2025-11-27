"""
Database models for NBA Props Analyzer
Simple, clean models: Team, Player, Game, PropLine
"""
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()


class Team(Base):
    """NBA Teams"""
    __tablename__ = "teams"

    id = Column(Integer, primary_key=True)
    nba_team_id = Column(Integer, unique=True, nullable=False)
    abbreviation = Column(String(3), unique=True, nullable=False)
    full_name = Column(String(100), nullable=False)

    players = relationship("Player", back_populates="team")
    home_games = relationship("Game", foreign_keys="Game.home_team_id", back_populates="home_team")
    away_games = relationship("Game", foreign_keys="Game.away_team_id", back_populates="away_team")


class Player(Base):
    """NBA Players"""
    __tablename__ = "players"

    id = Column(Integer, primary_key=True)
    nba_player_id = Column(Integer, unique=True, nullable=False)
    full_name = Column(String(100), nullable=False)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=True)

    team = relationship("Team", back_populates="players")
    prop_lines = relationship("PropLine", back_populates="player")


class Game(Base):
    """NBA Games"""
    __tablename__ = "games"

    id = Column(Integer, primary_key=True)
    nba_game_id = Column(String(50), unique=True, nullable=False)
    game_date = Column(DateTime, nullable=False)
    home_team_id = Column(Integer, ForeignKey("teams.id"), nullable=False)
    away_team_id = Column(Integer, ForeignKey("teams.id"), nullable=False)
    is_completed = Column(Boolean, default=False)

    home_team = relationship("Team", foreign_keys=[home_team_id], back_populates="home_games")
    away_team = relationship("Team", foreign_keys=[away_team_id], back_populates="away_games")
    prop_lines = relationship("PropLine", back_populates="game")


class PropLine(Base):
    """Betting Lines for Player Props"""
    __tablename__ = "prop_lines"

    id = Column(Integer, primary_key=True)
    game_id = Column(Integer, ForeignKey("games.id"), nullable=False)
    player_id = Column(Integer, ForeignKey("players.id"), nullable=False)
    prop_type = Column(String(50), nullable=False)  # points, rebounds, assists, threes
    line_value = Column(Float, nullable=False)  # The O/U number
    over_odds = Column(Integer, nullable=True)  # American odds (e.g., -110)
    under_odds = Column(Integer, nullable=True)
    bookmaker = Column(String(50), nullable=True)
    collected_at = Column(DateTime, default=datetime.utcnow)
    is_latest = Column(Boolean, default=True)

    game = relationship("Game", back_populates="prop_lines")
    player = relationship("Player", back_populates="prop_lines")
    plays = relationship("Play", back_populates="prop_line")


class Play(Base):
    """Analyzed betting plays with recommendations"""
    __tablename__ = "plays"

    id = Column(Integer, primary_key=True)
    prop_line_id = Column(Integer, ForeignKey("prop_lines.id"), nullable=False)
    player_name = Column(String(100), nullable=False)
    stat_type = Column(String(50), nullable=False)
    line_value = Column(Float, nullable=False)

    # Analysis data
    season_avg = Column(Float, nullable=True)
    last5_avg = Column(Float, nullable=True)
    expected_value = Column(Float, nullable=True)
    std_dev = Column(Float, nullable=True)
    deviation = Column(Float, nullable=True)
    z_score = Column(Float, nullable=True)
    games_played = Column(Integer, nullable=True)

    # Recommendation
    recommendation = Column(String(20), nullable=False)  # OVER, UNDER, NO PLAY
    confidence = Column(String(20), nullable=True)  # High, Medium, N/A

    # Odds info
    bookmaker = Column(String(50), nullable=True)
    over_odds = Column(Integer, nullable=True)
    under_odds = Column(Integer, nullable=True)

    # Tracking
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Future: actual results for backtesting
    actual_result = Column(Float, nullable=True)
    result_collected_at = Column(DateTime, nullable=True)
    was_correct = Column(Boolean, nullable=True)

    prop_line = relationship("PropLine", back_populates="plays")


class PlayerGameStats(Base):
    """Cached NBA player game-by-game statistics"""
    __tablename__ = "player_game_stats"

    id = Column(Integer, primary_key=True)
    player_id = Column(Integer, ForeignKey("players.id"), nullable=False)
    game_id = Column(Integer, ForeignKey("games.id"), nullable=True)  # Nullable - we cache all games, not just ones we bet on
    nba_game_id = Column(String(50), nullable=False)
    game_date = Column(DateTime, nullable=False)

    # Core stats
    minutes = Column(Float, nullable=True)
    points = Column(Integer, nullable=True)
    rebounds = Column(Integer, nullable=True)
    assists = Column(Integer, nullable=True)
    steals = Column(Integer, nullable=True)
    blocks = Column(Integer, nullable=True)
    turnovers = Column(Integer, nullable=True)

    # Shooting stats
    fgm = Column(Integer, nullable=True)  # Field goals made
    fga = Column(Integer, nullable=True)  # Field goals attempted
    fg_pct = Column(Float, nullable=True)  # Field goal %
    fg3m = Column(Integer, nullable=True)  # 3-pointers made
    fg3a = Column(Integer, nullable=True)  # 3-pointers attempted
    fg3_pct = Column(Float, nullable=True)  # 3-point %
    ftm = Column(Integer, nullable=True)  # Free throws made
    fta = Column(Integer, nullable=True)  # Free throws attempted
    ft_pct = Column(Float, nullable=True)  # Free throw %

    # Metadata
    season = Column(String(10), nullable=False)  # "2024-25"
    fetched_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    player = relationship("Player")
    game = relationship("Game")


class APICallLog(Base):
    """Track API calls for monitoring and rate limiting"""
    __tablename__ = "api_call_logs"

    id = Column(Integer, primary_key=True)
    api_name = Column(String(50), nullable=False)  # 'nba_api', 'odds_api'
    endpoint = Column(String(200), nullable=True)
    player_id = Column(Integer, nullable=True)
    season = Column(String(10), nullable=True)
    cache_hit = Column(Boolean, default=False)
    called_at = Column(DateTime, default=datetime.utcnow, nullable=False)
