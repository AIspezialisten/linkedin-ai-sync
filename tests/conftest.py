"""
Test configuration and fixtures.
"""

import pytest
import asyncio
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables for tests
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    load_dotenv(env_path)


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(autouse=True)
def setup_test_environment():
    """Set up test environment before each test."""
    # Any test setup can go here
    yield
    # Any test cleanup can go here