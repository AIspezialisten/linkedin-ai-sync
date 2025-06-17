# LinkedIn-CRM AI Sync

> AI-powered LinkedIn to Microsoft Dynamics CRM synchronization system with intelligent duplicate detection using Ollama and PydanticAI.

## Features

- **LinkedIn Integration**: Connect to LinkedIn Member Snapshot API
- **CRM Integration**: Sync with Microsoft Dynamics CRM via Web API
- **AI Duplicate Detection**: Use local Ollama with mistral-small:24b for intelligent contact matching
- **Confidence Scoring**: HIGH/MEDIUM/LOW/NONE confidence levels with similarity scores
- **MCP Architecture**: Built with Model Context Protocol servers
- **CLI Interface**: Easy-to-use command-line tools
- **Docker Support**: Complete containerized setup with docker-compose

## =� Quick Start Options

### Option 1: Docker (Recommended)

Perfect for quick setup and testing:

```bash
# 1. Copy environment template
cp .env.example .env

# 2. Edit .env with your credentials
nano .env

# 3. Start everything with Docker
make up

# 4. Test the system
make test
make test-ai
```

### Option 2: Local Development

For active development:

```bash
# 1. Setup Environment
cp .env.example .env
# Edit .env with your credentials

# 2. Install Dependencies
uv sync

# 3. Test Connectivity
uv run linkedin-sync test-connectivity

# 4. Test AI Detection
uv run linkedin-sync test-ai-detection
```

## =3 Docker Usage

The project includes a complete Docker setup:

```bash
# Quick commands with Makefile
make help          # Show all available commands
make up            # Start all services
make logs          # View logs
make test          # Run tests
make shell         # Interactive shell
make clean         # Cleanup resources

# Or use docker-compose directly
docker-compose up -d
docker-compose logs -f
docker-compose exec linkedin-sync bash
```

### Architecture

- **`linkedin-sync`**: Main application container with MCP servers
  - LinkedIn MCP Server (port 8001)
  - Microsoft Dynamics CRM MCP Server (port 8002)  
  - Official Playwright MCP Server (port 8003)
- **`ollama`**: AI model server (mistral-small:24b)
- **`model-downloader`**: Downloads AI model on first run

## =� Documentation

- **`README.Docker.md`**: Complete Docker setup guide
- **`CLAUDE.md`**: Detailed development documentation
- **`Makefile`**: Quick command reference

## <� Example AI Duplicate Detection

The system can intelligently detect duplicates like this:

**LinkedIn Contact:** John Smith - Microsoft Corporation - Senior Software Engineer  
**CRM Contact:** John Smith - Software Engineer - j.smith@microsoft.com

**AI Result:**  DUPLICATE (85% confidence) - "Names match exactly, similar roles, email domain aligns with company"

## = Security

- Environment variables for all credentials
- No secrets in version control
- Docker security best practices
- Non-root container execution

## > Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test with `make test`
5. Submit a pull request

## =� License

This project is licensed under the MIT License.

---

**Repository:** https://github.com/AIspezialisten/linkedin-ai-sync