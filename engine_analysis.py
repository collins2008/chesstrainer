import chess.pgn
import chess.engine
import argparse
import os

def analyze_blunders(pgn_path, username, engine_path, target_opening=None, threshold=150):
    print(f"Starting engine analysis for {username}...")
    
    if not os.path.exists(engine_path) and engine_path.lower() != "stockfish":
        print(f"Error: Stockfish engine not found at {engine_path}")
        print("Please ensure you provide the correct path to the stockfish executable using --engine")
        return

    try:
        engine = chess.engine.SimpleEngine.popen_uci(engine_path)
    except Exception as e:
        print(f"Failed to start engine: {e}")
        print("Please make sure Stockfish is installed and the path is correct.")
        return
    
    games_analyzed = 0
    blunders_found = 0
    
    try:
        with open(pgn_path, encoding="utf-8") as pgn_file:
            while True:
                game = chess.pgn.read_game(pgn_file)
                if game is None:
                    break
                
                headers = game.headers
                white = headers.get("White")
                black = headers.get("Black")
                
                if username not in (white, black):
                    continue
                
                opening = headers.get("Opening")
                if not opening and "ECOUrl" in headers:
                    url_part = headers["ECOUrl"].split("/")[-1]
                    opening = url_part.replace("-", " ")
                if not opening:
                    opening = "Unknown Opening"
                    
                if target_opening and target_opening.lower() not in opening.lower():
                    continue
                    
                is_white = (username == white)
                
                # To save time, let's only analyze games you lost or drew
                result = headers.get("Result")
                if (is_white and result == "1-0") or (not is_white and result == "0-1"):
                    continue
                
                board = game.board()
                prev_eval = 0
                
                print(f"\nAnalyzing Game: {white} vs {black} ({opening})")
                
                for move_num, move in enumerate(game.mainline_moves()):
                    board.push(move)
                    
                    # Depth 15 is a sweet spot for speed and decent tactical accuracy
                    info = engine.analyse(board, chess.engine.Limit(depth=15))
                    score = info["score"].white()
                    
                    if score.is_mate():
                        current_eval = 10000 if score.mate() > 0 else -10000
                    else:
                        current_eval = score.score()
                    
                    user_moved = (is_white and move_num % 2 == 0) or (not is_white and move_num % 2 == 1)
                    
                    if user_moved and move_num > 0:
                        eval_diff = current_eval - prev_eval
                        
                        if is_white and eval_diff < -threshold:
                            print(f"  [Blunder!] Move {(move_num // 2) + 1}. {move} | Eval dropped by {abs(eval_diff)} cp (New Eval: {current_eval/100:.2f})")
                            blunders_found += 1
                        elif not is_white and eval_diff > threshold:
                            print(f"  [Blunder!] Move {(move_num // 2) + 1}... {move} | Eval dropped by {abs(eval_diff)} cp (New Eval: {-current_eval/100:.2f})")
                            blunders_found += 1
                            
                    prev_eval = current_eval
                    
                games_analyzed += 1
                
                # Limit to 3 games for demonstration purposes so it doesn't run forever
                if games_analyzed >= 3:
                    print("\nReached limit of 3 games for this run.")
                    break
                    
    finally:
        engine.quit()
        
    print(f"\nAnalysis complete. Analyzed {games_analyzed} games and found {blunders_found} blunders.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Analyze games with Stockfish to find blunders")
    parser.add_argument("pgn_file", help="Path to the PGN file")
    parser.add_argument("username", help="Your chess username")
    parser.add_argument("--engine", default="stockfish", help="Path to Stockfish executable. E.g. C:/stockfish/stockfish-windows-x86-64-avx2.exe")
    parser.add_argument("--opening", help="Filter by a specific opening (e.g., 'Scandinavian Defense')")
    parser.add_argument("--threshold", type=int, default=150, help="Centipawn drop threshold for a blunder (default: 150)")
    
    args = parser.parse_args()
    
    analyze_blunders(args.pgn_file, args.username, args.engine, args.opening, args.threshold)
