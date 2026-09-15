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
    if platform == "chess.com":
        success = ingest.ingest_chesscom(username)
    elif platform == "lichess":
        success = ingest.ingest_lichess(username)
        
    if success:
        # Trigger analysis on all unanalyzed games for this user
        from engine import run_analysis
        from database import Game
        games = db.query(Game).filter((Game.white == username) | (Game.black == username)).all()
        for g in games:
            background_tasks.add_task(run_analysis, g.game_id)
            
        return {"status": "success", "message": f"Successfully synced {platform} games. Engine analysis running in background."}
    else:
        return {"status": "error", "message": f"Failed to sync {platform} games."}

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
