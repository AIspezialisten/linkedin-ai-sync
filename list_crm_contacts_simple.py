#!/usr/bin/env python3
"""
List all contacts from Microsoft Dynamics CRM using standard fields only.
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


async def get_access_token():
    """Get OAuth access token for Dynamics CRM."""
    config = {
        "tenant_id": os.getenv("DYNAMICS_TENANT_ID"),
        "client_id": os.getenv("DYNAMICS_CLIENT_ID"),
        "client_secret": os.getenv("DYNAMICS_CLIENT_SECRET"),
        "crm_url": os.getenv("DYNAMICS_CRM_URL")
    }
    
    missing = [k for k, v in config.items() if not v]
    if missing:
        print(f"❌ Missing Dynamics CRM environment variables: {', '.join(missing)}")
        return None, None
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        token_url = f"https://login.microsoftonline.com/{config['tenant_id']}/oauth2/v2.0/token"
        
        data = {
            "grant_type": "client_credentials",
            "client_id": config['client_id'],
            "client_secret": config['client_secret'],
            "scope": f"{config['crm_url']}/.default"
        }
        
        try:
            response = await client.post(token_url, data=data)
            response.raise_for_status()
            
            token_data = response.json()
            return token_data["access_token"], config['crm_url']
            
        except Exception as e:
            print(f"❌ Error getting access token: {str(e)}")
            return None, None


async def list_crm_contacts():
    """List all contacts from Dynamics CRM."""
    access_token, crm_url = await get_access_token()
    if not access_token:
        return []
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        headers = {
            "Authorization": f"Bearer {access_token}",
            "OData-MaxVersion": "4.0",
            "OData-Version": "4.0",
            "Content-Type": "application/json"
        }
        
        # First, try without any $select to see what fields are available
        api_url = f"{crm_url}/api/data/v9.2/contacts"
        params = {
            "$top": 5  # Just get first 5 to see the structure
        }
        
        try:
            print("🔍 Discovering available fields...")
            response = await client.get(api_url, headers=headers, params=params)
            response.raise_for_status()
            
            data = response.json()
            contacts = data.get("value", [])
            
            if contacts:
                print(f"✓ Found {len(contacts)} contacts. Available fields:")
                sample_contact = contacts[0]
                available_fields = list(sample_contact.keys())
                
                # Show available fields
                for field in sorted(available_fields):
                    print(f"  - {field}")
                
                print(f"\n" + "="*50)
                print("CONTACTS LIST")
                print("="*50)
            
            # Now get all contacts with only standard fields
            params = {
                "$select": "contactid,firstname,lastname,fullname,emailaddress1,jobtitle,telephone1,createdon,modifiedon",
                "$orderby": "modifiedon desc",
                "$top": 100
            }
            
            response = await client.get(api_url, headers=headers, params=params)
            response.raise_for_status()
            
            data = response.json()
            all_contacts = data.get("value", [])
            
            return all_contacts
                        
        except Exception as e:
            print(f"❌ Error retrieving contacts: {str(e)}")
            if hasattr(e, 'response'):
                print(f"Response text: {e.response.text}")
            return []


async def main():
    print("Microsoft Dynamics CRM Contacts")
    print("=" * 50)
    
    contacts = await list_crm_contacts()
    
    if contacts:
        print(f"\nFound {len(contacts)} contacts in CRM:")
        print("-" * 30)
        
        for i, contact in enumerate(contacts, 1):
            fullname = contact.get('fullname', 'No name')
            firstname = contact.get('firstname', '')
            lastname = contact.get('lastname', '')
            email = contact.get('emailaddress1', '')
            jobtitle = contact.get('jobtitle', '')
            phone = contact.get('telephone1', '')
            contact_id = contact.get('contactid', '')
            created = contact.get('createdon', '')
            modified = contact.get('modifiedon', '')
            
            print(f"\n{i}. {fullname}")
            if firstname or lastname:
                print(f"   Name: {firstname} {lastname}")
            if email:
                print(f"   📧 Email: {email}")
            if jobtitle:
                print(f"   💼 Job: {jobtitle}")
            if phone:
                print(f"   📞 Phone: {phone}")
            print(f"   🆔 ID: {contact_id}")
            if created:
                print(f"   📅 Created: {created[:10]}")
            if modified:
                print(f"   ✏️  Modified: {modified[:10]}")
        
        # Summary
        print(f"\n📊 SUMMARY:")
        print(f"   Total contacts: {len(contacts)}")
        
        contacts_with_email = len([c for c in contacts if c.get('emailaddress1')])
        contacts_with_phone = len([c for c in contacts if c.get('telephone1')])
        contacts_with_job = len([c for c in contacts if c.get('jobtitle')])
        
        print(f"   With email: {contacts_with_email}")
        print(f"   With phone: {contacts_with_phone}")
        print(f"   With job title: {contacts_with_job}")
        
        # Simple list for copying
        print(f"\n📋 Simple list:")
        for i, contact in enumerate(contacts, 1):
            fullname = contact.get('fullname', 'No name')
            email = contact.get('emailaddress1', '')
            print(f"{i}. {fullname}" + (f" ({email})" if email else ""))
    else:
        print("No contacts found in CRM or error occurred")


if __name__ == "__main__":
    asyncio.run(main())