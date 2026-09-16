import json
import os
from sqlalchemy.orm import Session
from database import Game, Move
from google import genai
from datetime import datetime

def extract_features(db: Session, username: str):
    # Fetch all games ordered by date/time (we can use id as proxy for chronological order if they were ingested sequentially)
    games = db.query(Game).filter((Game.white.ilike(username)) | (Game.black.ilike(username))).order_by(Game.id.asc()).all()
    
    total_games = len(games)
    wins, losses, draws = 0, 0, 0
    openings = {}
    
    # Endgame Conversion metrics
    endgame_reached_winning = 0
    endgame_converted = 0
    endgame_blown = 0

    tilt_cpl = []
    baseline_cpl = []
    
    # Store game results to calculate tilt (loss followed by next game)
    game_results_for_tilt = []

    for game in games:
        is_white = game.white.lower() == username.lower()
        won = (game.result == "1-0" and is_white) or (game.result == "0-1" and not is_white)
        lost = (game.result == "0-1" and is_white) or (game.result == "1-0" and not is_white)
        
        if won: wins += 1
        elif lost: losses += 1
        else: draws += 1
            
        op = game.opening_name
        if not op: op = "Unknown"
        if op not in openings:
            openings[op] = {'wins': 0, 'losses': 0, 'draws': 0, 'total': 0}
            
        openings[op]['total'] += 1
        if won: openings[op]['wins'] += 1
        elif lost: openings[op]['losses'] += 1
        else: openings[op]['draws'] += 1

        game_results_for_tilt.append((game.game_id, lost))

    sorted_openings = sorted(openings.items(), key=lambda x: x[1]['total'], reverse=True)[:10]
    
    # Engine features
    moves = db.query(Move).join(Game, Move.game_id == Game.game_id).filter((Game.white.ilike(username)) | (Game.black.ilike(username))).all()
    
    # Create fast O(1) lookup dictionary for games
    game_dict = {g.game_id: g for g in games}
    
    cpl_by_phase = {"opening": [], "middlegame": [], "endgame": []}
    mistake_types = {}
    
    blunders = 0
    complacency_blunders = 0
    time_pressure_blunders = 0
    
    game_avg_cpls = {}

    for m in moves:
        game = game_dict.get(m.game_id)
        if not game: continue
        
        is_white = game.white.lower() == username.lower()
        user_moved = (is_white and m.ply % 2 != 0) or (not is_white and m.ply % 2 == 0)
        
        # Check Endgame Conversion (did user enter endgame with >+200 but not win?)
        if user_moved and m.game_phase == "endgame" and getattr(game, '_endgame_counted', False) is False:
            eval_for_user = m.eval_before_cp if is_white else -m.eval_before_cp
            if m.eval_before_cp is not None and eval_for_user >= 200:
                endgame_reached_winning += 1
                won = (game.result == "1-0" and is_white) or (game.result == "0-1" and not is_white)
                if won:
                    endgame_converted += 1
                else:
                    endgame_blown += 1
                setattr(game, '_endgame_counted', True)

        if user_moved and m.centipawn_loss is not None:
            cpl = min(m.centipawn_loss, 1000)
            phase = m.game_phase or "middlegame"
            if phase in cpl_by_phase:
                cpl_by_phase[phase].append(cpl)
                
            if m.game_id not in game_avg_cpls:
                game_avg_cpls[m.game_id] = []
            game_avg_cpls[m.game_id].append(cpl)
                
            if m.classification == "blunder":
                blunders += 1
                
                # Complacency
                eval_for_user = m.eval_before_cp if is_white else -m.eval_before_cp
                if m.eval_before_cp is not None and eval_for_user > 300:
                    complacency_blunders += 1
                    
                # Time pressure blunder
                if m.clock_seconds_remaining is not None and m.clock_seconds_remaining < 30:
                    time_pressure_blunders += 1
                    
                # Taxonomy
                mtype = m.mistake_type or "unknown"
                mistake_types[mtype] = mistake_types.get(mtype, 0) + 1

    # Calculate Tilt (CPL in games following a loss)
    for i in range(len(game_results_for_tilt) - 1):
        game_id, lost = game_results_for_tilt[i]
        next_game_id, _ = game_results_for_tilt[i+1]
        
        if next_game_id in game_avg_cpls:
            avg_cpl = sum(game_avg_cpls[next_game_id]) / len(game_avg_cpls[next_game_id])
            if lost:
                tilt_cpl.append(avg_cpl)
            else:
                baseline_cpl.append(avg_cpl)

    avg_cpl_opening = round(sum(cpl_by_phase["opening"])/len(cpl_by_phase["opening"]), 1) if cpl_by_phase["opening"] else 0
    avg_cpl_middlegame = round(sum(cpl_by_phase["middlegame"])/len(cpl_by_phase["middlegame"]), 1) if cpl_by_phase["middlegame"] else 0
    avg_cpl_endgame = round(sum(cpl_by_phase["endgame"])/len(cpl_by_phase["endgame"]), 1) if cpl_by_phase["endgame"] else 0
    
    total_user_moves = sum(len(v) for v in cpl_by_phase.values())
    avg_total_cpl = round(sum(sum(v) for v in cpl_by_phase.values()) / total_user_moves, 1) if total_user_moves > 0 else 0

    avg_tilt_cpl = round(sum(tilt_cpl)/len(tilt_cpl), 1) if tilt_cpl else 0
    avg_baseline_cpl = round(sum(baseline_cpl)/len(baseline_cpl), 1) if baseline_cpl else 0

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
            "blunders": blunders,
            "time_pressure_blunders": time_pressure_blunders,
            "complacency_blunders": complacency_blunders,
            "mistake_taxonomy": mistake_types,
            "endgame_reached_winning": endgame_reached_winning,
            "endgame_converted": endgame_converted,
            "endgame_blown": endgame_blown,
            "avg_baseline_cpl": avg_baseline_cpl,
            "avg_tilt_cpl": avg_tilt_cpl
        }
    }

