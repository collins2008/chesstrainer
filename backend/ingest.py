import requests
import berserk
from database import SessionLocal, Game
import os

def ingest_chesscom(username: str):
    db = SessionLocal()
    headers = {"User-Agent": "ChessCoachPWA/1.0 (contact@example.com)"}
    archives_url = f"https://api.chess.com/pub/player/{username}/games/archives"
    
    res = requests.get(archives_url, headers=headers)
    if res.status_code != 200:
        return False
        
    archives = res.json().get("archives", [])
    
    # Just fetch the last 2 months to be fast for now
    for month_url in archives[-2:]:
        games_res = requests.get(month_url, headers=headers)
        if games_res.status_code == 200:
            games_data = games_res.json().get("games", [])
            for game_data in games_data:
                game_id = game_data.get("url")
                if not game_id: continue
                
                # Check if exists
                if db.query(Game).filter(Game.game_id == game_id).first():
                    continue
                    
                white = game_data.get("white", {}).get("username")
                black = game_data.get("black", {}).get("username")
                
                # parse result
                result_str = ""
                pgn = game_data.get("pgn", "")
                if "[Result \"1-0\"]" in pgn: result_str = "1-0"
                elif "[Result \"0-1\"]" in pgn: result_str = "0-1"
                elif "[Result \"1/2-1/2\"]" in pgn: result_str = "1/2-1/2"
                
                opening = "Unknown"
                if "ECOUrl" in pgn:
                    # super hacky parsing just to get data fast
                    try:
                        opening = pgn.split("[ECOUrl \"")[1].split("\"]")[0].split("/")[-1].replace("-", " ")
                    except:
                        pass
                
                new_game = Game(
                    game_id=game_id,
                    platform="chess.com",
                    date=game_data.get("end_time"),
                    time_control=game_data.get("time_control"),
                    white=white,
                    black=black,
                    result=result_str,
                    opening_name=opening,
                    raw_pgn=pgn
                )
                db.add(new_game)
                
    db.commit()
    db.close()
    return True

def ingest_lichess(username: str, token: str = None):
    db = SessionLocal()
    # Lichess export API
    url = f"https://lichess.org/api/games/user/{username}"
    params = {
        "moves": "true",
        "clocks": "true",
        "evals": "true",
        "opening": "true",
        "pgnInJson": "false",
        "max": 50 # Limit for now to avoid massive downloads
    }
    headers = {"Accept": "application/x-chess-pgn"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
        
    try:
        res = requests.get(url, params=params, headers=headers)
        if res.status_code != 200:
            print(f"Lichess API error: {res.status_code}")
            return False
            
        import chess.pgn
        import io
        
        pgn_io = io.StringIO(res.text)
        while True:
            game = chess.pgn.read_game(pgn_io)
            if game is None:
                break
                
            headers = game.headers
            game_id = headers.get("Site", "")
            if not game_id:
                continue
                
            # Check if exists
            if db.query(Game).filter(Game.game_id == game_id).first():
                continue
                
            white = headers.get("White")
            black = headers.get("Black")
            result = headers.get("Result")
            opening = headers.get("Opening", "Unknown")
            
            # Re-export PGN string to store
            exporter = chess.pgn.StringExporter(headers=True, variations=True, comments=True)
            raw_pgn = game.accept(exporter)
            
            new_game = Game(
                game_id=game_id,
                platform="lichess",
                date=headers.get("UTCDate"),
                time_control=headers.get("TimeControl"),
                white=white,
                black=black,
                result=result,
                opening_name=opening,
                raw_pgn=raw_pgn
            )
            db.add(new_game)
            
        db.commit()
    except Exception as e:
        print(f"Lichess ingest error: {e}")
        db.rollback()
        db.close()
        return False
        
    db.close()
    return True

