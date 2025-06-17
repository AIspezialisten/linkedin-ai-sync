"""
AI-powered duplicate detection service using PydanticAI and Ollama.

This module uses Mistral-small:24b via Ollama to intelligently compare
LinkedIn contacts with CRM contacts to identify potential duplicates.
"""

import asyncio
import logging
import os
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum
from dataclasses import dataclass

from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider
import ollama


class MatchConfidence(str, Enum):
    """Confidence levels for duplicate matches."""
    HIGH = "high"       # Very likely the same person (95%+ confidence)
    MEDIUM = "medium"   # Probably the same person (70-95% confidence)
    LOW = "low"         # Possibly the same person (40-70% confidence)
    NONE = "none"       # Different people (0-40% confidence)


class DuplicateMatch(BaseModel):
    """Result of a duplicate detection comparison."""
    linkedin_contact: Dict[str, Any] = Field(description="LinkedIn contact data")
    crm_contact: Dict[str, Any] = Field(description="CRM contact data")
    confidence: MatchConfidence = Field(description="Confidence level of the match")
    similarity_score: float = Field(description="Numerical similarity score (0-1)", ge=0, le=1)
    reasoning: str = Field(description="Explanation of why this is/isn't a match")
    matching_fields: List[str] = Field(description="Fields that suggest this is a match")
    conflicting_fields: List[str] = Field(description="Fields that suggest this isn't a match")


class ComparisonResult(BaseModel):
    """Structured result for contact comparison."""
    is_duplicate: bool = Field(description="Whether the contacts are likely duplicates")
    confidence: MatchConfidence = Field(description="Confidence level")
    similarity_score: float = Field(description="Similarity score from 0 to 1", ge=0, le=1)
    reasoning: str = Field(description="Detailed reasoning for the decision")
    matching_fields: List[str] = Field(description="Fields that match or are similar")
    conflicting_fields: List[str] = Field(description="Fields that don't match or conflict")


@dataclass
class ContactComparison:
    """Input data for contact comparison."""
    linkedin_contact: Dict[str, Any]
    crm_contact: Dict[str, Any]


