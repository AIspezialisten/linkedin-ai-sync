#!/usr/bin/env python3
"""
Test script to check LinkedIn data availability and count contacts.
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


async def test_linkedin_data():
    """Test LinkedIn API to see available data and count contacts."""
    access_token = os.getenv("LINKEDIN_ACCESS_TOKEN")
    if not access_token:
        print("❌ LINKEDIN_ACCESS_TOKEN not found in environment")
        return
    
    print("LinkedIn Data Analysis")
    print("=" * 50)
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        headers = {
            "Authorization": f"Bearer {access_token}",
            "LinkedIn-Version": "202312",
            "Content-Type": "application/json"
        }
        
        # Test different domains to see what data is available
        domains_to_test = [
            "CONNECTIONS",
            "PROFILE", 
            "CONTACTS",
            "NETWORK",
            "PEOPLE"
        ]
        
        for domain in domains_to_test:
            print(f"\nTesting domain: {domain}")
            print("-" * 30)
            
            try:
                url = "https://api.linkedin.com/rest/memberSnapshotData"
                params = {
                    "q": "criteria",
                    "domain": domain
                }
                
                response = await client.get(url, headers=headers, params=params)
                
                if response.status_code == 200:
                    data = response.json()
                    print(f"✓ Status: SUCCESS")
                    print(f"  Response keys: {list(data.keys())}")
                    
                    if "elements" in data:
                        elements = data["elements"]
                        print(f"  Elements count: {len(elements)}")
                        
                        # Analyze the structure
                        if elements:
                            first_element = elements[0]
                            print(f"  First element keys: {list(first_element.keys())}")
                            
                            # Look for connection data specifically
                            if "memberConnections" in first_element:
                                connections = first_element["memberConnections"]
                                if "elements" in connections:
                                    connection_list = connections["elements"]
                                    print(f"  🎯 CONNECTIONS FOUND: {len(connection_list)}")
                                    
                                    # Show sample connection data
                                    if connection_list:
                                        sample = connection_list[0]
                                        print(f"  Sample connection keys: {list(sample.keys())}")
                                        if "person" in sample:
                                            person = sample["person"]
                                            print(f"    Person data keys: {list(person.keys())}")
                                else:
                                    print(f"  memberConnections structure: {list(connections.keys())}")
                            
                            # Look for other data types
                            for key in first_element.keys():
                                if key != "memberConnections":
                                    value = first_element[key]
                                    if isinstance(value, dict) and "elements" in value:
                                        print(f"  {key} elements: {len(value['elements'])}")
                                    elif isinstance(value, list):
                                        print(f"  {key} list length: {len(value)}")
                    else:
                        print(f"  No 'elements' key found. Available keys: {list(data.keys())}")
                        
                elif response.status_code == 404:
                    print(f"⚠ Status: NOT FOUND (domain not supported)")
                elif response.status_code == 403:
                    print(f"⚠ Status: FORBIDDEN (insufficient permissions)")
                else:
                    print(f"✗ Status: ERROR ({response.status_code})")
                    print(f"  Response: {response.text[:200]}...")
                    
            except Exception as e:
                print(f"✗ ERROR: {str(e)}")
        
        # Test the exact working endpoint
        print(f"\n" + "=" * 50)
        print("DETAILED CONNECTIONS ANALYSIS")
        print("=" * 50)
        
        try:
            url = "https://api.linkedin.com/rest/memberSnapshotData"
            params = {
                "q": "criteria",
                "domain": "CONNECTIONS"
            }
            
            response = await client.get(url, headers=headers, params=params)
            
            if response.status_code == 200:
                data = response.json()
                print(f"✓ Successfully retrieved connections data")
                
                # Deep dive into connections
                total_connections = 0
                connection_details = []
                
                if "elements" in data:
                    for element in data["elements"]:
                        if "memberConnections" in element:
                            connections = element["memberConnections"]
                            if "elements" in connections:
                                connection_list = connections["elements"]
                                total_connections += len(connection_list)
                                
                                # Collect sample connection info
                                for conn in connection_list[:5]:  # First 5 for analysis
                                    conn_info = {}
                                    if "person" in conn:
                                        person = conn["person"]
                                        conn_info = {
                                            "has_name": "name" in person,
                                            "has_headline": "headline" in person,
                                            "has_location": "location" in person,
                                            "person_keys": list(person.keys())
                                        }
                                    else:
                                        conn_info = {
                                            "direct_keys": list(conn.keys()),
                                            "structure": "direct"
                                        }
                                    connection_details.append(conn_info)
                
                print(f"\n📊 SUMMARY:")
                print(f"  Total connections found: {total_connections}")
                
                if connection_details:
                    print(f"  Sample connection structures:")
                    for i, detail in enumerate(connection_details):
                        print(f"    Connection {i+1}: {detail}")
                
                # Show raw structure for debugging
                print(f"\n🔍 RAW DATA STRUCTURE:")
                print(json.dumps(data, indent=2)[:1000] + "..." if len(json.dumps(data)) > 1000 else json.dumps(data, indent=2))
                
            else:
                print(f"✗ Failed to get connections: {response.status_code}")
                print(f"Response: {response.text}")
                
        except Exception as e:
            print(f"✗ Error analyzing connections: {str(e)}")


if __name__ == "__main__":
    asyncio.run(test_linkedin_data())