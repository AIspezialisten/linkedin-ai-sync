#!/usr/bin/env python3
"""
List all contacts from Microsoft Dynamics CRM.
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
        
        # Get contacts with specific fields
        api_url = f"{crm_url}/api/data/v9.2/contacts"
        params = {
            "$select": "contactid,firstname,lastname,fullname,emailaddress1,jobtitle,telephone1,mobilephone,address1_city,address1_country,description,linkedin_profile,createdon,modifiedon",
            "$orderby": "modifiedon desc",
            "$top": 100  # Get up to 100 contacts
        }
        
        try:
            response = await client.get(api_url, headers=headers, params=params)
            response.raise_for_status()
            
            data = response.json()
            contacts = data.get("value", [])
            
            return contacts
                        
        except Exception as e:
            print(f"❌ Error retrieving contacts: {str(e)}")
            return []


async def main():
    print("Microsoft Dynamics CRM Contacts")
    print("=" * 50)
    
    contacts = await list_crm_contacts()
    
    if contacts:
        print(f"Found {len(contacts)} contacts in CRM:\n")
        
        # Simple list
        print("📋 Contact List:")
        for i, contact in enumerate(contacts, 1):
            fullname = contact.get('fullname', 'No name')
            company = contact.get('jobtitle', 'No title')
            email = contact.get('emailaddress1', 'No email')
            print(f"{i}. {fullname} - {company}")
            if email != 'No email':
                print(f"   📧 {email}")
        
        print(f"\n📝 Detailed Contact Information:")
        print("-" * 50)
        
        for i, contact in enumerate(contacts, 1):
            print(f"\n{i}. CONTACT ID: {contact.get('contactid', 'N/A')}")
            print(f"   Name: {contact.get('firstname', '')} {contact.get('lastname', '')}")
            print(f"   Full Name: {contact.get('fullname', 'N/A')}")
            print(f"   Email: {contact.get('emailaddress1', 'Not provided')}")
            print(f"   Job Title: {contact.get('jobtitle', 'Not provided')}")
            print(f"   Phone: {contact.get('telephone1', 'Not provided')}")
            print(f"   Mobile: {contact.get('mobilephone', 'Not provided')}")
            print(f"   Location: {contact.get('address1_city', 'Not provided')}")
            if contact.get('address1_country'):
                print(f"   Country: {contact.get('address1_country')}")
            if contact.get('linkedin_profile'):
                print(f"   LinkedIn: {contact.get('linkedin_profile')}")
            if contact.get('description'):
                description = contact.get('description', '')[:100]
                print(f"   Description: {description}{'...' if len(contact.get('description', '')) > 100 else ''}")
            print(f"   Created: {contact.get('createdon', 'N/A')}")
            print(f"   Modified: {contact.get('modifiedon', 'N/A')}")
        
        # Summary stats
        print(f"\n📊 SUMMARY:")
        print(f"   Total contacts: {len(contacts)}")
        
        contacts_with_email = len([c for c in contacts if c.get('emailaddress1')])
        contacts_with_phone = len([c for c in contacts if c.get('telephone1')])
        contacts_with_linkedin = len([c for c in contacts if c.get('linkedin_profile')])
        contacts_with_jobtitle = len([c for c in contacts if c.get('jobtitle')])
        
        print(f"   With email: {contacts_with_email}")
        print(f"   With phone: {contacts_with_phone}")
        print(f"   With LinkedIn: {contacts_with_linkedin}")
        print(f"   With job title: {contacts_with_jobtitle}")
        
        # Check for LinkedIn connections already in CRM
        linkedin_profiles = [c.get('linkedin_profile', '') for c in contacts if c.get('linkedin_profile')]
        if linkedin_profiles:
            print(f"\n🔗 LinkedIn profiles already in CRM:")
            for profile in linkedin_profiles:
                print(f"   - {profile}")
    else:
        print("No contacts found in CRM")


if __name__ == "__main__":
    asyncio.run(main())