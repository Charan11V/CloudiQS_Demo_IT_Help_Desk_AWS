#!/bin/bash

# Agentic Bakery Web - Quick Start Script

echo "🥐 Agentic Bakery Pro - Web UI Setup"
echo "===================================="
echo ""

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "❌ Node.js is not installed. Please install Node.js 20+ first."
    exit 1
fi

echo "✓ Node.js version: $(node --version)"
echo ""

# Check if backend is running
echo "🔍 Checking backend API at http://localhost:8002..."
if curl -s http://localhost:8002/health > /dev/null 2>&1; then
    echo "✓ Backend API is running"
else
    echo "⚠️  Backend API is not responding at http://localhost:8002"
    echo "   Make sure the bakery_api service is running first!"
    echo ""
fi

# Install dependencies
if [ ! -d "node_modules" ]; then
    echo "📦 Installing dependencies..."
    npm install
else
    echo "✓ Dependencies already installed"
fi
echo ""

# Create .env.local if it doesn't exist
if [ ! -f ".env.local" ]; then
    echo "📝 Creating .env.local..."
    cp .env.example .env.local 2>/dev/null || echo "# Local environment variables" > .env.local
else
    echo "✓ .env.local exists"
fi
echo ""

echo "🚀 Starting development server..."
echo ""
echo "   Frontend: http://localhost:3000"
echo "   Backend:  http://localhost:8002"
echo ""
echo "Demo Personas (Northstar):"
echo "  • NS-001 (Asha Rao) - Employee"
echo "  • NS-002 (Rahul Sharma) - IT Engineer"
echo ""

npm run dev
