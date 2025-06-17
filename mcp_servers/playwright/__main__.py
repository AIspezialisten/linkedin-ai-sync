"""
Entry point for the custom Playwright MCP Server with LinkedIn cookies.
"""

import asyncio
import logging
import sys
from .server import PlaywrightMCPServer


async def main():
    """Main entry point for the Playwright MCP server."""
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stderr),
            logging.FileHandler('/app/data/playwright_mcp.log', mode='a')
        ]
    )
    
    logger = logging.getLogger(__name__)
    logger.info("🎭 Starting Playwright MCP Server with LinkedIn cookies...")
    
    try:
        server = PlaywrightMCPServer()
        await server.run()
    except KeyboardInterrupt:
        logger.info("Server interrupted by user")
    except Exception as e:
        logger.error(f"Server error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())