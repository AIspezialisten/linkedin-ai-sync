"""
Entry point for the simplified Playwright server with LinkedIn cookies.
"""

import asyncio
import logging
import sys
from .server import main


if __name__ == "__main__":
    asyncio.run(main())