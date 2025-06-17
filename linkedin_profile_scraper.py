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
from pathlib import Path
from typing import Dict, List, Any, Optional
from dotenv import load_dotenv
import httpx
from datetime import datetime

from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider


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
    contact_info: List[str] = Field(default_factory=list, description="Contact information")
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
        """Get LinkedIn connections using the existing API."""
        access_token = os.getenv("LINKEDIN_ACCESS_TOKEN")
        if not access_token:
            raise ValueError("LINKEDIN_ACCESS_TOKEN not found in environment")
        
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
                
                if "elements" in data:
                    for element in data["elements"]:
                        if "snapshotData" in element:
                            connections = element["snapshotData"]
                            self.logger.info(f"Found {len(connections)} LinkedIn connections")
                            return connections
                
                return []
                            
            except Exception as e:
                self.logger.error(f"Error getting LinkedIn connections: {str(e)}")
                return []
    
    async def scrape_profile_with_ai(self, profile_url: str, connection_data: Dict[str, Any]) -> LinkedInProfileData:
        """Use PydanticAI to scrape a LinkedIn profile."""
        self.logger.info(f"AI scraping profile: {profile_url}")
        
        # Create a detailed prompt for the AI agent
        scraping_prompt = f"""
Please scrape this LinkedIn profile and extract structured data: {profile_url}

Original connection data from LinkedIn API:
- Name: {connection_data.get('First Name', '')} {connection_data.get('Last Name', '')}
- Company: {connection_data.get('Company', '')}
- Position: {connection_data.get('Position', '')}
- Connected On: {connection_data.get('Connected On', '')}

Steps to follow:
1. Create a new browser page
2. Navigate to the profile URL: {profile_url}
3. Wait for the page to load (3-5 seconds)
4. Extract all available profile information using appropriate CSS selectors
5. Take a screenshot for verification
6. Close the page when done

Important: 
- Handle any errors gracefully
- If navigation fails, return an error
- Extract as much data as possible even if some selectors don't work
- Be respectful with timing (wait between actions)
- Return structured data matching the LinkedInProfileData model

Current timestamp: {datetime.now().isoformat()}
"""
        
        try:
            # Run the AI scraping agent
            result = await self.scraping_agent.run(scraping_prompt)
            
            # Add metadata to the result
            profile_data = result.output
            profile_data.profile_url = profile_url
            profile_data.scraped_at = datetime.now().isoformat()
            
            self.logger.info(f"AI extraction completed for {profile_url}")
            return profile_data
            
        except Exception as e:
            self.logger.error(f"AI scraping failed for {profile_url}: {str(e)}")
            
            # Return error data
            return LinkedInProfileData(
                profile_url=profile_url,
                scraped_at=datetime.now().isoformat(),
                scraping_success=False,
                error_message=str(e),
                full_name=f"{connection_data.get('First Name', '')} {connection_data.get('Last Name', '')}".strip()
            )
    
    async def scrape_all_profiles(self, max_profiles: Optional[int] = None, delay_seconds: float = 3.0) -> List[LinkedInProfileData]:
        """Scrape all LinkedIn connection profiles using AI."""
        # Get LinkedIn connections
        connections = await self.get_linkedin_connections()
        
        if not connections:
            self.logger.error("No LinkedIn connections found")
            return []
        
        if max_profiles:
            connections = connections[:max_profiles]
            self.logger.info(f"Limited to first {max_profiles} profiles")
        
        scraped_profiles = []
        
        for i, connection in enumerate(connections):
            profile_url = connection.get("URL", "")
            
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
                self.logger.info(f"AI scraping profile {i+1}/{len(connections)}: {profile_url}")
                
                # Use AI to scrape the profile
                profile_data = await self.scrape_profile_with_ai(profile_url, connection)
                scraped_profiles.append(profile_data)
                
                # Respectful delay between requests
                if i < len(connections) - 1:
                    self.logger.info(f"Waiting {delay_seconds} seconds before next profile...")
                    await asyncio.sleep(delay_seconds)
                
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
        
        return scraped_profiles
    
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
    print("Using PydanticAI + Playwright MCP Server")
    print("=" * 60)
    
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
        print(f"\n🚀 Starting AI-powered profile scraping...")
        print(f"⏱️ Estimated time: {(max_profiles or len(connections)) * 3 / 60:.1f} minutes")
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