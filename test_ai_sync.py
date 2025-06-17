#!/usr/bin/env python3
"""
Test script for AI-powered synchronization between LinkedIn and Dynamics CRM.

This script demonstrates the complete sync workflow with AI duplicate detection.
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
from sync.synchronizer import LinkedInDynamicsSynchronizer, SyncOrchestrator
from sync.ai_duplicate_detection import DuplicateDetectionService
from sync.cli import MockMCPClient


def setup_logging():
    """Set up logging for the test."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    return logging.getLogger(__name__)


async def test_ai_sync_workflow():
    """Test the complete AI-powered sync workflow."""
    logger = setup_logging()
    
    print("🔄 Testing AI-Powered Synchronization Workflow")
    print("=" * 60)
    
    # Sample LinkedIn contacts (your actual 4 contacts)
    linkedin_contacts = [
        {
            "Company": "VeeCollective GmbH",
            "Position": "Assistent Buchhaltung",
            "First Name": "Ardiana",
            "Connected On": "19 Mar 2025",
            "Last Name": "Krasniqi",
            "URL": "https://www.linkedin.com/in/ardiana-krasniqi-a52925284",
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
        },
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
            "Company": "Strong SD",
            "Position": "Lead Generation",
            "First Name": "Victoriia",
            "Connected On": "25 Feb 2025",
            "Last Name": "Malynovska",
            "URL": "https://www.linkedin.com/in/victoriia-malynovska-b85799236",
            "Email Address": ""
        }
    ]
    
    # Sample CRM contacts (subset of your actual CRM data)
    crm_contacts = [
        {
            "contactid": "4d0a9084-c0e7-ef11-be20-7c1e52124a3f",
            "firstname": "Johannes",
            "lastname": "Keschl",
            "fullname": "Johannes Keschl",
            "emailaddress1": "johannes.keschl@stihl.at",
            "jobtitle": "kaufmännischer Leiter",
            "telephone1": None,
            "createdon": "2025-02-10",
            "modifiedon": "2025-06-17"
        },
        {
            "contactid": "b88fdd1d-934a-f011-877a-7c1e525035fc",
            "firstname": "Sebastian",
            "lastname": "Winkler",
            "fullname": "Sebastian Winkler",
            "emailaddress1": "s.winkler@ekaflor.de",
            "jobtitle": "Geschäftsführer",
            "telephone1": "+49 (911) 9811666",
            "createdon": "2025-06-16",
            "modifiedon": "2025-06-16"
        },
        {
            "contactid": "7c9d7d23-0e4a-f011-877a-7c1e525035fc",
            "firstname": "Pierre",
            "lastname": "Heck",
            "fullname": "Pierre Heck",
            "emailaddress1": None,
            "jobtitle": "Head of Sales D-A-CH",
            "telephone1": "+49 (221) 59709 211",
            "createdon": "2025-06-15",
            "modifiedon": "2025-06-15"
        },
        {
            "contactid": "c7d91d45-2248-f011-877a-7c1e525035fc",
            "firstname": "Dennis",
            "lastname": "Entrop",
            "fullname": "Dennis Entrop",
            "emailaddress1": None,
            "jobtitle": None,
            "telephone1": None,
            "createdon": "2025-06-13",
            "modifiedon": "2025-06-13"
        }
    ]
    
    print(f"📊 Test Data:")
    print(f"  LinkedIn contacts: {len(linkedin_contacts)}")
    print(f"  CRM contacts: {len(crm_contacts)}")
    
    try:
        # Test 1: Initialize AI-powered synchronizer
        print(f"\n🤖 Step 1: Initializing AI-powered synchronizer...")
        
        # Use mock clients for testing
        linkedin_client = MockMCPClient("linkedin")
        dynamics_client = MockMCPClient("dynamics")
        
        synchronizer = LinkedInDynamicsSynchronizer(
            linkedin_client=linkedin_client,
            dynamics_client=dynamics_client,
            logger=logger,
            enable_ai_duplicate_detection=True,
            ollama_model="mistral-small:24b"
        )
        
        print(f"✅ Synchronizer initialized with AI duplicate detection")
        
        # Test 2: Run AI duplicate detection
        print(f"\n🔍 Step 2: Running AI duplicate detection...")
        
        ai_analysis = await synchronizer.find_duplicates_with_ai(
            linkedin_contacts, 
            crm_contacts
        )
        
        if "error" in ai_analysis:
            print(f"❌ AI analysis failed: {ai_analysis['error']}")
            return
        
        print(f"✅ AI analysis completed:")
        print(f"  Contacts with potential duplicates: {ai_analysis['contacts_with_potential_duplicates']}")
        print(f"  High confidence matches: {ai_analysis['high_confidence_matches']}")
        print(f"  Medium confidence matches: {ai_analysis['medium_confidence_matches']}")
        print(f"  Low confidence matches: {ai_analysis['low_confidence_matches']}")
        
        # Test 3: Show AI recommendations
        print(f"\n📋 Step 3: AI Recommendations:")
        
        safe_contacts = ai_analysis.get('contacts_safe_to_sync', [])
        review_contacts = ai_analysis.get('contacts_need_review', [])
        
        print(f"  ✅ Safe to sync ({len(safe_contacts)} contacts):")
        for contact in safe_contacts:
            print(f"    - {contact['linkedin_contact']}: {contact['action']}")
            print(f"      Reason: {contact['reason']}")
        
        print(f"  ⚠️  Need review ({len(review_contacts)} contacts):")
        for contact in review_contacts:
            print(f"    - {contact['linkedin_contact']}: {contact['action']}")
            print(f"      Reason: {contact['reason']}")
        
        # Test 4: Run AI-powered sync
        print(f"\n🔄 Step 4: Running AI-powered synchronization...")
        
        stats, results, full_analysis = await synchronizer.sync_batch_with_ai_detection(
            linkedin_contacts,
            crm_contacts,
            auto_sync_safe_contacts=True
        )
        
        print(f"✅ AI-powered sync completed:")
        print(f"  Total processed: {stats.total_processed}")
        print(f"  Created: {stats.created}")
        print(f"  Updated: {stats.updated}")
        print(f"  Skipped: {stats.skipped}")
        print(f"  Errors: {stats.errors}")
        
        # Test 5: Show detailed results
        print(f"\n📊 Step 5: Detailed Results:")
        
        for result in results:
            contact_info = result.linkedin_id or "Unknown contact"
            print(f"  {result.action}: {contact_info}")
            print(f"    Message: {result.message}")
            if result.details:
                print(f"    Details: {json.dumps(result.details, indent=6)}")
        
        # Save results
        output_file = "ai_sync_test_results.json"
        with open(output_file, 'w') as f:
            json.dump({
                "stats": {
                    "total_processed": stats.total_processed,
                    "created": stats.created,
                    "updated": stats.updated,
                    "skipped": stats.skipped,
                    "errors": stats.errors,
                    "start_time": stats.start_time.isoformat(),
                    "end_time": stats.end_time.isoformat() if stats.end_time else None
                },
                "ai_analysis": full_analysis,
                "results": [
                    {
                        "success": r.success,
                        "message": r.message,
                        "action": r.action,
                        "linkedin_id": r.linkedin_id,
                        "crm_contact_id": r.crm_contact_id,
                        "details": r.details
                    } for r in results
                ]
            }, f, indent=2, default=str)
        
        print(f"\n💾 Test results saved to: {output_file}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error in AI sync workflow: {str(e)}")
        print("ℹ️  Make sure Ollama is running with mistral-small:24b model")
        return False


