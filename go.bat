@echo off
setlocal

REM Resolve project root from script location and move there.
cd /d "%~dp0"

echo Starting backend in APP_ENV=go mode...
echo.

cd backend
set APP_ENV=go
call .venv\Scripts\activate.bat

echo Virtual environment activated
echo APP_ENV=%APP_ENV%
echo Starting uvicorn server on http://localhost:8001
echo.

cd ..
python -m uvicorn backend.main:app --reload --port 8001