def generate_coach_report(features: dict, username: str):
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return "GEMINI_API_KEY environment variable not set. Please set it to generate reports."
        
    client = genai.Client(api_key=api_key)
    
    prompt = f"""
    Act as an elite, brutally honest chess grandmaster and data scientist. 
    Review the following deep-dive telemetry extracted from my recent games. 
    
    Username: {username}
    Record: {features['wins']}W - {features['losses']}L - {features['draws']}D ({features['win_rate']}%)
    
    [BEHAVIORAL & ENGINE METRICS]
    - Overall Avg CPL: {features['engine_metrics']['average_centipawn_loss']}
    - Phase Avg CPL: Opening={features['engine_metrics']['cpl_opening']}, Middlegame={features['engine_metrics']['cpl_middlegame']}, Endgame={features['engine_metrics']['cpl_endgame']}
    - Total Blunders: {features['engine_metrics']['blunders']}
    - Time-Pressure Blunders (<30s): {features['engine_metrics']['time_pressure_blunders']}
    - Complacency Blunders (from +3.00 winning position): {features['engine_metrics']['complacency_blunders']}
    
    [MISTAKE TAXONOMY]
    {json.dumps(features['engine_metrics']['mistake_taxonomy'], indent=2)}
    
    [ENDGAME CONVERSION]
    - Reached endgame with winning advantage: {features['engine_metrics']['endgame_reached_winning']} times
    - Actually converted to a win: {features['engine_metrics']['endgame_converted']} times
    - Blown (Drawn or Lost): {features['engine_metrics']['endgame_blown']} times
    
    [TILT SIGNATURE]
    - Baseline Avg CPL: {features['engine_metrics']['avg_baseline_cpl']}
    - Avg CPL in games immediately following a loss: {features['engine_metrics']['avg_tilt_cpl']}
    
    [TOP OPENINGS]
    {json.dumps(features['top_openings'], indent=2)}
    
    [OUTPUT INSTRUCTIONS]
    Do NOT output generic chess advice. You MUST format your response EXACTLY using the following 5 markdown sections:

    ### 1. Headline diagnosis
    Provide a plain-language summary of my current identity as a player and the 2-3 things most responsible for my rating ceiling right now. Not a laundry list, a prioritized diagnosis.

    ### 2. Ranked priority list
    The 3-5 specific things to work on, ranked by estimated rating-point impact. For each, include:
    - **What the data shows:** (Cite the specific stat from above)
    - **Why it matters:** (Why this specific gap is costing rating points)
    - **What kind of resource would fix it:** (e.g., "a rook endgame course", "a habit-tracking checklist for blunder-checking")
    - **How to know it's working:** (The specific metric that should move if I improve)

    ### 3. Suggested weekly structure
    Provide a time-budget template for study allocation (e.g., "40% tactics pattern work, 25% endgame technique") based purely on my data.

    ### 4. What to explicitly *not* prioritize right now
    Tell me what is NOT my bottleneck based on the data (e.g., "your opening theory is already solid, do not study openings").

    ### 5. Re-check schedule
    Recommend when to re-run this report to track metric shifts (e.g. after X games).
    """
    
    response = client.models.generate_content(
        model='gemini-2.5-pro',
        contents=prompt,
    )
    
    return response.text
