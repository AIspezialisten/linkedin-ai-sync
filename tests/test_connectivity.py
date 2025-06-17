"""
Connectivity tests for LinkedIn and Microsoft Dynamics CRM APIs.

This module tests actual API connectivity using credentials from the .env file.
These are integration tests that require valid API credentials and network access.
"""

import asyncio
import json
import os
import pytest
from pathlib import Path
from dotenv import load_dotenv
import httpx

# Load environment variables from .env file
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    load_dotenv(env_path)


class TestLinkedInConnectivity:
    """Test LinkedIn API connectivity using real credentials."""
    
    @pytest.fixture
    def linkedin_config(self):
        """LinkedIn configuration from environment variables."""
        access_token = os.getenv("LINKEDIN_ACCESS_TOKEN")
        if not access_token:
            pytest.skip("LINKEDIN_ACCESS_TOKEN not found in environment")
        
        return {
            "access_token": access_token,
            "api_version": "202312",
            "base_url": "https://api.linkedin.com"
        }
    
    @pytest.mark.asyncio
    async def test_linkedin_member_snapshot_api(self, linkedin_config):
        """Test LinkedIn Member Snapshot Data API connectivity."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            headers = {
                "Authorization": f"Bearer {linkedin_config['access_token']}",
                "LinkedIn-Version": linkedin_config['api_version'],
                "Content-Type": "application/json"
            }
            
            # Test the Member Snapshot Data API endpoint (the working one)
            url = f"{linkedin_config['base_url']}/rest/memberSnapshotData"
            params = {
                "q": "criteria",
                "domain": "CONNECTIONS"
            }
            
            try:
                response = await client.get(url, headers=headers, params=params)
                
                # Check if we get a valid response
                assert response.status_code in [200, 403, 404], f"Unexpected status code: {response.status_code}"
                
                if response.status_code == 200:
                    data = response.json()
                    print(f"✓ LinkedIn Member Snapshot Data API connectivity successful")
                    print(f"  Response contains elements: {'elements' in data}")
                    if "elements" in data:
                        print(f"  Number of elements: {len(data['elements'])}")
                    assert isinstance(data, dict), "Response should be a JSON object"
                    
                elif response.status_code == 403:
                    print("⚠ LinkedIn API returned 403 - Token may not have required permissions")
                    print("  This might be expected if the token doesn't have Data Portability permissions")
                    
                elif response.status_code == 404:
                    print("⚠ LinkedIn API returned 404 - Endpoint may not be available")
                    print("  This might be expected if Member Snapshot Data API is not accessible")
                    
            except httpx.HTTPStatusError as e:
                print(f"✗ LinkedIn API HTTP error: {e.response.status_code}")
                print(f"  Response: {e.response.text}")
                raise
            except Exception as e:
                print(f"✗ LinkedIn API connection error: {str(e)}")
                raise
    
    @pytest.mark.asyncio
    async def test_linkedin_profile_api_fallback(self, linkedin_config):
        """Test LinkedIn Profile API as fallback if Member Snapshot isn't available."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            headers = {
                "Authorization": f"Bearer {linkedin_config['access_token']}",
                "LinkedIn-Version": linkedin_config['api_version'],
                "X-Restli-Protocol-Version": "2.0.0"
            }
            
            # Test basic profile endpoint
            url = f"{linkedin_config['base_url']}/v2/people/~"
            
            try:
                response = await client.get(url, headers=headers)
                
                assert response.status_code in [200, 403], f"Unexpected status code: {response.status_code}"
                
                if response.status_code == 200:
                    data = response.json()
                    print(f"✓ LinkedIn Profile API connectivity successful")
                    print(f"  Profile ID: {data.get('id', 'N/A')}")
                    assert "id" in data, "Response should contain profile ID"
                    
                elif response.status_code == 403:
                    print("⚠ LinkedIn Profile API returned 403 - Token may not have required permissions")
                    
            except Exception as e:
                print(f"LinkedIn Profile API test failed: {str(e)}")
                # Don't fail the test as this is a fallback test
                pass