class AIDuplicateDetector:
    """AI-powered duplicate detection using PydanticAI and Ollama."""
    
    def __init__(self, ollama_model: str = None, ollama_host: str = None):
        """
        Initialize the AI duplicate detector.
        
        Args:
            ollama_model: Name of the Ollama model to use (defaults to env OLLAMA_MODEL)
            ollama_host: URL of the Ollama server (defaults to env OLLAMA_HOST)
        """
        self.logger = logging.getLogger(__name__)
        
        # Use environment variables if not provided
        if not ollama_model:
            ollama_model = os.getenv('OLLAMA_MODEL', 'mistral-small:24b')
        if not ollama_host:
            ollama_host = os.getenv('OLLAMA_HOST', 'http://localhost:11434')
        
        self.ollama_model = ollama_model
        self.ollama_host = ollama_host
        
        # Create Ollama model using OpenAI provider
        ollama_model_instance = OpenAIModel(
            model_name=ollama_model,
            provider=OpenAIProvider(base_url=ollama_host + '/v1')
        )
        
        # Create PydanticAI agent with Ollama model
        self.agent = Agent(
            model=ollama_model_instance,
            result_type=ComparisonResult,
            system_prompt=self._get_system_prompt()
        )
    
    def _get_system_prompt(self) -> str:
        """Get the system prompt for the AI agent."""
        return """
You are a contact duplicate detection expert. Compare LinkedIn contacts with CRM contacts to determine if they are the same person.

Return a structured response with:
- is_duplicate: true/false
- confidence: "high", "medium", "low", or "none"
- similarity_score: 0.0 to 1.0
- reasoning: brief explanation
- matching_fields: list of fields that match
- conflicting_fields: list of fields that don't match

Confidence levels:
- high: Very likely same person (name + company match or unique identifier)
- medium: Probably same person (name + some professional details match)
- low: Possibly same person (partial matches)
- none: Different people (major conflicts or no significant matches)

Focus on name similarity, company/job alignment, and contact information.
"""
    
    async def compare_contacts(self, linkedin_contact: Dict[str, Any], 
                             crm_contact: Dict[str, Any]) -> ComparisonResult:
        """
        Compare a LinkedIn contact with a CRM contact to detect duplicates.
        
        Args:
            linkedin_contact: LinkedIn contact data
            crm_contact: CRM contact data
            
        Returns:
            ComparisonResult with duplicate detection analysis
        """
        try:
            # Prepare the comparison prompt
            prompt = self._build_comparison_prompt(linkedin_contact, crm_contact)
            
            # Run the AI analysis using PydanticAI
            result = await self.agent.run(prompt)
            
            return result.output
            
        except Exception as e:
            self.logger.error(f"Error in AI duplicate detection: {str(e)}")
            # Return a fallback result
            return ComparisonResult(
                is_duplicate=False,
                confidence=MatchConfidence.NONE,
                similarity_score=0.0,
                reasoning=f"Error during AI analysis: {str(e)}",
                matching_fields=[],
                conflicting_fields=[]
            )
    
    def _build_comparison_prompt(self, linkedin_contact: Dict[str, Any], 
                               crm_contact: Dict[str, Any]) -> str:
        """Build a detailed comparison prompt for the AI agent."""
        
        # Extract relevant fields from LinkedIn contact
        linkedin_data = {
            "first_name": (linkedin_contact.get("First Name") or "").strip(),
            "last_name": (linkedin_contact.get("Last Name") or "").strip(),
            "company": (linkedin_contact.get("Company") or "").strip(),
            "position": (linkedin_contact.get("Position") or "").strip(),
            "url": (linkedin_contact.get("URL") or "").strip(),
            "email": (linkedin_contact.get("Email Address") or "").strip(),
            "connected_on": (linkedin_contact.get("Connected On") or "").strip()
        }
        
        # Extract relevant fields from CRM contact
        crm_data = {
            "first_name": (crm_contact.get("firstname") or "").strip(),
            "last_name": (crm_contact.get("lastname") or "").strip(),
            "full_name": (crm_contact.get("fullname") or "").strip(),
            "email": (crm_contact.get("emailaddress1") or "").strip(),
            "job_title": (crm_contact.get("jobtitle") or "").strip(),
            "phone": (crm_contact.get("telephone1") or "").strip(),
            "mobile": (crm_contact.get("mobilephone") or "").strip(),
            "city": (crm_contact.get("address1_city") or "").strip(),
            "country": (crm_contact.get("address1_country") or "").strip(),
            "description": (crm_contact.get("description") or "").strip(),
            "linkedin_profile": (crm_contact.get("mc_linkedin") or "") or (crm_contact.get("mc_linkedinprofile") or "")
        }
        
        prompt = f"""
Compare these contacts:

LinkedIn: {linkedin_data['first_name']} {linkedin_data['last_name']} - {linkedin_data['company']} - {linkedin_data['position']}
CRM: {crm_data['first_name']} {crm_data['last_name']} - {crm_data['job_title']}

LinkedIn email: {linkedin_data['email'] or 'none'}
CRM email: {crm_data['email'] or 'none'}

Are these the same person? Consider name similarity, company/job alignment, and any matching contact details.
"""
        
        return prompt
    
    async def find_duplicates_for_linkedin_contact(self, 
                                                 linkedin_contact: Dict[str, Any],
                                                 crm_contacts: List[Dict[str, Any]],
                                                 min_confidence: MatchConfidence = MatchConfidence.LOW) -> List[DuplicateMatch]:
        """
        Find potential duplicates in CRM for a single LinkedIn contact.
        
        Args:
            linkedin_contact: LinkedIn contact to search for
            crm_contacts: List of CRM contacts to search in
            min_confidence: Minimum confidence level to include in results
            
        Returns:
            List of potential duplicate matches, sorted by confidence
        """
        matches = []
        
        self.logger.info(f"Searching for duplicates of LinkedIn contact: {linkedin_contact.get('First Name', '')} {linkedin_contact.get('Last Name', '')}")
        
        # Compare with each CRM contact
        for crm_contact in crm_contacts:
            try:
                result = await self.compare_contacts(linkedin_contact, crm_contact)
                
                # Create a duplicate match if confidence meets threshold
                confidence_levels = {
                    MatchConfidence.HIGH: 4,
                    MatchConfidence.MEDIUM: 3,
                    MatchConfidence.LOW: 2,
                    MatchConfidence.NONE: 1
                }
                
                if confidence_levels[result.confidence] >= confidence_levels[min_confidence]:
                    match = DuplicateMatch(
                        linkedin_contact=linkedin_contact,
                        crm_contact=crm_contact,
                        confidence=result.confidence,
                        similarity_score=result.similarity_score,
                        reasoning=result.reasoning,
                        matching_fields=result.matching_fields,
                        conflicting_fields=result.conflicting_fields
                    )
                    matches.append(match)
                    
                    self.logger.info(f"Found {result.confidence} confidence match with CRM contact: {crm_contact.get('fullname', 'Unknown')}")
                
            except Exception as e:
                self.logger.error(f"Error comparing contacts: {str(e)}")
                continue
        
        # Sort by confidence and similarity score
        matches.sort(key=lambda x: (
            confidence_levels[x.confidence],
            x.similarity_score
        ), reverse=True)
        
        return matches
    
    async def find_all_duplicates(self, 
                                linkedin_contacts: List[Dict[str, Any]],
                                crm_contacts: List[Dict[str, Any]],
                                min_confidence: MatchConfidence = MatchConfidence.MEDIUM) -> Dict[str, List[DuplicateMatch]]:
        """
        Find duplicates for all LinkedIn contacts against CRM contacts.
        
        Args:
            linkedin_contacts: List of LinkedIn contacts
            crm_contacts: List of CRM contacts
            min_confidence: Minimum confidence level for matches
            
        Returns:
            Dictionary mapping LinkedIn contact names to their potential duplicates
        """
        all_matches = {}
        
        self.logger.info(f"Starting duplicate detection for {len(linkedin_contacts)} LinkedIn contacts against {len(crm_contacts)} CRM contacts")
        
        for linkedin_contact in linkedin_contacts:
            contact_name = f"{linkedin_contact.get('First Name', '')} {linkedin_contact.get('Last Name', '')}".strip()
            
            matches = await self.find_duplicates_for_linkedin_contact(
                linkedin_contact, 
                crm_contacts, 
                min_confidence
            )
            
            if matches:
                all_matches[contact_name] = matches
                self.logger.info(f"Found {len(matches)} potential duplicates for {contact_name}")
            else:
                self.logger.info(f"No duplicates found for {contact_name}")
        
        return all_matches


