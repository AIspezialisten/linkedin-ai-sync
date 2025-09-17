# Use Python 3.11 slim image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies including build tools for Python extensions
RUN apt-get update && apt-get install -y \
    curl \
    git \
    ca-certificates \
    build-essential \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js for frontend and Playwright MCP server
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs

# Install uv (fast Python package manager)
RUN pip install uv

# Copy dependency files and README (required by pyproject.toml)
COPY pyproject.toml uv.lock README.md ./

# Install Python dependencies using uv
RUN uv sync --frozen

# Install the official Playwright MCP server
RUN npm install -g @playwright/mcp

# Copy frontend package files first for better Docker layer caching
COPY web/frontend/package*.json ./web/frontend/
WORKDIR /app/web/frontend

# Install frontend dependencies
RUN npm ci --only=production

# Copy all application code
WORKDIR /app
COPY . .

# Build the React frontend
WORKDIR /app/web/frontend
RUN npm run build

# Return to app directory
WORKDIR /app

# Copy and make entrypoint executable
COPY docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

# Create non-root user for security and fix permissions
RUN useradd --create-home --shell /bin/bash app && \
    chown -R app:app /app && \
    chmod -R 755 /app/.venv 2>/dev/null || true
USER app

# Create data directory for persistent storage
RUN mkdir -p /app/data

# Expose ports for web interface and MCP servers
EXPOSE 19000 8001 8002 8003

# Health check for web interface
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:19000/api/health || exit 1

# Set entrypoint
ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]

# Default command - keeps container running for interactive use
CMD ["tail", "-f", "/dev/null"]