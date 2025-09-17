#!/usr/bin/env python3
"""
Startup script for the duplicate management web server.
"""

import os
import sys
import asyncio
import logging
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import uvicorn
from dotenv import load_dotenv

from web.models import db_manager
from web.api import app


def setup_logging():
    """Setup logging for the web server."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('web_server.log')
        ]
    )


def check_requirements():
    """Check if all required dependencies are available."""
    required_packages = [
        'fastapi',
        'uvicorn',
        'sqlalchemy',
        'pydantic'
    ]

    missing_packages = []
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)

    if missing_packages:
        print(f"Missing required packages: {', '.join(missing_packages)}")
        print("Install them with: uv sync")
        sys.exit(1)


def main():
    """Main startup function."""
    print("🚀 Starting LinkedIn-CRM Duplicate Management Web Server...")

    # Load environment variables
    load_dotenv()

    # Setup logging
    setup_logging()
    logger = logging.getLogger(__name__)

    # Check requirements
    check_requirements()

    # Initialize database
    try:
        db_manager.create_tables()
        logger.info("Database tables initialized")
    except Exception as e:
        logger.error(f"Failed to initialize database: {str(e)}")
        sys.exit(1)

    # Server configuration
    host = os.getenv('WEB_HOST', '0.0.0.0')
    port = int(os.getenv('WEB_PORT', '8000'))
    reload = os.getenv('WEB_RELOAD', 'false').lower() == 'true'
    workers = int(os.getenv('WEB_WORKERS', '1'))

    logger.info(f"Starting server on {host}:{port}")
    if reload:
        logger.info("Auto-reload enabled for development")

    print(f"🌐 Web interface will be available at: http://{host}:{port}")
    print(f"📊 Dashboard: http://{host}:{port}/")
    print(f"👥 Duplicates: http://{host}:{port}/duplicates")
    print(f"🔧 API docs: http://{host}:{port}/docs")
    print()

    # Start the server
    try:
        uvicorn.run(
            "web.api:app",
            host=host,
            port=port,
            reload=reload,
            workers=workers if not reload else 1,
            log_level="info"
        )
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server failed to start: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()