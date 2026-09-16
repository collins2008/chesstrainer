import os
import json
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy.orm import Session
from database import SessionLocal, Game, Move
import utils
from google import genai
from google.genai import types

router = APIRouter()

CROSS_SESSION_MEMORY = {}

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: List[ChatMessage]

def get_opening_performance(db: Session, username: str, opening_name: str, color: str = "white"):
    games = db.query(Game).filter(
        Game.opening_name.ilike(f"%{opening_name}%"),
        ((Game.white.ilike(username)) if color == "white" else (Game.black.ilike(username)))
    ).all()
    
    if not games:
        return f"No games found for opening '{opening_name}' as {color}."
        
    wins, losses, draws = 0, 0, 0
    for g in games:
        won = (g.result == "1-0" and color == "white") or (g.result == "0-1" and color == "black")
        lost = (g.result == "0-1" and color == "white") or (g.result == "1-0" and color == "black")
        if won: wins += 1
        elif lost: losses += 1
        else: draws += 1
        
    return f"Opening: {opening_name} as {color}. Record: {wins}W - {losses}L - {draws}D. Total games: {len(games)}"

def get_recent_blunders(db: Session, username: str, limit: int = 3):
    games = db.query(Game).filter((Game.white.ilike(username)) | (Game.black.ilike(username))).order_by(Game.date.desc()).limit(10).all()
    game_ids = [g.game_id for g in games]
    
    moves = db.query(Move).filter(Move.game_id.in_(game_ids), Move.classification == "blunder").limit(limit).all()
    
    if not moves:
        return "No recent blunders found."
        
    res = []
    for m in moves:
        res.append(f"Game ID: {m.game_id}, Ply: {m.ply}, Move: {m.move_san}, WP Loss: {m.win_prob_loss}%, Mistake Type: {m.mistake_type}")
        
    return "\n".join(res)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/chat/{username}")
async def chat_with_coach(username: str, req: ChatRequest, db: Session = Depends(get_db)):
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="GEMINI_API_KEY not set")

    features = utils.extract_features(db, username)
    cross_session = CROSS_SESSION_MEMORY.get(username, "No previous session summary.")
    
    system_instruction = f"""
    You are an elite, brutally honest AI Chess Coach.
    Your student is {username}.
    
    [CROSS-SESSION MEMORY]
    {cross_session}
    
    [GROUNDING DATA: CURRENT METRICS]
    - Record: {features['wins']}W - {features['losses']}L - {features['draws']}D ({features['win_rate']}%)
    - Avg WP Loss Per Move: {features['engine_metrics'].get('avg_wp_loss_per_move')}%
    - Complacency Blunders: {features['engine_metrics'].get('complacency_blunders')}
    - Endgame Conversion Rate: {features['engine_metrics'].get('endgame_converted')} won / {features['engine_metrics'].get('endgame_reached_winning')} reached
    
    RULES:
    1. Be direct, honest, and strict. Do not validate bad chess.
    2. Answer ONLY using the grounded data provided or the function-calling tools. Do NOT invent stats.
    3. If asked about a specific opening, game, or recent blunders, USE YOUR TOOLS.
    4. Only Chess.com is the source of truth for their rating goals.
    """

    client = genai.Client(api_key=api_key)
    
    tools = [
        types.FunctionDeclaration(
            name="get_opening_performance",
            description="Get the user's historical performance in a specific opening.",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "opening_name": types.Schema(type=types.Type.STRING),
                    "color": types.Schema(type=types.Type.STRING, description="'white' or 'black'")
                },
                required=["opening_name", "color"]
            )
        ),
        types.FunctionDeclaration(
            name="get_recent_blunders",
            description="Retrieve the user's most recent blunders.",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "limit": types.Schema(type=types.Type.INTEGER)
                }
            )
        )
    ]
    
    gemini_tools = [types.Tool(function_declarations=tools)]
    
    contents = []
    for m in req.messages:
        role = "user" if m.role == "user" else "model"
        contents.append(types.Content(role=role, parts=[types.Part.from_text(text=m.content)]))
        
    try:
        response = client.models.generate_content(
            model='gemini-2.5-pro',
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                tools=gemini_tools,
                temperature=0.4
            )
        )
        
        if response.function_calls:
            call = response.function_calls[0]
            if call.name == "get_opening_performance":
                args = call.args
                result = get_opening_performance(db, username, args.get("opening_name", ""), args.get("color", "white"))
            elif call.name == "get_recent_blunders":
                args = call.args
                result = get_recent_blunders(db, username, args.get("limit", 3))
            else:
                result = "Tool not implemented"
                
            contents.append(response.candidates[0].content)
            contents.append(
                types.Content(
                    role="user",
                    parts=[
                        types.Part.from_function_response(
                            name=call.name,
                            response={"result": result}
                        )
                    ]
                )
            )
            
            final_response = client.models.generate_content(
                model='gemini-2.5-pro',
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    tools=gemini_tools,
                    temperature=0.4
                )
            )
            return {"status": "success", "reply": final_response.text}
        
        return {"status": "success", "reply": response.text}
        
    except Exception as e:
        return {"status": "error", "message": str(e)}
