# Web Interface for Duplicate Management

This document describes the web-based interface for managing duplicate contacts between LinkedIn and Microsoft Dynamics CRM.

## 🌟 Features

- **Dashboard**: Overview of duplicate statistics and recent sync sessions
- **Duplicate Review**: Side-by-side comparison of LinkedIn and CRM contacts
- **AI-Powered Analysis**: Confidence levels and reasoning for each potential duplicate
- **One-Click Updates**: Select fields to update in CRM with a single click
- **Bulk Actions**: Approve, reject, or flag multiple duplicates
- **Real-time Updates**: Changes are immediately reflected in the CRM

## 🚀 Quick Start

### 1. Install Dependencies

```bash
# Install Python dependencies
uv sync

# The web interface dependencies are automatically included
```

### 2. Build Frontend (Optional - for development)

```bash
# Build the React frontend
./scripts/build_frontend.sh
```

### 3. Start the Web Server

```bash
# Option 1: Use the startup script
./scripts/start_web_interface.sh

# Option 2: Use the Python command
uv run linkedin-web

# Option 3: Use the Python module directly
uv run python web/start_server.py
```

### 4. Access the Interface

Open your browser and navigate to:
- **Dashboard**: http://localhost:8000/
- **Duplicates**: http://localhost:8000/duplicates
- **API Documentation**: http://localhost:8000/docs

## 🔄 Workflow

### 1. Run Sync with Web Review

```bash
# Sync with AI detection and store duplicates for web review
uv run linkedin-sync sync-with-web-review --ai-detection --limit 50

# Auto-sync safe contacts, store others for review
uv run linkedin-sync sync-with-web-review --ai-detection --auto-sync --limit 50
```

### 2. Review Duplicates in Web Interface

1. **Navigate to Duplicates Page**: View all pending duplicates
2. **Review Each Match**: See side-by-side contact comparison
3. **Read AI Analysis**: Understand why contacts are flagged as duplicates
4. **Select Fields to Update**: Choose which information to sync to CRM
5. **Take Action**: Approve, reject, or flag for later review

### 3. Actions Available

- **✅ Approve & Update CRM**: Select fields to update and sync to CRM
- **❌ Reject**: Mark as not a duplicate (contacts remain separate)
- **🏷️ Flag for Later**: Mark for later review if unsure

## 📊 Dashboard Features

### Statistics Overview
- Pending duplicates requiring review
- Total duplicates found by confidence level
- Sync session history
- CRM update success rates

### Confidence Levels
- **🔴 HIGH**: Very likely duplicates (95%+ confidence)
- **🟡 MEDIUM**: Probable duplicates (70-95% confidence)
- **🟢 LOW**: Possible duplicates (40-70% confidence)
- **⚪ NONE**: Different people (0-40% confidence)

## 🛠️ Configuration

### Environment Variables

```bash
# Web server configuration
WEB_HOST=0.0.0.0          # Server host (default: 0.0.0.0)
WEB_PORT=8000             # Server port (default: 8000)
WEB_RELOAD=false          # Auto-reload for development (default: false)
WEB_WORKERS=1             # Number of worker processes (default: 1)

# Database configuration
DATABASE_URL=sqlite:///duplicates.db  # SQLite database path

# API configuration (inherited from main .env)
LINKEDIN_ACCESS_TOKEN=your_token
DYNAMICS_TENANT_ID=your_tenant_id
DYNAMICS_CLIENT_ID=your_client_id
DYNAMICS_CLIENT_SECRET=your_client_secret
DYNAMICS_CRM_URL=https://your-org.crm4.dynamics.com

# AI configuration
OLLAMA_MODEL=mistral-small:24b
OLLAMA_HOST=http://localhost:11434
```

## 🏗️ Architecture

### Components

1. **FastAPI Backend** (`web/api.py`)
   - RESTful API for duplicate management
   - Database operations
   - CRM integration

2. **React Frontend** (`web/frontend/`)
   - Modern responsive UI
   - Real-time updates
   - Mobile-friendly design

3. **SQLite Database** (`web/models.py`)
   - Stores duplicate candidates
   - Tracks user decisions
   - Audit trail

4. **Service Layer** (`web/services.py`)
   - Business logic
   - CRM operations
   - Data validation

### API Endpoints

- `GET /api/duplicates` - Get paginated duplicates
- `GET /api/duplicates/{id}` - Get specific duplicate
- `POST /api/duplicates/{id}/approve` - Approve and update CRM
- `POST /api/duplicates/{id}/reject` - Reject duplicate
- `POST /api/duplicates/{id}/flag` - Flag for later review
- `GET /api/stats` - Get dashboard statistics

## 🔧 Development

### Frontend Development

```bash
# Navigate to frontend directory
cd web/frontend

# Install dependencies
npm install

# Start development server
npm start

# The frontend will be available at http://localhost:3000
# It will proxy API requests to the backend at http://localhost:8000
```

### Backend Development

```bash
# Start with auto-reload
WEB_RELOAD=true uv run python web/start_server.py

# Or use uvicorn directly
uv run uvicorn web.api:app --reload --host 0.0.0.0 --port 8000
```

## 🐛 Troubleshooting

### Common Issues

1. **Frontend not loading**
   - Ensure frontend is built: `./scripts/build_frontend.sh`
   - Check if Node.js is installed

2. **Database errors**
   - Database is automatically created
   - Check file permissions in project directory

3. **API errors**
   - Verify environment variables are set
   - Check MCP server connections
   - Review server logs

### Logs

- Server logs: `web_server.log`
- Frontend build logs: `web/frontend/npm-debug.log`
- MCP logs: Check individual MCP server outputs

## 📱 Mobile Support

The web interface is fully responsive and works on:
- Desktop browsers
- Tablets
- Mobile phones

## 🔒 Security

- No authentication implemented (suitable for internal use)
- Environment variables for sensitive data
- SQLite database for simplicity
- CORS enabled for local development

## 🚀 Production Deployment

For production use:

1. **Build frontend**: `./scripts/build_frontend.sh`
2. **Set production environment variables**
3. **Use reverse proxy** (nginx, Apache)
4. **Enable HTTPS**
5. **Configure proper logging**
6. **Set up database backups**

Example production start:
```bash
WEB_HOST=127.0.0.1 WEB_PORT=8000 WEB_WORKERS=4 uv run linkedin-web
```