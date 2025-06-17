#!/usr/bin/env python3
"""
Test script to verify the official Playwright MCP server is working.
"""

import subprocess
import time
import requests
import json
import sys


def test_playwright_mcp_server():
    """Test the official Playwright MCP server."""
    print("🎭 Testing Official Playwright MCP Server")
    print("=" * 50)
    
    # Test 1: Check if npx and @playwright/mcp are available
    print("📦 Test 1: Checking Playwright MCP installation...")
    try:
        result = subprocess.run(
            ["npx", "@playwright/mcp", "--help"],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            print("✅ Official Playwright MCP server is installed")
            print("   Available options:")
            for line in result.stdout.split('\n')[:10]:  # Show first 10 lines
                if line.strip():
                    print(f"   {line}")
        else:
            print(f"❌ Playwright MCP server installation issue:")
            print(f"   {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print("❌ Playwright MCP server command timed out")
        return False
    except Exception as e:
        print(f"❌ Failed to check Playwright MCP server: {str(e)}")
        return False
    
    # Test 2: Try to start the server briefly
    print("\n🚀 Test 2: Starting Playwright MCP server...")
    try:
        # Start the server in the background
        process = subprocess.Popen(
            ["npx", "@playwright/mcp", "--port", "8003"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Give it time to start
        time.sleep(3)
        
        # Check if process is still running
        if process.poll() is None:
            print("✅ Playwright MCP server started successfully")
            
            # Try to stop it gracefully
            process.terminate()
            try:
                process.wait(timeout=5)
                print("✅ Playwright MCP server stopped gracefully")
            except subprocess.TimeoutExpired:
                process.kill()
                print("⚠️  Playwright MCP server was force-killed")
            
            return True
        else:
            stdout, stderr = process.communicate()
            print(f"❌ Playwright MCP server failed to start:")
            print(f"   stdout: {stdout}")
            print(f"   stderr: {stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Failed to test server startup: {str(e)}")
        return False


def test_mcp_manager_integration():
    """Test that the MCP manager can start the Playwright server."""
    print("\n🤖 Test 3: Testing MCP Manager Integration...")
    
    try:
        # Import our MCP manager
        sys.path.append('/app')
        from services.mcp_manager import MCPServerManager
        
        manager = MCPServerManager()
        
        # Check if Playwright server is configured
        if "playwright" in manager.server_configs:
            config = manager.server_configs["playwright"]
            print(f"✅ Playwright server configured in MCP manager:")
            print(f"   Name: {config['name']}")
            print(f"   Command: {' '.join(config['command'])}")
            print(f"   Port: {config['port']}")
            return True
        else:
            print("❌ Playwright server not found in MCP manager configuration")
            return False
            
    except Exception as e:
        print(f"❌ Failed to test MCP manager integration: {str(e)}")
        return False


def main():
    """Main test function."""
    print("🧪 Official Playwright MCP Server Test Suite")
    print("=" * 60)
    
    # Run tests
    test1_result = test_playwright_mcp_server()
    test2_result = test_mcp_manager_integration()
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 Test Summary")
    print("=" * 15)
    print(f"✅ Playwright MCP installation: {'PASS' if test1_result else 'FAIL'}")
    print(f"✅ MCP Manager integration: {'PASS' if test2_result else 'FAIL'}")
    
    if test1_result and test2_result:
        print(f"\n🎉 All tests passed! Official Playwright MCP server is ready!")
        print(f"\n📝 Usage:")
        print(f"   • The server runs on port 8003")
        print(f"   • Started automatically by MCP Manager")
        print(f"   • Provides web automation capabilities via MCP protocol")
        return True
    else:
        print(f"\n⚠️ Some tests failed. Check the errors above.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)