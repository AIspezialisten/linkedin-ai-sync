#!/usr/bin/env python3
"""
Quick test runner for connectivity tests.

This script can be run directly to test API connectivity without pytest.
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from tests.test_connectivity import TestIntegratedConnectivity


async def main():
    """Run the comprehensive connectivity test."""
    print("LinkedIn-Dynamics CRM Connectivity Test")
    print("=======================================")
    print()
    
    test_instance = TestIntegratedConnectivity()
    await test_instance.test_full_connectivity_check()


if __name__ == "__main__":
    asyncio.run(main())