#!/usr/bin/env python3
"""
Extract LinkedIn profile URLs from all connections.
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


async def extract_linkedin_urls():
    """Extract all LinkedIn profile URLs from connections."""
    access_token = os.getenv("LINKEDIN_ACCESS_TOKEN")
    if not access_token:
        print("❌ LINKEDIN_ACCESS_TOKEN not found")
        return []
    
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
            
            urls = []
            
            if "elements" in data:
                for element in data["elements"]:
                    if "snapshotData" in element:
                        connections = element["snapshotData"]
                        
                        for conn in connections:
                            name = f"{conn.get('First Name', '').strip()} {conn.get('Last Name', '').strip()}"
                            url = conn.get('URL', '')
                            company = conn.get('Company', '')
                            position = conn.get('Position', '')
                            
                            urls.append({
                                'name': name,
                                'url': url,
                                'company': company,
                                'position': position
                            })
            
            return urls
                        
        except Exception as e:
            print(f"❌ Error: {str(e)}")
            return []


async def main():
    print("LinkedIn Profile URLs")
    print("=" * 50)
    
    urls = await extract_linkedin_urls()
    
    if urls:
        print(f"Found {len(urls)} LinkedIn connections:\n")
        
        # Simple list format
        print("📋 Profile URLs:")
        for i, conn in enumerate(urls, 1):
            print(f"{i}. {conn['url']}")
        
        print(f"\n📝 Detailed list:")
        for i, conn in enumerate(urls, 1):
            print(f"{i}. {conn['name']}")
            print(f"   URL: {conn['url']}")
            print(f"   Company: {conn['company']}")
            print(f"   Position: {conn['position']}")
            print()
        
        # Just URLs for easy copying
        print("🔗 URLs only (for copying):")
        for conn in urls:
            print(conn['url'])
    else:
        print("No connections found")


if __name__ == "__main__":
    asyncio.run(main())