#!/bin/bash
set -e

echo "🚀 Starting LinkedIn-CRM AI Sync System"
echo "=================================="

# Check if required environment variables are set
if [ -z "$LINKEDIN_ACCESS_TOKEN" ]; then
    echo "⚠️  Warning: LINKEDIN_ACCESS_TOKEN not set"
fi

if [ -z "$DYNAMICS_CLIENT_SECRET" ]; then
    echo "⚠️  Warning: DYNAMICS_CLIENT_SECRET not set"
fi

# Wait for Ollama to be ready (on host)
echo "🔍 Checking Ollama connection..."
OLLAMA_URL="${OLLAMA_HOST:-http://localhost:11434}"
for i in {1..30}; do
    if curl -s "${OLLAMA_URL}/api/tags" > /dev/null 2>&1; then
        echo "✅ Ollama is ready at ${OLLAMA_URL}!"
        break
    fi
    echo "⏳ Waiting for Ollama... ($i/30)"
    sleep 2
done

# Check if mistral-small:24b model is available
echo "🤖 Checking AI model availability..."
if curl -s "${OLLAMA_URL}/api/tags" | grep -q "mistral-small:24b"; then
    echo "✅ mistral-small:24b model is available!"
else
    echo "⚠️  mistral-small:24b model not found. Please ensure it's installed on the host:"
    echo "    ollama pull mistral-small:24b"
fi

# Start MCP Server Manager in background
echo "🤖 Starting MCP Server Manager..."
python /app/services/mcp_manager.py &
MCP_MANAGER_PID=$!

# Give MCP servers time to start
echo "⏳ Waiting for MCP servers to initialize..."
sleep 5

# Check MCP server status
echo "📊 MCP Server Status:"
python /app/services/mcp_manager.py status

echo ""
echo "🎯 LinkedIn-CRM AI Sync System is ready!"
echo ""
echo "Available commands:"
echo "  🧪 Test connectivity:     uv run linkedin-sync test-connectivity"
echo "  🤖 Test AI detection:     uv run linkedin-sync test-ai-detection"
echo "  🎭 Test Playwright:       uv run linkedin-sync test-playwright"
echo "  📊 List LinkedIn contacts: uv run python count_connections.py"
echo "  📋 List CRM contacts:     uv run python list_crm_contacts_simple.py"
echo "  🔄 Show duplicate example: uv run python show_duplicate_details.py"
echo "  🕷️ Scrape profiles (AI):   uv run linkedin-sync scrape-profiles"
echo "  📈 View scraped data:     uv run python view_scraped_profiles.py"
echo "  🌐 MCP server status:     uv run linkedin-sync mcp-status"
echo ""
echo "For help: uv run linkedin-sync --help"
echo ""

# Setup cleanup trap
cleanup() {
    echo "🧹 Cleaning up MCP servers..."
    kill $MCP_MANAGER_PID 2>/dev/null || true
    wait $MCP_MANAGER_PID 2>/dev/null || true
}
trap cleanup EXIT

# Execute the command passed to the script
exec "$@"