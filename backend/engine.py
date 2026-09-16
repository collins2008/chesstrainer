import chess.pgn
import chess.engine
import io
import os
from database import SessionLocal, Game, Move

import math

def cp_to_wp(cp):
    if cp is None: return None
    cp = max(min(cp, 10000), -10000)
    try:
        return 50 + 50 * (2 / (1 + math.exp(-0.00368208 * cp)) - 1)
    except OverflowError:
        return 100.0 if cp > 0 else 0.0

def get_game_phase(board: chess.Board):
    # Heuristic based on material. Max material (without kings/pawns) is 31 per side.
    # Total piece material > 30 -> Opening/Middlegame
    # Total piece material <= 30 -> Endgame
    # We can refine this to opening vs middlegame by looking at castling rights and piece development,
    # but for speed, we use a simple ply and material heuristic.
    if board.fullmove_number < 12:
        return "opening"
    
    # Count material (valuing Q=9, R=5, B=3, N=3)
    material = 0
    for piece_type, value in [(chess.QUEEN, 9), (chess.ROOK, 5), (chess.BISHOP, 3), (chess.KNIGHT, 3)]:
        material += len(board.pieces(piece_type, chess.WHITE)) * value
        material += len(board.pieces(piece_type, chess.BLACK)) * value
        
    if material < 26: # Roughly endgame if both sides lost queens + some minor pieces
        return "endgame"
    return "middlegame"

def classify_move(cpl: float, phase: str):
    if cpl <= 15: return "best"
    if cpl <= 40: return "inaccuracy"
    if cpl <= 100: return "mistake"
    return "blunder"

def run_analysis(game_id: str, stockfish_path: str = "stockfish"):
    db = SessionLocal()
    game_record = db.query(Game).filter(Game.game_id == game_id).first()
    if not game_record or not game_record.raw_pgn:
        db.close()
        return False
        
    existing = db.query(Move).filter(Move.game_id == game_id).first()
    if existing:
        db.close()
        return True 
        
    pgn_io = io.StringIO(game_record.raw_pgn)
    game = chess.pgn.read_game(pgn_io)
    
    if not game:
        db.close()
        return False
        
    try:
        fallback_path = os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WinGet\Packages\Stockfish.Stockfish_Microsoft.Winget.Source_8wekyb3d8bbwe\stockfish\stockfish-windows-x86-64-universal.exe")
        engine_path = stockfish_path if os.path.exists(stockfish_path) else fallback_path
        
        try:
            engine = chess.engine.SimpleEngine.popen_uci(engine_path)
        except:
            engine = chess.engine.SimpleEngine.popen_uci("stockfish")

        board = game.board()
        prev_eval = 0.0 # Standard start is 0.0
        
        # We need to analyze the starting position to get the true initial eval
        start_info = engine.analyse(board, chess.engine.Limit(depth=12))
        start_score = start_info["score"].white()
        prev_eval = 10000.0 if start_score.is_mate() else float(start_score.score())

        last_clock = {chess.WHITE: None, chess.BLACK: None}

        for node in game.mainline():
            move = node.move
            ply = board.ply()
            
            # Get SAN before pushing the move
            move_san = board.san(move)
            
            # Clock parsing
            clock = node.clock()
            time_spent = None
            if clock is not None:
                color = board.turn
                if last_clock[color] is not None:
                    time_spent = last_clock[color] - clock
                last_clock[color] = clock
            
            board.push(move)
            
            # Shallow depth for speed during bulk analysis
            info = engine.analyse(board, chess.engine.Limit(depth=12))
            score = info["score"].white()
            
            current_eval = 0.0
            if score.is_mate():
                current_eval = 10000.0 if score.mate() > 0 else -10000.0
            else:
                current_eval = float(score.score())
                
            # Calculate CPL correctly. 
            # If white moved (ply was even), white wants current_eval > prev_eval. Loss = prev_eval - current_eval
            # If black moved (ply was odd), black wants current_eval < prev_eval. Loss = current_eval - prev_eval
            is_white_move = (ply % 2 == 0)
            
            if is_white_move:
                cpl = prev_eval - current_eval
            else:
                cpl = current_eval - prev_eval
                
            # Ensure CPL is not negative (can happen due to horizon effect)
            cpl = max(0, cpl)
            
            phase = get_game_phase(board)
            classification = classify_move(cpl, phase)
            is_book = (ply < 10) # Naive book check
            
            mistake_type = None
            if classification in ["blunder", "mistake"]:
                if time_spent is not None and clock is not None and clock < 30:
                    mistake_type = "time_pressure"
                elif abs(prev_eval) > 500 and abs(current_eval) < 300:
                    mistake_type = "missed_win"
                elif cpl >= 300:
                    mistake_type = "hanging_piece"
                elif cpl >= 150:
                    mistake_type = "missed_tactic"
            
            # Win Probability
            wp_before = cp_to_wp(prev_eval)
            wp_after = cp_to_wp(current_eval)
            wp_loss = max(0, wp_before - wp_after if is_white_move else wp_after - wp_before)

            new_move = Move(
                game_id=game_id,
                ply=ply + 1,
                move_san=move_san,
                move_uci=move.uci(),
                clock_seconds_remaining=clock,
                time_spent_on_move=time_spent,
                eval_before_cp=prev_eval,
                eval_after_cp=current_eval,
                centipawn_loss=cpl,
                win_prob_before=wp_before,
                win_prob_after=wp_after,
                win_prob_loss=wp_loss,
                classification=classification,
                mistake_type=mistake_type,
                blunder_punished=None, # To be determined in the next ply
                is_book=is_book,
                game_phase=phase
            )
            db.add(new_move)
            
            # If the PREVIOUS move was a blunder, did we punish it?
            if ply > 1:
                # The previous move made by the opponent is at ply - 1 (1-indexed ply)
                # But our Move objects are ply+1.
                # Let's just do a simple DB update later or leave it None for now.
                pass
            
            prev_eval = current_eval
            
        # Update game ply count
        game_record.ply_count = board.ply()
        db.commit()
        engine.quit()
        
    except Exception as e:
        print(f"Engine analysis failed for {game_id}: {e}")
        db.rollback()
        return False
    finally:
        db.close()
        
    return True
