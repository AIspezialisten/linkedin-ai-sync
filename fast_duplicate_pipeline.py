#!/usr/bin/env python3
"""
Fast multi-stage duplicate detection pipeline optimized for speed.

This simplified version uses:
1. Blocking (same as before)
2. Fast similarity scoring instead of dedupe ML
3. Selective AI verification for top candidates

Designed to run quickly while maintaining good accuracy.
"""

import json
import logging
import time
from pathlib import Path
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass
from collections import defaultdict
import re
from unidecode import unidecode
import asyncio

# Import the blocking engine from our main pipeline
from duplicate_detection_pipeline import BlockingEngine, CandidatePair
from sync.ai_duplicate_detection import AIDuplicateDetector, MatchConfidence


@dataclass
class ScoredCandidate:
    """A candidate pair with similarity score."""
    linkedin_contact: Dict[str, Any]
    crm_contact: Dict[str, Any]
    blocking_reason: str
    similarity_score: float
    match_details: Dict[str, Any]


class FastSimilarityScorer:
    """Fast similarity scoring for candidate pairs."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def normalize_text(self, text: str) -> str:
        """Normalize text for comparison."""
        if not text:
            return ""
        return unidecode(str(text).lower().strip())
    
    def name_similarity(self, name1: str, name2: str) -> float:
        """Calculate name similarity score."""
        if not name1 or not name2:
            return 0.0
        
        name1 = self.normalize_text(name1)
        name2 = self.normalize_text(name2)
        
        # Exact match
        if name1 == name2:
            return 1.0
        
        # Check word overlap
        words1 = set(name1.split())
        words2 = set(name2.split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        # Jaccard similarity with boost for name words
        jaccard = len(intersection) / len(union)
        
        # Boost score if significant name words match
        significant_matches = sum(1 for word in intersection if len(word) > 2)
        if significant_matches > 0:
            jaccard = min(1.0, jaccard + 0.2 * significant_matches)
        
        return jaccard
    
    def email_similarity(self, email1: str, email2: str) -> float:
        """Calculate email similarity score."""
        if not email1 or not email2:
            return 0.0
        
        email1 = email1.lower().strip()
        email2 = email2.lower().strip()
        
        # Exact match
        if email1 == email2:
            return 1.0
        
        # Check username similarity (before @)
        try:
            user1 = email1.split('@')[0]
            user2 = email2.split('@')[0]
            
            if user1 == user2:
                return 0.8  # Same username, different domain
            
            # Check if one username contains the other
            if user1 in user2 or user2 in user1:
                return 0.6
                
        except:
            pass
        
        return 0.0
    
    def company_similarity(self, company1: str, company2: str) -> float:
        """Calculate company similarity score."""
        if not company1 or not company2:
            return 0.0
        
        company1 = self.normalize_text(company1)
        company2 = self.normalize_text(company2)
        
        # Remove common company suffixes
        for suffix in ['gmbh', 'ag', 'ltd', 'inc', 'corp', 'llc', 'sa', 'bv']:
            company1 = company1.replace(f' {suffix}', '').replace(f'{suffix} ', '')
            company2 = company2.replace(f' {suffix}', '').replace(f'{suffix} ', '')
        
        company1 = company1.strip()
        company2 = company2.strip()
        
        # Exact match
        if company1 == company2:
            return 1.0
        
        # One contains the other
        if company1 in company2 or company2 in company1:
            return 0.8
        
        # Word overlap
        words1 = set(company1.split())
        words2 = set(company2.split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union)
    
    def score_candidate_pair(self, linkedin_contact: Dict, crm_contact: Dict) -> ScoredCandidate:
        """Score a candidate pair using fast similarity metrics."""
        # Extract LinkedIn data
        linkedin_name = linkedin_contact.get('full_name', '')
        linkedin_email = linkedin_contact.get('email', '')
        linkedin_company = ''
        
        current_pos = linkedin_contact.get('current_position', '')
        if current_pos and ' at ' in current_pos:
            linkedin_company = current_pos.split(' at ')[-1]
        
        # Extract CRM data
        crm_name = crm_contact.get('fullname', '') or f"{crm_contact.get('firstname', '')} {crm_contact.get('lastname', '')}".strip()
        crm_email = crm_contact.get('emailaddress1', '')
        crm_company = crm_contact.get('companyname', '')
        
        # Calculate individual similarity scores
        name_score = self.name_similarity(linkedin_name, crm_name)
        email_score = self.email_similarity(linkedin_email, crm_email)
        company_score = self.company_similarity(linkedin_company, crm_company)
        
        # Calculate weighted overall score
        weights = {
            'name': 0.4,
            'email': 0.4,
            'company': 0.2
        }
        
        overall_score = (
            name_score * weights['name'] +
            email_score * weights['email'] +
            company_score * weights['company']
        )
        
        # Boost score for exact email matches
        if email_score == 1.0:
            overall_score = min(1.0, overall_score + 0.3)
        
        match_details = {
            'name_score': name_score,
            'email_score': email_score,
            'company_score': company_score,
            'linkedin_name': linkedin_name,
            'crm_name': crm_name,
            'linkedin_email': linkedin_email,
            'crm_email': crm_email,
            'linkedin_company': linkedin_company,
            'crm_company': crm_company
        }
        
        return ScoredCandidate(
            linkedin_contact=linkedin_contact,
            crm_contact=crm_contact,
            blocking_reason="",
            similarity_score=overall_score,
            match_details=match_details
        )


class FastDuplicateDetector:
    """Fast multi-stage duplicate detection pipeline."""
    
    def __init__(self, ollama_model: str = None, ollama_host: str = None):
        """Initialize the fast detector."""
        self.logger = logging.getLogger(__name__)
        
        # Initialize components
        self.blocking_engine = BlockingEngine()
        self.scorer = FastSimilarityScorer()
        self.ai_detector = AIDuplicateDetector(ollama_model, ollama_host)
        
        # Configuration
        self.fast_threshold_high = 0.8
        self.fast_threshold_medium = 0.6
        self.max_ai_comparisons = 1000  # Reduced for speed
    
    async def detect_duplicates(self, linkedin_contacts: List[Dict], crm_contacts: List[Dict]) -> Dict[str, Any]:
        """Run the fast multi-stage duplicate detection pipeline."""
        self.logger.info(f"Starting fast duplicate detection pipeline")
        self.logger.info(f"LinkedIn contacts: {len(linkedin_contacts):,}")
        self.logger.info(f"CRM contacts: {len(crm_contacts):,}")
        
        start_time = time.time()
        results = {
            "pipeline_stats": {
                "total_linkedin_contacts": len(linkedin_contacts),
                "total_crm_contacts": len(crm_contacts),
                "potential_comparisons": len(linkedin_contacts) * len(crm_contacts),
                "stages_completed": 0,
                "total_runtime_seconds": 0
            },
            "stage_1_blocking": {},
            "stage_2_scoring": {},
            "stage_3_ai": {},
            "final_results": {
                "high_confidence_matches": [],
                "medium_confidence_matches": [],
                "low_confidence_matches": []
            }
        }
        
        # Stage 1: Blocking
        self.logger.info("=" * 50)
        self.logger.info("STAGE 1: Fast Pre-filtering (Blocking)")
        self.logger.info("=" * 50)
        
        candidate_pairs = self.blocking_engine.generate_candidate_pairs(linkedin_contacts, crm_contacts)
        
        results["stage_1_blocking"] = {
            "candidates_generated": len(candidate_pairs),
            "reduction_factor": results["pipeline_stats"]["potential_comparisons"] / len(candidate_pairs) if candidate_pairs else 1
        }
        results["pipeline_stats"]["stages_completed"] = 1
        
        if not candidate_pairs:
            self.logger.warning("No candidate pairs found in blocking stage")
            return results
        
        # Stage 2: Fast Scoring
        self.logger.info("=" * 50)
        self.logger.info("STAGE 2: Fast Similarity Scoring")
        self.logger.info("=" * 50)
        
        scoring_results = self._run_scoring_stage(candidate_pairs)
        results["stage_2_scoring"] = scoring_results
        results["pipeline_stats"]["stages_completed"] = 2
        
        # Stage 3: Selective AI Verification
        self.logger.info("=" * 50)
        self.logger.info("STAGE 3: AI Verification (Selective)")
        self.logger.info("=" * 50)
        
        ai_results = await self._run_ai_stage(
            scoring_results["high_confidence_pairs"],
            scoring_results["medium_confidence_pairs"]
        )
        results["stage_3_ai"] = ai_results
        results["pipeline_stats"]["stages_completed"] = 3
        
        # Combine final results
        self._combine_final_results(results, scoring_results, ai_results)
        
        # Calculate total runtime
        results["pipeline_stats"]["total_runtime_seconds"] = time.time() - start_time
        
        self.logger.info("=" * 50)
        self.logger.info("FAST PIPELINE COMPLETE")
        self.logger.info("=" * 50)
        self._print_pipeline_summary(results)
        
        return results
    
    def _run_scoring_stage(self, candidate_pairs: List[CandidatePair]) -> Dict[str, Any]:
        """Run the fast similarity scoring stage."""
        self.logger.info(f"Scoring {len(candidate_pairs)} candidate pairs...")
        
        scored_pairs = []
        
        for i, pair in enumerate(candidate_pairs):
            if i % 1000 == 0 and i > 0:
                self.logger.info(f"Scoring progress: {i}/{len(candidate_pairs)}")
            
            scored = self.scorer.score_candidate_pair(pair.linkedin_contact, pair.crm_contact)
            scored.blocking_reason = pair.blocking_reason
            scored_pairs.append(scored)
        
        # Sort by similarity score
        scored_pairs.sort(key=lambda x: x.similarity_score, reverse=True)
        
        # Categorize by score thresholds
        high_confidence = [p for p in scored_pairs if p.similarity_score >= self.fast_threshold_high]
        medium_confidence = [p for p in scored_pairs if self.fast_threshold_medium <= p.similarity_score < self.fast_threshold_high]
        low_confidence = [p for p in scored_pairs if p.similarity_score < self.fast_threshold_medium]
        
        self.logger.info(f"Scoring complete: {len(high_confidence)} high, {len(medium_confidence)} medium, {len(low_confidence)} low confidence")
        
        return {
            "total_pairs_scored": len(scored_pairs),
            "high_confidence_pairs": high_confidence,
            "medium_confidence_pairs": medium_confidence,
            "low_confidence_pairs": low_confidence,
            "fast_threshold_high": self.fast_threshold_high,
            "fast_threshold_medium": self.fast_threshold_medium,
            "top_10_matches": [
                {
                    "similarity_score": p.similarity_score,
                    "linkedin_name": p.match_details.get('linkedin_name', ''),
                    "crm_name": p.match_details.get('crm_name', ''),
                    "linkedin_email": p.match_details.get('linkedin_email', ''),
                    "crm_email": p.match_details.get('crm_email', ''),
                    "match_details": p.match_details
                } for p in scored_pairs[:10]
            ]
        }
    
    async def _run_ai_stage(self, high_confidence_pairs: List[ScoredCandidate], medium_confidence_pairs: List[ScoredCandidate]) -> Dict[str, Any]:
        """Run the selective AI verification stage."""
        ai_results = {
            "pairs_processed": 0,
            "pairs_skipped": 0,
            "high_confidence_auto_accepted": len(high_confidence_pairs),
            "medium_confidence_ai_verified": 0,
            "ai_confirmations": [],
            "ai_rejections": []
        }
        
        # Auto-accept high confidence scoring matches
        self.logger.info(f"Auto-accepting {len(high_confidence_pairs)} high-confidence scored matches")
        
        # AI verification for medium confidence matches (limited)
        pairs_to_verify = medium_confidence_pairs[:self.max_ai_comparisons]
        ai_results["pairs_skipped"] = len(medium_confidence_pairs) - len(pairs_to_verify)
        
        self.logger.info(f"AI verifying {len(pairs_to_verify)} medium-confidence pairs")
        
        for i, scored_pair in enumerate(pairs_to_verify):
            if i % 50 == 0 and i > 0:
                self.logger.info(f"AI verification progress: {i}/{len(pairs_to_verify)}")
            
            try:
                ai_result = await self.ai_detector.compare_contacts(
                    scored_pair.linkedin_contact, 
                    scored_pair.crm_contact
                )
                
                ai_match_data = {
                    "original_scored_match": {
                        "similarity_score": scored_pair.similarity_score,
                        "match_details": scored_pair.match_details,
                        "blocking_reason": scored_pair.blocking_reason
                    },
                    "ai_result": ai_result.model_dump(),
                    "combined_confidence": (scored_pair.similarity_score + ai_result.similarity_score) / 2,
                    "linkedin_contact": scored_pair.linkedin_contact,
                    "crm_contact": scored_pair.crm_contact
                }
                
                if ai_result.is_duplicate and ai_result.confidence in [MatchConfidence.HIGH, MatchConfidence.MEDIUM]:
                    ai_results["ai_confirmations"].append(ai_match_data)
                else:
                    ai_results["ai_rejections"].append(ai_match_data)
                
                ai_results["pairs_processed"] += 1
                
            except Exception as e:
                self.logger.error(f"Error in AI verification: {str(e)}")
                continue
        
        ai_results["medium_confidence_ai_verified"] = ai_results["pairs_processed"]
        
        self.logger.info(f"AI verification complete: {len(ai_results['ai_confirmations'])} confirmed, {len(ai_results['ai_rejections'])} rejected")
        
        return ai_results
    
    def _combine_final_results(self, results: Dict, scoring_results: Dict, ai_results: Dict):
        """Combine results from all stages into final recommendations."""
        final_results = results["final_results"]
        
        # Convert high confidence scored pairs to standard format
        high_confidence_matches = []
        for scored_pair in scoring_results["high_confidence_pairs"]:
            match_data = {
                "confidence_score": scored_pair.similarity_score,
                "linkedin_profile": {
                    "full_name": scored_pair.linkedin_contact.get('full_name', ''),
                    "email": scored_pair.linkedin_contact.get('email', ''),
                    "profile_url": scored_pair.linkedin_contact.get('profile_url', ''),
                    "source_data": scored_pair.linkedin_contact
                },
                "crm_contact": {
                    "full_name": scored_pair.crm_contact.get('fullname', ''),
                    "email": scored_pair.crm_contact.get('emailaddress1', ''),
                    "source_data": scored_pair.crm_contact
                },
                "match_details": scored_pair.match_details,
                "detection_method": "fast_scoring"
            }
            high_confidence_matches.append(match_data)
        
        # High confidence: Scored matches + AI confirmations
        final_results["high_confidence_matches"] = high_confidence_matches + ai_results["ai_confirmations"]
        
        # Medium confidence: AI rejections (need manual review)
        final_results["medium_confidence_matches"] = ai_results["ai_rejections"]
        
        # Low confidence: Low scored matches (sample only) - convert to serializable format
        low_confidence_matches = []
        for scored_pair in scoring_results["low_confidence_pairs"][:100]:  # Limit to first 100
            match_data = {
                "confidence_score": scored_pair.similarity_score,
                "linkedin_profile": {
                    "full_name": scored_pair.linkedin_contact.get('full_name', ''),
                    "email": scored_pair.linkedin_contact.get('email', ''),
                    "source_data": scored_pair.linkedin_contact
                },
                "crm_contact": {
                    "full_name": scored_pair.crm_contact.get('fullname', ''),
                    "email": scored_pair.crm_contact.get('emailaddress1', ''),
                    "source_data": scored_pair.crm_contact
                },
                "match_details": scored_pair.match_details,
                "detection_method": "fast_scoring"
            }
            low_confidence_matches.append(match_data)
        
        final_results["low_confidence_matches"] = low_confidence_matches
        
        # Calculate summary stats
        total_matches = (
            len(final_results["high_confidence_matches"]) +
            len(final_results["medium_confidence_matches"]) +
            len(final_results["low_confidence_matches"])
        )
        
        results["pipeline_stats"]["total_matches_found"] = total_matches
        results["pipeline_stats"]["high_confidence_matches"] = len(final_results["high_confidence_matches"])
        results["pipeline_stats"]["medium_confidence_matches"] = len(final_results["medium_confidence_matches"])
        results["pipeline_stats"]["low_confidence_matches"] = len(final_results["low_confidence_matches"])
    
    def _print_pipeline_summary(self, results: Dict):
        """Print a comprehensive summary of the pipeline results."""
        stats = results["pipeline_stats"]
        
        print(f"\n🚀 Fast Multi-Stage Duplicate Detection Results")
        print("=" * 60)
        print(f"📊 Input Data:")
        print(f"   LinkedIn contacts: {stats['total_linkedin_contacts']:,}")
        print(f"   CRM contacts: {stats['total_crm_contacts']:,}")
        print(f"   Potential comparisons: {stats['potential_comparisons']:,}")
        
        print(f"\n⚡ Performance:")
        print(f"   Stages completed: {stats['stages_completed']}/3")
        print(f"   Total runtime: {stats['total_runtime_seconds']:.1f} seconds")
        print(f"   Candidates after blocking: {results['stage_1_blocking']['candidates_generated']:,}")
        print(f"   Reduction factor: {results['stage_1_blocking']['reduction_factor']:.1f}x")
        
        print(f"\n🎯 Final Results:")
        print(f"   High confidence matches: {stats['high_confidence_matches']}")
        print(f"   Medium confidence matches: {stats['medium_confidence_matches']}")
        print(f"   Low confidence matches: {stats['low_confidence_matches']}")
        print(f"   Total matches found: {stats['total_matches_found']}")
        
        if results["stage_3_ai"]:
            ai_stats = results["stage_3_ai"]
            print(f"\n🤖 AI Verification:")
            print(f"   Pairs processed by AI: {ai_stats['pairs_processed']}")
            print(f"   AI confirmations: {len(ai_stats['ai_confirmations'])}")
            print(f"   AI rejections: {len(ai_stats['ai_rejections'])}")
        
        # Show top matches
        high_matches = results["final_results"]["high_confidence_matches"]
        if high_matches:
            print(f"\n🔥 Top 5 High-Confidence Matches:")
            print("-" * 40)
            for i, match in enumerate(high_matches[:5]):
                linkedin_name = match.get('linkedin_profile', {}).get('full_name', 'Unknown')
                crm_name = match.get('crm_contact', {}).get('full_name', 'Unknown')
                confidence = match.get('confidence_score', match.get('combined_confidence', 0))
                print(f"{i+1}. {linkedin_name} ↔ {crm_name} ({confidence:.2f})")
    
    def save_results(self, results: Dict[str, Any], output_file: str = None) -> Path:
        """Save pipeline results to JSON file."""
        if not output_file:
            output_file = f"data/fast_duplicate_results_{int(time.time())}.json"
        
        output_path = Path(output_file)
        output_path.parent.mkdir(exist_ok=True)
        
        # Add timestamp
        results["analysis_timestamp"] = time.strftime("%Y-%m-%d %H:%M:%S")
        
        # Create a clean copy without ScoredCandidate objects for JSON serialization
        clean_results = {}
        for key, value in results.items():
            if key == "stage_2_scoring":
                # Remove the non-serializable objects and keep only summary data
                clean_results[key] = {
                    "total_pairs_scored": value["total_pairs_scored"],
                    "high_confidence_count": len(value["high_confidence_pairs"]),
                    "medium_confidence_count": len(value["medium_confidence_pairs"]),
                    "low_confidence_count": len(value["low_confidence_pairs"]),
                    "fast_threshold_high": value["fast_threshold_high"],
                    "fast_threshold_medium": value["fast_threshold_medium"],
                    "top_10_matches": value.get("top_10_matches", [])
                }
            else:
                clean_results[key] = value
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(clean_results, f, indent=2, ensure_ascii=False)
        
        file_size = output_path.stat().st_size / 1024 / 1024
        self.logger.info(f"Results saved to {output_path} ({file_size:.1f} MB)")
        
        return output_path


async def main():
    """Main function to run the fast duplicate detection pipeline."""
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('data/fast_duplicate_detection.log', mode='a')
        ]
    )
    
    logger = logging.getLogger(__name__)
    
    print("🚀 Fast Multi-Stage Duplicate Detection Pipeline")
    print("=" * 60)
    
    # Load data
    linkedin_file = Path("data/linkedin_profiles_detailed.json")
    crm_file = Path("data/dynamics_crm_contacts_all.json")
    
    if not linkedin_file.exists():
        print(f"❌ LinkedIn data file not found: {linkedin_file}")
        return False
    
    if not crm_file.exists():
        print(f"❌ CRM data file not found: {crm_file}")
        return False
    
    try:
        # Load LinkedIn contacts
        with open(linkedin_file, 'r', encoding='utf-8') as f:
            linkedin_data = json.load(f)
        linkedin_contacts = linkedin_data.get('profiles', [])
        
        # Load CRM contacts
        with open(crm_file, 'r', encoding='utf-8') as f:
            crm_data = json.load(f)
        crm_contacts = crm_data.get('contacts', [])
        
        if not linkedin_contacts:
            print("❌ No LinkedIn contacts found")
            return False
        
        if not crm_contacts:
            print("❌ No CRM contacts found")
            return False
        
        # Initialize and run pipeline
        detector = FastDuplicateDetector()
        results = await detector.detect_duplicates(linkedin_contacts, crm_contacts)
        
        # Save results
        output_file = detector.save_results(results)
        
        print(f"\n✅ Fast duplicate detection complete!")
        print(f"📁 Full results saved to: {output_file}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error in fast duplicate detection: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    import asyncio
    success = asyncio.run(main())
    exit(0 if success else 1)