#!/usr/bin/env python3
"""
Multi-stage duplicate detection pipeline for LinkedIn and CRM contacts.

This pipeline uses a three-stage approach to efficiently detect duplicates:
1. Fast pre-filtering (blocking) to reduce candidate pairs
2. ML-based ranking using dedupe library
3. Selective AI verification for final decisions

Reduces comparisons from 7.4M to manageable numbers while maintaining accuracy.
"""

import json
import logging
import time
from pathlib import Path
from typing import Dict, List, Any, Tuple, Set
from dataclasses import dataclass
from collections import defaultdict
import re
from unidecode import unidecode

# Import existing components
from duplicate_finder import DuplicateFinder
from sync.ai_duplicate_detection import AIDuplicateDetector, MatchConfidence


@dataclass
class CandidatePair:
    """Represents a candidate duplicate pair."""
    linkedin_contact: Dict[str, Any]
    crm_contact: Dict[str, Any]
    blocking_reason: str
    similarity_score: float = 0.0


class BlockingEngine:
    """Fast pre-filtering to create candidate pairs using blocking techniques."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def normalize_for_blocking(self, text: str) -> str:
        """Normalize text for blocking (more aggressive than dedupe normalization)."""
        if not text or not str(text).strip():
            return ""
        
        # Convert to lowercase, remove accents
        text = unidecode(str(text).lower())
        
        # Remove all non-alphanumeric characters
        text = re.sub(r'[^a-z0-9]', '', text)
        
        # Remove common prefixes/suffixes
        text = re.sub(r'^(dr|prof|mr|mrs|ms)', '', text)
        text = re.sub(r'(gmbh|ag|ltd|inc|corp|llc)$', '', text)
        
        return text.strip()
    
    def extract_email_domain(self, email: str) -> str:
        """Extract domain from email address."""
        if not email or '@' not in email:
            return ""
        return email.split('@')[1].lower().strip()
    
    def create_name_blocks(self, linkedin_contacts: List[Dict], crm_contacts: List[Dict]) -> Dict[str, List]:
        """Create blocking keys based on names."""
        blocks = defaultdict(list)
        
        # Process LinkedIn contacts
        for i, contact in enumerate(linkedin_contacts):
            full_name = contact.get('full_name', '')
            if full_name:
                # Block by normalized full name
                normalized = self.normalize_for_blocking(full_name)
                if len(normalized) >= 3:
                    blocks[f"name_{normalized}"].append(('linkedin', i, contact))
                
                # Block by first/last name combination
                parts = full_name.split()
                if len(parts) >= 2:
                    first = self.normalize_for_blocking(parts[0])
                    last = self.normalize_for_blocking(parts[-1])
                    if len(first) >= 2 and len(last) >= 2:
                        blocks[f"name_{first}_{last}"].append(('linkedin', i, contact))
        
        # Process CRM contacts
        for i, contact in enumerate(crm_contacts):
            full_name = contact.get('fullname', '') or f"{contact.get('firstname', '')} {contact.get('lastname', '')}".strip()
            if full_name:
                # Block by normalized full name
                normalized = self.normalize_for_blocking(full_name)
                if len(normalized) >= 3:
                    blocks[f"name_{normalized}"].append(('crm', i, contact))
                
                # Block by first/last name combination
                first_name = contact.get('firstname', '')
                last_name = contact.get('lastname', '')
                if first_name and last_name:
                    first = self.normalize_for_blocking(first_name)
                    last = self.normalize_for_blocking(last_name)
                    if len(first) >= 2 and len(last) >= 2:
                        blocks[f"name_{first}_{last}"].append(('crm', i, contact))
        
        return blocks
    
    def create_email_blocks(self, linkedin_contacts: List[Dict], crm_contacts: List[Dict]) -> Dict[str, List]:
        """Create blocking keys based on email addresses and domains."""
        blocks = defaultdict(list)
        
        # Process LinkedIn contacts
        for i, contact in enumerate(linkedin_contacts):
            email = contact.get('email', '')
            if email and '@' in email:
                # Block by exact email
                blocks[f"email_{email.lower()}"].append(('linkedin', i, contact))
                
                # Block by email domain for company matching
                domain = self.extract_email_domain(email)
                if domain and not domain.endswith(('.gmail.com', '.outlook.com', '.yahoo.com', '.hotmail.com')):
                    blocks[f"domain_{domain}"].append(('linkedin', i, contact))
        
        # Process CRM contacts
        for i, contact in enumerate(crm_contacts):
            email = contact.get('emailaddress1', '')
            if email and '@' in email:
                # Block by exact email
                blocks[f"email_{email.lower()}"].append(('crm', i, contact))
                
                # Block by email domain for company matching
                domain = self.extract_email_domain(email)
                if domain and not domain.endswith(('.gmail.com', '.outlook.com', '.yahoo.com', '.hotmail.com')):
                    blocks[f"domain_{domain}"].append(('crm', i, contact))
        
        return blocks
    
    def create_company_blocks(self, linkedin_contacts: List[Dict], crm_contacts: List[Dict]) -> Dict[str, List]:
        """Create blocking keys based on company names."""
        blocks = defaultdict(list)
        
        # Process LinkedIn contacts
        for i, contact in enumerate(linkedin_contacts):
            current_pos = contact.get('current_position', '')
            if current_pos and ' at ' in current_pos:
                company = current_pos.split(' at ')[-1]
                normalized = self.normalize_for_blocking(company)
                if len(normalized) >= 3:
                    blocks[f"company_{normalized}"].append(('linkedin', i, contact))
        
        # Process CRM contacts
        for i, contact in enumerate(crm_contacts):
            company = contact.get('companyname', '') or contact.get('parentcustomerid', '')
            if company:
                normalized = self.normalize_for_blocking(company)
                if len(normalized) >= 3:
                    blocks[f"company_{normalized}"].append(('crm', i, contact))
        
        return blocks
    
    def generate_candidate_pairs(self, linkedin_contacts: List[Dict], crm_contacts: List[Dict]) -> List[CandidatePair]:
        """Generate candidate pairs using multiple blocking strategies."""
        self.logger.info("Starting blocking phase...")
        start_time = time.time()
        
        all_blocks = {}
        
        # Create different types of blocks
        name_blocks = self.create_name_blocks(linkedin_contacts, crm_contacts)
        email_blocks = self.create_email_blocks(linkedin_contacts, crm_contacts)
        company_blocks = self.create_company_blocks(linkedin_contacts, crm_contacts)
        
        # Combine all blocks
        all_blocks.update({f"name_{k}": v for k, v in name_blocks.items()})
        all_blocks.update({f"email_{k}": v for k, v in email_blocks.items()})
        all_blocks.update({f"company_{k}": v for k, v in company_blocks.items()})
        
        # Generate candidate pairs from blocks
        candidate_pairs = []
        seen_pairs = set()
        
        for block_key, records in all_blocks.items():
            if len(records) < 2:
                continue
            
            # Find LinkedIn and CRM records in this block
            linkedin_records = [r for r in records if r[0] == 'linkedin']
            crm_records = [r for r in records if r[0] == 'crm']
            
            # Create pairs between LinkedIn and CRM records
            for linkedin_record in linkedin_records:
                for crm_record in crm_records:
                    # Create unique pair identifier
                    pair_id = (linkedin_record[1], crm_record[1])
                    
                    if pair_id not in seen_pairs:
                        seen_pairs.add(pair_id)
                        
                        candidate_pair = CandidatePair(
                            linkedin_contact=linkedin_record[2],
                            crm_contact=crm_record[2],
                            blocking_reason=block_key
                        )
                        candidate_pairs.append(candidate_pair)
        
        elapsed = time.time() - start_time
        reduction_factor = (len(linkedin_contacts) * len(crm_contacts)) / len(candidate_pairs) if candidate_pairs else 1
        
        self.logger.info(f"Blocking complete in {elapsed:.2f}s")
        self.logger.info(f"Reduced from {len(linkedin_contacts) * len(crm_contacts):,} to {len(candidate_pairs):,} candidates")
        self.logger.info(f"Reduction factor: {reduction_factor:.1f}x")
        
        return candidate_pairs


class MultiStageDuplicateDetector:
    """Main pipeline for multi-stage duplicate detection."""
    
    def __init__(self, ollama_model: str = None, ollama_host: str = None):
        """Initialize the multi-stage detector."""
        self.logger = logging.getLogger(__name__)
        
        # Initialize components
        self.blocking_engine = BlockingEngine()
        self.dedupe_finder = DuplicateFinder()
        self.ai_detector = AIDuplicateDetector(ollama_model, ollama_host)
        
        # Configuration
        self.dedupe_threshold_high = 0.8
        self.dedupe_threshold_medium = 0.5
        self.max_ai_comparisons = 10000
    
    async def detect_duplicates(self, linkedin_contacts: List[Dict], crm_contacts: List[Dict]) -> Dict[str, Any]:
        """
        Run the complete multi-stage duplicate detection pipeline.
        
        Args:
            linkedin_contacts: List of LinkedIn contacts
            crm_contacts: List of CRM contacts
            
        Returns:
            Comprehensive duplicate detection results
        """
        self.logger.info(f"Starting multi-stage duplicate detection")
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
            "stage_2_dedupe": {},
            "stage_3_ai": {},
            "final_results": {
                "high_confidence_matches": [],
                "medium_confidence_matches": [],
                "low_confidence_matches": [],
                "no_matches": []
            }
        }
        
        # Stage 1: Blocking
        self.logger.info("=" * 50)
        self.logger.info("STAGE 1: Fast Pre-filtering (Blocking)")
        self.logger.info("=" * 50)
        
        candidate_pairs = self.blocking_engine.generate_candidate_pairs(linkedin_contacts, crm_contacts)
        
        results["stage_1_blocking"] = {
            "candidates_generated": len(candidate_pairs),
            "reduction_factor": results["pipeline_stats"]["potential_comparisons"] / len(candidate_pairs) if candidate_pairs else 1,
            "blocking_strategies": ["name_matching", "email_matching", "company_matching"]
        }
        results["pipeline_stats"]["stages_completed"] = 1
        
        if not candidate_pairs:
            self.logger.warning("No candidate pairs found in blocking stage")
            return results
        
        # Stage 2: Dedupe ML Ranking
        self.logger.info("=" * 50)
        self.logger.info("STAGE 2: ML-based Candidate Ranking (dedupe)")
        self.logger.info("=" * 50)
        
        dedupe_results = await self._run_dedupe_stage(candidate_pairs)
        results["stage_2_dedupe"] = dedupe_results
        results["pipeline_stats"]["stages_completed"] = 2
        
        # Stage 3: Selective AI Verification
        self.logger.info("=" * 50)
        self.logger.info("STAGE 3: AI Verification (Selective)")
        self.logger.info("=" * 50)
        
        ai_results = await self._run_ai_stage(
            dedupe_results["high_confidence_pairs"],
            dedupe_results["medium_confidence_pairs"]
        )
        results["stage_3_ai"] = ai_results
        results["pipeline_stats"]["stages_completed"] = 3
        
        # Combine final results
        self._combine_final_results(results, dedupe_results, ai_results)
        
        # Calculate total runtime
        results["pipeline_stats"]["total_runtime_seconds"] = time.time() - start_time
        
        self.logger.info("=" * 50)
        self.logger.info("PIPELINE COMPLETE")
        self.logger.info("=" * 50)
        self._print_pipeline_summary(results)
        
        return results
    
    async def _run_dedupe_stage(self, candidate_pairs: List[CandidatePair]) -> Dict[str, Any]:
        """Run the dedupe ML ranking stage."""
        # Convert candidate pairs to dedupe format
        linkedin_contacts = [pair.linkedin_contact for pair in candidate_pairs]
        crm_contacts = [pair.crm_contact for pair in candidate_pairs]
        
        # Use existing dedupe functionality
        data_dict = self.dedupe_finder.prepare_data_for_dedupe(crm_contacts, linkedin_contacts)
        deduper = self.dedupe_finder.train_dedupe_model(data_dict)
        clustered_dupes = self.dedupe_finder.find_duplicates(data_dict, deduper)
        matches = self.dedupe_finder.analyze_duplicates(clustered_dupes, data_dict)
        
        # Categorize matches by confidence
        high_confidence = [m for m in matches if m['confidence_score'] >= self.dedupe_threshold_high]
        medium_confidence = [m for m in matches if self.dedupe_threshold_medium <= m['confidence_score'] < self.dedupe_threshold_high]
        low_confidence = [m for m in matches if m['confidence_score'] < self.dedupe_threshold_medium]
        
        self.logger.info(f"Dedupe results: {len(high_confidence)} high, {len(medium_confidence)} medium, {len(low_confidence)} low confidence")
        
        return {
            "total_matches": len(matches),
            "high_confidence_pairs": high_confidence,
            "medium_confidence_pairs": medium_confidence,
            "low_confidence_pairs": low_confidence,
            "dedupe_threshold_high": self.dedupe_threshold_high,
            "dedupe_threshold_medium": self.dedupe_threshold_medium
        }
    
    async def _run_ai_stage(self, high_confidence_pairs: List[Dict], medium_confidence_pairs: List[Dict]) -> Dict[str, Any]:
        """Run the selective AI verification stage."""
        ai_results = {
            "pairs_processed": 0,
            "pairs_skipped": 0,
            "high_confidence_auto_accepted": len(high_confidence_pairs),
            "medium_confidence_ai_verified": 0,
            "ai_confirmations": [],
            "ai_rejections": []
        }
        
        # Auto-accept high confidence dedupe matches
        self.logger.info(f"Auto-accepting {len(high_confidence_pairs)} high-confidence dedupe matches")
        
        # AI verification for medium confidence matches (limited by max_ai_comparisons)
        pairs_to_verify = medium_confidence_pairs[:self.max_ai_comparisons]
        ai_results["pairs_skipped"] = len(medium_confidence_pairs) - len(pairs_to_verify)
        
        self.logger.info(f"AI verifying {len(pairs_to_verify)} medium-confidence pairs")
        
        for i, match in enumerate(pairs_to_verify):
            if i % 100 == 0:
                self.logger.info(f"AI verification progress: {i}/{len(pairs_to_verify)}")
            
            try:
                # Convert match format for AI detector
                linkedin_contact = match['linkedin_profile']['source_data']
                crm_contact = match['crm_contact']['source_data']
                
                ai_result = await self.ai_detector.compare_contacts(linkedin_contact, crm_contact)
                
                ai_match_data = {
                    "original_dedupe_match": match,
                    "ai_result": ai_result.dict(),
                    "combined_confidence": (match['confidence_score'] + ai_result.similarity_score) / 2
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
    
    def _combine_final_results(self, results: Dict, dedupe_results: Dict, ai_results: Dict):
        """Combine results from all stages into final recommendations."""
        final_results = results["final_results"]
        
        # High confidence: Auto-accepted dedupe + AI confirmations
        final_results["high_confidence_matches"] = (
            dedupe_results["high_confidence_pairs"] + 
            ai_results["ai_confirmations"]
        )
        
        # Medium confidence: AI rejections (need manual review)
        final_results["medium_confidence_matches"] = ai_results["ai_rejections"]
        
        # Low confidence: Dedupe low confidence matches
        final_results["low_confidence_matches"] = dedupe_results["low_confidence_pairs"]
        
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
        
        print(f"\n🎯 Multi-Stage Duplicate Detection Pipeline Results")
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
    
    def save_results(self, results: Dict[str, Any], output_file: str = None) -> Path:
        """Save pipeline results to JSON file."""
        if not output_file:
            output_file = f"data/multistage_duplicate_results_{int(time.time())}.json"
        
        output_path = Path(output_file)
        output_path.parent.mkdir(exist_ok=True)
        
        # Add timestamp
        results["analysis_timestamp"] = time.strftime("%Y-%m-%d %H:%M:%S")
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        file_size = output_path.stat().st_size / 1024 / 1024
        self.logger.info(f"Results saved to {output_path} ({file_size:.1f} MB)")
        
        return output_path


async def main():
    """Main function to run the multi-stage duplicate detection pipeline."""
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('data/multistage_duplicate_detection.log', mode='a')
        ]
    )
    
    logger = logging.getLogger(__name__)
    
    print("🚀 Multi-Stage Duplicate Detection Pipeline")
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
        detector = MultiStageDuplicateDetector()
        results = await detector.detect_duplicates(linkedin_contacts, crm_contacts)
        
        # Save results
        output_file = detector.save_results(results)
        
        print(f"\n✅ Multi-stage duplicate detection complete!")
        print(f"📁 Full results saved to: {output_file}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error in multi-stage duplicate detection: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    import asyncio
    success = asyncio.run(main())
    exit(0 if success else 1)