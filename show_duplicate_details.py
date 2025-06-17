#!/usr/bin/env python3
"""
Show detailed example of AI duplicate detection.
"""

import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    load_dotenv(env_path)

from sync.ai_duplicate_detection import DuplicateDetectionService


async def show_duplicate_example():
    """Show a detailed example of duplicate detection."""
    print("🔍 AI Duplicate Detection Example")
    print("=" * 50)
    
    # Create realistic test contacts that might be duplicates
    linkedin_contact = {
        "First Name": "John",
        "Last Name": "Smith",
        "Company": "Microsoft Corporation",
        "Position": "Senior Software Engineer",
        "URL": "https://www.linkedin.com/in/john-smith-123",
        "Email Address": "",
        "Connected On": "2024-01-15"
    }
    
    crm_contact = {
        "contactid": "12345-abcd-6789",
        "firstname": "John",
        "lastname": "Smith",
        "fullname": "John Smith",
        "emailaddress1": "j.smith@microsoft.com",
        "jobtitle": "Software Engineer",
        "telephone1": "+1-555-0123",
        "address1_city": "Seattle",
        "address1_country": "USA"
    }
    
    print("📝 Contact Comparison:")
    print()
    print("LinkedIn Contact:")
    print(f"  Name: {linkedin_contact['First Name']} {linkedin_contact['Last Name']}")
    print(f"  Company: {linkedin_contact['Company']}")
    print(f"  Position: {linkedin_contact['Position']}")
    print(f"  Email: {linkedin_contact['Email Address'] or 'Not provided'}")
    print()
    print("CRM Contact:")
    print(f"  Name: {crm_contact['firstname']} {crm_contact['lastname']}")
    print(f"  Job Title: {crm_contact['jobtitle']}")
    print(f"  Email: {crm_contact['emailaddress1']}")
    print(f"  Phone: {crm_contact['telephone1']}")
    print(f"  Location: {crm_contact['address1_city']}, {crm_contact['address1_country']}")
    
    try:
        # Initialize the duplicate detection service
        detector = DuplicateDetectionService()
        
        print("\n🤖 AI Analysis in Progress...")
        result = await detector.detector.compare_contacts(linkedin_contact, crm_contact)
        
        print(f"\n📊 AI Analysis Results:")
        print(f"  🎯 Duplicate Found: {'YES' if result.is_duplicate else 'NO'}")
        print(f"  🎚️  Confidence Level: {result.confidence.value.upper()}")
        print(f"  📈 Similarity Score: {result.similarity_score:.2f} / 1.00")
        print(f"  💭 AI Reasoning: {result.reasoning}")
        
        if result.matching_fields:
            print(f"  ✅ Matching Fields: {', '.join(result.matching_fields)}")
        
        if result.conflicting_fields:
            print(f"  ❌ Conflicting Fields: {', '.join(result.conflicting_fields)}")
        
        print(f"\n🎯 Conclusion:")
        if result.confidence.value == "high":
            print("  → These contacts are very likely the same person")
        elif result.confidence.value == "medium":
            print("  → These contacts are probably the same person")
        elif result.confidence.value == "low":
            print("  → These contacts might be the same person")
        else:
            print("  → These contacts are different people")
        
        return result
        
    except Exception as e:
        print(f"❌ Error in AI analysis: {str(e)}")
        return None


async def main():
    """Main function."""
    result = await show_duplicate_example()
    
    if result:
        print(f"\n✅ Successfully demonstrated AI duplicate detection!")
    else:
        print(f"\n❌ Failed to run AI duplicate detection.")


if __name__ == "__main__":
    asyncio.run(main())