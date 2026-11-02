@echo off
REM Agentic Bakery Pro - Run Script (Windows)

echo Starting Agentic Bakery Pro IT Helpdesk API...
echo.

REM Check if Docker is available
docker-compose --version >nul 2>&1
if %errorlevel% == 0 (
    echo Using Docker Compose...
    docker-compose up --build
) else (
    echo Using local Python...
    
    REM Check if virtual environment exists
    if not exist "venv" (
        echo Creating virtual environment...
        python -m venv venv
    )
    
    REM Activate virtual environment
    call venv\Scripts\activate.bat
    
    REM Install dependencies
    echo Installing dependencies...
    pip install -r requirements.txt
    
    REM Copy env file if not exists
    if not exist ".env" (
        copy .env.example .env
        echo Created .env file from template
    )
    
    REM Seed database
    echo Seeding database...
    python -m app.seed --reset
    
    REM Run server
    echo.
    echo Starting server on http://localhost:8000
    echo API docs: http://localhost:8000/docs
    echo.
    uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
)