class DuplicateDetectionService:
    """Service for managing duplicate detection operations."""
    
    def __init__(self, ollama_model: str = None, ollama_host: str = None):
        """Initialize the duplicate detection service."""
        self.detector = AIDuplicateDetector(ollama_model, ollama_host)
        self.logger = logging.getLogger(__name__)
    
    async def analyze_linkedin_vs_crm(self, 
                                    linkedin_contacts: List[Dict[str, Any]],
                                    crm_contacts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze LinkedIn contacts against CRM to find duplicates and generate sync recommendations.
        
        Args:
            linkedin_contacts: List of LinkedIn contacts
            crm_contacts: List of CRM contacts
            
        Returns:
            Analysis results with sync recommendations
        """
        self.logger.info("Starting comprehensive duplicate analysis")
        
        # Find all potential duplicates
        duplicates = await self.detector.find_all_duplicates(
            linkedin_contacts,
            crm_contacts,
            min_confidence=MatchConfidence.LOW
        )
        
        # Analyze results and generate recommendations
        analysis = {
            "total_linkedin_contacts": len(linkedin_contacts),
            "total_crm_contacts": len(crm_contacts),
            "contacts_with_potential_duplicates": len(duplicates),
            "high_confidence_matches": 0,
            "medium_confidence_matches": 0,
            "low_confidence_matches": 0,
            "contacts_safe_to_sync": [],
            "contacts_need_review": [],
            "duplicate_details": duplicates
        }
        
        # Count matches by confidence level
        for contact_name, matches in duplicates.items():
            best_match = matches[0]  # Highest confidence match
            
            if best_match.confidence == MatchConfidence.HIGH:
                analysis["high_confidence_matches"] += 1
                analysis["contacts_need_review"].append({
                    "linkedin_contact": contact_name,
                    "action": "skip_sync",
                    "reason": f"High confidence duplicate found: {best_match.crm_contact.get('fullname', 'Unknown')}",
                    "match_details": best_match.dict()
                })
            elif best_match.confidence == MatchConfidence.MEDIUM:
                analysis["medium_confidence_matches"] += 1
                analysis["contacts_need_review"].append({
                    "linkedin_contact": contact_name,
                    "action": "manual_review",
                    "reason": f"Medium confidence duplicate found: {best_match.crm_contact.get('fullname', 'Unknown')}",
                    "match_details": best_match.dict()
                })
            else:  # LOW confidence
                analysis["low_confidence_matches"] += 1
                analysis["contacts_safe_to_sync"].append({
                    "linkedin_contact": contact_name,
                    "action": "sync_with_caution",
                    "reason": f"Low confidence duplicate found: {best_match.crm_contact.get('fullname', 'Unknown')}",
                    "match_details": best_match.dict()
                })
        
        # Identify contacts with no duplicates (safe to sync)
        for linkedin_contact in linkedin_contacts:
            contact_name = f"{linkedin_contact.get('First Name', '')} {linkedin_contact.get('Last Name', '')}".strip()
            
            if contact_name not in duplicates:
                analysis["contacts_safe_to_sync"].append({
                    "linkedin_contact": contact_name,
                    "action": "sync",
                    "reason": "No duplicates found - safe to sync",
                    "match_details": None
                })
        
        self.logger.info(f"Duplicate analysis complete: {analysis['high_confidence_matches']} high, {analysis['medium_confidence_matches']} medium, {analysis['low_confidence_matches']} low confidence matches")
        
        return analysis