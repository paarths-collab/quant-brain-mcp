@echo off
set PYTHONUNBUFFERED=1
set PYTHONPATH=%~dp0
call "%~dp0.venv\Scripts\activate.bat"
python "%~dp0main.py"
