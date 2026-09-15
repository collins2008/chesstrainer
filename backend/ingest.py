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
    
    # Pre-fetch existing game IDs to avoid N+1 queries
    existing_games = {g[0] for g in db.query(Game.game_id).filter(Game.platform == "chess.com").all()}
    
    # Fetch games from newest month to oldest
    for month_url in reversed(archives):
        games_res = requests.get(month_url, headers=headers)
        if games_res.status_code == 200:
            games_data = games_res.json().get("games", [])
            if not games_data:
                continue
                
            new_games_found = False
            for game_data in games_data:
                game_id = game_data.get("url")
                if not game_id: continue
                
                # Check if exists
                if game_id in existing_games:
                    continue
                    
                new_games_found = True
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
                
            # If we looked at a month that had games, but NONE of them were new,
            # it means we've reached the point in history where everything is already synced!
            if not new_games_found:
                break
                
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
        "pgnInJson": "false"
    }
    headers = {
        "Accept": "application/x-chess-pgn",
        "User-Agent": "AI_Chess_Coach/1.0 (personal use)"
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
        
    try:
        with requests.get(url, params=params, headers=headers, stream=True) as res:
            if res.status_code != 200:
                print(f"Lichess API error: {res.status_code}")
                return False
                
            import chess.pgn
            import io
            
            existing_games = {g[0] for g in db.query(Game.game_id).filter(Game.platform == "lichess").all()}
            
            # Stream the response instead of loading everything into memory
            res.raw.decode_content = True
            pgn_io = io.TextIOWrapper(res.raw, encoding='utf-8')
            
            while True:
                game = chess.pgn.read_game(pgn_io)
                if game is None:
                    break
                    
                headers = game.headers
                game_id = headers.get("Site", "")
                if not game_id:
                    continue
                    
                # If we encounter a game we already have, we can stop!
                # Lichess exports from newest to oldest by default.
                if game_id in existing_games:
                    break
                    
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

