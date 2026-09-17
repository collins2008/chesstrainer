from fastapi import FastAPI, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from fastapi.middleware.cors import CORSMiddleware
import database
import sys
import ingest
import engine
import chat
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="AI Chess Coach API")

# Configure CORS for Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, restrict this to frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router)

def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/")
def read_root():
    return {"status": "ok", "message": "Chess Coach API is running"}

import ingest

@app.post("/sync/{platform}/{username}")
def sync_games(platform: str, username: str, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    success = False
    messages = []
    
    if platform in ["chess.com", "all"]:
        if ingest.ingest_chesscom(username):
            messages.append("Chess.com")
            success = True
    if platform in ["lichess", "all"]:
        if ingest.ingest_lichess(username):
            messages.append("Lichess")
            success = True
            
    if success:
        # Trigger analysis on all unanalyzed games sequentially in one background task
        def run_all_analysis():
            from engine import run_analysis
            from database import SessionLocal, Game, Move
            db_session = SessionLocal()
            try:
                games = db_session.query(Game).filter((Game.white.ilike(username)) | (Game.black.ilike(username))).all()
                for g in games:
                    if g.ply_count is None:
                        run_analysis(g.game_id)
            finally:
                db_session.close()
                
        background_tasks.add_task(run_all_analysis)
            
        platforms_synced = " & ".join(messages)
        return {"status": "success", "message": f"Successfully synced {platforms_synced} games. Engine analysis running in background."}
    else:
        return {"status": "error", "message": f"Failed to sync games."}

from database import Game, Move
@app.get("/status/{username}")
def get_status(username: str, db: Session = Depends(get_db)):
    total_games = db.query(Game).filter((Game.white.ilike(username)) | (Game.black.ilike(username))).count()
    
    # Count how many games have been fully processed by the engine
    analyzed_games = db.query(Game).filter(
        ((Game.white.ilike(username)) | (Game.black.ilike(username))) & 
        (Game.ply_count.isnot(None))
    ).count()
    
    return {
        "total_games": total_games,
        "analyzed_games": analyzed_games,
        "is_analyzing": analyzed_games < total_games and total_games > 0
    }

@app.get("/drills/blunders/{username}")
def get_blunders(username: str, db: Session = Depends(get_db)):
    # Fetch 10 random blunders made by the user
    from sqlalchemy.sql.expression import func
    blunders = db.query(Move, Game).join(Game, Move.game_id == Game.game_id).filter(
        ((Game.white.ilike(username)) & (Move.ply % 2 != 0)) | # White's turn (odd ply)
        ((Game.black.ilike(username)) & (Move.ply % 2 == 0)),  # Black's turn (even ply)
        Move.classification == "blunder"
    ).order_by(func.random()).limit(10).all()
    
    results = []
    for move, game in blunders:
        results.append({
            "game_id": game.game_id,
            "platform": game.platform,
            "date": game.date,
            "ply": move.ply,
            "move_san": move.move_san,
            "mistake_type": move.mistake_type,
            "centipawn_loss": move.centipawn_loss,
            "raw_pgn": game.raw_pgn
        })
    return {"status": "success", "blunders": results}

import utils
from pydantic import BaseModel

class GoalRequest(BaseModel):
    target_rating: str = ""
    target_date: str = ""
    time_budget: str = ""
    constraints: str = ""
    api_key: str = ""

@app.post("/report/{username}")
def generate_report(username: str, goal: GoalRequest, db: Session = Depends(get_db)):
    if not goal.api_key:
        return {"status": "error", "message": "Please provide your Gemini API key in the UI."}
        
    features = utils.extract_features(db, username)
    if features["total_games"] == 0:
        return {"status": "error", "message": f"No games found for {username}. Please sync games first."}
        
    try:
        # Override the env var temporarily so utils picks it up
        os.environ["GEMINI_API_KEY"] = goal.api_key
        report_md = utils.generate_coach_report(features, username, goal)
        return {"status": "success", "report": report_md, "stats": features}
    except Exception as e:
        return {"status": "error", "message": str(e)}
