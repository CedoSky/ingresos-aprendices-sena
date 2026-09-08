@echo off
cd /d "%~dp0"
set "PYTHON=%~dp0..\.venv\Scripts\python.exe"

echo Starting Flask development server...
"%PYTHON%" app.py
