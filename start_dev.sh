#!/bin/bash
# FlakeRadar Local Development Setup

echo "🎯 Setting up FlakeRadar Local Development Environment"

# Install the package in development mode
echo "📦 Installing FlakeRadar in development mode..."
pip install -e .

# Set up environment variables for local development
echo "🔧 Setting up environment variables..."
export FLAKERADAR_TOKEN="flake_tk_local_dev_demo_token123"
export FLAKERADAR_BACKEND_URL="http://localhost:5000"

# Start the local development server in background
echo "🚀 Starting local development server..."
python dev_server.py &
DEV_SERVER_PID=$!

# Wait for server to start
sleep 3

echo ""
echo "✅ FlakeRadar Local Development Environment Ready!"
echo ""
echo "🌐 Dashboard URL: http://localhost:5000/dashboard/local-dev-team"
echo "🔧 API Base URL: http://localhost:5000/api/v1"
echo "💾 Local Database: ~/.flakeradar/local_team_db.sqlite3"
echo ""
echo "🧪 Test the setup:"
echo "   export FLAKERADAR_TOKEN=\"flake_tk_local_dev_demo_token123\""
echo "   flakeradar --project \"TestApp\" --environment \"local\" --results \"src/flakeradar/sample_results/*.xml\""
echo ""
echo "🛑 To stop the dev server: kill $DEV_SERVER_PID"
echo ""

# Save PID for easy cleanup
echo $DEV_SERVER_PID > .dev_server.pid
echo "Development server PID saved to .dev_server.pid"
