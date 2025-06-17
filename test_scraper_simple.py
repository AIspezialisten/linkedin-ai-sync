#!/usr/bin/env python3
"""
Simple test of the LinkedIn profile scraper without MCP server dependency.
Tests the basic structure and LinkedIn API integration.
"""

import asyncio
import json
import logging
import os
from pathlib import Path
from dotenv import load_dotenv
from datetime import datetime


async def test_linkedin_connections():
    """Test getting LinkedIn connections."""
    print("🧪 Testing LinkedIn Connections API")
    print("=" * 40)
    
    # Load environment
    env_path = Path(__file__).parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
    
    access_token = os.getenv("LINKEDIN_ACCESS_TOKEN")
    if not access_token:
        print("❌ LINKEDIN_ACCESS_TOKEN not found")
        return False
    
    print("✅ LinkedIn access token found")
    
    try:
        import httpx
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            headers = {
                "Authorization": f"Bearer {access_token}",
                "LinkedIn-Version": "202312",
                "Content-Type": "application/json"
            }
            
            url = "https://api.linkedin.com/rest/memberSnapshotData"
            params = {
                "q": "criteria",
                "domain": "CONNECTIONS"
            }
            
            print("📡 Making API request to LinkedIn...")
            response = await client.get(url, headers=headers, params=params)
            response.raise_for_status()
            
            data = response.json()
            
            if "elements" in data:
                for element in data["elements"]:
                    if "snapshotData" in element:
                        connections = element["snapshotData"]
                        print(f"✅ Found {len(connections)} LinkedIn connections")
                        
                        # Show sample connection data
                        if connections:
                            sample = connections[0]
                            print(f"\n📝 Sample connection data:")
                            print(f"   Name: {sample.get('First Name', '')} {sample.get('Last Name', '')}")
                            print(f"   Company: {sample.get('Company', 'N/A')}")
                            print(f"   Position: {sample.get('Position', 'N/A')}")
                            print(f"   URL: {sample.get('URL', 'N/A')}")
                            print(f"   Connected On: {sample.get('Connected On', 'N/A')}")
                        
                        return connections
            
            print("❌ No connection data found in response")
            return False
            
    except Exception as e:
        print(f"❌ LinkedIn API test failed: {str(e)}")
        return False


async def test_ai_model():
    """Test AI model connection."""
    print("\n🤖 Testing AI Model Connection")
    print("=" * 35)
    
    try:
        import ollama
        
        print("📡 Connecting to Ollama...")
        models = ollama.list()
        model_names = [model.model for model in models.models]
        
        required_model = os.getenv('OLLAMA_MODEL', 'mistral-small:24b')
        
        if required_model in model_names:
            print(f"✅ AI model {required_model} is available")
            return True
        else:
            print(f"❌ AI model {required_model} not found")
            print(f"   Available models: {', '.join(model_names[:3])}...")
            return False
            
    except Exception as e:
        print(f"❌ AI model test failed: {str(e)}")
        return False


async def test_pydantic_models():
    """Test Pydantic model structure."""
    print("\n📋 Testing Pydantic Models")
    print("=" * 30)
    
    try:
        from pydantic import BaseModel, Field
        from linkedin_profile_scraper import LinkedInProfileData
        
        # Create test profile data
        test_data = LinkedInProfileData(
            full_name="Test User",
            headline="Software Engineer",
            location="San Francisco, CA",
            about="This is a test profile",
            current_position="Senior Engineer at Test Company",
            experience=["Experience 1", "Experience 2"],
            education=["University of Test"],
            skills=["Python", "JavaScript", "AI"],
            connections_count="500+ connections",
            contact_info=["test@example.com"],
            profile_url="https://linkedin.com/in/testuser",
            scraped_at=datetime.now().isoformat(),
            scraping_success=True
        )
        
        print("✅ LinkedInProfileData model created successfully")
        print(f"   Name: {test_data.full_name}")
        print(f"   Skills: {len(test_data.skills)} found")
        print(f"   Success: {test_data.scraping_success}")
        
        # Test JSON serialization
        json_data = test_data.model_dump()
        print("✅ JSON serialization works")
        
        return True
        
    except Exception as e:
        print(f"❌ Pydantic model test failed: {str(e)}")
        return False


async def test_file_operations():
    """Test file operations."""
    print("\n📁 Testing File Operations")
    print("=" * 30)
    
    try:
        # Create data directory
        data_dir = Path("data")
        data_dir.mkdir(exist_ok=True)
        print("✅ Data directory created")
        
        # Test writing JSON
        test_file = data_dir / "test_output.json"
        test_data = {
            "test": True,
            "timestamp": datetime.now().isoformat(),
            "profiles": [
                {
                    "name": "Test User",
                    "url": "https://example.com"
                }
            ]
        }
        
        with open(test_file, 'w', encoding='utf-8') as f:
            json.dump(test_data, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Test file written: {test_file}")
        print(f"   Size: {test_file.stat().st_size} bytes")
        
        # Clean up
        test_file.unlink()
        print("✅ File cleanup successful")
        
        return True
        
    except Exception as e:
        print(f"❌ File operations test failed: {str(e)}")
        return False


async def main():
    """Run all tests."""
    print("🧪 LinkedIn Profile Scraper - Component Tests")
    print("=" * 60)
    
    # Run individual tests
    test_results = {}
    
    test_results["linkedin_api"] = await test_linkedin_connections()
    test_results["ai_model"] = await test_ai_model()
    test_results["pydantic_models"] = await test_pydantic_models()
    test_results["file_operations"] = await test_file_operations()
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 Test Results Summary")
    print("=" * 25)
    
    for test_name, result in test_results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"   {test_name.replace('_', ' ').title()}: {status}")
    
    passed = sum(1 for r in test_results.values() if r)
    total = len(test_results)
    
    print(f"\n🎯 Overall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All component tests passed! Ready for scraping.")
    else:
        print("⚠️ Some tests failed. Check configuration before scraping.")
    
    return passed == total


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)