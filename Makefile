# 🚀 LinkedIn-CRM AI Sync - Docker Commands

.PHONY: help build up down logs status clean test shell

# Default target
help: ## Show this help message
	@echo "🤖 LinkedIn-CRM AI Sync - Docker Commands"
	@echo "========================================"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# 🏗️ Build and Setup
build: ## Build Docker images
	@echo "🏗️ Building Docker images..."
	docker-compose build

setup: ## Copy .env.example to .env (if not exists)
	@if [ ! -f .env ]; then \
		echo "📝 Creating .env from template..."; \
		cp .env.example .env; \
		echo "✅ .env created! Please edit it with your credentials."; \
	else \
		echo "ℹ️  .env already exists"; \
	fi

# 🚀 Service Management
up: setup ## Start all services
	@echo "🚀 Starting LinkedIn-CRM AI Sync system..."
	docker-compose up -d
	@echo "✅ Services started! Use 'make logs' to view output."

down: ## Stop all services
	@echo "🛑 Stopping all services..."
	docker-compose down

restart: ## Restart all services
	@echo "🔄 Restarting services..."
	docker-compose restart

# 📊 Monitoring
logs: ## Show logs from all services
	@echo "📊 Showing logs (Ctrl+C to exit)..."
	docker-compose logs -f

status: ## Show service status
	@echo "📋 Service Status:"
	@docker-compose ps

health: ## Check health of all services
	@echo "🏥 Health Check:"
	@docker-compose exec ollama curl -s http://localhost:11434/api/tags > /dev/null && echo "✅ Ollama: Healthy" || echo "❌ Ollama: Unhealthy"
	@docker-compose exec linkedin-sync python -c "import sys; print('✅ LinkedIn-Sync: Healthy')" 2>/dev/null || echo "❌ LinkedIn-Sync: Unhealthy"

# 🧪 Testing
test: ## Run connectivity tests
	@echo "🧪 Running connectivity tests..."
	docker-compose exec linkedin-sync uv run linkedin-sync test-connectivity

test-ai: ## Test AI duplicate detection
	@echo "🤖 Testing AI duplicate detection..."
	docker-compose exec linkedin-sync uv run linkedin-sync test-ai-detection

test-playwright: ## Test Playwright MCP server
	@echo "🎭 Testing Playwright MCP server..."
	docker-compose exec linkedin-sync uv run linkedin-sync test-playwright

test-linkedin: ## List LinkedIn contacts
	@echo "📱 Listing LinkedIn contacts..."
	docker-compose exec linkedin-sync uv run python count_connections.py

test-crm: ## List CRM contacts
	@echo "📋 Listing CRM contacts..."
	docker-compose exec linkedin-sync uv run python list_crm_contacts_simple.py

demo: ## Show AI duplicate detection demo
	@echo "🎯 Running AI duplicate detection demo..."
	docker-compose exec linkedin-sync uv run python show_duplicate_details.py

mcp-status: ## Show MCP server status
	@echo "🤖 Checking MCP server status..."
	docker-compose exec linkedin-sync uv run linkedin-sync mcp-status

scrape-profiles: ## Scrape LinkedIn profiles with AI (interactive)
	@echo "🕷️ Starting AI-powered LinkedIn profile scraping..."
	docker-compose exec linkedin-sync uv run linkedin-sync scrape-profiles

scrape-sample: ## Scrape first 5 LinkedIn profiles for testing
	@echo "🧪 Scraping first 5 profiles for testing..."
	docker-compose exec linkedin-sync uv run linkedin-sync scrape-profiles --max-profiles 5 --delay 2.0

# 🛠️ Development
shell: ## Open interactive shell in main container
	@echo "🐚 Opening shell in linkedin-sync container..."
	docker-compose exec linkedin-sync bash

dev: ## Start in development mode with file watching
	@echo "👨‍💻 Starting development environment..."
	docker-compose up -d
	@echo "📁 Code changes will be reflected automatically"
	@echo "🐚 Use 'make shell' to access the container"

# 🧹 Cleanup
clean: ## Remove stopped containers and unused images
	@echo "🧹 Cleaning up Docker resources..."
	docker-compose down
	docker system prune -f

clean-volumes: ## Remove all volumes (WARNING: Deletes AI models!)
	@echo "⚠️  WARNING: This will delete all AI models (~14GB)"
	@read -p "Are you sure? [y/N] " -n 1 -r; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		echo ""; \
		echo "🗑️  Removing volumes..."; \
		docker-compose down -v; \
		echo "✅ Volumes removed"; \
	else \
		echo ""; \
		echo "❌ Cancelled"; \
	fi

reset: clean-volumes build up ## Complete reset: remove everything and rebuild

# 🔍 Debugging
debug-ollama: ## Debug Ollama service
	@echo "🔍 Ollama Debug Information:"
	@echo "📊 Service Status:"
	@docker-compose ps ollama
	@echo "📝 Recent Logs:"
	@docker-compose logs --tail=20 ollama
	@echo "🤖 Available Models:"
	@docker-compose exec ollama ollama list || echo "❌ Cannot connect to Ollama"

debug-app: ## Debug main application
	@echo "🔍 Application Debug Information:"
	@echo "📊 Service Status:"
	@docker-compose ps linkedin-sync
	@echo "📝 Recent Logs:"
	@docker-compose logs --tail=20 linkedin-sync
	@echo "🌍 Environment Variables:"
	@docker-compose exec linkedin-sync env | grep -E "(LINKEDIN|DYNAMICS|OLLAMA)" || echo "❌ Cannot access container"

debug-network: ## Debug network connectivity
	@echo "🔍 Network Debug Information:"
	@echo "🌐 Network Details:"
	@docker network inspect linkedin-sync-network
	@echo "🔗 Container Connectivity:"
	@docker-compose exec linkedin-sync curl -s http://ollama:11434/api/tags > /dev/null && echo "✅ linkedin-sync → ollama: OK" || echo "❌ linkedin-sync → ollama: FAIL"

# 📦 Model Management
download-model: ## Download AI model manually
	@echo "📥 Downloading mistral-small:24b model..."
	docker-compose exec ollama ollama pull mistral-small:24b

model-info: ## Show AI model information
	@echo "🤖 AI Model Information:"
	@docker-compose exec ollama ollama list
	@echo "💾 Storage Usage:"
	@docker volume inspect linkedin-sync-ollama-data | grep -A 5 "Mountpoint"

# 🚀 Quick Actions
quick-test: up ## Quick start and test everything
	@echo "⏳ Waiting for services to be ready..."
	@sleep 10
	@make health
	@make test
	@make test-ai

# 📚 Documentation
docs: ## Show available commands and help
	@echo "📚 Available Documentation:"
	@echo "  📄 README.Docker.md - Complete Docker setup guide"
	@echo "  📄 CLAUDE.md - Detailed API and development docs"
	@echo "  📄 .env.example - Environment configuration template"
	@echo ""
	@echo "🔗 Quick Links:"
	@echo "  🌐 Repository: https://github.com/AIspezialisten/linkedin-ai-sync"
	@echo "  🤖 Ollama UI: http://localhost:11434"