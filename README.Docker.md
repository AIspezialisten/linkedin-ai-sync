# 🐳 Docker Setup for LinkedIn-CRM AI Sync with Web Interface

This document provides complete instructions for running the LinkedIn-CRM AI synchronization system with web interface using Docker.

## 🚀 Quick Start

### 1. Prerequisites

- Docker Engine 20.10+
- Docker Compose 2.0+
- **Ollama running on host** with mistral-small:24b model
- At least 2GB free disk space (for application data)
- 4GB+ RAM recommended

### 2. Environment Setup

Copy the environment template and fill in your credentials:

```bash
cp .env.example .env
```

Edit `.env` with your actual credentials:

```bash
# LinkedIn API Configuration
LINKEDIN_ACCESS_TOKEN=your_linkedin_oauth_token_here

# Microsoft Dynamics CRM Configuration
DYNAMICS_TENANT_ID=your_tenant_id_here
DYNAMICS_CLIENT_ID=your_client_id_here
DYNAMICS_CLIENT_SECRET=your_client_secret_here
DYNAMICS_CRM_URL=https://your-org.crm4.dynamics.com

# AI Configuration (connects to host Ollama server)
OLLAMA_MODEL=mistral-small:24b
OLLAMA_HOST=http://host.docker.internal:11434
OPENAI_API_KEY=ollama

# Web Interface Configuration (pre-configured for Docker)
WEB_HOST=0.0.0.0
WEB_PORT=19000
DATABASE_URL=sqlite:///data/duplicates.db
```

### 3. Setup Host Ollama (Required)

Ensure Ollama is running on your host system:

```bash
# Install Ollama (if not already installed)
curl -fsSL https://ollama.ai/install.sh | sh

# Start Ollama server
ollama serve

# Download required model (in another terminal)
ollama pull mistral-small:24b

# Verify Ollama is accessible
curl http://localhost:11434/api/tags
```

### 4. Start the System

```bash
# Option 1: Using Make commands (recommended)
make up          # Start all services
make logs        # View logs
make status      # Check status

# Option 2: Using docker-compose directly
docker-compose up -d
docker-compose logs -f
docker-compose ps
```

### 5. Access the Web Interface

Once the services are running, access the web interface:

- **🌐 Web Dashboard**: http://localhost:19000
- **📊 Duplicates Management**: http://localhost:19000/duplicates
- **📖 API Documentation**: http://localhost:19000/docs
- **🔧 Health Check**: http://localhost:19000/api/health

The web interface provides:
- Interactive dashboard with statistics
- Side-by-side duplicate contact comparison
- One-click CRM updates with field selection
- Mobile-responsive design
- Real-time session tracking

## 🏗️ Architecture

The Docker setup includes one main service that connects to host Ollama:

### 📱 `linkedin-sync` 
- Main application container
- Python 3.11 with uv package manager and Node.js
- Contains all LinkedIn-CRM sync logic
- AI duplicate detection system
- Runs multiple MCP servers:
  - LinkedIn MCP Server (port 8001)
  - Microsoft Dynamics CRM MCP Server (port 8002)
  - Official Playwright MCP Server (port 8003)

### 🧠 Host Ollama Server
- Ollama running on host system (not in container)
- Hosts mistral-small:24b model
- Accessible via `host.docker.internal:11434`
- Container connects to host Ollama for AI processing

## 🎮 Usage Commands

### Connect to the Application Container

```bash
# Enter interactive shell
docker-compose exec linkedin-sync bash

# Or run commands directly
docker-compose exec linkedin-sync uv run linkedin-sync --help
```

### Test the System

