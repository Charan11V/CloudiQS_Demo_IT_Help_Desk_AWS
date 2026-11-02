@echo off
REM Agentic Bakery Web - Quick Start Script (Windows)

echo.
echo 🥐 Agentic Bakery Pro - Web UI Setup
echo ====================================
echo.

REM Check if Node.js is installed
where node >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo ❌ Node.js is not installed. Please install Node.js 20+ first.
    pause
    exit /b 1
)

echo ✓ Node.js is installed
node --version
echo.

REM Check if backend is running
echo 🔍 Checking backend API at http://localhost:8002...
curl -s http://localhost:8002/health >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    echo ✓ Backend API is running
) else (
    echo ⚠️  Backend API is not responding at http://localhost:8002
    echo    Make sure the bakery_api service is running first!
)
echo.

REM Install dependencies
if not exist "node_modules" (
    echo 📦 Installing dependencies...
    call npm install
) else (
    echo ✓ Dependencies already installed
)
echo.

REM Create .env.local if it doesn't exist
if not exist ".env.local" (
    echo 📝 Creating .env.local...
    if exist ".env.example" (
        copy .env.example .env.local >nul
    ) else (
        echo # Local environment variables > .env.local
    )
) else (
    echo ✓ .env.local exists
)
echo.

echo 🚀 Starting development server...
echo.
echo    Frontend: http://localhost:3000
echo    Backend:  http://localhost:8002
echo.
echo Demo Personas (Northstar):
echo   • NS-001 (Asha Rao) - Employee
echo   • NS-002 (Rahul Sharma) - IT Engineer
echo.

call npm run dev
