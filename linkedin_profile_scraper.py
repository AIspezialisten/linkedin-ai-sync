#!/usr/bin/env python3
"""
LinkedIn Profile Scraper using PydanticAI with Playwright MCP Server.

This script uses PydanticAI to orchestrate LinkedIn profile scraping
through the Playwright MCP server, providing structured data extraction.
"""

import asyncio
import json
import logging
import os
import time
import random
from pathlib import Path
from typing import Dict, List, Any, Optional
from dotenv import load_dotenv
import httpx
from datetime import datetime

from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider

# MCP Client for connecting to our custom Playwright server
import subprocess
import tempfile


class LinkedInProfileData(BaseModel):
    """Structured LinkedIn profile data."""
    full_name: Optional[str] = Field(None, description="Full name of the person")
    headline: Optional[str] = Field(None, description="Professional headline/title")
    location: Optional[str] = Field(None, description="Geographic location")
    about: Optional[str] = Field(None, description="About/summary section")
    current_position: Optional[str] = Field(None, description="Current job title and company")
    experience: List[str] = Field(default_factory=list, description="Work experience entries")
    education: List[str] = Field(default_factory=list, description="Education entries")
    skills: List[str] = Field(default_factory=list, description="Skills listed")
    connections_count: Optional[str] = Field(None, description="Number of connections")
    
    # Structured contact information for syncing
    email: Optional[str] = Field(None, description="Email address")
    phone: Optional[str] = Field(None, description="Phone number")
    website: Optional[str] = Field(None, description="Personal/company website")
    birthday: Optional[str] = Field(None, description="Birthday information")
    
    # Raw contact info for reference
    contact_info: List[str] = Field(default_factory=list, description="Raw contact information")
    profile_url: str = Field(..., description="LinkedIn profile URL")
    scraped_at: str = Field(..., description="Timestamp when scraped")
    scraping_success: bool = Field(True, description="Whether scraping was successful")
    error_message: Optional[str] = Field(None, description="Error message if scraping failed")