async def test_ollama_setup():
    """Test if Ollama is properly set up."""
    print("🔌 Testing Ollama Setup")
    print("=" * 30)
    
    try:
        import ollama
        
        # Test connection
        models = ollama.list()
        print("✅ Ollama is running")
        
        # Check for mistral-small model
        model_names = [model['name'] for model in models['models']]
        if 'mistral-small:24b' in model_names:
            print("✅ mistral-small:24b model is available")
            
            # Test a simple generation
            response = ollama.generate(
                model='mistral-small:24b',
                prompt='Say "Hello from Mistral!"',
                stream=False
            )
            print("✅ Model generation test successful")
            print(f"   Response: {response['response'].strip()}")
            return True
        else:
            print("❌ mistral-small:24b model not found")
            print("   Available models:", model_names)
            print("   Run: ollama pull mistral-small:24b")
            return False
            
    except Exception as e:
        print(f"❌ Ollama setup failed: {str(e)}")
        print("   Make sure Ollama is running: ollama serve")
        return False


async def main():
    """Main test function."""
    print("🚀 AI-Powered Synchronization Test Suite")
    print("=" * 60)
    
    # Test Ollama setup first
    if not await test_ollama_setup():
        print("\n❌ Cannot proceed without proper Ollama setup")
        print("   1. Start Ollama: ollama serve")
        print("   2. Install model: ollama pull mistral-small:24b")
        return
    
    # Run the AI sync workflow test
    print(f"\n" + "=" * 60)
    success = await test_ai_sync_workflow()
    
    # Summary
    print(f"\n" + "=" * 60)
    print("🎯 Test Summary")
    print("=" * 15)
    if success:
        print("🎉 All tests passed!")
        print("   AI-powered duplicate detection is working")
        print("   Intelligent synchronization is ready to use")
        print("\n📖 Next steps:")
        print("   1. Review ai_sync_test_results.json for detailed analysis")
        print("   2. Use the CLI with --ai-detection flag for real syncing")
        print("   3. Manually review contacts marked for review")
    else:
        print("❌ Tests failed. Check the error messages above.")


if __name__ == "__main__":
    asyncio.run(main())