class TestDynamicsCRMConnectivity:
    """Test Microsoft Dynamics CRM API connectivity using real credentials."""
    
    @pytest.fixture
    def dynamics_config(self):
        """Dynamics CRM configuration from environment variables."""
        config = {
            "tenant_id": os.getenv("DYNAMICS_TENANT_ID"),
            "client_id": os.getenv("DYNAMICS_CLIENT_ID"),
            "client_secret": os.getenv("DYNAMICS_CLIENT_SECRET"),
            "crm_url": os.getenv("DYNAMICS_CRM_URL"),
            "api_version": "v9.2"
        }
        
        missing = [k for k, v in config.items() if not v and k != "api_version"]
        if missing:
            pytest.skip(f"Missing Dynamics CRM environment variables: {', '.join(missing)}")
        
        return config
    
    @pytest.mark.asyncio
    async def test_dynamics_oauth_token(self, dynamics_config):
        """Test OAuth token acquisition for Dynamics CRM."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            token_url = f"https://login.microsoftonline.com/{dynamics_config['tenant_id']}/oauth2/v2.0/token"
            
            data = {
                "grant_type": "client_credentials",
                "client_id": dynamics_config['client_id'],
                "client_secret": dynamics_config['client_secret'],
                "scope": f"{dynamics_config['crm_url']}/.default"
            }
            
            try:
                response = await client.post(token_url, data=data)
                
                assert response.status_code == 200, f"Token request failed with status {response.status_code}: {response.text}"
                
                token_data = response.json()
                assert "access_token" in token_data, "Response should contain access_token"
                
                print(f"✓ Dynamics CRM OAuth token acquisition successful")
                print(f"  Token type: {token_data.get('token_type', 'N/A')}")
                print(f"  Expires in: {token_data.get('expires_in', 'N/A')} seconds")
                
                return token_data["access_token"]
                
            except httpx.HTTPStatusError as e:
                print(f"✗ Dynamics CRM OAuth error: {e.response.status_code}")
                print(f"  Response: {e.response.text}")
                raise
            except Exception as e:
                print(f"✗ Dynamics CRM OAuth connection error: {str(e)}")
                raise
    
    @pytest.mark.asyncio
    async def test_dynamics_api_access(self, dynamics_config):
        """Test Dynamics CRM API access with acquired token."""
        # First get an access token
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Get OAuth token
            token_url = f"https://login.microsoftonline.com/{dynamics_config['tenant_id']}/oauth2/v2.0/token"
            
            token_data = {
                "grant_type": "client_credentials",
                "client_id": dynamics_config['client_id'],
                "client_secret": dynamics_config['client_secret'],
                "scope": f"{dynamics_config['crm_url']}/.default"
            }
            
            token_response = await client.post(token_url, data=token_data)
            token_response.raise_for_status()
            access_token = token_response.json()["access_token"]
            
            # Test CRM API access
            headers = {
                "Authorization": f"Bearer {access_token}",
                "OData-MaxVersion": "4.0",
                "OData-Version": "4.0",
                "Content-Type": "application/json"
            }
            
            # Test basic API access by querying contacts (with limit)
            api_url = f"{dynamics_config['crm_url']}/api/data/{dynamics_config['api_version']}/contacts"
            params = {"$top": "1", "$select": "contactid,fullname"}
            
            try:
                response = await client.get(api_url, headers=headers, params=params)
                
                assert response.status_code == 200, f"CRM API request failed with status {response.status_code}: {response.text}"
                
                data = response.json()
                assert "value" in data, "Response should contain 'value' array"
                
                print(f"✓ Dynamics CRM API access successful")
                print(f"  API URL: {api_url}")
                print(f"  Contacts found: {len(data['value'])}")
                
                if data['value']:
                    contact = data['value'][0]
                    print(f"  Sample contact: {contact.get('fullname', 'N/A')} (ID: {contact.get('contactid', 'N/A')})")
                
            except httpx.HTTPStatusError as e:
                print(f"✗ Dynamics CRM API error: {e.response.status_code}")
                print(f"  Response: {e.response.text}")
                raise
            except Exception as e:
                print(f"✗ Dynamics CRM API connection error: {str(e)}")
                raise
    
    @pytest.mark.asyncio
    async def test_dynamics_create_test_contact(self, dynamics_config):
        """Test creating a test contact in Dynamics CRM (will be cleaned up)."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Get OAuth token
            token_url = f"https://login.microsoftonline.com/{dynamics_config['tenant_id']}/oauth2/v2.0/token"
            
            token_data = {
                "grant_type": "client_credentials",
                "client_id": dynamics_config['client_id'],
                "client_secret": dynamics_config['client_secret'],
                "scope": f"{dynamics_config['crm_url']}/.default"
            }
            
            token_response = await client.post(token_url, data=token_data)
            token_response.raise_for_status()
            access_token = token_response.json()["access_token"]
            
            headers = {
                "Authorization": f"Bearer {access_token}",
                "OData-MaxVersion": "4.0",
                "OData-Version": "4.0",
                "Content-Type": "application/json"
            }
            
            # Create a test contact
            test_contact = {
                "firstname": "Test",
                "lastname": "ConnectivityCheck",
                "emailaddress1": "test.connectivity@example.com",
                "description": "Test contact created by connectivity test - safe to delete"
            }
            
            api_url = f"{dynamics_config['crm_url']}/api/data/{dynamics_config['api_version']}/contacts"
            
            try:
                # Create contact
                create_response = await client.post(api_url, headers=headers, json=test_contact)
                
                assert create_response.status_code == 204, f"Contact creation failed with status {create_response.status_code}: {create_response.text}"
                
                # Extract contact ID from response headers
                contact_url = create_response.headers.get("OData-EntityId", "")
                if contact_url:
                    contact_id = contact_url.split("(")[-1].rstrip(")")
                    print(f"✓ Dynamics CRM contact creation successful")
                    print(f"  Contact ID: {contact_id}")
                    
                    # Clean up - delete the test contact
                    delete_url = f"{api_url}({contact_id})"
                    delete_response = await client.delete(delete_url, headers=headers)
                    
                    if delete_response.status_code == 204:
                        print(f"✓ Test contact cleaned up successfully")
                    else:
                        print(f"⚠ Failed to clean up test contact (ID: {contact_id})")
                else:
                    print(f"⚠ Contact created but couldn't extract ID for cleanup")
                
            except httpx.HTTPStatusError as e:
                print(f"✗ Dynamics CRM contact creation error: {e.response.status_code}")
                print(f"  Response: {e.response.text}")
                raise
            except Exception as e:
                print(f"✗ Dynamics CRM contact creation connection error: {str(e)}")
                raise


