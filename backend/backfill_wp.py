import math
import sqlite3
from sqlalchemy.orm import Session
from database import SessionLocal, Move

def cp_to_wp(cp):
    """
    Standard Lichess Win Probability formula.
    WP = 50 + 50 * (2 / (1 + exp(-0.00368208 * cp)) - 1)
    """
    if cp is None:
        return None
    # clamp cp between -10000 and 10000 to prevent overflow
    cp = max(min(cp, 10000), -10000)
    try:
        wp = 50 + 50 * (2 / (1 + math.exp(-0.00368208 * cp)) - 1)
        return wp
    except OverflowError:
        return 100.0 if cp > 0 else 0.0

def migrate_and_backfill():
    # 1. Run raw ALTER TABLE to safely add columns if they don't exist
    conn = sqlite3.connect('chess_coach.db')
    try:
        conn.execute('ALTER TABLE moves ADD COLUMN win_prob_before FLOAT')
        conn.execute('ALTER TABLE moves ADD COLUMN win_prob_after FLOAT')
        conn.execute('ALTER TABLE moves ADD COLUMN win_prob_loss FLOAT')
        conn.commit()
    except sqlite3.OperationalError:
        # Columns likely already exist
        pass
    finally:
        conn.close()

    # 2. Compute WP for all moves using SQLAlchemy
    db: Session = SessionLocal()
    print("Fetching moves for WP backfill...")
    moves = db.query(Move).filter(Move.eval_before_cp.isnot(None), Move.win_prob_loss.is_(None)).all()
    
    total = len(moves)
    print(f"Backfilling {total} moves...")
    
    batch_size = 10000
    for i, move in enumerate(moves):
        # eval_before_cp is always from White's perspective
        wp_before = cp_to_wp(move.eval_before_cp)
        wp_after = cp_to_wp(move.eval_after_cp)
        
        move.win_prob_before = wp_before
        move.win_prob_after = wp_after
        
        # Calculate loss from the moving player's perspective
        # If white moved (ply % 2 != 0), white wanted WP to stay high. Loss = wp_before - wp_after
        # If black moved (ply % 2 == 0), black wanted WP to stay low. Loss = wp_after - wp_before
        is_white_move = (move.ply % 2 != 0)
        
        if is_white_move:
            loss = wp_before - wp_after
        else:
            loss = wp_after - wp_before
            
        move.win_prob_loss = max(0, loss)
        
        if i % batch_size == 0 and i > 0:
            db.commit()
            print(f"Processed {i}/{total} moves")
            
    db.commit()
    db.close()
    print("Backfill complete.")

if __name__ == "__main__":
    migrate_and_backfill()
