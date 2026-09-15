from sqlalchemy import create_engine, Column, Integer, String, Float, ForeignKey, Boolean
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = "sqlite:///./chess_coach.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class Game(Base):
    __tablename__ = "games"

    id = Column(Integer, primary_key=True, index=True)
    game_id = Column(String, unique=True, index=True)
    platform = Column(String)
    date = Column(String)
    time_control = Column(String)
    white = Column(String)
    black = Column(String)
    white_rating = Column(Integer, nullable=True)
    black_rating = Column(Integer, nullable=True)
    result = Column(String)
    termination = Column(String, nullable=True)
    eco_code = Column(String, nullable=True)
    opening_name = Column(String)
    ply_count = Column(Integer, nullable=True)
    raw_pgn = Column(String)

class Move(Base):
    __tablename__ = "moves"

    id = Column(Integer, primary_key=True, index=True)
    game_id = Column(String, ForeignKey("games.game_id"), index=True)
    ply = Column(Integer)
    move_san = Column(String)
    move_uci = Column(String)
    clock_seconds_remaining = Column(Float, nullable=True)
    time_spent_on_move = Column(Float, nullable=True)
    eval_before_cp = Column(Float, nullable=True)
    eval_after_cp = Column(Float, nullable=True)
    centipawn_loss = Column(Float, nullable=True)
    classification = Column(String, nullable=True) # best, inaccuracy, mistake, blunder
    mistake_type = Column(String, nullable=True) # hanging_piece, missed_mate, missed_tactic, time_pressure
    blunder_punished = Column(Boolean, nullable=True)
    is_book = Column(Boolean, default=False)
    game_phase = Column(String, nullable=True) # opening, middlegame, endgame

Base.metadata.create_all(bind=engine)
