#!/usr/bin/env python3
"""
View and analyze scraped LinkedIn profile data.
"""

import json
import sys
from pathlib import Path
from datetime import datetime


def view_scraped_profiles():
    """View the scraped LinkedIn profiles data."""
    data_file = Path("data/linkedin_profiles_detailed.json")
    
    if not data_file.exists():
        print("❌ No scraped profile data found")
        print(f"   Expected file: {data_file}")
        print("   Run: uv run linkedin-sync scrape-profiles")
        return
    
    try:
        with open(data_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        session = data.get('scraping_session', {})
        profiles = data.get('profiles', [])
        
        print("📊 LinkedIn Profile Scraping Results")
        print("=" * 50)
        
        # Session info
        print(f"🕐 Scraped: {session.get('timestamp', 'Unknown')}")
        print(f"📱 Total profiles: {session.get('total_profiles', 0)}")
        print(f"✅ Successful: {session.get('successful_scrapes', 0)}")
        print(f"❌ Failed: {session.get('failed_scrapes', 0)}")
        print(f"🤖 AI Model: {session.get('ai_model', 'Unknown')}")
        print(f"🛠️ Scraper: {session.get('scraper_type', 'Unknown')}")
        
        if not profiles:
            print("\n❌ No profile data found")
            return
        
        # Show sample successful profiles
        successful_profiles = [p for p in profiles if p.get('scraping_success', False)]
        failed_profiles = [p for p in profiles if not p.get('scraping_success', True)]
        
        if successful_profiles:
            print(f"\n✅ Successful Profiles ({len(successful_profiles)}):")
            print("-" * 30)
            
            for i, profile in enumerate(successful_profiles[:5]):  # Show first 5
                print(f"\n{i+1}. {profile.get('full_name', 'Unknown')}")
                print(f"   🌐 URL: {profile.get('profile_url', '')}")
                print(f"   💼 Headline: {profile.get('headline', 'Not found')}")
                print(f"   📍 Location: {profile.get('location', 'Not found')}")
                print(f"   🏢 Current Position: {profile.get('current_position', 'Not found')}")
                
                skills = profile.get('skills', [])
                experience = profile.get('experience', [])
                education = profile.get('education', [])
                
                print(f"   🎯 Skills: {len(skills)} found")
                if skills:
                    print(f"      {', '.join(skills[:3])}{'...' if len(skills) > 3 else ''}")
                
                print(f"   💼 Experience: {len(experience)} entries")
                print(f"   🎓 Education: {len(education)} entries")
            
            if len(successful_profiles) > 5:
                print(f"\n   ... and {len(successful_profiles) - 5} more successful profiles")
        
        if failed_profiles:
            print(f"\n❌ Failed Profiles ({len(failed_profiles)}):")
            print("-" * 25)
            
            for i, profile in enumerate(failed_profiles[:3]):  # Show first 3 failures
                print(f"\n{i+1}. {profile.get('full_name', 'Unknown')}")
                print(f"   🌐 URL: {profile.get('profile_url', '')}")
                print(f"   ❌ Error: {profile.get('error_message', 'Unknown error')}")
            
            if len(failed_profiles) > 3:
                print(f"\n   ... and {len(failed_profiles) - 3} more failed profiles")
        
        # Data quality analysis
        print(f"\n📈 Data Quality Analysis:")
        print("-" * 25)
        
        if successful_profiles:
            # Count fields with data
            fields = ['full_name', 'headline', 'location', 'about', 'current_position']
            field_counts = {}
            
            for field in fields:
                count = sum(1 for p in successful_profiles if p.get(field))
                field_counts[field] = count
                percentage = (count / len(successful_profiles)) * 100
                print(f"   {field.replace('_', ' ').title()}: {count}/{len(successful_profiles)} ({percentage:.1f}%)")
            
            # Average counts
            avg_skills = sum(len(p.get('skills', [])) for p in successful_profiles) / len(successful_profiles)
            avg_experience = sum(len(p.get('experience', [])) for p in successful_profiles) / len(successful_profiles)
            avg_education = sum(len(p.get('education', [])) for p in successful_profiles) / len(successful_profiles)
            
            print(f"\n📊 Average per profile:")
            print(f"   Skills: {avg_skills:.1f}")
            print(f"   Experience entries: {avg_experience:.1f}")
            print(f"   Education entries: {avg_education:.1f}")
        
        # File info
        file_size = data_file.stat().st_size
        print(f"\n📁 File Information:")
        print(f"   Path: {data_file}")
        print(f"   Size: {file_size / 1024:.1f} KB")
        print(f"   Modified: {datetime.fromtimestamp(data_file.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S')}")
        
    except Exception as e:
        print(f"❌ Error reading profile data: {str(e)}")


def main():
    """Main function."""
    if len(sys.argv) > 1 and sys.argv[1] in ['--help', '-h']:
        print("📊 LinkedIn Profile Data Viewer")
        print("Usage: python view_scraped_profiles.py")
        print("Views data from: /app/data/linkedin_profiles_detailed.json")
        return
    
    view_scraped_profiles()


if __name__ == "__main__":
    main()