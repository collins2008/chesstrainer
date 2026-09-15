import json
import os
from sqlalchemy.orm import Session
from database import Game, Move
from google import genai

def extract_features(db: Session, username: str):
    games = db.query(Game).filter((Game.white.ilike(username)) | (Game.black.ilike(username))).all()
    
    total_games = len(games)
    wins, losses, draws = 0, 0, 0
    openings = {}
    
    for game in games:
        is_white = game.white.lower() == username.lower()
        
        if game.result == "1-0":
            if is_white: wins += 1
            else: losses += 1
        elif game.result == "0-1":
            if is_white: losses += 1
            else: wins += 1
        else:
            draws += 1
            
        op = game.opening_name
        if not op: op = "Unknown"
        if op not in openings:
            openings[op] = {'wins': 0, 'losses': 0, 'draws': 0, 'total': 0}
            
        openings[op]['total'] += 1
        if game.result == "1-0":
            if is_white: openings[op]['wins'] += 1
            else: openings[op]['losses'] += 1
        elif game.result == "0-1":
            if is_white: openings[op]['losses'] += 1
            else: openings[op]['wins'] += 1
        else:
            openings[op]['draws'] += 1

    sorted_openings = sorted(openings.items(), key=lambda x: x[1]['total'], reverse=True)[:10]
    
    # Engine features (The deep dive)
    moves = db.query(Move).join(Game, Move.game_id == Game.game_id).filter((Game.white.ilike(username)) | (Game.black.ilike(username))).all()
    
    cpl_by_phase = {"opening": [], "middlegame": [], "endgame": []}
    blunders = 0
    complacency_blunders = 0
    time_pressure_cpl = []
    
    for m in moves:
        game = next((g for g in games if g.game_id == m.game_id), None)
        if not game: continue
        
        is_white = game.white.lower() == username.lower()
        # ply is 1-indexed. White moves on odd plies, Black moves on even plies.
        user_moved = (is_white and m.ply % 2 != 0) or (not is_white and m.ply % 2 == 0)
        
        if user_moved and m.centipawn_loss is not None:
            cpl = min(m.centipawn_loss, 1000)
            phase = m.game_phase or "middlegame"
            if phase in cpl_by_phase:
                cpl_by_phase[phase].append(cpl)
                
            if m.classification == "blunder":
                blunders += 1
                # Complacency blunder: blundering when you are already winning heavily (+3.00)
                eval_for_user = m.eval_before_cp if is_white else -m.eval_before_cp
                if m.eval_before_cp is not None and eval_for_user > 300:
                    complacency_blunders += 1
                    
            # Time pressure behavior: clock under 60 seconds
            if m.clock_seconds_remaining is not None and m.clock_seconds_remaining < 60:
                time_pressure_cpl.append(cpl)

    avg_cpl_opening = round(sum(cpl_by_phase["opening"])/len(cpl_by_phase["opening"]), 1) if cpl_by_phase["opening"] else 0
    avg_cpl_middlegame = round(sum(cpl_by_phase["middlegame"])/len(cpl_by_phase["middlegame"]), 1) if cpl_by_phase["middlegame"] else 0
    avg_cpl_endgame = round(sum(cpl_by_phase["endgame"])/len(cpl_by_phase["endgame"]), 1) if cpl_by_phase["endgame"] else 0
    avg_cpl_time_pressure = round(sum(time_pressure_cpl)/len(time_pressure_cpl), 1) if time_pressure_cpl else 0
    
    total_user_moves = sum(len(v) for v in cpl_by_phase.values())
    avg_total_cpl = round(sum(sum(v) for v in cpl_by_phase.values()) / total_user_moves, 1) if total_user_moves > 0 else 0

    return {
        "total_games": total_games,
        "wins": wins,
        "losses": losses,
        "draws": draws,
        "win_rate": round(wins/total_games * 100, 2) if total_games > 0 else 0,
        "top_openings": sorted_openings,
        "engine_metrics": {
            "total_moves_analyzed": total_user_moves,
            "average_centipawn_loss": avg_total_cpl,
            "cpl_opening": avg_cpl_opening,
            "cpl_middlegame": avg_cpl_middlegame,
            "cpl_endgame": avg_cpl_endgame,
            "cpl_under_60s": avg_cpl_time_pressure,
            "blunders": blunders,
            "complacency_blunders": complacency_blunders
        }
    }

def generate_coach_report(features: dict, username: str):
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return "GEMINI_API_KEY environment variable not set. Please set it to generate reports."
        
    client = genai.Client(api_key=api_key)
    
    prompt = f"""
    Act as an elite, brutally honest, but encouraging chess grandmaster and data scientist. 
    Review the following deep-dive telemetry extracted from my recent games. This is not surface-level data; these are my actual structural habits.
    
    Username: {username}
    Record: {features['wins']}W - {features['losses']}L - {features['draws']}D ({features['win_rate']}%)
    
    [BEHAVIORAL & ENGINE METRICS]
    - Overall Avg CPL: {features['engine_metrics']['average_centipawn_loss']}
    - Opening Phase Avg CPL: {features['engine_metrics']['cpl_opening']}
    - Middlegame Phase Avg CPL: {features['engine_metrics']['cpl_middlegame']}
    - Endgame Phase Avg CPL: {features['engine_metrics']['cpl_endgame']}
    - Time-Pressure CPL (<60s on clock): {features['engine_metrics']['cpl_under_60s']}
    - Total Blunders: {features['engine_metrics']['blunders']}
    - Complacency Blunders (Blundering from a +3.00 winning position): {features['engine_metrics']['complacency_blunders']}
    
    [TOP OPENINGS]
    {json.dumps(features['top_openings'], indent=2)}
    
    [COACHING DIRECTIVES]
    Analyze this specific data. Do not give generic advice. 
    1. Diagnose my phase-specific weaknesses based on the CPL drops.
    2. Assess my time-pressure resilience and tilt/complacency profiles.
    3. Tell me the 3 uncomfortable truths about my playstyle that are capping my rating based on these exact metrics.
    4. Provide a concrete, prioritized training plan (e.g. which phases/openings to study).
    """
    
    response = client.models.generate_content(
        model='gemini-2.5-pro',
        contents=prompt,
    )
    
    return response.text
