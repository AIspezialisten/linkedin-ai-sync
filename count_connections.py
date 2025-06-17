#!/usr/bin/env python3
"""
Quick script to count LinkedIn connections and show the data structure.
"""

import asyncio
import json
import os
from pathlib import Path
from dotenv import load_dotenv
import httpx

# Load environment variables
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    load_dotenv(env_path)


async def count_linkedin_connections():
    """Count LinkedIn connections and analyze the data."""
    access_token = os.getenv("LINKEDIN_ACCESS_TOKEN")
    if not access_token:
        print("❌ LINKEDIN_ACCESS_TOKEN not found")
        return
    
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
        
        try:
            response = await client.get(url, headers=headers, params=params)
            response.raise_for_status()
            
            data = response.json()
            
            print("LinkedIn Connections Count")
            print("=" * 40)
            
            total_connections = 0
            
            if "elements" in data:
                for element in data["elements"]:
                    if "snapshotData" in element:
                        connections = element["snapshotData"]
                        total_connections += len(connections)
                        
                        print(f"📊 Total connections found: {len(connections)}")
                        print(f"📄 Paging info: {data.get('paging', {})}")
                        
                        if connections:
                            print(f"\n📋 Sample connections:")
                            for i, conn in enumerate(connections[:3]):  # Show first 3
                                print(f"  {i+1}. {conn.get('First Name', '')} {conn.get('Last Name', '')}")
                                print(f"     Company: {conn.get('Company', 'N/A')}")
                                print(f"     Position: {conn.get('Position', 'N/A')}")
                                print(f"     Connected: {conn.get('Connected On', 'N/A')}")
                                print(f"     Email: {conn.get('Email Address', 'Not available')}")
                                print()
                        
                        print(f"🔑 Available fields per connection:")
                        if connections:
                            sample_keys = list(connections[0].keys())
                            for key in sample_keys:
                                print(f"  - {key}")
            
            return total_connections
                        
        except Exception as e:
            print(f"❌ Error: {str(e)}")
            return 0


if __name__ == "__main__":
    count = asyncio.run(count_linkedin_connections())
    print(f"\n🎯 Final count: {count} LinkedIn connections available via API")