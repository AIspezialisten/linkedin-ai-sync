#!/usr/bin/env python3
"""
Test script for AI-powered duplicate detection using real LinkedIn and CRM data.

This script tests the Ollama/Mistral integration for finding duplicates between
LinkedIn contacts and Microsoft Dynamics CRM contacts.
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

# Import our modules
from sync.ai_duplicate_detection import DuplicateDetectionService, MatchConfidence
from list_crm_contacts_simple import list_crm_contacts
from count_connections import count_linkedin_connections


def setup_logging():
    """Set up logging for the test."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    return logging.getLogger(__name__)


async def get_linkedin_contacts():
    """Get LinkedIn contacts from the API."""
    import httpx
    
    access_token = os.getenv("LINKEDIN_ACCESS_TOKEN")
    if not access_token:
        print("❌ LINKEDIN_ACCESS_TOKEN not found")
        return []
    
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
                        return element["snapshotData"]
            
            return []
                        
        except Exception as e:
            print(f"❌ Error getting LinkedIn contacts: {str(e)}")
            return []


async def get_crm_contacts():
    """Get CRM contacts."""
    try:
        contacts = await list_crm_contacts()
        return contacts
    except Exception as e:
        print(f"❌ Error getting CRM contacts: {str(e)}")
        return []


async def test_single_comparison():
    """Test AI duplicate detection with a single comparison."""
    logger = setup_logging()
    
    print("🧪 Testing Single Contact Comparison")
    print("=" * 50)
    
    # Sample LinkedIn contact
    linkedin_contact = {
        "First Name": "John",
        "Last Name": "Doe", 
        "Company": "Tech Company Inc.",
        "Position": "Software Engineer",
        "URL": "https://www.linkedin.com/in/john-doe-123",
        "Email Address": "",
        "Connected On": "2024-01-15"
    }
    
    # Sample CRM contact
    crm_contact = {
        "contactid": "12345",
        "firstname": "John",
        "lastname": "Doe",
        "fullname": "John Doe",
        "emailaddress1": "john.doe@techcompany.com",
        "jobtitle": "Senior Software Engineer",
        "telephone1": "+1-555-0123",
        "address1_city": "San Francisco",
        "address1_country": "USA"
    }
    
    try:
        # Initialize the duplicate detection service
        detector = DuplicateDetectionService()
        
        print("🤖 Analyzing contacts with AI...")
        result = await detector.detector.compare_contacts(linkedin_contact, crm_contact)
        
        print(f"\n📊 AI Analysis Results:")
        print(f"  Is Duplicate: {result.is_duplicate}")
        print(f"  Confidence: {result.confidence}")
        print(f"  Similarity Score: {result.similarity_score:.2f}")
        print(f"  Reasoning: {result.reasoning}")
        print(f"  Matching Fields: {result.matching_fields}")
        print(f"  Conflicting Fields: {result.conflicting_fields}")
        
        return result.is_duplicate
        
    except Exception as e:
        print(f"❌ Error in AI analysis: {str(e)}")
        print("ℹ️  Make sure Ollama is running with mistral-small:24b model")
        print("    Run: ollama run mistral-small:24b")
        return False


