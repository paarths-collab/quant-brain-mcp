@echo off
REM Boomerang Startup Script for Windows

echo ========================================
echo 🚀 Starting Boomerang Platform
echo ========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ⚠️  Python is not installed or not in PATH
    echo Please install Python 3.8 or higher
    pause
    exit /b 1
)

REM Check if backend directory exists
if not exist "backend" (
    echo ⚠️  Backend directory not found
    echo Please run this script from the project root
    pause
    exit /b 1
)

REM Start Backend
echo 📡 Starting Backend Server...
cd backend

REM Create virtual environment if it doesn't exist
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
)

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Install dependencies if needed
if not exist "venv\.installed" (
    echo Installing dependencies...
    pip install -r requirements.txt
    echo. > venv\.installed
)

REM Start backend in a new window
echo ✓ Starting FastAPI server on http://localhost:8000
start "Boomerang Backend" cmd /k "venv\Scripts\activate.bat && uvicorn main:app --host 0.0.0.0 --port 8000"

cd ..

REM Wait for backend to start
timeout /t 3 /nobreak >nul

REM Start Frontend
echo.
echo 🌐 Starting Frontend Server...
cd frontend

REM Start frontend server in a new window
echo ✓ Starting frontend on http://localhost:8080
start "Boomerang Frontend" cmd /k "python -m http.server 8080"

cd ..

REM Open browser
timeout /t 2 /nobreak >nul
start http://localhost:8080

echo.
echo ========================================
echo ✓ Boomerang is now running!
echo ========================================
echo.
echo 📊 Frontend:  http://localhost:8080
echo 📡 Backend:   http://localhost:8000
echo 📚 API Docs:  http://localhost:8000/docs
echo.
echo Two command windows have been opened:
echo   - Backend Server (FastAPI)
echo   - Frontend Server (HTTP)
echo.
echo Close those windows to stop the servers.
echo.
pause
