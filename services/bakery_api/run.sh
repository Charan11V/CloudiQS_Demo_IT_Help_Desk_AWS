#!/bin/bash

# Agentic Bakery Pro - Run Script

echo "🚀 Starting Agentic Bakery Pro IT Helpdesk API..."
echo ""

# Check if Docker is available
if command -v docker-compose &> /dev/null; then
    echo "📦 Using Docker Compose..."
    docker-compose up --build
else
    echo "🐍 Using local Python..."
    
    # Check if virtual environment exists
    if [ ! -d "venv" ]; then
        echo "Creating virtual environment..."
        python -m venv venv
    fi
    
    # Activate virtual environment
    source venv/bin/activate || . venv/Scripts/activate
    
    # Install dependencies
    echo "Installing dependencies..."
    pip install -r requirements.txt
    
    # Copy env file if not exists
    if [ ! -f ".env" ]; then
        cp .env.example .env
        echo "Created .env file from template"
    fi
    
    # Seed database
    echo "Seeding database..."
    python -m app.seed --reset
    
    # Run server
    echo ""
    echo "✅ Starting server on http://localhost:8000"
    echo "📖 API docs: http://localhost:8000/docs"
    echo ""
    uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
fi
