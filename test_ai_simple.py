#!/usr/bin/env python3
"""
Simple AI duplicate detection test with just a few contacts.
"""

import asyncio
import json
import os
import logging
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    load_dotenv(env_path)

from sync.ai_duplicate_detection import DuplicateDetectionService


def setup_logging():
    """Set up logging for the test."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    return logging.getLogger(__name__)


async def test_simple_ai_detection():
    """Test AI detection with just a few contacts."""
    logger = setup_logging()
    
    print("🤖 Simple AI Duplicate Detection Test")
    print("=" * 50)
    
    # Sample LinkedIn contacts (from your actual data)
    linkedin_contacts = [
        {
            "Company": "REDDOXX GmbH",
            "Position": "Head of Sales",
            "First Name": "Dennis",
            "Connected On": "27 Nov 2024",
            "Last Name": "Heinrich",
            "URL": "https://www.linkedin.com/in/dennis-heinrich-a06788265",
            "Email Address": ""
        },
        {
            "Company": "MI4People",
            "Position": "Co-Founder and Managing Director",
            "First Name": "Dr. Paul",
            "Connected On": "27 Nov 2024",
            "Last Name": "Springer",
            "URL": "https://www.linkedin.com/in/dr-paul-springer-94a5a817a",
            "Email Address": ""
        }
    ]
    
    # Sample CRM contacts (that might match)
    crm_contacts = [
        {
            "contactid": "7c9d7d23-0e4a-f011-877a-7c1e525035fc",
            "firstname": "Pierre",
            "lastname": "Heck",
            "fullname": "Pierre Heck",
            "emailaddress1": None,
            "jobtitle": "Head of Sales D-A-CH",
            "telephone1": "+49 (221) 59709 211"
        },
        {
            "contactid": "c7d91d45-2248-f011-877a-7c1e525035fc",
            "firstname": "Dennis",
            "lastname": "Entrop",
            "fullname": "Dennis Entrop",
            "emailaddress1": None,
            "jobtitle": None,
            "telephone1": None
        },
        {
            "contactid": "4d0a9084-c0e7-ef11-be20-7c1e52124a3f",
            "firstname": "Johannes",
            "lastname": "Keschl",
            "fullname": "Johannes Keschl",
            "emailaddress1": "johannes.keschl@stihl.at",
            "jobtitle": "kaufmännischer Leiter",
            "telephone1": None
        }
    ]
    
    print(f"📊 Test Data:")
    print(f"  LinkedIn contacts: {len(linkedin_contacts)}")
    print(f"  CRM contacts: {len(crm_contacts)}")
    
    try:
        # Initialize AI detector
        detector = DuplicateDetectionService()
        
        print(f"\n🔍 Testing AI duplicate detection...")
        
        # Test each LinkedIn contact against each CRM contact
        for i, linkedin_contact in enumerate(linkedin_contacts):
            linkedin_name = f"{linkedin_contact['First Name']} {linkedin_contact['Last Name']}"
            print(f"\n{i+1}. Testing LinkedIn contact: {linkedin_name}")
            print(f"   Company: {linkedin_contact['Company']}")
            print(f"   Position: {linkedin_contact['Position']}")
            
            best_match = None
            best_score = 0.0
            
            for j, crm_contact in enumerate(crm_contacts):
                crm_name = crm_contact['fullname']
                print(f"   Comparing with CRM contact: {crm_name}")
                
                # Run AI comparison
                result = await detector.detector.compare_contacts(linkedin_contact, crm_contact)
                
                print(f"     Result: {'DUPLICATE' if result.is_duplicate else 'DIFFERENT'}")
                print(f"     Confidence: {result.confidence}")
                print(f"     Score: {result.similarity_score:.2f}")
                print(f"     Reasoning: {result.reasoning[:100]}...")
                
                if result.similarity_score > best_score:
                    best_match = crm_contact
                    best_score = result.similarity_score
            
            if best_match:
                print(f"   🎯 Best match: {best_match['fullname']} (score: {best_score:.2f})")
            else:
                print(f"   ❌ No good matches found")
        
        print(f"\n✅ AI duplicate detection test completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error in AI detection: {str(e)}")
        return False


async def main():
    """Main test function."""
    success = await test_simple_ai_detection()
    
    if success:
        print(f"\n🎉 Test passed! AI duplicate detection is working correctly.")
    else:
        print(f"\n❌ Test failed. Check the error messages above.")


if __name__ == "__main__":
    asyncio.run(main())