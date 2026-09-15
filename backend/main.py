from fastapi import FastAPI, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from fastapi.middleware.cors import CORSMiddleware
import database

app = FastAPI(title="AI Chess Coach API")

# Configure CORS for Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, restrict this to frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
                analyzed_ids = {m[0] for m in db_session.query(Move.game_id).distinct().all()}
                for g in games:
                    if g.game_id not in analyzed_ids:
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
    
    # Count how many distinct games have at least one move analyzed
    analyzed_games = db.query(Move.game_id).join(Game, Move.game_id == Game.game_id).filter(
        (Game.white.ilike(username)) | (Game.black.ilike(username))
    ).distinct().count()
    
    return {
        "total_games": total_games,
        "analyzed_games": analyzed_games,
        "is_analyzing": analyzed_games < total_games and total_games > 0
    }

import utils

@app.get("/report/{username}")
def generate_report(username: str, db: Session = Depends(get_db)):
    features = utils.extract_features(db, username)
    if features["total_games"] == 0:
        return {"status": "error", "message": f"No games found for {username}. Please sync games first."}
        
    try:
        report_md = utils.generate_coach_report(features, username)
        return {"status": "success", "report": report_md, "stats": features}
    except Exception as e:
        return {"status": "error", "message": str(e)}
