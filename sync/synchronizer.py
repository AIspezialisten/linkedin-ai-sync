"""
LinkedIn-Dynamics CRM Synchronization Logic.

This module provides the core synchronization functionality between
LinkedIn Member Snapshot data and Microsoft Dynamics CRM contacts.
"""

import asyncio
import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel
from .ai_duplicate_detection import DuplicateDetectionService, MatchConfidence


class SyncResult(BaseModel):
    """Result of a synchronization operation."""
    success: bool
    message: str
    linkedin_id: Optional[str] = None
    crm_contact_id: Optional[str] = None
    action: str  # 'created', 'updated', 'skipped', 'error'
    details: Optional[Dict[str, Any]] = None


class SyncStats(BaseModel):
    """Statistics for a synchronization session."""
    total_processed: int = 0
    created: int = 0
    updated: int = 0
    skipped: int = 0
    errors: int = 0
    start_time: datetime
    end_time: Optional[datetime] = None


class LinkedInDynamicsSynchronizer:
    """
    Synchronizer for LinkedIn Member Snapshot data to Dynamics CRM contacts.
    
    This class orchestrates the data flow between LinkedIn and Dynamics CRM,
    handling data mapping, conflict resolution, and AI-powered duplicate detection.
    """
    
    def __init__(self, linkedin_client, dynamics_client, logger=None, 
                 enable_ai_duplicate_detection=True, ollama_model=None):
        """
        Initialize the synchronizer.
        
        Args:
            linkedin_client: LinkedIn MCP client instance
            dynamics_client: Dynamics CRM MCP client instance  
            logger: Optional logger instance
            enable_ai_duplicate_detection: Whether to use AI for duplicate detection
            ollama_model: Ollama model to use for AI duplicate detection (defaults to env)
        """
        self.linkedin_client = linkedin_client
        self.dynamics_client = dynamics_client
        self.logger = logger or logging.getLogger(__name__)
        
        # Initialize AI duplicate detection service
        self.enable_ai_duplicate_detection = enable_ai_duplicate_detection
        if enable_ai_duplicate_detection:
            try:
                self.duplicate_detector = DuplicateDetectionService(ollama_model=ollama_model)
                actual_model = ollama_model or os.getenv('OLLAMA_MODEL', 'mistral-small:24b')
                self.logger.info(f"AI duplicate detection enabled using {actual_model}")
            except Exception as e:
                self.logger.warning(f"Failed to initialize AI duplicate detection: {str(e)}")
                self.enable_ai_duplicate_detection = False
                self.duplicate_detector = None
        else:
            self.duplicate_detector = None
    
    async def find_duplicates_with_ai(self, linkedin_contacts: List[Dict[str, Any]], 
                                    crm_contacts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Use AI to find potential duplicates between LinkedIn and CRM contacts.
        
        Args:
            linkedin_contacts: List of LinkedIn contacts
            crm_contacts: List of CRM contacts
            
        Returns:
            AI analysis results with duplicate detection and sync recommendations
        """
        if not self.enable_ai_duplicate_detection:
            self.logger.warning("AI duplicate detection is disabled")
            return {
                "error": "AI duplicate detection is not available",
                "contacts_safe_to_sync": [
                    {
                        "linkedin_contact": f"{c.get('First Name', '')} {c.get('Last Name', '')}".strip(),
                        "action": "sync_without_ai",
                        "reason": "AI duplicate detection disabled - proceeding without duplicate check"
                    }
                    for c in linkedin_contacts
                ]
            }
        
        try:
            self.logger.info("Starting AI-powered duplicate detection analysis")
            analysis = await self.duplicate_detector.analyze_linkedin_vs_crm(
                linkedin_contacts, 
                crm_contacts
            )
            
            self.logger.info(f"AI duplicate detection completed: "
                           f"{analysis['contacts_with_potential_duplicates']} contacts have potential duplicates")
            
            return analysis
            
        except Exception as e:
            self.logger.error(f"AI duplicate detection failed: {str(e)}")
            return {
                "error": f"AI duplicate detection failed: {str(e)}",
                "contacts_safe_to_sync": []
            }
        
    async def sync_member_to_contact(self, linkedin_member: Dict[str, Any]) -> SyncResult:
        """
        Synchronize a single LinkedIn member to Dynamics CRM contact.
        
        Args:
            linkedin_member: LinkedIn member snapshot data
            
        Returns:
            SyncResult: Result of the synchronization operation
        """
        try:
            # Map LinkedIn data to CRM contact format
            crm_contact_data = self._map_linkedin_to_crm(linkedin_member)
            
            # Check if contact already exists
            existing_contact = await self._find_existing_contact(crm_contact_data)
            
            if existing_contact:
                # Update existing contact
                result = await self._update_existing_contact(existing_contact, crm_contact_data)
                result.linkedin_id = linkedin_member.get('id')
                return result
            else:
                # Create new contact
                result = await self._create_new_contact(crm_contact_data)
                result.linkedin_id = linkedin_member.get('id')
                return result
                
        except Exception as e:
            self.logger.error(f"Error syncing LinkedIn member {linkedin_member.get('id', 'Unknown')}: {str(e)}")
            return SyncResult(
                success=False,
                message=f"Synchronization error: {str(e)}",
                linkedin_id=linkedin_member.get('id'),
                action='error'
            )
    
    async def sync_batch(self, linkedin_members: List[Dict[str, Any]]) -> Tuple[SyncStats, List[SyncResult]]:
        """
        Synchronize a batch of LinkedIn members to CRM contacts.
        
        Args:
            linkedin_members: List of LinkedIn member snapshot data
            
        Returns:
            Tuple of (SyncStats, List[SyncResult])
        """
        stats = SyncStats(start_time=datetime.now())
        results = []
        
        self.logger.info(f"Starting batch synchronization of {len(linkedin_members)} LinkedIn members")
        
        for member in linkedin_members:
            result = await self.sync_member_to_contact(member)
            results.append(result)
            
            # Update statistics
            stats.total_processed += 1
            if result.success:
                if result.action == 'created':
                    stats.created += 1
                elif result.action == 'updated':
                    stats.updated += 1
                elif result.action == 'skipped':
                    stats.skipped += 1
            else:
                stats.errors += 1
                
        stats.end_time = datetime.now()
        
        self.logger.info(f"Batch synchronization completed. "
                        f"Processed: {stats.total_processed}, "
                        f"Created: {stats.created}, "
                        f"Updated: {stats.updated}, "
                        f"Skipped: {stats.skipped}, "
                        f"Errors: {stats.errors}")
        
        return stats, results
    
    async def sync_batch_with_ai_detection(self, linkedin_members: List[Dict[str, Any]], 
                                         crm_contacts: List[Dict[str, Any]],
                                         auto_sync_safe_contacts: bool = True) -> Tuple[SyncStats, List[SyncResult], Dict[str, Any]]:
        """
        Synchronize LinkedIn members with AI-powered duplicate detection.
        
        Args:
            linkedin_members: List of LinkedIn member data
            crm_contacts: List of existing CRM contacts
            auto_sync_safe_contacts: Whether to automatically sync contacts with no duplicates
            
        Returns:
            Tuple of (SyncStats, List[SyncResult], AI analysis results)
        """
        stats = SyncStats(start_time=datetime.now())
        results = []
        
        self.logger.info(f"Starting AI-powered sync for {len(linkedin_members)} LinkedIn contacts")
        
        # Step 1: Run AI duplicate detection
        ai_analysis = await self.find_duplicates_with_ai(linkedin_members, crm_contacts)
        
        if "error" in ai_analysis:
            self.logger.error(f"AI analysis failed: {ai_analysis['error']}")
            # Fallback to regular sync without AI
            return await self.sync_batch(linkedin_members)
        
        # Step 2: Process contacts based on AI recommendations
        contacts_to_sync = []
        contacts_skipped = []
        contacts_need_review = []
        
        for recommendation in ai_analysis.get("contacts_safe_to_sync", []):
            action = recommendation.get("action", "")
            linkedin_contact_name = recommendation.get("linkedin_contact", "")
            
            # Find the actual LinkedIn contact data
            linkedin_contact = None
            for contact in linkedin_members:
                contact_name = f"{contact.get('First Name', '')} {contact.get('Last Name', '')}".strip()
                if contact_name == linkedin_contact_name:
                    linkedin_contact = contact
                    break
            
            if not linkedin_contact:
                continue
                
            if action in ["sync", "sync_without_ai"] and auto_sync_safe_contacts:
                contacts_to_sync.append(linkedin_contact)
            elif action == "sync_with_caution":
                if auto_sync_safe_contacts:
                    contacts_to_sync.append(linkedin_contact)
                else:
                    contacts_need_review.append(recommendation)
            else:
                contacts_need_review.append(recommendation)
        
        for recommendation in ai_analysis.get("contacts_need_review", []):
            action = recommendation.get("action", "")
            if action == "skip_sync":
                contacts_skipped.append(recommendation)
            else:
                contacts_need_review.append(recommendation)
        
        # Step 3: Sync the safe contacts
        if contacts_to_sync:
            self.logger.info(f"Auto-syncing {len(contacts_to_sync)} contacts determined safe by AI")
            sync_stats, sync_results = await self.sync_batch(contacts_to_sync)
            
            # Merge results
            stats.total_processed += sync_stats.total_processed
            stats.created += sync_stats.created
            stats.updated += sync_stats.updated
            stats.skipped += sync_stats.skipped
            stats.errors += sync_stats.errors
            results.extend(sync_results)
        
        # Step 4: Add results for skipped contacts
        for skipped in contacts_skipped:
            result = SyncResult(
                success=True,
                message=f"Skipped due to AI duplicate detection: {skipped.get('reason', 'Unknown')}",
                action='skipped_duplicate',
                details=skipped
            )
            results.append(result)
            stats.total_processed += 1
            stats.skipped += 1
        
        # Step 5: Add results for contacts needing review
        for review in contacts_need_review:
            result = SyncResult(
                success=True,
                message=f"Needs manual review: {review.get('reason', 'Unknown')}",
                action='needs_review',
                details=review
            )
            results.append(result)
            stats.total_processed += 1
            stats.skipped += 1
        
        stats.end_time = datetime.now()
        
        self.logger.info(f"AI-powered sync completed: "
                        f"synced: {len(contacts_to_sync)}, "
                        f"skipped: {len(contacts_skipped)}, "
                        f"need review: {len(contacts_need_review)}")
        
        return stats, results, ai_analysis
    
    def _map_linkedin_to_crm(self, linkedin_member: Dict[str, Any]) -> Dict[str, Any]:
        """
        Map LinkedIn member data to Dynamics CRM contact format.
        
        Args:
            linkedin_member: LinkedIn member snapshot data
            
        Returns:
            Dictionary with CRM contact data
        """
        crm_data = {}
        
        # Basic personal information
        if linkedin_member.get('firstName'):
            crm_data['firstname'] = linkedin_member['firstName']
        if linkedin_member.get('lastName'):
            crm_data['lastname'] = linkedin_member['lastName']
        
        # Professional information
        if linkedin_member.get('headline'):
            crm_data['jobtitle'] = linkedin_member['headline']
        
        # Contact information (LinkedIn typically doesn't provide direct contact info)
        # This would need to be supplemented by other data sources or manual entry
        
        # Location information
        if linkedin_member.get('location'):
            # LinkedIn location format may vary, basic parsing
            location = linkedin_member['location']
            crm_data['address1_city'] = location  # Simplified mapping
        
        # Professional summary
        if linkedin_member.get('summary'):
            crm_data['description'] = linkedin_member['summary']
        
        # Industry information
        if linkedin_member.get('industryName'):
            # Could be mapped to a custom field or included in description
            current_desc = crm_data.get('description', '')
            crm_data['description'] = f"{current_desc}\n\nIndustry: {linkedin_member['industryName']}".strip()
        
        # LinkedIn profile URL (custom field)
        if linkedin_member.get('id'):
            crm_data['linkedin_profile'] = f"https://www.linkedin.com/in/{linkedin_member['id']}/"
        
        # Additional professional information from positions
        if linkedin_member.get('positions'):
            positions = linkedin_member['positions']
            if positions:
                # Use the most recent position for job title if headline isn't available
                current_position = positions[0] if positions else None
                if current_position and not crm_data.get('jobtitle'):
                    crm_data['jobtitle'] = current_position.get('title', '')
                
                # Add company information to description
                if current_position and current_position.get('companyName'):
                    current_desc = crm_data.get('description', '')
                    crm_data['description'] = f"{current_desc}\n\nCurrent Company: {current_position['companyName']}".strip()
        
        return crm_data
    
    async def _find_existing_contact(self, crm_contact_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Find existing contact in CRM based on the contact data.
        
        Args:
            crm_contact_data: CRM contact data to search for
            
        Returns:
            Existing contact data if found, None otherwise
        """
        try:
            # Search strategies (in order of preference):
            # 1. By LinkedIn profile URL (if available)
            # 2. By email address (if available)
            # 3. By full name match
            
            # Strategy 1: LinkedIn profile URL
            if crm_contact_data.get('linkedin_profile'):
                linkedin_url = crm_contact_data['linkedin_profile']
                filter_expr = f"linkedin_profile eq '{linkedin_url}'"
                
                search_result = await self.dynamics_client.call_tool({
                    "name": "search_contacts",
                    "arguments": {
                        "filter": filter_expr,
                        "top": 1
                    }
                })
                
                if search_result.get('success') and search_result.get('data', {}).get('value'):
                    return search_result['data']['value'][0]
            
            # Strategy 2: Email address (if available)
            if crm_contact_data.get('emailaddress1'):
                email = crm_contact_data['emailaddress1']
                filter_expr = f"emailaddress1 eq '{email}'"
                
                search_result = await self.dynamics_client.call_tool({
                    "name": "search_contacts", 
                    "arguments": {
                        "filter": filter_expr,
                        "top": 1
                    }
                })
                
                if search_result.get('success') and search_result.get('data', {}).get('value'):
                    return search_result['data']['value'][0]
            
            # Strategy 3: Full name match
            if crm_contact_data.get('firstname') and crm_contact_data.get('lastname'):
                firstname = crm_contact_data['firstname']
                lastname = crm_contact_data['lastname']
                filter_expr = f"firstname eq '{firstname}' and lastname eq '{lastname}'"
                
                search_result = await self.dynamics_client.call_tool({
                    "name": "search_contacts",
                    "arguments": {
                        "filter": filter_expr,
                        "top": 1
                    }
                })
                
                if search_result.get('success') and search_result.get('data', {}).get('value'):
                    return search_result['data']['value'][0]
            
            return None
            
        except Exception as e:
            self.logger.warning(f"Error searching for existing contact: {str(e)}")
            return None
    
    async def _create_new_contact(self, crm_contact_data: Dict[str, Any]) -> SyncResult:
        """
        Create a new contact in Dynamics CRM.
        
        Args:
            crm_contact_data: Contact data to create
            
        Returns:
            SyncResult: Result of the creation operation
        """
        try:
            result = await self.dynamics_client.call_tool({
                "name": "create_contact",
                "arguments": crm_contact_data
            })
            
            if result.get('success'):
                return SyncResult(
                    success=True,
                    message="Contact created successfully",
                    crm_contact_id=result.get('contact_id'),
                    action='created',
                    details=crm_contact_data
                )
            else:
                return SyncResult(
                    success=False,
                    message=f"Failed to create contact: {result.get('message', 'Unknown error')}",
                    action='error',
                    details=crm_contact_data
                )
                
        except Exception as e:
            return SyncResult(
                success=False,
                message=f"Error creating contact: {str(e)}",
                action='error',
                details=crm_contact_data
            )
    
    async def _update_existing_contact(self, existing_contact: Dict[str, Any], 
                                     new_data: Dict[str, Any]) -> SyncResult:
        """
        Update an existing contact in Dynamics CRM.
        
        Args:
            existing_contact: Existing contact data from CRM
            new_data: New data to update
            
        Returns:
            SyncResult: Result of the update operation
        """
        try:
            contact_id = existing_contact.get('contactid')
            if not contact_id:
                return SyncResult(
                    success=False,
                    message="No contact ID found in existing contact",
                    action='error'
                )
            
            # Determine what fields need updating
            updates_needed = self._determine_updates_needed(existing_contact, new_data)
            
            if not updates_needed:
                return SyncResult(
                    success=True,
                    message="Contact is already up to date",
                    crm_contact_id=contact_id,
                    action='skipped'
                )
            
            # Perform the update
            result = await self.dynamics_client.call_tool({
                "name": "update_contact",
                "arguments": {
                    "contact_id": contact_id,
                    "data": updates_needed
                }
            })
            
            if result.get('success'):
                return SyncResult(
                    success=True,
                    message="Contact updated successfully",
                    crm_contact_id=contact_id,
                    action='updated',
                    details=updates_needed
                )
            else:
                return SyncResult(
                    success=False,
                    message=f"Failed to update contact: {result.get('message', 'Unknown error')}",
                    crm_contact_id=contact_id,
                    action='error',
                    details=updates_needed
                )
                
        except Exception as e:
            return SyncResult(
                success=False,
                message=f"Error updating contact: {str(e)}",
                action='error'
            )
    
    def _determine_updates_needed(self, existing_contact: Dict[str, Any], 
                                new_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Determine what fields need to be updated based on existing and new data.
        
        Args:
            existing_contact: Existing contact data
            new_data: New data from LinkedIn
            
        Returns:
            Dictionary of fields that need to be updated
        """
        updates = {}
        
        # Define fields that should be updated if they're different
        # and the new data has a value
        updateable_fields = [
            'firstname', 'lastname', 'jobtitle', 'description', 
            'linkedin_profile', 'address1_city'
        ]
        
        for field in updateable_fields:
            new_value = new_data.get(field)
            existing_value = existing_contact.get(field)
            
            # Update if:
            # 1. New data has a value and existing doesn't
            # 2. New data has a different value than existing
            if new_value and (not existing_value or new_value != existing_value):
                # Special handling for description field - append rather than replace
                if field == 'description' and existing_value:
                    # Avoid duplicating information
                    if new_value not in existing_value:
                        updates[field] = f"{existing_value}\n\n{new_value}"
                else:
                    updates[field] = new_value
        
        return updates


class SyncOrchestrator:
    """
    Orchestrates the complete synchronization process between LinkedIn and Dynamics CRM.
    """
    
    def __init__(self, linkedin_client, dynamics_client, logger=None):
        """
        Initialize the sync orchestrator.
        
        Args:
            linkedin_client: LinkedIn MCP client instance
            dynamics_client: Dynamics CRM MCP client instance
            logger: Optional logger instance
        """
        self.linkedin_client = linkedin_client
        self.dynamics_client = dynamics_client
        self.synchronizer = LinkedInDynamicsSynchronizer(
            linkedin_client, dynamics_client, logger
        )
        self.logger = logger or logging.getLogger(__name__)
    
    async def sync_user_profile(self) -> Tuple[SyncStats, List[SyncResult]]:
        """
        Synchronize the authenticated user's LinkedIn profile to CRM.
        
        Returns:
            Tuple of (SyncStats, List[SyncResult])
        """
        try:
            # Get the authenticated user's LinkedIn profile
            profile_result = await self.linkedin_client.call_tool({
                "name": "get_member_snapshot_data",
                "arguments": {"domain": "PROFILE"}
            })
            
            if not profile_result.get('success'):
                raise Exception(f"Failed to get LinkedIn profile: {profile_result.get('message', 'Unknown error')}")
            
            profile_data = profile_result.get('data', {})
            
            # Synchronize the profile
            return await self.synchronizer.sync_batch([profile_data])
            
        except Exception as e:
            self.logger.error(f"Error synchronizing user profile: {str(e)}")
            stats = SyncStats(start_time=datetime.now(), end_time=datetime.now())
            stats.errors = 1
            stats.total_processed = 1
            
            error_result = SyncResult(
                success=False,
                message=f"Failed to sync user profile: {str(e)}",
                action='error'
            )
            
            return stats, [error_result]
    
    async def sync_connections(self, keywords: Optional[str] = None, 
                              limit: int = 50) -> Tuple[SyncStats, List[SyncResult]]:
        """
        Synchronize LinkedIn connections to CRM contacts.
        
        Args:
            keywords: Optional keywords to filter connections
            limit: Maximum number of connections to sync
            
        Returns:
            Tuple of (SyncStats, List[SyncResult])
        """
        try:
            # Get LinkedIn connections data
            connections_result = await self.linkedin_client.call_tool({
                "name": "get_connections_data",
                "arguments": {}
            })
            
            if not connections_result.get('success'):
                raise Exception(f"Failed to get LinkedIn connections: {connections_result.get('message', 'Unknown error')}")
            
            connections_data = connections_result.get('data', {}).get('elements', [])
            
            # Synchronize the connections
            return await self.synchronizer.sync_batch(connections_data)
            
        except Exception as e:
            self.logger.error(f"Error synchronizing connections: {str(e)}")
            stats = SyncStats(start_time=datetime.now(), end_time=datetime.now())
            stats.errors = 1
            stats.total_processed = 1
            
            error_result = SyncResult(
                success=False,
                message=f"Failed to sync connections: {str(e)}",
                action='error'
            )
            
            return stats, [error_result]