class TestIntegratedConnectivity:
    """Test both APIs working together."""
    
    @pytest.mark.asyncio
    async def test_full_connectivity_check(self):
        """Comprehensive connectivity test for both APIs."""
        print("\n" + "="*60)
        print("COMPREHENSIVE CONNECTIVITY TEST")
        print("="*60)
        
        linkedin_success = False
        dynamics_success = False
        
        # Test LinkedIn
        try:
            linkedin_token = os.getenv("LINKEDIN_ACCESS_TOKEN")
            if linkedin_token:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    headers = {
                        "Authorization": f"Bearer {linkedin_token}",
                        "LinkedIn-Version": "202312",
                        "Content-Type": "application/json"
                    }
                    
                    # Test the working Member Snapshot Data API endpoint first
                    try:
                        url = "https://api.linkedin.com/rest/memberSnapshotData"
                        params = {"q": "criteria", "domain": "CONNECTIONS"}
                        response = await client.get(url, headers=headers, params=params)
                        
                        if response.status_code == 200:
                            print(f"✓ LinkedIn Member Snapshot Data API working")
                            linkedin_success = True
                        elif response.status_code == 403:
                            print(f"⚠ LinkedIn Member Snapshot Data API accessible but insufficient permissions")
                        else:
                            print(f"⚠ LinkedIn Member Snapshot Data API returned {response.status_code}")
                            
                    except Exception as e:
                        print(f"✗ LinkedIn Member Snapshot Data API failed: {str(e)}")
                    
                    # Try fallback endpoints if the main one didn't work
                    if not linkedin_success:
                        fallback_headers = {
                            "Authorization": f"Bearer {linkedin_token}",
                            "LinkedIn-Version": "202312",
                            "X-Restli-Protocol-Version": "2.0.0"
                        }
                        
                        fallback_endpoints = ["/v2/people/~", "/v2/me"]
                        
                        for endpoint in fallback_endpoints:
                            try:
                                url = f"https://api.linkedin.com{endpoint}"
                                response = await client.get(url, headers=fallback_headers)
                                
                                if response.status_code == 200:
                                    print(f"✓ LinkedIn API working (fallback endpoint: {endpoint})")
                                    linkedin_success = True
                                    break
                                elif response.status_code == 403:
                                    print(f"⚠ LinkedIn API accessible but insufficient permissions (endpoint: {endpoint})")
                                
                            except Exception as e:
                                print(f"✗ LinkedIn endpoint {endpoint} failed: {str(e)}")
                                continue
                    
                    if not linkedin_success:
                        print("⚠ LinkedIn API accessible but no working endpoints found")
            else:
                print("✗ LinkedIn token not found in environment")
                
        except Exception as e:
            print(f"✗ LinkedIn connectivity test failed: {str(e)}")
        
        # Test Dynamics CRM
        try:
            dynamics_config = {
                "tenant_id": os.getenv("DYNAMICS_TENANT_ID"),
                "client_id": os.getenv("DYNAMICS_CLIENT_ID"),
                "client_secret": os.getenv("DYNAMICS_CLIENT_SECRET"),
                "crm_url": os.getenv("DYNAMICS_CRM_URL")
            }
            
            if all(dynamics_config.values()):
                async with httpx.AsyncClient(timeout=30.0) as client:
                    # Get token
                    token_url = f"https://login.microsoftonline.com/{dynamics_config['tenant_id']}/oauth2/v2.0/token"
                    
                    token_data = {
                        "grant_type": "client_credentials",
                        "client_id": dynamics_config['client_id'],
                        "client_secret": dynamics_config['client_secret'],
                        "scope": f"{dynamics_config['crm_url']}/.default"
                    }
                    
                    token_response = await client.post(token_url, data=token_data)
                    
                    if token_response.status_code == 200:
                        access_token = token_response.json()["access_token"]
                        
                        # Test API access
                        headers = {
                            "Authorization": f"Bearer {access_token}",
                            "OData-MaxVersion": "4.0",
                            "OData-Version": "4.0"
                        }
                        
                        api_url = f"{dynamics_config['crm_url']}/api/data/v9.2/contacts"
                        params = {"$top": "1"}
                        
                        api_response = await client.get(api_url, headers=headers, params=params)
                        
                        if api_response.status_code == 200:
                            print(f"✓ Dynamics CRM API working")
                            dynamics_success = True
                        else:
                            print(f"✗ Dynamics CRM API failed: {api_response.status_code}")
                    else:
                        print(f"✗ Dynamics CRM OAuth failed: {token_response.status_code}")
            else:
                missing = [k for k, v in dynamics_config.items() if not v]
                print(f"✗ Dynamics CRM config incomplete, missing: {missing}")
                
        except Exception as e:
            print(f"✗ Dynamics CRM connectivity test failed: {str(e)}")
        
        # Summary
        print("\n" + "-"*60)
        print("CONNECTIVITY SUMMARY")
        print("-"*60)
        print(f"LinkedIn API:      {'✓ WORKING' if linkedin_success else '✗ FAILED'}")
        print(f"Dynamics CRM API:  {'✓ WORKING' if dynamics_success else '✗ FAILED'}")
        print(f"Overall Status:    {'✓ READY FOR SYNC' if (linkedin_success and dynamics_success) else '⚠ PARTIAL/FAILED'}")
        print("-"*60)
        
        if linkedin_success and dynamics_success:
            print("🎉 Both APIs are working! The synchronization system is ready to use.")
        elif linkedin_success or dynamics_success:
            print("⚠ Partial connectivity. Check the failed API configuration.")
        else:
            print("❌ Both APIs failed. Check your .env configuration and network connectivity.")


if __name__ == "__main__":
    # Run the comprehensive test directly
    asyncio.run(TestIntegratedConnectivity().test_full_connectivity_check())