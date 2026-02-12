@echo off
echo Starting AI Advisor Backend Server...
echo.

cd backend
call .venv\Scripts\activate.bat

echo Virtual environment activated
echo Starting uvicorn server on http://localhost:8001
echo.

cd ..
python -m uvicorn backend.main:app --reload --port 8001