async def test_real_data_analysis():
    """Test AI duplicate detection with real LinkedIn and CRM data."""
    logger = setup_logging()
    
    print("\n🔍 Testing with Real Data")
    print("=" * 50)
    
    # Get real data
    print("📥 Fetching LinkedIn contacts...")
    linkedin_contacts = await get_linkedin_contacts()
    
    print("📥 Fetching CRM contacts...")
    crm_contacts = await get_crm_contacts()
    
    if not linkedin_contacts:
        print("❌ No LinkedIn contacts found")
        return
    
    if not crm_contacts:
        print("❌ No CRM contacts found")
        return
    
    print(f"✅ Found {len(linkedin_contacts)} LinkedIn contacts")
    print(f"✅ Found {len(crm_contacts)} CRM contacts")
    
    try:
        # Initialize the duplicate detection service
        detector = DuplicateDetectionService()
        
        print("\n🤖 Running AI duplicate detection analysis...")
        analysis = await detector.analyze_linkedin_vs_crm(linkedin_contacts, crm_contacts)
        
        # Display results
        print(f"\n📊 AI Duplicate Analysis Results:")
        print(f"  LinkedIn contacts analyzed: {analysis['total_linkedin_contacts']}")
        print(f"  CRM contacts searched: {analysis['total_crm_contacts']}")
        print(f"  Contacts with potential duplicates: {analysis['contacts_with_potential_duplicates']}")
        print(f"  High confidence matches: {analysis['high_confidence_matches']}")
        print(f"  Medium confidence matches: {analysis['medium_confidence_matches']}")
        print(f"  Low confidence matches: {analysis['low_confidence_matches']}")
        
        # Show sync recommendations
        print(f"\n🔄 Sync Recommendations:")
        safe_contacts = analysis.get('contacts_safe_to_sync', [])
        review_contacts = analysis.get('contacts_need_review', [])
        
        print(f"  ✅ Safe to sync: {len(safe_contacts)} contacts")
        for contact in safe_contacts:
            print(f"    - {contact['linkedin_contact']}: {contact['action']}")
        
        print(f"  ⚠️  Need review: {len(review_contacts)} contacts")
        for contact in review_contacts:
            print(f"    - {contact['linkedin_contact']}: {contact['action']}")
            print(f"      Reason: {contact['reason']}")
        
        # Show detailed duplicate matches
        if analysis.get('duplicate_details'):
            print(f"\n🔍 Detailed Duplicate Analysis:")
            for contact_name, matches in analysis['duplicate_details'].items():
                print(f"\n  📝 {contact_name}:")
                for i, match in enumerate(matches):
                    crm_name = match.crm_contact.get('fullname', 'Unknown')
                    print(f"    {i+1}. Potential match: {crm_name}")
                    print(f"       Confidence: {match.confidence}")
                    print(f"       Score: {match.similarity_score:.2f}")
                    print(f"       Reasoning: {match.reasoning[:100]}...")
        
        # Save detailed results to file
        output_file = "ai_duplicate_analysis_results.json"
        with open(output_file, 'w') as f:
            json.dump(analysis, f, indent=2, default=str)
        print(f"\n💾 Detailed results saved to: {output_file}")
        
        return analysis
        
    except Exception as e:
        print(f"❌ Error in real data analysis: {str(e)}")
        print("ℹ️  Make sure Ollama is running with mistral-small:24b model")
        print("    Run: ollama run mistral-small:24b")
        return None


async def test_ollama_connection():
    """Test if Ollama is running and has the required model."""
    print("🔌 Testing Ollama Connection")
    print("=" * 30)
    
    try:
        import ollama
        
        # Test connection
        models = ollama.list()
        print("✅ Ollama is running")
        
        # Check for mistral-small model
        model_names = [model.model for model in models.models]
        if 'mistral-small:24b' in model_names:
            print("✅ mistral-small:24b model is available")
            return True
        else:
            print("❌ mistral-small:24b model not found")
            print("   Available models:", model_names)
            print("   Run: ollama pull mistral-small:24b")
            return False
            
    except Exception as e:
        print(f"❌ Ollama connection failed: {str(e)}")
        print("   Make sure Ollama is running: ollama serve")
        return False


async def main():
    """Main test function."""
    print("🚀 AI Duplicate Detection Test Suite")
    print("=" * 60)
    
    # Test 1: Ollama connection
    if not await test_ollama_connection():
        print("\n❌ Cannot proceed without Ollama. Please start Ollama and install mistral-small:24b")
        return
    
    # Test 2: Single comparison test
    print(f"\n" + "=" * 60)
    single_test_result = await test_single_comparison()
    
    # Test 3: Real data analysis
    print(f"\n" + "=" * 60)
    real_data_result = await test_real_data_analysis()
    
    # Summary
    print(f"\n" + "=" * 60)
    print("🎯 Test Summary")
    print("=" * 15)
    print(f"✅ Ollama connection: Working")
    print(f"{'✅' if single_test_result is not None else '❌'} Single comparison: {'Working' if single_test_result is not None else 'Failed'}")
    print(f"{'✅' if real_data_result is not None else '❌'} Real data analysis: {'Working' if real_data_result is not None else 'Failed'}")
    
    if real_data_result:
        print(f"\n🎉 AI duplicate detection is working!")
        print(f"   Found {real_data_result.get('contacts_with_potential_duplicates', 0)} contacts with potential duplicates")
        print(f"   Ready for intelligent synchronization!")
    else:
        print(f"\n⚠️  Some tests failed. Check Ollama setup and credentials.")


if __name__ == "__main__":
    asyncio.run(main())