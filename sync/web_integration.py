"""
Integration layer between synchronizer and web interface.
"""

import asyncio
import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from web.models import db_manager, DuplicateCandidate, DuplicateStatus, SyncSession
from web.services import DuplicateManagementService
from .synchronizer import LinkedInDynamicsSynchronizer, SyncStats, SyncResult


class WebEnabledSynchronizer(LinkedInDynamicsSynchronizer):
    """
    Enhanced synchronizer that integrates with the web interface for duplicate management.
    """

    def __init__(self, linkedin_client, dynamics_client, logger=None,
                 enable_ai_duplicate_detection=True, ollama_model=None,
                 enable_web_interface=True):
        """
        Initialize the web-enabled synchronizer.

        Args:
            linkedin_client: LinkedIn MCP client instance
            dynamics_client: Dynamics CRM MCP client instance
            logger: Optional logger instance
            enable_ai_duplicate_detection: Whether to use AI for duplicate detection
            ollama_model: Ollama model to use for AI duplicate detection
            enable_web_interface: Whether to store duplicates for web review
        """
        super().__init__(linkedin_client, dynamics_client, logger,
                        enable_ai_duplicate_detection, ollama_model)

        self.enable_web_interface = enable_web_interface

        if enable_web_interface:
            # Initialize database
            db_manager.create_tables()

    async def sync_with_web_review(self, linkedin_members: List[Dict[str, Any]],
                                 crm_contacts: List[Dict[str, Any]] = None,
                                 auto_sync_safe_contacts: bool = True,
                                 session_id: str = None) -> Tuple[SyncStats, List[SyncResult], Dict[str, Any]]:
        """
        Enhanced sync that stores duplicates for web review and only auto-syncs safe contacts.

        Args:
            linkedin_members: List of LinkedIn member data
            crm_contacts: List of existing CRM contacts (will fetch if not provided)
            auto_sync_safe_contacts: Whether to automatically sync contacts with no duplicates
            session_id: Optional session ID for tracking

        Returns:
            Tuple of (SyncStats, List[SyncResult], AI analysis results)
        """
        if not session_id:
            session_id = str(uuid.uuid4())

        # Create database session for web interface
        db_session = None
        duplicate_service = None

        if self.enable_web_interface:
            db_session = db_manager.get_session()
            duplicate_service = DuplicateManagementService(db_session, self.dynamics_client)

            # Create sync session record
            sync_session = duplicate_service.create_sync_session(session_id)

        try:
            self.logger.info(f"Starting web-enabled sync for {len(linkedin_members)} LinkedIn contacts")

            # Get CRM contacts if not provided
            if crm_contacts is None:
                crm_contacts = await self._get_all_crm_contacts()

            # Update session with contact counts
            if duplicate_service:
                duplicate_service.update_sync_session(
                    session_id,
                    linkedin_contacts_count=len(linkedin_members),
                    crm_contacts_count=len(crm_contacts)
                )

            # Step 1: Run AI duplicate detection
            ai_analysis = await self.find_duplicates_with_ai(linkedin_members, crm_contacts)

            if "error" in ai_analysis:
                self.logger.error(f"AI analysis failed: {ai_analysis['error']}")
                if duplicate_service:
                    duplicate_service.update_sync_session(
                        session_id,
                        completed_at=datetime.utcnow(),
                        success='failed',
                        error_message=ai_analysis['error']
                    )
                # Fallback to regular sync without AI
                stats, results = await self.sync_batch(linkedin_members)
                return stats, results, ai_analysis

            # Step 2: Store HIGH and MEDIUM confidence duplicates for web review
            duplicates_stored = 0
            if self.enable_web_interface and duplicate_service:
                try:
                    stored_ids = await duplicate_service.store_duplicate_candidates(ai_analysis, session_id)
                    duplicates_stored = len(stored_ids)
                    self.logger.info(f"Stored {duplicates_stored} duplicates for web review")
                except Exception as e:
                    self.logger.error(f"Error storing duplicates for web review: {str(e)}")

            # Step 3: Process contacts based on AI recommendations
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

            # Step 4: Sync the safe contacts automatically
            stats = SyncStats(start_time=datetime.now())
            results = []

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

            # Step 5: Add results for skipped contacts
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

            # Step 6: Add results for contacts needing manual review (stored in web interface)
            for review in contacts_need_review:
                result = SyncResult(
                    success=True,
                    message=f"Stored for web review: {review.get('reason', 'Unknown')}",
                    action='needs_web_review',
                    details=review
                )
                results.append(result)
                stats.total_processed += 1
                stats.skipped += 1

            stats.end_time = datetime.now()

            # Update sync session with final results
            if duplicate_service:
                duplicate_service.update_sync_session(
                    session_id,
                    duplicates_found=duplicates_stored,
                    auto_synced=len(contacts_to_sync),
                    manual_review_required=len(contacts_need_review),
                    completed_at=datetime.utcnow(),
                    success='success' if stats.errors == 0 else 'partial'
                )

            self.logger.info(f"Web-enabled sync completed: "
                           f"auto-synced: {len(contacts_to_sync)}, "
                           f"skipped: {len(contacts_skipped)}, "
                           f"need web review: {len(contacts_need_review)}, "
                           f"stored duplicates: {duplicates_stored}")

            return stats, results, ai_analysis

        except Exception as e:
            self.logger.error(f"Error in web-enabled sync: {str(e)}")

            if duplicate_service:
                duplicate_service.update_sync_session(
                    session_id,
                    completed_at=datetime.utcnow(),
                    success='failed',
                    error_message=str(e)
                )

            # Return error stats
            stats = SyncStats(start_time=datetime.now(), end_time=datetime.now())
            stats.errors = 1
            stats.total_processed = 1

            error_result = SyncResult(
                success=False,
                message=f"Web-enabled sync failed: {str(e)}",
                action='error'
            )

            return stats, [error_result], {"error": str(e)}

        finally:
            if db_session:
                db_session.close()

    async def _get_all_crm_contacts(self) -> List[Dict[str, Any]]:
        """
        Fetch all CRM contacts for duplicate comparison.

        Returns:
            List of CRM contact data
        """
        try:
            # Get all contacts from CRM (this might need pagination for large datasets)
            result = await self.dynamics_client.call_tool({
                "name": "list_contacts",
                "arguments": {
                    "limit": 1000  # Adjust as needed
                }
            })

            if result.get('success'):
                contacts = result.get('data', {}).get('value', [])
                self.logger.info(f"Retrieved {len(contacts)} CRM contacts for duplicate comparison")
                return contacts
            else:
                self.logger.error(f"Failed to retrieve CRM contacts: {result.get('message', 'Unknown error')}")
                return []

        except Exception as e:
            self.logger.error(f"Error retrieving CRM contacts: {str(e)}")
            return []


