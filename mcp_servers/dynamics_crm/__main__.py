"""
Microsoft Dynamics CRM MCP Server entry point.
"""

import asyncio
from .server import main

if __name__ == "__main__":
    asyncio.run(main())