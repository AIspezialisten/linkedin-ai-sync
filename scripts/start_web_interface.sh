#!/bin/bash

# Complete startup script for the web interface

set -e

echo "🌐 Starting LinkedIn-CRM Duplicate Management Web Interface..."

# Navigate to project root
cd "$(dirname "$0")/.."

# Check if Python virtual environment is active
if [[ -z "$VIRTUAL_ENV" ]] && [[ ! -f ".venv/bin/activate" ]]; then
    echo "⚠️  No virtual environment detected. Using system Python."
    echo "💡 Consider using: uv sync"
fi

# Load environment variables
if [[ -f ".env" ]]; then
    echo "📄 Loading environment variables from .env"
    export $(grep -v '^#' .env | xargs)
else
    echo "⚠️  No .env file found. Using default configuration."
fi

# Check if frontend is built
if [[ ! -d "web/frontend/build" ]]; then
    echo "🏗️  Frontend not built. Building now..."
    ./scripts/build_frontend.sh
else
    echo "✅ Frontend build found"
fi

# Check required Python dependencies
echo "🔍 Checking Python dependencies..."
if ! python -c "import fastapi, uvicorn, sqlalchemy" 2>/dev/null; then
    echo "❌ Missing required Python dependencies."
    echo "🔧 Installing with: uv sync"
    uv sync
fi

# Start the web server
echo "🚀 Starting web server..."
echo ""

python web/start_server.py