#!/bin/bash

# Build script for the React frontend

set -e

echo "🔧 Building React frontend for duplicate management..."

# Navigate to frontend directory
cd "$(dirname "$0")/../web/frontend"

# Check if Node.js is available
if ! command -v node &> /dev/null; then
    echo "❌ Node.js is required but not installed."
    echo "Please install Node.js from https://nodejs.org/"
    exit 1
fi

# Check if npm is available
if ! command -v npm &> /dev/null; then
    echo "❌ npm is required but not installed."
    exit 1
fi

echo "📦 Installing frontend dependencies..."
npm install

echo "🏗️  Building production frontend..."
npm run build

echo "✅ Frontend build completed successfully!"
echo "📁 Build files are in: web/frontend/build/"
echo ""
echo "🚀 Start the web server with:"
echo "   uv run python web/start_server.py"