"""
Service layer for duplicate management operations.
"""

import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc

from .models import DuplicateCandidate, DuplicateStatus, MatchConfidence, SyncSession


class DuplicateManagementService:
    """Service for managing duplicate detection and resolution operations."""

    def __init__(self, db_session: Session, dynamics_client=None):
        """
        Initialize the duplicate management service.

        Args:
            db_session: SQLAlchemy database session
            dynamics_client: Optional Dynamics CRM client for updates
        """
        self.db = db_session
        self.dynamics_client = dynamics_client
        self.logger = logging.getLogger(__name__)

    async def store_duplicate_candidates(self, ai_analysis: Dict[str, Any], session_id: str = None) -> List[int]:
        """
        Store AI-detected duplicate candidates for user review.

        Args:
            ai_analysis: Results from AI duplicate detection
            session_id: Optional sync session ID for tracking

        Returns:
            List of created duplicate candidate IDs
        """
        created_ids = []

        try:
            # Extract duplicate details from AI analysis
            duplicate_details = ai_analysis.get('duplicate_details', {})

            for linkedin_contact_name, matches in duplicate_details.items():
                for match in matches:
                    # Only store HIGH and MEDIUM confidence matches for review
                    if match.confidence in [MatchConfidence.HIGH, MatchConfidence.MEDIUM]:
                        duplicate = DuplicateCandidate(
                            linkedin_contact_data=match.linkedin_contact,
                            crm_contact_data=match.crm_contact,
                            confidence=match.confidence,
                            similarity_score=match.similarity_score,
                            reasoning=match.reasoning,
                            matching_fields=match.matching_fields,
                            conflicting_fields=match.conflicting_fields,
                            status=DuplicateStatus.PENDING
                        )

                        self.db.add(duplicate)
                        self.db.flush()  # Get the ID
                        created_ids.append(duplicate.id)

                        self.logger.info(f"Stored duplicate candidate {duplicate.id} for review: "
                                       f"{linkedin_contact_name} vs {match.crm_contact.get('fullname', 'Unknown')}")

            self.db.commit()
            self.logger.info(f"Stored {len(created_ids)} duplicate candidates for user review")

        except Exception as e:
            self.db.rollback()
            self.logger.error(f"Error storing duplicate candidates: {str(e)}")
            raise

        return created_ids

    def get_pending_duplicates(self, limit: int = 20, offset: int = 0,
                              confidence_filter: Optional[MatchConfidence] = None) -> Tuple[List[DuplicateCandidate], int]:
        """
        Get paginated list of duplicate candidates needing user review.

        Args:
            limit: Maximum number of records to return
            offset: Number of records to skip
            confidence_filter: Optional confidence level filter

        Returns:
            Tuple of (duplicate candidates, total count)
        """
        try:
            query = self.db.query(DuplicateCandidate).filter(
                DuplicateCandidate.status == DuplicateStatus.PENDING
            )

            if confidence_filter:
                query = query.filter(DuplicateCandidate.confidence == confidence_filter)

            # Get total count for pagination
            total_count = query.count()

            # Apply pagination and ordering
            duplicates = query.order_by(desc(DuplicateCandidate.similarity_score)).offset(offset).limit(limit).all()

            self.logger.info(f"Retrieved {len(duplicates)} pending duplicates (offset: {offset}, limit: {limit})")
            return duplicates, total_count

        except Exception as e:
            self.logger.error(f"Error retrieving pending duplicates: {str(e)}")
            raise

    def get_duplicate_by_id(self, duplicate_id: int) -> Optional[DuplicateCandidate]:
        """Get a specific duplicate candidate by ID."""
        try:
            return self.db.query(DuplicateCandidate).filter(DuplicateCandidate.id == duplicate_id).first()
        except Exception as e:
            self.logger.error(f"Error retrieving duplicate {duplicate_id}: {str(e)}")
            raise

    async def approve_duplicate_and_update_crm(self, duplicate_id: int, update_data: Dict[str, Any],
                                             user_decision: str = None) -> bool:
        """
        User approves duplicate - update CRM and mark as resolved.

        Args:
            duplicate_id: ID of the duplicate candidate
            update_data: Fields to update in CRM
            user_decision: User's decision notes

        Returns:
            True if successful, False otherwise
        """
        try:
            duplicate = self.get_duplicate_by_id(duplicate_id)
            if not duplicate:
                self.logger.error(f"Duplicate {duplicate_id} not found")
                return False

            if duplicate.status != DuplicateStatus.PENDING:
                self.logger.warning(f"Duplicate {duplicate_id} is not pending (status: {duplicate.status})")
                return False

            # Update the duplicate record
            duplicate.status = DuplicateStatus.APPROVED
            duplicate.update_data = update_data
            duplicate.user_decision = user_decision
            duplicate.updated_at = datetime.utcnow()

            # Update CRM if client is available
            if self.dynamics_client and update_data:
                success = await self._update_crm_contact(duplicate, update_data)
                if success:
                    duplicate.status = DuplicateStatus.UPDATED
                    duplicate.processed_at = datetime.utcnow()
                else:
                    duplicate.status = DuplicateStatus.ERROR
                    duplicate.error_message = "Failed to update CRM contact"

            self.db.commit()
            self.logger.info(f"Approved duplicate {duplicate_id} and updated CRM")
            return True

        except Exception as e:
            self.db.rollback()
            self.logger.error(f"Error approving duplicate {duplicate_id}: {str(e)}")
            return False

    async def reject_duplicate(self, duplicate_id: int, reason: str = None) -> bool:
        """
        User rejects duplicate - mark as rejected.

        Args:
            duplicate_id: ID of the duplicate candidate
            reason: Reason for rejection

        Returns:
            True if successful, False otherwise
        """
        try:
            duplicate = self.get_duplicate_by_id(duplicate_id)
            if not duplicate:
                self.logger.error(f"Duplicate {duplicate_id} not found")
                return False

            duplicate.status = DuplicateStatus.REJECTED
            duplicate.user_decision = reason or "User rejected - not a duplicate"
            duplicate.updated_at = datetime.utcnow()

            self.db.commit()
            self.logger.info(f"Rejected duplicate {duplicate_id}: {reason}")
            return True

        except Exception as e:
            self.db.rollback()
            self.logger.error(f"Error rejecting duplicate {duplicate_id}: {str(e)}")
            return False

    async def flag_for_later(self, duplicate_id: int, reason: str = None) -> bool:
        """
        Flag duplicate for later review.

        Args:
            duplicate_id: ID of the duplicate candidate
            reason: Reason for flagging

        Returns:
            True if successful, False otherwise
        """
        try:
            duplicate = self.get_duplicate_by_id(duplicate_id)
            if not duplicate:
                return False

            duplicate.status = DuplicateStatus.FLAGGED
            duplicate.user_decision = reason or "Flagged for later review"
            duplicate.updated_at = datetime.utcnow()

            self.db.commit()
            self.logger.info(f"Flagged duplicate {duplicate_id} for later review")
            return True

        except Exception as e:
            self.db.rollback()
            self.logger.error(f"Error flagging duplicate {duplicate_id}: {str(e)}")
            return False

    def get_duplicate_stats(self) -> Dict[str, Any]:
        """Get statistics about duplicate candidates."""
        try:
            stats = {
                'total_duplicates': self.db.query(DuplicateCandidate).count(),
                'pending': self.db.query(DuplicateCandidate).filter(
                    DuplicateCandidate.status == DuplicateStatus.PENDING
                ).count(),
                'approved': self.db.query(DuplicateCandidate).filter(
                    DuplicateCandidate.status == DuplicateStatus.APPROVED
                ).count(),
                'rejected': self.db.query(DuplicateCandidate).filter(
                    DuplicateCandidate.status == DuplicateStatus.REJECTED
                ).count(),
                'updated': self.db.query(DuplicateCandidate).filter(
                    DuplicateCandidate.status == DuplicateStatus.UPDATED
                ).count(),
                'flagged': self.db.query(DuplicateCandidate).filter(
                    DuplicateCandidate.status == DuplicateStatus.FLAGGED
                ).count(),
                'errors': self.db.query(DuplicateCandidate).filter(
                    DuplicateCandidate.status == DuplicateStatus.ERROR
                ).count(),
            }

            # Confidence level breakdown
            stats['by_confidence'] = {
                'high': self.db.query(DuplicateCandidate).filter(
                    DuplicateCandidate.confidence == MatchConfidence.HIGH
                ).count(),
                'medium': self.db.query(DuplicateCandidate).filter(
                    DuplicateCandidate.confidence == MatchConfidence.MEDIUM
                ).count(),
                'low': self.db.query(DuplicateCandidate).filter(
                    DuplicateCandidate.confidence == MatchConfidence.LOW
                ).count()
            }

            return stats

        except Exception as e:
            self.logger.error(f"Error getting duplicate stats: {str(e)}")
            return {}

    async def _update_crm_contact(self, duplicate: DuplicateCandidate, update_data: Dict[str, Any]) -> bool:
        """
        Update CRM contact with the specified data.

        Args:
            duplicate: The duplicate candidate
            update_data: Data to update in CRM

        Returns:
            True if successful, False otherwise
        """
        try:
            if not self.dynamics_client:
                self.logger.warning("No Dynamics client available for CRM update")
                return False

            crm_contact = duplicate.crm_contact_data
            contact_id = crm_contact.get('contactid')

            if not contact_id:
                self.logger.error(f"No contact ID found in CRM contact data for duplicate {duplicate.id}")
                return False

            # Call the Dynamics CRM client to update the contact
            result = await self.dynamics_client.call_tool({
                "name": "update_contact",
                "arguments": {
                    "contact_id": contact_id,
                    "data": update_data
                }
            })

            if result.get('success'):
                self.logger.info(f"Successfully updated CRM contact {contact_id} for duplicate {duplicate.id}")
                return True
            else:
                error_msg = result.get('message', 'Unknown error')
                self.logger.error(f"Failed to update CRM contact {contact_id}: {error_msg}")
                duplicate.error_message = error_msg
                return False

        except Exception as e:
            self.logger.error(f"Error updating CRM contact for duplicate {duplicate.id}: {str(e)}")
            duplicate.error_message = str(e)
            return False

    def create_sync_session(self, session_id: str = None) -> SyncSession:
        """Create a new sync session for tracking."""
        if not session_id:
            session_id = str(uuid.uuid4())

        session = SyncSession(session_id=session_id)
        self.db.add(session)
        self.db.commit()
        return session

    def update_sync_session(self, session_id: str, **kwargs) -> bool:
        """Update sync session with results."""
        try:
            session = self.db.query(SyncSession).filter(SyncSession.session_id == session_id).first()
            if session:
                for key, value in kwargs.items():
                    if hasattr(session, key):
                        setattr(session, key, value)
                self.db.commit()
                return True
            return False
        except Exception as e:
            self.logger.error(f"Error updating sync session {session_id}: {str(e)}")
            return False

    def get_recent_sessions(self, limit: int = 10) -> List[SyncSession]:
        """Get recent sync sessions."""
        try:
            return self.db.query(SyncSession).order_by(desc(SyncSession.started_at)).limit(limit).all()
        except Exception as e:
            self.logger.error(f"Error retrieving recent sessions: {str(e)}")
            return []