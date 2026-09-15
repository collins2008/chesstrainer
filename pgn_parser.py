import chess.pgn
import argparse
from collections import defaultdict

def analyze_openings(pgn_path, username):
    # Data structure: opening_name -> {'wins': 0, 'losses': 0, 'draws': 0, 'as_white': 0, 'as_black': 0}
    stats = defaultdict(lambda: {'wins': 0, 'losses': 0, 'draws': 0, 'as_white': 0, 'as_black': 0})
    
    total_games = 0
    with open(pgn_path, encoding="utf-8") as pgn_file:
        while True:
            game = chess.pgn.read_game(pgn_file)
            if game is None:
                break
            
            headers = game.headers
            white = headers.get("White")
            black = headers.get("Black")
            result = headers.get("Result")
            
            opening = headers.get("Opening")
            if not opening and "ECOUrl" in headers:
                url_part = headers["ECOUrl"].split("/")[-1]
                opening = url_part.replace("-", " ")
            if not opening:
                opening = "Unknown Opening"
                
            if username not in (white, black):
                continue
                
            total_games += 1
            
            is_white = (username == white)
            
            if is_white:
                stats[opening]['as_white'] += 1
                if result == '1-0':
                    stats[opening]['wins'] += 1
                elif result == '0-1':
                    stats[opening]['losses'] += 1
                else:
                    stats[opening]['draws'] += 1
            else:
                stats[opening]['as_black'] += 1
                if result == '0-1':
                    stats[opening]['wins'] += 1
                elif result == '1-0':
                    stats[opening]['losses'] += 1
                else:
                    stats[opening]['draws'] += 1

    print(f"Total games analyzed for {username}: {total_games}")
    print("\n--- Opening Win/Loss Distribution ---")
    
    # Sort by total games played in that opening
    sorted_openings = sorted(stats.items(), key=lambda x: (x[1]['wins'] + x[1]['losses'] + x[1]['draws']), reverse=True)
    
    for opening, data in sorted_openings[:20]: # Show top 20 for brevity
        total = data['wins'] + data['losses'] + data['draws']
        win_rate = (data['wins'] / total) * 100 if total > 0 else 0
        print(f"{opening}:")
        print(f"  Total Games: {total} (White: {data['as_white']}, Black: {data['as_black']})")
        print(f"  Wins: {data['wins']} | Losses: {data['losses']} | Draws: {data['draws']}")
        print(f"  Win Rate: {win_rate:.2f}%")
        print("-" * 40)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Analyze Chess Openings from PGN")
    parser.add_argument("pgn_file", help="Path to the PGN file")
    parser.add_argument("username", help="Your chess username")
    args = parser.parse_args()
    
    analyze_openings(args.pgn_file, args.username)