```bash
# Test connectivity to LinkedIn and CRM
docker-compose exec linkedin-sync uv run linkedin-sync test-connectivity

# Test AI duplicate detection
docker-compose exec linkedin-sync uv run linkedin-sync test-ai-detection

# Test Playwright web automation
docker-compose exec linkedin-sync uv run linkedin-sync test-playwright

# List LinkedIn contacts
docker-compose exec linkedin-sync uv run python count_connections.py

# List CRM contacts  
docker-compose exec linkedin-sync uv run python list_crm_contacts_simple.py

# Show AI duplicate detection example
docker-compose exec linkedin-sync uv run python show_duplicate_details.py

# Check MCP server status
docker-compose exec linkedin-sync uv run linkedin-sync mcp-status
```

### Monitor AI Model Download

The first startup downloads the ~14GB mistral-small:24b model:

```bash
# Check download progress
docker-compose logs -f model-downloader

# Check available models in Ollama
docker-compose exec ollama ollama list
```

## 📊 Data Persistence

The setup includes persistent volumes:

- **`linkedin-sync-ollama-data`**: Stores AI models (~15GB)
- **`linkedin-sync-app-data`**: Stores application data and logs

```bash
# View volume usage
docker volume ls | grep linkedin-sync

# Inspect volume details
docker volume inspect linkedin-sync-ollama-data
```

## 🔧 Development Mode

For development, the source code is mounted as a volume:

```bash
# Edit files on host, changes reflect in container
# Volume mount: .:/app (see docker-compose.yml)

# Restart after code changes
docker-compose restart linkedin-sync
```

## 🛠️ Troubleshooting

### Check Service Health

```bash
# View all service status
docker-compose ps

# Check specific service logs
docker-compose logs linkedin-sync
docker-compose logs ollama
docker-compose logs model-downloader
```

### AI Model Issues

```bash
# Check if model is downloaded
docker-compose exec ollama ollama list

# Manually download model
docker-compose exec ollama ollama pull mistral-small:24b

# Test Ollama directly
curl http://localhost:11434/api/tags
```

### Network Connectivity

```bash
# Test internal network connectivity
docker-compose exec linkedin-sync curl http://ollama:11434/api/tags

# Check container networking
docker network inspect linkedin-sync-network
```

### Reset Everything

```bash
# Stop all services
docker-compose down

# Remove volumes (WARNING: Deletes AI models)
docker-compose down -v

# Rebuild from scratch
docker-compose build --no-cache
docker-compose up -d
```

## 🚦 Performance Notes

### First Startup
- Initial build: ~5-10 minutes
- Model download: ~30-60 minutes (14GB download)
- Total first-run time: ~45-70 minutes

### Resource Usage
- **CPU**: Moderate during AI inference
- **RAM**: 4-6GB during operation
- **Disk**: ~16GB total (models + containers)
- **Network**: Outbound for API calls

### Production Considerations
- Use specific image tags instead of `latest`
- Configure log rotation
- Set resource limits in docker-compose.yml
- Use secrets management for credentials
- Consider using Docker Swarm or Kubernetes for scaling

## 🔐 Security

### Environment Variables
- Never commit `.env` files
- Use Docker secrets in production
- Rotate API tokens regularly

### Container Security
- Runs as non-root user (`app`)
- Minimal attack surface
- Network isolation between services

### Data Protection
- Persistent volumes are isolated
- No sensitive data in logs
- API tokens passed via environment only

## 📝 Useful Docker Commands

```bash
# View resource usage
docker stats

# Clean up unused resources
docker system prune -f

# View detailed container info
docker-compose exec linkedin-sync env
docker-compose exec linkedin-sync ps aux

# Backup volumes
docker run --rm -v linkedin-sync-ollama-data:/data -v $(pwd):/backup alpine tar czf /backup/ollama-backup.tar.gz /data

# Monitor logs in real-time
docker-compose logs -f --tail=50
```

## 🎯 Next Steps

Once running successfully:

1. **Configure your credentials** in `.env`
2. **Test connectivity** to LinkedIn and CRM APIs
3. **Run AI duplicate detection** tests
4. **Explore the CLI commands** for synchronization
5. **Set up monitoring** for production use

For detailed API documentation and advanced usage, see `CLAUDE.md`.