class LinkedInProfileScraper:
    """Scrapes LinkedIn profiles using PydanticAI and Playwright MCP."""
    
    def __init__(self, ollama_model: str = None, ollama_host: str = None):
        self.logger = logging.getLogger(__name__)
        self.output_file = Path("data/linkedin_profiles_detailed.json")
        self.output_file.parent.mkdir(parents=True, exist_ok=True)
        
        # MCP Server connection
        self.mcp_server_process = None
        self.browser_launched = False
        self.context_id = None
        self.page_id = None
        
        # Delay configuration
        self.delay_min = float(os.getenv('SCRAPER_DELAY_MIN', '3.0'))
        self.delay_max = float(os.getenv('SCRAPER_DELAY_MAX', '10.0'))
        
        # AI Configuration
        if not ollama_model:
            ollama_model = os.getenv('OLLAMA_MODEL', 'mistral-small:24b')
        if not ollama_host:
            ollama_host = os.getenv('OLLAMA_HOST', 'http://localhost:11434')
        
        # Create Ollama model using OpenAI provider
        ollama_model_instance = OpenAIModel(
            model_name=ollama_model,
            provider=OpenAIProvider(base_url=ollama_host + '/v1')
        )
        
        # Create PydanticAI agent for profile extraction
        self.scraping_agent = Agent(
            model=ollama_model_instance,
            result_type=LinkedInProfileData,
            system_prompt=self._get_scraping_prompt()
        )
    
    async def start_mcp_server(self):
        """Start our custom Playwright server."""
        try:
            self.logger.info("Starting custom Playwright server...")
            
            # Start the server process with stdin/stdout pipes
            self.mcp_server_process = subprocess.Popen(
                ["uv", "run", "python", "-m", "mcp_servers.playwright"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=0  # Unbuffered
            )
            
            # Wait a moment for the server to start
            await asyncio.sleep(2)
            
            if self.mcp_server_process.poll() is None:
                # Test the server with a health check
                health_result = await self.call_playwright_server("health_check", {})
                if health_result.get("success"):
                    self.logger.info("✅ Playwright server started and responding")
                    return True
                else:
                    self.logger.error(f"Server health check failed: {health_result}")
                    return False
            else:
                stdout, stderr = self.mcp_server_process.communicate()
                self.logger.error(f"Server failed to start: {stderr}")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to start server: {str(e)}")
            return False
    
    async def call_playwright_server(self, action: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """Call the simplified Playwright server with retry logic."""
        max_retries = 2
        base_timeout = 70.0  # Increased base timeout
        
        for attempt in range(max_retries + 1):
            try:
                if attempt > 0:
                    self.logger.info(f"🔄 Retry attempt {attempt}/{max_retries} for {action}")
                    # Exponential backoff delay before retry
                    retry_delay = 5 * (2 ** (attempt - 1))
                    await asyncio.sleep(retry_delay)
                
                self.logger.info(f"🔧 Calling server action: {action} (attempt {attempt + 1})")
                
                # Create command
                command = {
                    "action": action,
                    "args": args
                }
                
                # Send command to server via stdin/stdout
                if self.mcp_server_process and self.mcp_server_process.poll() is None:
                    self.logger.info(f"📤 Sending command to server: {action}")
                    
                    # Write command as string (since we used text=True)
                    command_json = json.dumps(command) + "\n"
                    self.mcp_server_process.stdin.write(command_json)
                    self.mcp_server_process.stdin.flush()
                    
                    self.logger.info(f"⏳ Waiting for server response (timeout: {base_timeout}s)...")
                    
                    # Read response with timeout (increased timeout)
                    try:
                        response_line = await asyncio.wait_for(
                            asyncio.to_thread(self.mcp_server_process.stdout.readline),
                            timeout=base_timeout
                        )
                        
                        if response_line:
                            self.logger.info(f"📥 Received server response")
                            response = json.loads(response_line.strip())
                            
                            # Check if response indicates success
                            if response.get("success") or not response.get("error"):
                                return response
                            elif attempt < max_retries:
                                self.logger.warning(f"⚠️ Server returned error, will retry: {response.get('error', 'Unknown error')}")
                                continue
                            else:
                                return response
                        else:
                            if attempt < max_retries:
                                self.logger.warning(f"⚠️ Empty response from server, will retry")
                                continue
                            else:
                                self.logger.error(f"❌ Empty response from server")
                                return {"error": "No response from server"}
                            
                    except asyncio.TimeoutError:
                        if attempt < max_retries:
                            self.logger.warning(f"⚠️ Server response timeout after {base_timeout} seconds, will retry")
                            continue
                        else:
                            self.logger.error(f"⏰ Server response timeout after {base_timeout} seconds (final attempt)")
                            return {"error": f"Server response timeout after {base_timeout} seconds"}
                        
                else:
                    self.logger.error(f"❌ Server not running (poll: {self.mcp_server_process.poll() if self.mcp_server_process else 'None'})")
                    
                    # Try to restart server if it's dead
                    if attempt < max_retries:
                        self.logger.info(f"🔄 Attempting to restart server...")
                        await self.cleanup_browser()
                        if await self.start_mcp_server():
                            continue
                    
                    return {"error": "Server not running"}
                    
            except Exception as e:
                if attempt < max_retries:
                    self.logger.warning(f"⚠️ Error calling Playwright server, will retry: {str(e)}")
                    continue
                else:
                    self.logger.error(f"💥 Error calling Playwright server (final attempt): {str(e)}")
                    return {"error": str(e)}
        
        return {"error": "Max retries exceeded"}
    
    async def initialize_browser(self):
        """Initialize browser with LinkedIn authentication."""
        # Browser initialization is now handled by the server for each request
        return True
    
    async def scrape_profile_direct(self, profile_url: str) -> Dict[str, Any]:
        """Directly scrape a LinkedIn profile using the Playwright server."""
        try:
            self.logger.info(f"🔍 Scraping profile: {profile_url}")
            
            # Call the server to scrape the profile
            result = await self.call_playwright_server("scrape_profile", {
                "profile_url": profile_url
            })
            
            # Log detailed results for debugging
            if result.get("success"):
                self.logger.info(f"✅ Profile scraped successfully")
                extracted_data = result.get("extracted_data", {})
                self.logger.info(f"📊 Extracted name: {extracted_data.get('full_name', 'N/A')}")
                self.logger.info(f"📊 Extracted headline: {extracted_data.get('headline', 'N/A')}")
                if result.get("screenshot_path"):
                    self.logger.info(f"📸 Screenshot saved: {result['screenshot_path']}")
            else:
                self.logger.error(f"❌ Profile scraping failed: {result.get('error', 'Unknown error')}")
                if result.get("screenshot_path"):
                    self.logger.error(f"📸 Error screenshot: {result['screenshot_path']}")
                if result.get("current_url"):
                    self.logger.error(f"🌐 Final URL: {result['current_url']}")
                if result.get("page_title"):
                    self.logger.error(f"📄 Page title: {result['page_title']}")
            
            return result
                
        except Exception as e:
            self.logger.error(f"Error scraping profile {profile_url}: {str(e)}")
            return {"error": str(e)}
    
    async def cleanup_browser(self):
        """Clean up browser resources."""
        try:
            if self.mcp_server_process:
                self.mcp_server_process.terminate()
                await asyncio.sleep(1)
                if self.mcp_server_process.poll() is None:
                    self.mcp_server_process.kill()
                self.mcp_server_process = None
            
            self.logger.info("✅ Server cleanup completed")
            
        except Exception as e:
            self.logger.error(f"Error during cleanup: {str(e)}")
    
    def _get_scraping_prompt(self) -> str:
        """Get the system prompt for the scraping agent."""
        return """
You are an expert web scraper specialized in extracting structured data from LinkedIn profiles.

Your task is to coordinate with a Playwright MCP server to navigate to LinkedIn profiles and extract comprehensive contact and professional information.

For each LinkedIn profile, you should:

1. Navigate to the profile URL
2. Wait for the page to load
3. Extract the following information systematically:
   - Full name (from main heading)
   - Professional headline/title
   - Location
   - About/summary section
   - Current position and company
   - Work experience (up to 5 recent entries)
   - Education (up to 3 entries)
   - Skills (up to 10)
   - Connection count
   - Any visible contact information

4. Handle errors gracefully and provide meaningful error messages

Use CSS selectors appropriate for LinkedIn's current layout:
- Name: "h1.text-heading-xlarge", ".pv-text-details__left-panel h1"
- Headline: ".text-body-medium.break-words", ".pv-text-details__left-panel .text-body-medium"
- Location: ".text-body-small.inline.t-black--light.break-words"
- About: ".pv-about-section .inline-show-more-text", "[data-field='summary']"
- Experience: "#experience ~ .pvs-list .pvs-entity"
- Education: "#education ~ .pvs-list .pvs-entity"
- Skills: "#skills ~ .pvs-list .pvs-entity__path"

Always return structured data even if some fields are missing. Mark scraping_success as false only if the navigation or page loading fails completely.
"""
    
    async def get_linkedin_connections(self) -> List[Dict[str, Any]]:
        """Get LinkedIn connections using the LinkedIn Member Snapshot API with pagination.
        
        The Member Snapshot API requires pagination to retrieve all connections.
        This method will make multiple API calls to collect all available connections.
        """
        access_token = os.getenv("LINKEDIN_ACCESS_TOKEN")
        if not access_token:
            raise ValueError("LINKEDIN_ACCESS_TOKEN not found in environment")
        
        all_connections = []
        start = 0
        count = 200  # Fetch 200 connections per page to minimize API calls
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            headers = {
                "Authorization": f"Bearer {access_token}",
                "LinkedIn-Version": "202312",
                "Content-Type": "application/json"
            }
            
            url = "https://api.linkedin.com/rest/memberSnapshotData"
            
            try:
                self.logger.info("Fetching LinkedIn connections via Member Snapshot API with pagination...")
                page_num = 1
                
                while True:
                    params = {
                        "q": "criteria",
                        "domain": "CONNECTIONS",
                        "start": start,
                        "count": count
                    }
                    
                    self.logger.info(f"Fetching batch {page_num} (start={start})...")
                    response = await client.get(url, headers=headers, params=params)
                    response.raise_for_status()
                    
                    data = response.json()
                    
                    # Log API response structure for debugging
                    paging = data.get("paging", {})
                    total_batches = paging.get('total', 0)
                    self.logger.info(f"Batch {page_num} paging info: start={paging.get('start', 'N/A')}, "
                                   f"total_batches={total_batches}")
                    
                    # Extract connections from this batch
                    page_connections = []
                    if "elements" in data:
                        for element in data["elements"]:
                            if "snapshotData" in element:
                                page_connections = element["snapshotData"]
                                break
                    
                    # If no connections found on this batch, we're done
                    if not page_connections:
                        self.logger.info(f"No more connections found on batch {page_num}, pagination complete")
                        break
                    
                    # Add connections from this batch
                    all_connections.extend(page_connections)
                    self.logger.info(f"Batch {page_num}: Found {len(page_connections)} connections "
                                   f"(total so far: {len(all_connections)})")
                    
                    # LinkedIn's Member Snapshot API uses batch-based pagination where:
                    # start=0 gets first batch, start=1 gets second batch, etc.
                    # The 'total' field indicates number of batches, not total connections
                    start += 1
                    page_num += 1
                    
                    # If we've reached the total number of batches, we're done
                    if start >= total_batches:
                        self.logger.info(f"Reached total batches ({total_batches}), pagination complete")
                        break
                    
                    # Add a small delay between API calls to be respectful
                    await asyncio.sleep(1.0)
                
                self.logger.info(f"✅ Pagination complete! Found {len(all_connections)} total LinkedIn connections across {page_num} pages")
                return all_connections
                            
            except Exception as e:
                self.logger.error(f"Error getting LinkedIn connections: {str(e)}")
                # Return whatever connections we managed to collect
                if all_connections:
                    self.logger.info(f"Returning {len(all_connections)} connections collected before error")
                return all_connections
    
    async def scrape_profile_with_ai(self, profile_url: str, connection_data: Dict[str, Any]) -> LinkedInProfileData:
        """Use our custom Playwright MCP server to scrape a LinkedIn profile."""
        self.logger.info(f"MCP scraping profile: {profile_url}")
        
        try:
            # Add timeout to prevent hanging (increased timeout)
            scrape_result = await asyncio.wait_for(
                self.scrape_profile_direct(profile_url),
                timeout=90.0  # 90 second timeout per profile (increased)
            )
            
            if not scrape_result.get("success"):
                # Return error data
                return LinkedInProfileData(
                    profile_url=profile_url,
                    scraped_at=datetime.now().isoformat(),
                    scraping_success=False,
                    error_message=scrape_result.get("error", "Unknown error"),
                    full_name=f"{connection_data.get('First Name', '')} {connection_data.get('Last Name', '')}".strip()
                )
            
            # Process the successfully scraped data
            extracted_data = scrape_result.get("extracted_data", {})
            
            # Extract structured contact fields
            email = extracted_data.get("contact_email", "")
            phone = extracted_data.get("contact_phone", "")
            website = extracted_data.get("contact_website", "")
            birthday = ""
            
            # Collect raw contact info for reference
            contact_info = []
            
            # Process other contact info to extract additional structured data
            if extracted_data.get("contact_other"):
                for item in extracted_data["contact_other"]:
                    # Clean whitespace
                    clean_item = ' '.join(item.split())
                    
                    # Skip empty or very short items
                    if len(clean_item) < 3:
                        continue
                    
                    # Skip items that are just linkedin URLs without useful info
                    if clean_item.startswith("linkedin.com/in/") and len(clean_item) < 30:
                        continue
                    
                    # Skip items that are just single words like "Website" or "Telefonnummer"
                    if len(clean_item.split()) == 1 and clean_item in ["Website", "Telefonnummer", "E-Mail-Adresse", "Geburtstag", "Vernetzt"]:
                        continue
                    
                    # Extract birthday from German text
                    if "Geburtstag" in clean_item or "Juni" in clean_item or "Januar" in clean_item or "Februar" in clean_item or "März" in clean_item or "April" in clean_item or "Mai" in clean_item or "Juli" in clean_item or "August" in clean_item or "September" in clean_item or "Oktober" in clean_item or "November" in clean_item or "Dezember" in clean_item:
                        # Extract date pattern like "20. Juni"
                        import re
                        date_match = re.search(r'\d{1,2}\. \w+', clean_item)
                        if date_match and not birthday:
                            birthday = date_match.group()
                    
                    # Extract additional email if not already found
                    if "@" in clean_item and not email:
                        import re
                        email_match = re.search(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', clean_item)
                        if email_match:
                            email = email_match.group()
                    
                    # Extract additional phone if not already found (skip LinkedIn URLs)
                    if (any(char.isdigit() for char in clean_item) and not phone and len(clean_item) > 8 and
                        'linkedin.com' not in clean_item.lower()):
                        import re
                        phone_match = re.search(r'[\+]?[0-9][\d\s\-–—\(\)\.]{8,}', clean_item)
                        if phone_match:
                            # Clean up phone number (preserve original formatting for display)
                            clean_phone = phone_match.group().strip()
                            
                            # Extract digits only for validation
                            digits_only = re.sub(r'\D', '', clean_phone)
                            
                            # More restrictive validation - avoid years, dates, short numbers
                            if (len(digits_only) >= 9 and len(digits_only) <= 15 and
                                not re.match(r'^(19|20)\d{2}$', digits_only) and  # Not a 4-digit year
                                not re.match(r'^(19|20)\d{6}$', digits_only) and  # Not a date like 20250618
                                not re.match(r'^\d{4}$', digits_only) and         # Not a 4-digit number
                                not re.match(r'^\d{2}$', digits_only)):           # Not a 2-digit number
                                phone = clean_phone
                    
                    # Extract additional website if not already found
                    if ("http" in clean_item or ".de" in clean_item or ".com" in clean_item) and not website:
                        import re
                        # Look for URLs or domain names
                        url_match = re.search(r'https?://[^\s]+|[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}/?[^\s]*', clean_item)
                        if url_match:
                            found_url = url_match.group()
                            if not found_url.startswith("http"):
                                found_url = "https://" + found_url
                            website = found_url
                    
                    contact_info.append(clean_item)
            
            # Map the extracted data to our model with structured contact fields
            return LinkedInProfileData(
                full_name=extracted_data.get("full_name", ""),
                headline=extracted_data.get("headline", ""),
                location=extracted_data.get("location", ""),
                about=extracted_data.get("about", ""),
                current_position=extracted_data.get("current_position", ""),
                experience=extracted_data.get("experience", []),
                education=extracted_data.get("education", []),
                skills=extracted_data.get("skills", []),
                connections_count=extracted_data.get("connections_count", ""),
                # Structured contact fields for syncing
                email=email if email else None,
                phone=phone if phone else None,
                website=website if website else None,
                birthday=birthday if birthday else None,
                # Raw contact info for reference
                contact_info=contact_info,
                profile_url=profile_url,
                scraped_at=datetime.now().isoformat(),
                scraping_success=True
            )
            
        except asyncio.TimeoutError:
            self.logger.error(f"Timeout after 90 seconds for {profile_url}")
            
            # Return timeout error data
            return LinkedInProfileData(
                profile_url=profile_url,
                scraped_at=datetime.now().isoformat(),
                scraping_success=False,
                error_message="Timeout after 90 seconds",
                full_name=f"{connection_data.get('First Name', '')} {connection_data.get('Last Name', '')}".strip()
            )
        
        except Exception as e:
            self.logger.error(f"MCP+AI scraping failed for {profile_url}: {str(e)}")
            
            # Return error data
            return LinkedInProfileData(
                profile_url=profile_url,
                scraped_at=datetime.now().isoformat(),
                scraping_success=False,
                error_message=str(e),
                full_name=f"{connection_data.get('First Name', '')} {connection_data.get('Last Name', '')}".strip()
            )
    
    async def load_existing_profiles(self) -> List[LinkedInProfileData]:
        """Load existing scraped profiles from JSON file."""
        if not self.output_file.exists():
            self.logger.info("No existing profiles file found, starting fresh")
            return []
        
        try:
            with open(self.output_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            profiles_data = data.get('profiles', [])
            existing_profiles = []
            
            for profile_dict in profiles_data:
                try:
                    profile = LinkedInProfileData(**profile_dict)
                    existing_profiles.append(profile)
                except Exception as e:
                    self.logger.warning(f"Skipping invalid profile data: {e}")
            
            self.logger.info(f"Loaded {len(existing_profiles)} existing profiles from {self.output_file}")
            return existing_profiles
            
        except Exception as e:
            self.logger.error(f"Error loading existing profiles: {e}")
            return []
    
    def get_scraped_urls(self, profiles: List[LinkedInProfileData]) -> set:
        """Get set of already scraped profile URLs."""
        return {profile.profile_url for profile in profiles if profile.profile_url}
    
    async def scrape_all_profiles(self, max_profiles: Optional[int] = None, delay_seconds: float = 3.0) -> List[LinkedInProfileData]:
        """Scrape all LinkedIn connection profiles using our custom MCP server."""
        try:
            # Load existing profiles to resume from where we left off
            existing_profiles = await self.load_existing_profiles()
            scraped_urls = self.get_scraped_urls(existing_profiles)
            
            self.logger.info(f"Resume mode: Found {len(existing_profiles)} existing profiles, {len(scraped_urls)} unique URLs")
            
            # Start MCP server
            if not await self.start_mcp_server():
                self.logger.error("Failed to start MCP server")
                return existing_profiles
            
            # Get LinkedIn connections
            connections = await self.get_linkedin_connections()
            
            if not connections:
                self.logger.error("No LinkedIn connections found")
                return existing_profiles
            
            # Filter out already scraped connections
            remaining_connections = []
            for conn in connections:
                profile_url = conn.get("URL", "")
                if profile_url and profile_url not in scraped_urls:
                    remaining_connections.append(conn)
            
            self.logger.info(f"Total connections: {len(connections)}, Already scraped: {len(connections) - len(remaining_connections)}, Remaining: {len(remaining_connections)}")
            
            if max_profiles:
                remaining_connections = remaining_connections[:max_profiles]
                self.logger.info(f"Limited to first {max_profiles} remaining profiles")
            
            if not remaining_connections:
                self.logger.info("All connections already scraped!")
                return existing_profiles
            
            # Initialize browser with LinkedIn cookies
            if not await self.initialize_browser():
                self.logger.error("Failed to initialize browser")
                return existing_profiles
            
            # Start with existing profiles
            scraped_profiles = existing_profiles.copy()
            
            # Add heartbeat to detect freezing
            async def heartbeat():
                while True:
                    await asyncio.sleep(30)  # Heartbeat every 30 seconds
                    self.logger.info(f"💓 Heartbeat - Main loop is alive")
            
            # Start heartbeat task
            heartbeat_task = asyncio.create_task(heartbeat())
            
            try:
                for i, connection in enumerate(remaining_connections):
                    profile_url = connection.get("URL", "")
                    total_count = len(existing_profiles) + i + 1
                    total_target = len(existing_profiles) + len(remaining_connections)
                    
                    self.logger.info(f"🔵 Starting iteration {i+1}/{len(remaining_connections)} (total progress: {total_count}/{total_target}) for profile: {profile_url}")
                    
                    if not profile_url:
                        self.logger.warning(f"No URL found for connection {i+1}")
                        # Create error entry
                        scraped_profiles.append(LinkedInProfileData(
                            profile_url="",
                            scraped_at=datetime.now().isoformat(),
                            scraping_success=False,
                            error_message="No profile URL found",
                            full_name=f"{connection.get('First Name', '')} {connection.get('Last Name', '')}".strip()
                        ))
                        continue
                    
                    try:
                        self.logger.info(f"🔄 MCP+AI scraping profile {i+1}/{len(remaining_connections)} (total: {total_count}/{total_target}): {profile_url}")
                        start_time = datetime.now()
                        
                        # Use MCP+AI to scrape the profile
                        self.logger.info(f"🚀 Starting profile AI scraping for {i+1}/{len(remaining_connections)}")
                        profile_data = await self.scrape_profile_with_ai(profile_url, connection)
                        self.logger.info(f"✨ Finished profile AI scraping for {i+1}/{len(remaining_connections)}")
                        
                        scraped_profiles.append(profile_data)
                        
                        # Log completion time
                        end_time = datetime.now()
                        duration = (end_time - start_time).total_seconds()
                        if profile_data.scraping_success:
                            self.logger.info(f"✅ Profile {i+1}/{len(remaining_connections)} (total: {total_count}/{total_target}) completed in {duration:.1f}s")
                        else:
                            self.logger.warning(f"❌ Profile {i+1}/{len(remaining_connections)} (total: {total_count}/{total_target}) failed in {duration:.1f}s: {profile_data.error_message}")
                        
                        # Save data after each successful profile to prevent data loss
                        self.logger.info(f"💾 Starting save for profile {i+1}/{len(remaining_connections)} (total: {total_count}/{total_target})...")
                        await self.save_profiles_to_json(scraped_profiles)
                        self.logger.info(f"✅ Saved progress after profile {i+1}/{len(remaining_connections)} (total: {total_count}/{total_target})")
                        
                        # Respectful delay between requests (randomized)
                        if i < len(remaining_connections) - 1:
                            # Increase delays if we're getting timeouts
                            if profile_data.scraping_success:
                                random_delay = random.uniform(self.delay_min, self.delay_max)
                            else:
                                # Longer delay after failures to avoid rate limiting
                                random_delay = random.uniform(self.delay_max, self.delay_max * 2)
                                self.logger.info(f"📉 Using longer delay due to failure")
                            
                            self.logger.info(f"⏱️  Starting delay of {random_delay:.1f} seconds before next profile...")
                            await asyncio.sleep(random_delay)
                            self.logger.info(f"⏱️  Delay completed, moving to next profile")
                            
                            # Restart server periodically to prevent memory leaks
                            if (i + 1) % 20 == 0:
                                self.logger.info(f"🔄 Restarting server after {i + 1} profiles to prevent memory leaks...")
                                await self.cleanup_browser()
                                if await self.start_mcp_server():
                                    self.logger.info(f"✅ Server restarted successfully")
                                else:
                                    self.logger.error(f"❌ Failed to restart server")
                                    break
                        
                    except Exception as e:
                        self.logger.error(f"Error scraping profile {profile_url}: {str(e)}")
                        # Create error entry
                        scraped_profiles.append(LinkedInProfileData(
                            profile_url=profile_url,
                            scraped_at=datetime.now().isoformat(),
                            scraping_success=False,
                            error_message=str(e),
                            full_name=f"{connection.get('First Name', '')} {connection.get('Last Name', '')}".strip()
                        ))
                        
                        # Save data even after errors to preserve progress
                        self.logger.info(f"💾 Saving progress after error on profile {i+1}/{len(remaining_connections)} (total: {total_count}/{total_target})...")
                        await self.save_profiles_to_json(scraped_profiles)
            
                return scraped_profiles
            finally:
                # Cancel heartbeat task
                heartbeat_task.cancel()
                try:
                    await heartbeat_task
                except asyncio.CancelledError:
                    pass
            
        finally:
            # Always cleanup browser resources
            await self.cleanup_browser()
    
    async def save_profiles_to_json(self, profiles: List[LinkedInProfileData]):
        """Save scraped profiles to JSON file."""
        try:
            # Convert Pydantic models to dictionaries
            profiles_data = [profile.model_dump() for profile in profiles]
            
            output_data = {
                "scraping_session": {
                    "timestamp": datetime.now().isoformat(),
                    "total_profiles": len(profiles),
                    "successful_scrapes": len([p for p in profiles if p.scraping_success]),
                    "failed_scrapes": len([p for p in profiles if not p.scraping_success]),
                    "scraper_type": "PydanticAI + Playwright MCP",
                    "ai_model": os.getenv('OLLAMA_MODEL', 'mistral-small:24b')
                },
                "profiles": profiles_data
            }
            
            with open(self.output_file, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"Saved {len(profiles)} profiles to {self.output_file}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error saving profiles to JSON: {str(e)}")
            return False


async def main():
    """Main scraping function."""
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('data/linkedin_scraper.log', mode='a')
        ]
    )
    
    logger = logging.getLogger(__name__)
    
    # Load environment variables
    env_path = Path(__file__).parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
    
    print("🤖 AI-Powered LinkedIn Profile Scraper")
    print("Using Custom Playwright MCP Server + LinkedIn Cookies + PydanticAI")
    print("=" * 70)
    
    # Check required environment variables
    if not os.getenv("LINKEDIN_ACCESS_TOKEN"):
        print("❌ LINKEDIN_ACCESS_TOKEN not found in environment")
        return
    
    # Check AI configuration
    print(f"🧠 AI Model: {os.getenv('OLLAMA_MODEL', 'mistral-small:24b')}")
    print(f"🔗 Ollama Host: {os.getenv('OLLAMA_HOST', 'http://localhost:11434')}")
    
    # Initialize scraper
    scraper = LinkedInProfileScraper()
    
    try:
        print("\n📱 Getting LinkedIn connections...")
        connections = await scraper.get_linkedin_connections()
        
        if not connections:
            print("❌ No LinkedIn connections found")
            return
        
        print(f"✅ Found {len(connections)} LinkedIn connections")
        
        # Check for environment variables from CLI
        max_profiles = None
        delay_seconds = 3.0
        
        if os.getenv('SCRAPER_MAX_PROFILES'):
            max_profiles = int(os.getenv('SCRAPER_MAX_PROFILES'))
            print(f"📊 Will scrape first {max_profiles} profiles (from CLI)")
        elif os.getenv('SCRAPER_DELAY'):
            delay_seconds = float(os.getenv('SCRAPER_DELAY'))
            print(f"⏱️ Using delay: {delay_seconds} seconds (from CLI)")
        else:
            # Interactive mode
            user_input = input(f"\n🤔 Scrape profiles with AI? (y/n/number): ").strip().lower()
            
            if user_input == 'n':
                print("❌ Scraping cancelled by user")
                return
            elif user_input.isdigit():
                max_profiles = int(user_input)
                print(f"📊 Will scrape first {max_profiles} profiles")
            elif user_input == 'y':
                print(f"📊 Will scrape all {len(connections)} profiles")
            else:
                print("❌ Invalid input, cancelling")
                return
        
        # Start AI scraping
        delay_min = float(os.getenv('SCRAPER_DELAY_MIN', '3.0'))
        delay_max = float(os.getenv('SCRAPER_DELAY_MAX', '10.0'))
        avg_delay = (delay_min + delay_max) / 2
        print(f"\n🚀 Starting AI-powered profile scraping...")
        print(f"⏱️ Estimated time: {(max_profiles or len(connections)) * avg_delay / 60:.1f} minutes (randomized {delay_min}-{delay_max}s delays)")
        print(f"🤖 Each profile will be analyzed by AI for optimal data extraction")
        
        profiles = await scraper.scrape_all_profiles(max_profiles=max_profiles, delay_seconds=delay_seconds)
        
        if profiles:
            print(f"\n💾 Saving {len(profiles)} profiles to JSON...")
            success = await scraper.save_profiles_to_json(profiles)
            
            if success:
                print(f"✅ Successfully saved profiles to: {scraper.output_file}")
                
                # Print summary
                successful = len([p for p in profiles if p.scraping_success])
                failed = len([p for p in profiles if not p.scraping_success])
                
                print(f"\n📊 AI Scraping Summary:")
                print(f"   ✅ Successful: {successful}")
                print(f"   ❌ Failed: {failed}")
                print(f"   📁 File: {scraper.output_file}")
                print(f"   📏 File size: {scraper.output_file.stat().st_size / 1024:.1f} KB")
                print(f"   🤖 AI Model: {os.getenv('OLLAMA_MODEL', 'mistral-small:24b')}")
                
                # Show sample data
                if successful > 0:
                    sample_profile = next(p for p in profiles if p.scraping_success)
                    print(f"\n📝 Sample extracted data:")
                    print(f"   Name: {sample_profile.full_name}")
                    print(f"   Headline: {sample_profile.headline}")
                    print(f"   Location: {sample_profile.location}")
                    print(f"   Skills: {len(sample_profile.skills)} found")
                    print(f"   Experience: {len(sample_profile.experience)} entries")
            else:
                print("❌ Failed to save profiles to JSON")
        else:
            print("❌ No profiles were scraped")
            
    except Exception as e:
        logger.error(f"Error in main scraping process: {str(e)}")
        print(f"❌ Scraping failed: {str(e)}")


if __name__ == "__main__":
    asyncio.run(main())