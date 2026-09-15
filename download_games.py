import requests
import berserk
import argparse
import os

def download_chesscom_games(username, output_file):
    print(f"Downloading chess.com games for {username}...")
    headers = {"User-Agent": "MyChessCoachApp/1.0 (contact@example.com)"}
    archives_url = f"https://api.chess.com/pub/player/{username}/games/archives"

    res = requests.get(archives_url, headers=headers)
    if res.status_code != 200:
        print(f"Error fetching archives from chess.com: {res.status_code}")
        return

    archives = res.json().get("archives", [])

    with open(output_file, "w", encoding="utf-8") as outfile:
        for month_url in archives:
            pgn_url = f"{month_url}/pgn"
            print(f"Fetching {pgn_url}...")
            month_res = requests.get(pgn_url, headers=headers)
            if month_res.status_code == 200:
                outfile.write(month_res.text + "\n\n")
    print(f"Chess.com games saved to {output_file}")

def download_lichess_games(username, token, output_file):
    print(f"Downloading lichess games for {username}...")
    session = berserk.TokenSession(token)
    client = berserk.Client(session=session)

    with open(output_file, "w", encoding="utf-8") as f:
        # Use generator to stream games to file
        games_generator = client.games.export_by_user(
            username, as_pgn=True, clocks=True, evals=True
        )
        for game in games_generator:
            f.write(game + "\n\n")
    print(f"Lichess games saved to {output_file}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download games from Chess.com or Lichess")
    parser.add_argument("--platform", choices=["chesscom", "lichess"], required=True, help="Platform to download from")
    parser.add_argument("--username", required=True, help="Your username on the platform")
    parser.add_argument("--output", default="games.pgn", help="Output PGN file name")
    parser.add_argument("--token", help="Lichess API token (required if platform is lichess)")

    args = parser.parse_args()

    if args.platform == "chesscom":
        download_chesscom_games(args.username, args.output)
    elif args.platform == "lichess":
        if not args.token:
            token = os.environ.get("LICHESS_TOKEN")
            if not token:
                print("Error: Lichess token is required. Pass via --token or LICHESS_TOKEN env var.")
                exit(1)
        else:
            token = args.token
        download_lichess_games(args.username, token, args.output)
