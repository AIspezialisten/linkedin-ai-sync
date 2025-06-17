#!/bin/bash

# 🐳 Docker Setup Validation Script
# Validates that all Docker components are working correctly

set -e

echo "🚀 LinkedIn-CRM AI Sync - Docker Validation"
echo "==========================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check functions
check_docker() {
    echo -n "🐳 Checking Docker... "
    if command -v docker &> /dev/null; then
        echo -e "${GREEN}✓${NC}"
        docker --version
    else
        echo -e "${RED}✗ Docker not found${NC}"
        exit 1
    fi
}

check_docker_compose() {
    echo -n "🐙 Checking Docker Compose... "
    if command -v docker-compose &> /dev/null; then
        echo -e "${GREEN}✓${NC}"
        docker-compose --version
    else
        echo -e "${RED}✗ Docker Compose not found${NC}"
        exit 1
    fi
}

check_env_file() {
    echo -n "📝 Checking .env file... "
    if [ -f ".env" ]; then
        echo -e "${GREEN}✓${NC}"
    else
        echo -e "${YELLOW}⚠ .env not found${NC}"
        echo "   Creating from template..."
        cp .env.example .env
        echo -e "   ${YELLOW}Please edit .env with your credentials${NC}"
    fi
}

check_disk_space() {
    echo -n "💾 Checking disk space... "
    available=$(df . | tail -1 | awk '{print $4}')
    required=16000000  # 16GB in KB
    
    if [ "$available" -gt "$required" ]; then
        echo -e "${GREEN}✓ $(($available/1024/1024))GB available${NC}"
    else
        echo -e "${YELLOW}⚠ Only $(($available/1024/1024))GB available (16GB+ recommended)${NC}"
    fi
}

validate_docker_compose() {
    echo -n "🔍 Validating docker-compose.yml... "
    if docker-compose config > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC}"
    else
        echo -e "${RED}✗ Invalid docker-compose.yml${NC}"
        exit 1
    fi
}

build_images() {
    echo "🏗️ Building Docker images..."
    docker-compose build --no-cache
    echo -e "${GREEN}✓ Images built successfully${NC}"
}

test_startup() {
    echo "🚀 Testing service startup..."
    
    echo "  Starting services..."
    docker-compose up -d
    
    echo "  Waiting for services to be ready..."
    sleep 30
    
    echo -n "  Checking linkedin-sync container... "
    if docker-compose ps linkedin-sync | grep -q "Up"; then
        echo -e "${GREEN}✓${NC}"
    else
        echo -e "${RED}✗${NC}"
        docker-compose logs linkedin-sync
        exit 1
    fi
    
    echo -n "  Checking ollama container... "
    if docker-compose ps ollama | grep -q "Up"; then
        echo -e "${GREEN}✓${NC}"
    else
        echo -e "${RED}✗${NC}"
        docker-compose logs ollama
        exit 1
    fi
    
    echo -n "  Testing ollama API... "
    if docker-compose exec ollama curl -s http://localhost:11434/api/tags > /dev/null; then
        echo -e "${GREEN}✓${NC}"
    else
        echo -e "${YELLOW}⚠ Ollama not ready yet${NC}"
    fi
}

cleanup() {
    echo "🧹 Cleaning up test containers..."
    docker-compose down
    echo -e "${GREEN}✓ Cleanup complete${NC}"
}

# Main validation
echo ""
check_docker
check_docker_compose
check_env_file
check_disk_space
validate_docker_compose

echo ""
echo "🔧 Running build and startup test..."
build_images
test_startup

echo ""
echo -e "${GREEN}🎉 Docker setup validation complete!${NC}"
echo ""
echo "Next steps:"
echo "1. Edit .env with your actual credentials"
echo "2. Run: make up"
echo "3. Run: make test"
echo "4. Run: make test-ai"
echo ""
echo "For help: make help"

# Optional cleanup
read -p "Clean up test containers? [y/N] " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    cleanup
else
    echo "ℹ️  Containers left running. Use 'make down' to stop them."
fi