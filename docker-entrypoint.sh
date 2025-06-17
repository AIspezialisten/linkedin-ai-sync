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

# Wait for Ollama to be ready
echo "🔍 Checking Ollama connection..."
for i in {1..30}; do
    if curl -s http://ollama:11434/api/tags > /dev/null 2>&1; then
        echo "✅ Ollama is ready!"
        break
    fi
    echo "⏳ Waiting for Ollama... ($i/30)"
    sleep 2
done

# Check if mistral-small:24b model is available
echo "🤖 Checking AI model availability..."
if curl -s http://ollama:11434/api/tags | grep -q "mistral-small:24b"; then
    echo "✅ mistral-small:24b model is available!"
else
    echo "⚠️  mistral-small:24b model not found. It may still be downloading."
    echo "    You can check progress with: docker-compose logs model-downloader"
fi

echo "🎯 LinkedIn-CRM AI Sync System is ready!"
echo ""
echo "Available commands:"
echo "  🧪 Test connectivity:     uv run linkedin-sync test-connectivity"
echo "  🤖 Test AI detection:     uv run linkedin-sync test-ai-detection"  
echo "  📊 List LinkedIn contacts: uv run python count_connections.py"
echo "  📋 List CRM contacts:     uv run python list_crm_contacts_simple.py"
echo "  🔄 Show duplicate example: uv run python show_duplicate_details.py"
echo ""
echo "For help: uv run linkedin-sync --help"
echo ""

# Execute the command passed to the script
exec "$@"