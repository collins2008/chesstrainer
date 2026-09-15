@echo off
echo Starting AI Chess Coach...

echo Starting FastAPI Backend...
start cmd /k "cd backend && uvicorn main:app --reload"

echo Starting Next.js Frontend...
start cmd /k "cd frontend && npm run dev"

echo Both servers are starting. You can access the PWA at http://localhost:3000
