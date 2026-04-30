@echo off
REM AI Cake Assistant - Windows Startup Script
REM This script activates the virtual environment and starts the Flask app

echo Checking for virtual environment...
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
)

echo Activating virtual environment...
call venv\Scripts\activate

echo Installing/updating requirements...
pip install -q -r requirements.txt

echo.
echo ========================================
echo  GB Delight - AI Cake Assistant
echo ========================================
echo.
echo Starting Flask application...
echo Open your browser at: http://127.0.0.1:5000
echo.
echo Press Ctrl+C to stop the server
echo.

python app.py
