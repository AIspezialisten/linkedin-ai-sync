#!/usr/bin/env python3
"""
Simplified duplicate detection example using dedupe library.

This demonstrates how to find matching contacts between CRM and LinkedIn data
using a smaller subset for faster processing.
"""

import json
import logging
import re
from pathlib import Path
from typing import Dict, List, Any, Tuple
import dedupe
from unidecode import unidecode


class SimpleDuplicateFinder:
    """Simple duplicate finder for demonstration purposes."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.crm_file = Path("data/dynamics_crm_contacts_all.json")
        self.linkedin_file = Path("data/linkedin_profiles_detailed.json")
        
    def load_sample_data(self, crm_limit: int = 100) -> Tuple[List[Dict], List[Dict]]:
        """Load a sample of CRM contacts and all LinkedIn profiles."""
        self.logger.info("Loading sample CRM contacts...")
        with open(self.crm_file, 'r', encoding='utf-8') as f:
            crm_data = json.load(f)
        
        crm_contacts = crm_data.get('contacts', [])[:crm_limit]  # Limit for demo
        self.logger.info(f"Loaded {len(crm_contacts)} CRM contacts (sample)")
        
        self.logger.info("Loading LinkedIn profiles...")
        with open(self.linkedin_file, 'r', encoding='utf-8') as f:
            linkedin_data = json.load(f)
        
        linkedin_profiles = linkedin_data.get('profiles', [])
        self.logger.info(f"Loaded {len(linkedin_profiles)} LinkedIn profiles")
        
        return crm_contacts, linkedin_profiles
    
    def normalize_text(self, text: str) -> str:
        """Normalize text for better matching."""
        if not text or not text.strip():
            return None  # Return None for empty strings to avoid dedupe errors
        
        # Convert to lowercase and remove accents
        text = unidecode(text.lower())
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        # Remove common business suffixes
        text = re.sub(r'\b(gmbh|ag|ltd|inc|corp|llc|co)\b', '', text)
        
        # Return None if the result is empty after normalization
        return text if text else None
    
    def prepare_record(self, record: Dict[str, Any], source: str, record_id: int) -> Dict[str, Any]:
        """Prepare a record for dedupe processing."""
        if source == 'crm':
            full_name = self.normalize_text(record.get('fullname', ''))
            email = self.normalize_text(record.get('emailaddress1', ''))
            phone = self.normalize_text(record.get('telephone1', '') or record.get('mobilephone', ''))
            company = self.normalize_text(record.get('companyname', ''))
            job_title = self.normalize_text(record.get('jobtitle', ''))
            
        else:  # linkedin
            full_name = self.normalize_text(record.get('full_name', ''))
            contact_info = record.get('contact_info', [])
            email = self.normalize_text(contact_info[0] if contact_info else '')
            phone = ''  # LinkedIn profiles typically don't have phone numbers
            
            # Extract company from current position
            current_position = record.get('current_position', '')
            company = ''
            if current_position and ' at ' in current_position:
                company = self.normalize_text(current_position.split(' at ')[-1])
            
            job_title = self.normalize_text(record.get('headline', ''))
        
        return {
            'record_id': f"{source}_{record_id}",
            'source': source,
            'full_name': full_name,
            'email': email,
            'phone': phone,
            'company': company,
            'job_title': job_title,
            'original_data': record
        }
    
    def prepare_data_for_dedupe(self, crm_contacts: List[Dict], linkedin_profiles: List[Dict]) -> Dict[str, Dict]:
        """Prepare all data for dedupe processing."""
        self.logger.info("Preparing data for dedupe...")
        
        data_dict = {}
        
        # Process CRM contacts
        for i, contact in enumerate(crm_contacts):
            prepared = self.prepare_record(contact, 'crm', i)
            data_dict[prepared['record_id']] = prepared
        
        # Process LinkedIn profiles
        for i, profile in enumerate(linkedin_profiles):
            prepared = self.prepare_record(profile, 'linkedin', i)
            data_dict[prepared['record_id']] = prepared
        
        self.logger.info(f"Prepared {len(data_dict)} total records for deduplication")
        return data_dict
    
    def create_simple_deduper(self, data_dict: Dict[str, Dict]) -> dedupe.Dedupe:
        """Create and train a simple dedupe model."""
        # Define fields for matching
        fields = [
            dedupe.variables.String('full_name', has_missing=True),
            dedupe.variables.String('email', has_missing=True),
            dedupe.variables.String('company', has_missing=True),
            dedupe.variables.String('job_title', has_missing=True)
        ]
        
        # Create dedupe object
        deduper = dedupe.Dedupe(fields)
        
        # Prepare training data
        deduper.prepare_training(data_dict, sample_size=min(1000, len(data_dict)))
        
        # Create automatic training examples
        training_examples = self.create_training_examples(data_dict)
        
        # Mark training examples
        for example in training_examples:
            if example['is_match']:
                deduper.mark_pairs({
                    'match': [(example['record_1'], example['record_2'])],
                    'distinct': []
                })
            else:
                deduper.mark_pairs({
                    'match': [],
                    'distinct': [(example['record_1'], example['record_2'])]
                })
        
        self.logger.info(f"Created {len(training_examples)} training examples")
        
        # Train the model
        self.logger.info("Training dedupe model...")
        deduper.train()
        
        return deduper
    
    def create_training_examples(self, data_dict: Dict[str, Dict]) -> List[Dict]:
        """Create training examples based on obvious matches and non-matches."""
        examples = []
        
        crm_records = [r for r in data_dict.values() if r['source'] == 'crm']
        linkedin_records = [r for r in data_dict.values() if r['source'] == 'linkedin']
        
        # Create positive examples (exact email matches)
        crm_emails = {r['email']: r for r in crm_records if r['email'] and '@' in r['email']}
        linkedin_emails = {r['email']: r for r in linkedin_records if r['email'] and '@' in r['email']}
        
        for email in crm_emails:
            if email in linkedin_emails:
                examples.append({
                    'is_match': True,
                    'record_1': crm_emails[email],
                    'record_2': linkedin_emails[email]
                })
        
        # Create negative examples (obviously different names)
        negative_count = 0
        for crm_record in crm_records[:5]:  # Limit to avoid too many examples
            for linkedin_record in linkedin_records:
                crm_name = crm_record.get('full_name', '').lower()
                linkedin_name = linkedin_record.get('full_name', '').lower()
                
                if (crm_name and linkedin_name and 
                    len(crm_name) > 5 and len(linkedin_name) > 5 and
                    not any(word in linkedin_name for word in crm_name.split() if len(word) > 2)):
                    
                    examples.append({
                        'is_match': False,
                        'record_1': crm_record,
                        'record_2': linkedin_record
                    })
                    
                    negative_count += 1
                    if negative_count >= 10:  # Limit negative examples
                        break
            
            if negative_count >= 10:
                break
        
        return examples
    
    def find_matches(self, data_dict: Dict[str, Dict], deduper: dedupe.Dedupe) -> List[Dict]:
        """Find matches using the trained model."""
        self.logger.info("Finding matches...")
        
        # Set threshold for matching
        threshold = 0.5  # Conservative threshold
        
        # Find duplicates
        clustered_dupes = deduper.partition(data_dict, threshold)
        
        results = []
        
        for cluster in clustered_dupes:
            cluster_records = [data_dict[record_id] for record_id in cluster]
            
            # Check if this cluster contains both CRM and LinkedIn records
            sources = {record['source'] for record in cluster_records}
            
            if 'crm' in sources and 'linkedin' in sources:
                crm_records = [r for r in cluster_records if r['source'] == 'crm']
                linkedin_records = [r for r in cluster_records if r['source'] == 'linkedin']
                
                for crm_record in crm_records:
                    for linkedin_record in linkedin_records:
                        match_result = {
                            'confidence_score': 0.8,  # Simplified scoring
                            'crm_contact': {
                                'full_name': crm_record.get('full_name', ''),
                                'email': crm_record.get('email', ''),
                                'company': crm_record.get('company', ''),
                                'job_title': crm_record.get('job_title', ''),
                                'original': crm_record['original_data']
                            },
                            'linkedin_profile': {
                                'full_name': linkedin_record.get('full_name', ''),
                                'email': linkedin_record.get('email', ''),
                                'company': linkedin_record.get('company', ''),
                                'job_title': linkedin_record.get('job_title', ''),
                                'profile_url': linkedin_record['original_data'].get('profile_url', ''),
                                'original': linkedin_record['original_data']
                            },
                            'match_reasons': self.analyze_match(crm_record, linkedin_record)
                        }
                        
                        results.append(match_result)
        
        self.logger.info(f"Found {len(results)} potential matches")
        return results
    
    def analyze_match(self, crm_record: Dict, linkedin_record: Dict) -> List[str]:
        """Analyze why two records might be a match."""
        reasons = []
        
        # Check name similarity
        crm_name = crm_record.get('full_name', '').lower()
        linkedin_name = linkedin_record.get('full_name', '').lower()
        
        if crm_name and linkedin_name:
            if crm_name == linkedin_name:
                reasons.append("Exact name match")
            elif any(word in linkedin_name for word in crm_name.split() if len(word) > 2):
                reasons.append("Name similarity")
        
        # Check email similarity
        crm_email = crm_record.get('email', '')
        linkedin_email = linkedin_record.get('email', '')
        
        if crm_email and linkedin_email and crm_email == linkedin_email:
            reasons.append("Exact email match")
        
        # Check company similarity
        crm_company = crm_record.get('company', '')
        linkedin_company = linkedin_record.get('company', '')
        
        if crm_company and linkedin_company:
            if crm_company in linkedin_company or linkedin_company in crm_company:
                reasons.append("Company match")
        
        return reasons
    
    def save_results(self, results: List[Dict]):
        """Save results to JSON file."""
        output_file = Path("data/simple_duplicate_results.json")
        
        summary = {
            'total_matches': len(results),
            'high_confidence': len([r for r in results if r['confidence_score'] > 0.8]),
            'medium_confidence': len([r for r in results if 0.5 <= r['confidence_score'] <= 0.8]),
            'analysis_method': 'Simple dedupe demonstration'
        }
        
        output_data = {
            'timestamp': self.get_timestamp(),
            'summary': summary,
            'matches': results
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        
        self.logger.info(f"Results saved to {output_file}")
        return output_file
    
    def get_timestamp(self) -> str:
        """Get current timestamp."""
        from datetime import datetime
        return datetime.now().isoformat()
    
    def print_results(self, results: List[Dict]):
        """Print results to console."""
        print(f"\n🔍 Simple Duplicate Detection Results")
        print("=" * 50)
        
        if not results:
            print("❌ No matches found")
            return
        
        print(f"✅ Found {len(results)} potential matches:")
        print("-" * 40)
        
        for i, result in enumerate(results):
            crm = result['crm_contact']
            linkedin = result['linkedin_profile']
            
            print(f"\n{i+1}. Match confidence: {result['confidence_score']:.1%}")
            print(f"   CRM: {crm['full_name']} | {crm['email']} | {crm['company']}")
            print(f"   LinkedIn: {linkedin['full_name']} | {linkedin['email']} | {linkedin['company']}")
            print(f"   Profile URL: {linkedin['profile_url']}")
            print(f"   Reasons: {', '.join(result['match_reasons'])}")


def main():
    """Main function."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("🔍 Simple CRM & LinkedIn Duplicate Detection Demo")
    print("=" * 60)
    
    finder = SimpleDuplicateFinder()
    
    try:
        # Load sample data (limited CRM contacts for speed)
        crm_contacts, linkedin_profiles = finder.load_sample_data(crm_limit=50)
        
        if not crm_contacts or not linkedin_profiles:
            print("❌ No data found")
            return False
        
        # Prepare data
        data_dict = finder.prepare_data_for_dedupe(crm_contacts, linkedin_profiles)
        
        # Create and train deduper
        deduper = finder.create_simple_deduper(data_dict)
        
        # Find matches
        results = finder.find_matches(data_dict, deduper)
        
        # Save and display results
        output_file = finder.save_results(results)
        finder.print_results(results)
        
        print(f"\n✅ Demo complete! Results saved to: {output_file}")
        print("\n💡 This demonstrates the basic concept. For production use:")
        print("   - Increase the sample size (crm_limit parameter)")
        print("   - Add more sophisticated training examples")
        print("   - Fine-tune the matching threshold")
        print("   - Add more fields for matching")
        
        return True
        
    except Exception as e:
        logging.error(f"Error in duplicate detection: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)