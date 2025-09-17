"""
Database models for the duplicate management web interface.
"""

import json
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from sqlalchemy import Column, Integer, String, Text, Float, DateTime, JSON, Enum as SQLEnum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine

Base = declarative_base()


class DuplicateStatus(str, Enum):
    """Status of a duplicate candidate."""
    PENDING = "pending"           # Waiting for user review
    APPROVED = "approved"         # User approved - CRM will be updated
    REJECTED = "rejected"         # User rejected - not a duplicate
    UPDATED = "updated"           # CRM has been successfully updated
    ERROR = "error"               # Error occurred during CRM update
    FLAGGED = "flagged"           # Flagged for later review


class MatchConfidence(str, Enum):
    """Confidence levels for duplicate matches."""
    HIGH = "high"       # Very likely the same person (95%+ confidence)
    MEDIUM = "medium"   # Probably the same person (70-95% confidence)
    LOW = "low"         # Possibly the same person (40-70% confidence)
    NONE = "none"       # Different people (0-40% confidence)


class DuplicateCandidate(Base):
    """A potential duplicate match between LinkedIn and CRM contacts."""
    __tablename__ = 'duplicate_candidates'

    id = Column(Integer, primary_key=True)

    # Contact data (stored as JSON)
    linkedin_contact_data = Column(JSON, nullable=False)
    crm_contact_data = Column(JSON, nullable=False)

    # AI analysis results
    confidence = Column(SQLEnum(MatchConfidence), nullable=False)
    similarity_score = Column(Float, nullable=False)
    reasoning = Column(Text, nullable=False)
    matching_fields = Column(JSON, nullable=False)  # List of field names that match
    conflicting_fields = Column(JSON, nullable=False)  # List of field names that conflict

    # Status tracking
    status = Column(SQLEnum(DuplicateStatus), default=DuplicateStatus.PENDING, nullable=False)
    user_decision = Column(Text)  # User's decision/notes
    update_data = Column(JSON)    # Fields user chose to update in CRM

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    processed_at = Column(DateTime)  # When CRM update was completed

    # Error tracking
    error_message = Column(Text)
    retry_count = Column(Integer, default=0)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'linkedin_contact_data': self.linkedin_contact_data,
            'crm_contact_data': self.crm_contact_data,
            'confidence': self.confidence.value if self.confidence else None,
            'similarity_score': self.similarity_score,
            'reasoning': self.reasoning,
            'matching_fields': self.matching_fields,
            'conflicting_fields': self.conflicting_fields,
            'status': self.status.value if self.status else None,
            'user_decision': self.user_decision,
            'update_data': self.update_data,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'processed_at': self.processed_at.isoformat() if self.processed_at else None,
            'error_message': self.error_message,
            'retry_count': self.retry_count
        }


class SyncSession(Base):
    """Track synchronization sessions for audit purposes."""
    __tablename__ = 'sync_sessions'

    id = Column(Integer, primary_key=True)
    session_id = Column(String(100), unique=True, nullable=False)

    # Session metadata
    linkedin_contacts_count = Column(Integer, default=0)
    crm_contacts_count = Column(Integer, default=0)
    duplicates_found = Column(Integer, default=0)
    auto_synced = Column(Integer, default=0)
    manual_review_required = Column(Integer, default=0)

    # Timestamps
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime)

    # Results
    success = Column(String(10))  # 'success', 'partial', 'failed'
    error_message = Column(Text)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'session_id': self.session_id,
            'linkedin_contacts_count': self.linkedin_contacts_count,
            'crm_contacts_count': self.crm_contacts_count,
            'duplicates_found': self.duplicates_found,
            'auto_synced': self.auto_synced,
            'manual_review_required': self.manual_review_required,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'success': self.success,
            'error_message': self.error_message
        }


class DatabaseManager:
    """Manages SQLite database connection and operations."""

    def __init__(self, database_url: str = "sqlite:///duplicates.db"):
        """
        Initialize database manager.

        Args:
            database_url: SQLite database URL
        """
        self.engine = create_engine(database_url, echo=False)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)

    def create_tables(self):
        """Create all database tables."""
        Base.metadata.create_all(bind=self.engine)

    def get_session(self):
        """Get a database session."""
        return self.SessionLocal()

    def drop_tables(self):
        """Drop all database tables (for testing)."""
        Base.metadata.drop_all(bind=self.engine)


# Global database manager instance
db_manager = DatabaseManager()