class WebSyncOrchestrator:
    """
    Enhanced orchestrator that integrates with the web interface.
    """

    def __init__(self, linkedin_client, dynamics_client, logger=None, enable_web_interface=True):
        """
        Initialize the web sync orchestrator.

        Args:
            linkedin_client: LinkedIn MCP client instance
            dynamics_client: Dynamics CRM MCP client instance
            logger: Optional logger instance
            enable_web_interface: Whether to enable web interface integration
        """
        self.linkedin_client = linkedin_client
        self.dynamics_client = dynamics_client
        self.synchronizer = WebEnabledSynchronizer(
            linkedin_client, dynamics_client, logger,
            enable_web_interface=enable_web_interface
        )
        self.logger = logger or logging.getLogger(__name__)

    async def sync_connections_with_web_review(self, keywords: Optional[str] = None,
                                             limit: int = 50,
                                             auto_sync_safe_contacts: bool = True) -> Tuple[SyncStats, List[SyncResult], Dict[str, Any]]:
        """
        Synchronize LinkedIn connections with web interface integration.

        Args:
            keywords: Optional keywords to filter connections
            limit: Maximum number of connections to sync
            auto_sync_safe_contacts: Whether to automatically sync safe contacts

        Returns:
            Tuple of (SyncStats, List[SyncResult], AI analysis results)
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

            # Apply limit
            if limit and len(connections_data) > limit:
                connections_data = connections_data[:limit]

            self.logger.info(f"Retrieved {len(connections_data)} LinkedIn connections for sync")

            # Synchronize with web interface
            return await self.synchronizer.sync_with_web_review(
                connections_data,
                auto_sync_safe_contacts=auto_sync_safe_contacts
            )

        except Exception as e:
            self.logger.error(f"Error synchronizing connections with web review: {str(e)}")
            stats = SyncStats(start_time=datetime.now(), end_time=datetime.now())
            stats.errors = 1
            stats.total_processed = 1

            error_result = SyncResult(
                success=False,
                message=f"Failed to sync connections: {str(e)}",
                action='error'
            )

            return stats, [error_result], {"error": str(e)}

    async def get_duplicate_management_service(self) -> DuplicateManagementService:
        """Get a duplicate management service instance."""
        db_session = db_manager.get_session()
        return DuplicateManagementService(db_session, self.dynamics_client)