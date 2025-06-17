#!/usr/bin/env python3
"""
Demo of the LinkedIn profile scraper workflow - showing the concept.
This creates mock scraped data to demonstrate the complete pipeline.
"""

import json
import os
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
import asyncio
import httpx


async def create_demo_scraped_data():
    """Create demo scraped LinkedIn profile data."""
    print("🎭 LinkedIn Profile Scraper - Demo Workflow")
    print("=" * 60)
    
    # Load environment
    env_path = Path(__file__).parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
    
    # 1. Get real LinkedIn connections for authentic URLs
    print("📱 Step 1: Fetching real LinkedIn connections...")
    
    access_token = os.getenv("LINKEDIN_ACCESS_TOKEN")
    if not access_token:
        print("❌ LINKEDIN_ACCESS_TOKEN not found")
        return False
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        headers = {
            "Authorization": f"Bearer {access_token}",
            "LinkedIn-Version": "202312",
            "Content-Type": "application/json"
        }
        
        url = "https://api.linkedin.com/rest/memberSnapshotData"
        params = {"q": "criteria", "domain": "CONNECTIONS"}
        
        response = await client.get(url, headers=headers, params=params)
        response.raise_for_status()
        
        data = response.json()
        connections = []
        
        if "elements" in data:
            for element in data["elements"]:
                if "snapshotData" in element:
                    connections = element["snapshotData"]
                    break
    
    if not connections:
        print("❌ No LinkedIn connections found")
        return False
    
    print(f"✅ Found {len(connections)} LinkedIn connections")
    
    # 2. Create enhanced mock data based on real connections
    print("\n🤖 Step 2: Creating enhanced profile data (simulating AI extraction)...")
    
    enhanced_profiles = []
    
    # Enhancement templates for different industries
    enhancements = {
        "tech": {
            "skills": ["Python", "JavaScript", "React", "AWS", "Docker", "Kubernetes", "AI/ML", "Data Science"],
            "about_template": "Experienced {position} with expertise in modern web technologies and cloud platforms. Passionate about building scalable solutions and leading high-performing teams.",
            "experience_template": [
                "Lead {position} at {company} (2022-Present) - Architecting scalable web applications",
                "Senior Software Engineer at TechCorp (2020-2022) - Built microservices architecture",
                "Software Engineer at StartupXYZ (2018-2020) - Full-stack development"
            ]
        },
        "sales": {
            "skills": ["Sales Strategy", "CRM", "Lead Generation", "Negotiations", "Account Management", "Business Development"],
            "about_template": "Results-driven {position} with proven track record in B2B sales and customer relationship management. Expert in driving revenue growth and building lasting client partnerships.",
            "experience_template": [
                "{position} at {company} (2021-Present) - Exceeded sales targets by 25%",
                "Sales Manager at SalesForce Inc (2019-2021) - Managed key accounts",
                "Account Executive at BusinessCorp (2017-2019) - Built new client relationships"
            ]
        },
        "marketing": {
            "skills": ["Digital Marketing", "SEO/SEM", "Content Strategy", "Social Media", "Analytics", "Brand Management"],
            "about_template": "Creative {position} specializing in digital marketing strategies and brand development. Proven ability to drive engagement and convert leads across multiple channels.",
            "experience_template": [
                "{position} at {company} (2020-Present) - Developed integrated marketing campaigns",
                "Marketing Manager at AdAgency (2018-2020) - Increased brand awareness by 40%",
                "Digital Marketing Specialist at MediaCorp (2016-2018) - Managed social campaigns"
            ]
        }
    }
    
    for i, connection in enumerate(connections):
        print(f"   Processing {i+1}/{len(connections)}: {connection.get('First Name', '')} {connection.get('Last Name', '')}")
        
        # Determine industry based on position/company
        position = connection.get('Position', '').lower()
        company = connection.get('Company', '').lower()
        
        if any(word in position + company for word in ['engineer', 'developer', 'tech', 'software', 'ai', 'data']):
            industry = "tech"
        elif any(word in position + company for word in ['sales', 'account', 'business development']):
            industry = "sales"
        elif any(word in position + company for word in ['marketing', 'brand', 'digital']):
            industry = "marketing"
        else:
            industry = "tech"  # Default
        
        enhancement = enhancements[industry]
        
        # Create enhanced profile data
        full_name = f"{connection.get('First Name', '')} {connection.get('Last Name', '')}".strip()
        
        enhanced_profile = {
            "full_name": full_name,
            "headline": connection.get('Position', 'Professional'),
            "location": "San Francisco Bay Area",  # Mock location
            "about": enhancement["about_template"].format(
                position=connection.get('Position', 'Professional'),
                company=connection.get('Company', 'Tech Company')
            ),
            "current_position": f"{connection.get('Position', 'Professional')} at {connection.get('Company', 'Company')}",
            "experience": [
                exp.format(
                    position=connection.get('Position', 'Professional'),
                    company=connection.get('Company', 'Company')
                ) for exp in enhancement["experience_template"]
            ],
            "education": [
                "Master of Business Administration - Stanford University (2014-2016)",
                f"Bachelor of Science - University of California (2010-2014)"
            ],
            "skills": enhancement["skills"],
            "connections_count": f"{500 + i * 50}+ connections",
            "contact_info": [f"{full_name.lower().replace(' ', '.')}@{connection.get('Company', 'company').lower().replace(' ', '')}.com"],
            "profile_url": connection.get('URL', ''),
            "scraped_at": datetime.now().isoformat(),
            "scraping_success": True,
            "original_connection_data": connection
        }
        
        enhanced_profiles.append(enhanced_profile)
    
    print(f"✅ Created {len(enhanced_profiles)} enhanced profiles")
    
    # 3. Save to JSON with metadata
    print("\n💾 Step 3: Saving enhanced data to JSON...")
    
    output_data = {
        "scraping_session": {
            "timestamp": datetime.now().isoformat(),
            "total_profiles": len(enhanced_profiles),
            "successful_scrapes": len(enhanced_profiles),
            "failed_scrapes": 0,
            "scraper_type": "Demo - Enhanced Mock Data",
            "ai_model": os.getenv('OLLAMA_MODEL', 'mistral-small:24b'),
            "description": "Demo data showing enhanced LinkedIn profiles with simulated AI extraction",
            "data_quality": {
                "profiles_with_skills": len([p for p in enhanced_profiles if p["skills"]]),
                "profiles_with_experience": len([p for p in enhanced_profiles if p["experience"]]),
                "profiles_with_about": len([p for p in enhanced_profiles if p["about"]]),
                "avg_skills_per_profile": sum(len(p["skills"]) for p in enhanced_profiles) / len(enhanced_profiles),
                "avg_experience_per_profile": sum(len(p["experience"]) for p in enhanced_profiles) / len(enhanced_profiles)
            }
        },
        "profiles": enhanced_profiles
    }
    
    output_file = Path("data/linkedin_profiles_detailed.json")
    output_file.parent.mkdir(exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Saved demo data to: {output_file}")
    print(f"   File size: {output_file.stat().st_size / 1024:.1f} KB")
    
    # 4. Display summary
    print("\n📊 Step 4: Data Summary")
    print("=" * 25)
    
    session = output_data["scraping_session"]
    quality = session["data_quality"]
    
    print(f"   Total profiles: {session['total_profiles']}")
    print(f"   Success rate: 100%")
    print(f"   Avg skills per profile: {quality['avg_skills_per_profile']:.1f}")
    print(f"   Avg experience entries: {quality['avg_experience_per_profile']:.1f}")
    
    # Show sample profiles
    print(f"\n📝 Sample Enhanced Profiles:")
    print("-" * 35)
    
    for i, profile in enumerate(enhanced_profiles[:3]):
        print(f"\n{i+1}. {profile['full_name']}")
        print(f"   🌐 URL: {profile['profile_url']}")
        print(f"   💼 Headline: {profile['headline']}")
        print(f"   📍 Location: {profile['location']}")
        print(f"   🎯 Skills: {len(profile['skills'])} - {', '.join(profile['skills'][:3])}...")
        print(f"   💼 Experience: {len(profile['experience'])} entries")
        print(f"   📧 Contact: {profile['contact_info'][0] if profile['contact_info'] else 'N/A'}")
        print(f"   📝 About: {profile['about'][:100]}...")
    
    if len(enhanced_profiles) > 3:
        print(f"\n   ... and {len(enhanced_profiles) - 3} more profiles")
    
    print(f"\n🎉 Demo Complete!")
    print(f"   This demonstrates what the AI-powered scraper would extract")
    print(f"   In production, this data would come from actual web scraping")
    print(f"   Use: python view_scraped_profiles.py to explore the data")
    
    return True


async def main():
    """Run the demo."""
    success = await create_demo_scraped_data()
    return success


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)