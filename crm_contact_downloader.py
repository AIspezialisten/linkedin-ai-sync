#!/usr/bin/env python3
"""
Microsoft Dynamics CRM Contact Downloader.

This script downloads ALL contacts from Microsoft Dynamics CRM
and stores them in a comprehensive JSON file.
"""

import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Dict, List, Any, Optional
from dotenv import load_dotenv
import httpx
from datetime import datetime
import time


class DynamicsCRMDownloader:
    """Downloads all contacts from Microsoft Dynamics CRM."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.output_file = Path("data/dynamics_crm_contacts_all.json")
        self.output_file.parent.mkdir(parents=True, exist_ok=True)
        
        # CRM Configuration
        self.tenant_id = os.getenv("DYNAMICS_TENANT_ID")
        self.client_id = os.getenv("DYNAMICS_CLIENT_ID")
        self.client_secret = os.getenv("DYNAMICS_CLIENT_SECRET")
        self.crm_url = os.getenv("DYNAMICS_CRM_URL")
        
        self.access_token = None
        self.token_expires_at = None
    
    async def get_access_token(self) -> str:
        """Get OAuth access token for Dynamics CRM."""
        if self.access_token and self.token_expires_at and time.time() < self.token_expires_at:
            return self.access_token
        
        self.logger.info("Getting new OAuth access token...")
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            token_url = f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token"
            
            data = {
                "grant_type": "client_credentials",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "scope": f"{self.crm_url}/.default"
            }
            
            try:
                response = await client.post(token_url, data=data)
                response.raise_for_status()
                
                token_data = response.json()
                self.access_token = token_data["access_token"]
                expires_in = token_data.get("expires_in", 3600)
                self.token_expires_at = time.time() + expires_in - 60  # 1 minute buffer
                
                self.logger.info("✅ OAuth token obtained successfully")
                return self.access_token
                
            except Exception as e:
                self.logger.error(f"Failed to get access token: {str(e)}")
                raise
    
    async def get_contacts_batch(self, skip: int = 0, top: int = 1000) -> Dict[str, Any]:
        """Get a batch of contacts from CRM."""
        access_token = await self.get_access_token()
        
        # Try without $select first to see what fields are available
        select_param = None
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/json",
                "OData-MaxVersion": "4.0",
                "OData-Version": "4.0"
            }
            
            # Start with a simple query first
            url = f"{self.crm_url}/api/data/v9.2/contacts"
            params = {}
            
            # Use the requested batch size (CRM can handle larger requests)
            
            params["$top"] = top
            
            # Skip parameter is not supported, so ignore it
            
            try:
                self.logger.info(f"Fetching contacts batch: skip={skip}, top={top}")
                response = await client.get(url, headers=headers, params=params)
                
                # Log response details for debugging
                self.logger.info(f"Response status: {response.status_code}")
                if response.status_code != 200:
                    self.logger.error(f"Response text: {response.text}")
                
                response.raise_for_status()
                
                data = response.json()
                return data
                
            except Exception as e:
                self.logger.error(f"Failed to get contacts batch: {str(e)}")
                raise
    
    async def get_contacts_from_url(self, url: str) -> Dict[str, Any]:
        """Get contacts from a specific URL (for pagination)."""
        access_token = await self.get_access_token()
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/json",
                "OData-MaxVersion": "4.0",
                "OData-Version": "4.0"
            }
            
            try:
                self.logger.info(f"Fetching from URL: {url[:100]}...")
                response = await client.get(url, headers=headers)
                
                # Log response details for debugging
                self.logger.info(f"Response status: {response.status_code}")
                if response.status_code != 200:
                    self.logger.error(f"Response text: {response.text}")
                
                response.raise_for_status()
                
                data = response.json()
                return data
                
            except Exception as e:
                self.logger.error(f"Failed to get contacts from URL: {str(e)}")
                raise
    
    async def get_total_contact_count(self) -> int:
        """Get the total number of contacts in CRM."""
        access_token = await self.get_access_token()
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/json",
                "OData-MaxVersion": "4.0",
                "OData-Version": "4.0"
            }
            
            # Get count only
            url = f"{self.crm_url}/api/data/v9.2/contacts/$count"
            
            try:
                response = await client.get(url, headers=headers)
                response.raise_for_status()
                
                # Remove BOM and whitespace, then convert to int
                count_text = response.text.strip().lstrip('\ufeff')
                count = int(count_text)
                self.logger.info(f"Total contacts in CRM: {count}")
                return count
                
            except Exception as e:
                self.logger.error(f"Failed to get contact count: {str(e)}")
                return 0
    
    async def download_all_contacts(self, batch_size: int = 1000) -> List[Dict[str, Any]]:
        """Download all contacts from CRM using multiple strategies."""
        self.logger.info("Starting comprehensive CRM contact download...")
        
        # Get total count first
        total_count = await self.get_total_contact_count()
        
        if total_count == 0:
            self.logger.warning("No contacts found in CRM")
            return []
        
        all_contacts = []
        batch_number = 1
        
        # Strategy 1: Try OData pagination first
        next_url = None
        
        while True:
            try:
                self.logger.info(f"Downloading batch {batch_number} (retrieved {len(all_contacts)}/{total_count} contacts so far)...")
                
                if next_url:
                    # Use the next link for subsequent requests
                    batch_data = await self.get_contacts_from_url(next_url)
                else:
                    # First request
                    batch_data = await self.get_contacts_batch(skip=0, top=batch_size)
                
                contacts = batch_data.get("value", [])
                
                if not contacts:
                    self.logger.info("No more contacts found via OData pagination")
                    break
                
                all_contacts.extend(contacts)
                
                self.logger.info(f"✅ Downloaded {len(contacts)} contacts in batch {batch_number}")
                self.logger.info(f"📊 Progress: {len(all_contacts)}/{total_count} contacts ({len(all_contacts)/total_count*100:.1f}%)")
                
                # Check for next page
                next_url = batch_data.get("@odata.nextLink")
                if not next_url:
                    self.logger.info("No @odata.nextLink found")
                    break
                
                batch_number += 1
                
                # Small delay to be respectful to the API
                await asyncio.sleep(0.5)
                
            except Exception as e:
                self.logger.error(f"Error downloading batch {batch_number}: {str(e)}")
                break
        
        # Strategy 2: If we didn't get all contacts, try date-based pagination
        if len(all_contacts) < total_count:
            self.logger.info(f"Only got {len(all_contacts)}/{total_count} contacts via OData. Trying date-based pagination...")
            remaining_contacts = await self.download_contacts_by_date_range(all_contacts)
            all_contacts.extend(remaining_contacts)
        
        # Strategy 3: If still missing contacts, try ID-based pagination
        if len(all_contacts) < total_count:
            self.logger.info(f"Still missing contacts ({len(all_contacts)}/{total_count}). Trying ID-based pagination...")
            remaining_contacts = await self.download_remaining_contacts_by_id(all_contacts)
            all_contacts.extend(remaining_contacts)
        
        # Strategy 4: Try different ordering and larger batches
        if len(all_contacts) < total_count:
            self.logger.info(f"Still missing contacts ({len(all_contacts)}/{total_count}). Trying different ordering strategies...")
            remaining_contacts = await self.download_with_different_ordering(all_contacts)
            all_contacts.extend(remaining_contacts)
        
        # Remove duplicates based on contactid
        unique_contacts = {}
        for contact in all_contacts:
            contact_id = contact.get('contactid')
            if contact_id and contact_id not in unique_contacts:
                unique_contacts[contact_id] = contact
        
        final_contacts = list(unique_contacts.values())
        
        self.logger.info(f"✅ Download complete! Retrieved {len(final_contacts)} unique contacts (removed {len(all_contacts) - len(final_contacts)} duplicates)")
        return final_contacts
    
    async def download_contacts_by_date_range(self, existing_contacts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Download contacts by date ranges to get missing contacts."""
        existing_ids = {contact.get('contactid') for contact in existing_contacts}
        new_contacts = []
        
        # Get date range of existing contacts
        existing_dates = []
        for contact in existing_contacts:
            created_date = contact.get('createdon')
            if created_date:
                existing_dates.append(created_date)
        
        if not existing_dates:
            self.logger.info("No creation dates found in existing contacts, skipping date-based pagination")
            return []
        
        # Sort dates to find gaps
        existing_dates.sort()
        latest_date = existing_dates[-1]
        
        self.logger.info(f"Latest contact date in existing data: {latest_date}")
        
        # Try to get contacts created after the latest date we have
        try:
            batch_data = await self.get_contacts_with_filter(f"createdon gt {latest_date}")
            contacts = batch_data.get("value", [])
            
            for contact in contacts:
                contact_id = contact.get('contactid')
                if contact_id and contact_id not in existing_ids:
                    new_contacts.append(contact)
                    existing_ids.add(contact_id)
            
            self.logger.info(f"Found {len(new_contacts)} additional contacts via date filtering")
            
        except Exception as e:
            self.logger.error(f"Error in date-based pagination: {str(e)}")
        
        return new_contacts
    
    async def download_remaining_contacts_by_id(self, existing_contacts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Try to get remaining contacts by using ID-based filtering."""
        existing_ids = {contact.get('contactid') for contact in existing_contacts}
        new_contacts = []
        
        # Try different filters to get remaining contacts
        filters = [
            "statecode eq 0",  # Active contacts only
            "statecode eq 1",  # Inactive contacts
            "createdon gt 2020-01-01T00:00:00Z",  # Contacts created after 2020
            "createdon lt 2020-01-01T00:00:00Z"   # Contacts created before 2020
        ]
        
        for filter_condition in filters:
            try:
                self.logger.info(f"Trying filter: {filter_condition}")
                batch_data = await self.get_contacts_with_filter(filter_condition)
                contacts = batch_data.get("value", [])
                
                added_count = 0
                for contact in contacts:
                    contact_id = contact.get('contactid')
                    if contact_id and contact_id not in existing_ids:
                        new_contacts.append(contact)
                        existing_ids.add(contact_id)
                        added_count += 1
                
                self.logger.info(f"Filter '{filter_condition}' added {added_count} new contacts")
                
                # Small delay between requests
                await asyncio.sleep(0.5)
                
            except Exception as e:
                self.logger.error(f"Error with filter '{filter_condition}': {str(e)}")
                continue
        
        self.logger.info(f"ID-based pagination found {len(new_contacts)} additional contacts")
        return new_contacts
    
    async def get_contacts_with_filter(self, filter_condition: str, top: int = 1000) -> Dict[str, Any]:
        """Get contacts with a specific OData filter."""
        access_token = await self.get_access_token()
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/json",
                "OData-MaxVersion": "4.0",
                "OData-Version": "4.0"
            }
            
            url = f"{self.crm_url}/api/data/v9.2/contacts"
            params = {
                "$filter": filter_condition,
                "$top": top
            }
            
            try:
                self.logger.info(f"Fetching contacts with filter: {filter_condition}")
                response = await client.get(url, headers=headers, params=params)
                
                self.logger.info(f"Response status: {response.status_code}")
                if response.status_code != 200:
                    self.logger.error(f"Response text: {response.text}")
                
                response.raise_for_status()
                
                data = response.json()
                return data
                
            except Exception as e:
                self.logger.error(f"Failed to get contacts with filter: {str(e)}")
                raise
    
    async def download_with_different_ordering(self, existing_contacts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Try different ordering strategies to get remaining contacts."""
        existing_ids = {contact.get('contactid') for contact in existing_contacts}
        new_contacts = []
        
        # Try different ordering strategies
        ordering_strategies = [
            "createdon asc",
            "modifiedon desc", 
            "modifiedon asc",
            "fullname asc",
            "fullname desc",
            "contactid asc",
            "contactid desc"
        ]
        
        for order_by in ordering_strategies:
            try:
                self.logger.info(f"Trying ordering: {order_by}")
                batch_data = await self.get_contacts_with_ordering(order_by)
                contacts = batch_data.get("value", [])
                
                added_count = 0
                for contact in contacts:
                    contact_id = contact.get('contactid')
                    if contact_id and contact_id not in existing_ids:
                        new_contacts.append(contact)
                        existing_ids.add(contact_id)
                        added_count += 1
                
                self.logger.info(f"Ordering '{order_by}' added {added_count} new contacts")
                
                # Small delay between requests
                await asyncio.sleep(0.5)
                
            except Exception as e:
                self.logger.error(f"Error with ordering '{order_by}': {str(e)}")
                continue
        
        self.logger.info(f"Different ordering strategies found {len(new_contacts)} additional contacts")
        return new_contacts
    
    async def get_contacts_with_ordering(self, order_by: str, top: int = 1000) -> Dict[str, Any]:
        """Get contacts with specific ordering."""
        access_token = await self.get_access_token()
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/json",
                "OData-MaxVersion": "4.0",
                "OData-Version": "4.0"
            }
            
            url = f"{self.crm_url}/api/data/v9.2/contacts"
            params = {
                "$orderby": order_by,
                "$top": top
            }
            
            try:
                self.logger.info(f"Fetching contacts with ordering: {order_by}")
                response = await client.get(url, headers=headers, params=params)
                
                self.logger.info(f"Response status: {response.status_code}")
                if response.status_code != 200:
                    self.logger.error(f"Response text: {response.text}")
                
                response.raise_for_status()
                
                data = response.json()
                return data
                
            except Exception as e:
                self.logger.error(f"Failed to get contacts with ordering: {str(e)}")
                raise
    
    async def analyze_contact_data(self, contacts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze the downloaded contact data for insights."""
        if not contacts:
            return {}
        
        analysis = {
            "total_contacts": len(contacts),
            "field_analysis": {},
            "data_completeness": {},
            "contact_types": {},
            "geographic_distribution": {},
            "creation_timeline": {},
            "top_companies": {},
            "top_job_titles": {}
        }
        
        # Analyze field completeness
        all_fields = set()
        for contact in contacts:
            all_fields.update(contact.keys())
        
        for field in all_fields:
            non_null_count = sum(1 for contact in contacts if contact.get(field) is not None and str(contact.get(field)).strip())
            analysis["field_analysis"][field] = {
                "total_records": len(contacts),
                "non_null_count": non_null_count,
                "completeness_percentage": (non_null_count / len(contacts)) * 100,
                "sample_values": [
                    str(contact.get(field)) for contact in contacts[:5] 
                    if contact.get(field) is not None
                ][:3]
            }
        
        # Key field completeness
        key_fields = ["fullname", "emailaddress1", "telephone1", "jobtitle", "companyname"]
        for field in key_fields:
            count = sum(1 for contact in contacts if contact.get(field))
            analysis["data_completeness"][field] = {
                "count": count,
                "percentage": (count / len(contacts)) * 100
            }
        
        # Geographic distribution
        countries = {}
        cities = {}
        for contact in contacts:
            country = contact.get("address1_country")
            city = contact.get("address1_city")
            
            if country:
                countries[country] = countries.get(country, 0) + 1
            if city:
                cities[city] = cities.get(city, 0) + 1
        
        analysis["geographic_distribution"] = {
            "top_countries": sorted(countries.items(), key=lambda x: x[1], reverse=True)[:10],
            "top_cities": sorted(cities.items(), key=lambda x: x[1], reverse=True)[:10]
        }
        
        # Top companies
        companies = {}
        for contact in contacts:
            company = contact.get("companyname")
            if company:
                companies[company] = companies.get(company, 0) + 1
        
        analysis["top_companies"] = sorted(companies.items(), key=lambda x: x[1], reverse=True)[:20]
        
        # Top job titles
        titles = {}
        for contact in contacts:
            title = contact.get("jobtitle")
            if title:
                titles[title] = titles.get(title, 0) + 1
        
        analysis["top_job_titles"] = sorted(titles.items(), key=lambda x: x[1], reverse=True)[:20]
        
        # Creation timeline (by year)
        timeline = {}
        for contact in contacts:
            created = contact.get("createdon")
            if created:
                try:
                    year = created[:4]  # Extract year from ISO date
                    timeline[year] = timeline.get(year, 0) + 1
                except:
                    pass
        
        analysis["creation_timeline"] = sorted(timeline.items())
        
        return analysis
    
    async def save_contacts_to_json(self, contacts: List[Dict[str, Any]], analysis: Dict[str, Any]):
        """Save all contacts and analysis to JSON file."""
        try:
            output_data = {
                "download_session": {
                    "timestamp": datetime.now().isoformat(),
                    "total_contacts_downloaded": len(contacts),
                    "crm_system": "Microsoft Dynamics CRM",
                    "crm_url": self.crm_url,
                    "download_method": "Comprehensive API Export",
                    "api_version": "v9.2",
                    "fields_retrieved": len(set().union(*(contact.keys() for contact in contacts))) if contacts else 0
                },
                "data_analysis": analysis,
                "contacts": contacts
            }
            
            with open(self.output_file, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, indent=2, ensure_ascii=False, default=str)
            
            file_size = self.output_file.stat().st_size
            self.logger.info(f"✅ Saved {len(contacts)} contacts to {self.output_file}")
            self.logger.info(f"📁 File size: {file_size / 1024 / 1024:.1f} MB")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error saving contacts to JSON: {str(e)}")
            return False


async def main():
    """Main download function."""
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('data/crm_download.log', mode='a')
        ]
    )
    
    logger = logging.getLogger(__name__)
    
    # Load environment variables
    env_path = Path(__file__).parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
    
    print("📋 Microsoft Dynamics CRM - Complete Contact Download")
    print("=" * 70)
    
    # Check required environment variables
    required_vars = ["DYNAMICS_TENANT_ID", "DYNAMICS_CLIENT_ID", "DYNAMICS_CLIENT_SECRET", "DYNAMICS_CRM_URL"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"❌ Missing required environment variables: {', '.join(missing_vars)}")
        return False
    
    print("✅ All CRM credentials found")
    print(f"🔗 CRM URL: {os.getenv('DYNAMICS_CRM_URL')}")
    
    # Initialize downloader
    downloader = DynamicsCRMDownloader()
    
    try:
        # Test connection first
        print("\n🔌 Testing CRM connection...")
        total_count = await downloader.get_total_contact_count()
        
        if total_count == 0:
            print("❌ No contacts found or connection failed")
            return False
        
        print(f"✅ CRM connection successful")
        print(f"📊 Total contacts to download: {total_count:,}")
        
        # Ask for confirmation
        try:
            user_input = input(f"\n🤔 Download all {total_count:,} contacts? This may take several minutes. (y/n): ").strip().lower()
            
            if user_input != 'y':
                print("❌ Download cancelled by user")
                return False
        except EOFError:
            # Auto-approve when running non-interactively
            print(f"\n🚀 Auto-approving download of {total_count:,} contacts (non-interactive mode)")
            pass
        
        # Start download
        print(f"\n🚀 Starting complete contact download...")
        print(f"⏱️ Estimated time: {total_count / 1000 * 2:.1f} minutes")
        
        start_time = time.time()
        contacts = await downloader.download_all_contacts(batch_size=1000)
        download_time = time.time() - start_time
        
        if not contacts:
            print("❌ No contacts were downloaded")
            return False
        
        print(f"\n✅ Download completed in {download_time:.1f} seconds")
        print(f"📊 Downloaded {len(contacts):,} contacts")
        
        # Analyze data
        print(f"\n📈 Analyzing contact data...")
        analysis = await downloader.analyze_contact_data(contacts)
        
        # Save to JSON
        print(f"\n💾 Saving contacts and analysis to JSON...")
        success = await downloader.save_contacts_to_json(contacts, analysis)
        
        if success:
            print(f"✅ Successfully saved all CRM contacts!")
            print(f"📁 File: {downloader.output_file}")
            print(f"📏 Size: {downloader.output_file.stat().st_size / 1024 / 1024:.1f} MB")
            
            # Show analysis summary
            print(f"\n📊 Data Analysis Summary:")
            print(f"   Total contacts: {analysis.get('total_contacts', 0):,}")
            
            completeness = analysis.get('data_completeness', {})
            print(f"   Data completeness:")
            for field, data in completeness.items():
                print(f"     {field}: {data['count']:,} ({data['percentage']:.1f}%)")
            
            top_companies = analysis.get('top_companies', [])[:5]
            if top_companies:
                print(f"   Top companies:")
                for company, count in top_companies:
                    print(f"     {company}: {count} contacts")
            
            top_countries = analysis.get('geographic_distribution', {}).get('top_countries', [])[:5]
            if top_countries:
                print(f"   Top countries:")
                for country, count in top_countries:
                    print(f"     {country}: {count} contacts")
            
            return True
        else:
            print("❌ Failed to save contacts")
            return False
            
    except Exception as e:
        logger.error(f"Error in download process: {str(e)}")
        print(f"❌ Download failed: {str(e)}")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)