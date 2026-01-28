#!/bin/bash

# Quick Start: User Simulation Setup

echo "======================================================================"
echo "User Simulation Setup"
echo "======================================================================"
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "⚠️  .env file not found"
    echo "Creating .env template..."
    echo "GEMINI_API_KEY=your_gemini_api_key_here" >> .env
    echo ""
    echo "📝 Please add your Gemini API key to .env file"
    echo "   Get your key from: https://makersuite.google.com/app/apikey"
    exit 1
fi

# Check if GEMINI_API_KEY is set
if ! grep -q "GEMINI_API_KEY=" .env || grep -q "GEMINI_API_KEY=your_gemini_api_key_here" .env; then
    echo "⚠️  GEMINI_API_KEY not set in .env file"
    echo "   Get your key from: https://makersuite.google.com/app/apikey"
    exit 1
fi

echo "✅ Environment configured"
echo ""

# Install dependencies
echo "📦 Installing dependencies..."
pip install -q google-genai python-dotenv httpx qdrant-client

echo "✅ Dependencies installed"
echo ""

# Check services
echo "🔍 Checking services..."

# Check V2 search server
if curl -s http://localhost:8002/docs > /dev/null 2>&1; then
    echo "  ✅ V2 Search server running (port 8002)"
else
    echo "  ⚠️  V2 Search server not running"
    echo "     Start it: cd search_engine_v2/search_engine && python server.py"
fi

# Check events server  
if curl -s http://localhost:8000/docs > /dev/null 2>&1; then
    echo "  ✅ Events server running (port 8000)"
else
    echo "  ⚠️  Events server not running"
    echo "     Start it: python server.py"
fi

echo ""
echo "======================================================================"
echo "Setup Complete!"
echo "======================================================================"
echo ""
echo "Quick test (3 sessions):"
echo "  python user_simulation/simulator.py"
echo ""
echo "Generate training data (50 sessions):"
echo "  python user_simulation/generate_training_data.py"
echo ""
echo "Custom generation:"
echo "  python user_simulation/generate_training_data.py --sessions 100"
echo ""
echo "======================================================================"
