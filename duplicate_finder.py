#!/usr/bin/env python3
"""
Duplicate detection between CRM contacts and LinkedIn profiles using dedupe library.

This script demonstrates how to find matching contacts between:
- Microsoft Dynamics CRM contacts (dynamics_crm_contacts_all.json)
- LinkedIn profiles (linkedin_profiles_detailed.json)

Uses the dedupe library for machine learning-based record linkage.
"""

import json
import logging
import os
import re
from pathlib import Path
from typing import Dict, List, Any, Tuple
import dedupe
from unidecode import unidecode


class DuplicateFinder:
    """Find duplicates between CRM contacts and LinkedIn profiles using dedupe."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.crm_file = Path("data/dynamics_crm_contacts_all.json")
        self.linkedin_file = Path("data/linkedin_profiles_detailed.json")
        self.training_file = Path("data/dedupe_training.json")
        self.settings_file = Path("data/dedupe_learned_settings")
        
    def load_data(self) -> Tuple[List[Dict], List[Dict]]:
        """Load CRM contacts and LinkedIn profiles."""
        self.logger.info("Loading CRM contacts...")
        with open(self.crm_file, 'r', encoding='utf-8') as f:
            crm_data = json.load(f)
        
        crm_contacts = crm_data.get('contacts', [])
        self.logger.info(f"Loaded {len(crm_contacts)} CRM contacts")
        
        self.logger.info("Loading LinkedIn profiles...")
        with open(self.linkedin_file, 'r', encoding='utf-8') as f:
            linkedin_data = json.load(f)
        
        linkedin_profiles = linkedin_data.get('profiles', [])
        self.logger.info(f"Loaded {len(linkedin_profiles)} LinkedIn profiles")
        
        return crm_contacts, linkedin_profiles
    
    def normalize_text(self, text: str) -> str:
        """Normalize text for better matching."""
        if not text or not str(text).strip():
            return None  # Return None for empty strings to avoid dedupe errors
        
        # Convert to string and lowercase, remove accents
        text = unidecode(str(text).lower())
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        # Remove common suffixes/prefixes
        text = re.sub(r'\b(dr|prof|mr|mrs|ms)\.\s*', '', text)
        text = re.sub(r'\b(gmbh|ag|ltd|inc|corp|llc)\b', '', text)
        
        # Return None if the result is empty after normalization
        result = text.strip()
        return result if result else None
    
    def prepare_crm_record(self, contact: Dict[str, Any], record_id: int) -> Dict[str, Any]:
        """Prepare a CRM contact record for dedupe processing."""
        # Extract and normalize key fields
        first_name = self.normalize_text(contact.get('firstname', ''))
        last_name = self.normalize_text(contact.get('lastname', ''))
        full_name = self.normalize_text(contact.get('fullname', ''))
        
        # If no full name, construct from first/last
        if not full_name and (first_name or last_name):
            full_name = f"{first_name} {last_name}".strip()
        
        email = self.normalize_text(contact.get('emailaddress1', ''))
        phone = self.normalize_text(contact.get('telephone1', '') or contact.get('mobilephone', ''))
        company = self.normalize_text(contact.get('companyname', ''))
        job_title = self.normalize_text(contact.get('jobtitle', ''))
        
        # Create address string
        address_parts = [
            contact.get('address1_line1', ''),
            contact.get('address1_city', ''),
            contact.get('address1_country', '')
        ]
        address = self.normalize_text(' '.join(filter(None, address_parts)))
        
        return {
            'record_id': f"crm_{record_id}",
            'source': 'crm',
            'full_name': full_name,
            'first_name': first_name,
            'last_name': last_name,
            'email': email,
            'phone': phone,
            'company': company,
            'job_title': job_title,
            'address': address,
            'original_data': contact
        }
    
    def prepare_linkedin_record(self, profile: Dict[str, Any], record_id: int) -> Dict[str, Any]:
        """Prepare a LinkedIn profile record for dedupe processing."""
        full_name = self.normalize_text(profile.get('full_name', ''))
        
        # Try to extract first/last name from full name
        name_parts = full_name.split()
        first_name = name_parts[0] if name_parts else ''
        last_name = name_parts[-1] if len(name_parts) > 1 else ''
        
        # Extract email from contact info
        contact_info = profile.get('contact_info', [])
        email = ''
        if contact_info and len(contact_info) > 0:
            email = self.normalize_text(contact_info[0])
        
        # Extract company from current position
        current_position = profile.get('current_position', '')
        company = ''
        if current_position and ' at ' in current_position:
            company = self.normalize_text(current_position.split(' at ')[-1])
        
        job_title = self.normalize_text(profile.get('headline', ''))
        location = self.normalize_text(profile.get('location', ''))
        
        return {
            'record_id': f"linkedin_{record_id}",
            'source': 'linkedin',
            'full_name': full_name,
            'first_name': first_name,
            'last_name': last_name,
            'email': email,
            'phone': '',  # LinkedIn profiles typically don't have phone numbers
            'company': company,
            'job_title': job_title,
            'address': location,
            'original_data': profile
        }
    
    def is_record_valid(self, record: Dict[str, Any]) -> bool:
        """Check if a record has enough non-empty fields for dedupe processing."""
        key_fields = ['full_name', 'first_name', 'last_name', 'email', 'company', 'job_title']
        non_empty_count = sum(1 for field in key_fields if record.get(field))
        
        # Require at least 2 non-empty key fields
        return non_empty_count >= 2
    
    def prepare_data_for_dedupe(self, crm_contacts: List[Dict], linkedin_profiles: List[Dict]) -> Dict[str, Dict]:
        """Prepare all data for dedupe processing."""
        self.logger.info("Preparing data for dedupe...")
        
        data_dict = {}
        skipped_records = 0
        
        # Process CRM contacts
        for i, contact in enumerate(crm_contacts):
            prepared = self.prepare_crm_record(contact, i)
            
            if self.is_record_valid(prepared):
                data_dict[prepared['record_id']] = prepared
            else:
                skipped_records += 1
                self.logger.debug(f"Skipped CRM record {i} - insufficient data")
        
        # Process LinkedIn profiles
        for i, profile in enumerate(linkedin_profiles):
            prepared = self.prepare_linkedin_record(profile, i)
            
            if self.is_record_valid(prepared):
                data_dict[prepared['record_id']] = prepared
            else:
                skipped_records += 1
                self.logger.debug(f"Skipped LinkedIn record {i} - insufficient data")
        
        self.logger.info(f"Prepared {len(data_dict)} valid records for deduplication")
        if skipped_records > 0:
            self.logger.info(f"Skipped {skipped_records} records with insufficient data")
        
        return data_dict
    
    def create_dedupe_fields(self) -> List:
        """Define the fields for dedupe to use in matching."""
        return [
            dedupe.variables.String('full_name', has_missing=True),
            dedupe.variables.String('first_name', has_missing=True),
            dedupe.variables.String('last_name', has_missing=True),
            dedupe.variables.String('email', has_missing=True),
            dedupe.variables.String('phone', has_missing=True),
            dedupe.variables.String('company', has_missing=True),
            dedupe.variables.String('job_title', has_missing=True),
            dedupe.variables.String('address', has_missing=True)
        ]
    
    def train_dedupe_model(self, data_dict: Dict[str, Dict]) -> dedupe.Dedupe:
        """Train the dedupe model with user input or load existing settings."""
        fields = self.create_dedupe_fields()
        
        # Create dedupe object
        deduper = dedupe.Dedupe(fields)
        
        # Check if we have existing training data
        if self.settings_file.exists():
            self.logger.info("Loading existing dedupe settings...")
            with open(self.settings_file, 'rb') as f:
                deduper.prepare_training(data_dict)
                deduper.readSettings(f)
        else:
            self.logger.info("Training new dedupe model...")
            
            # Prepare training data
            deduper.prepare_training(data_dict, sample_size=15000)
            
            # Check if we have training data
            if self.training_file.exists():
                self.logger.info("Loading existing training data...")
                with open(self.training_file, 'r') as f:
                    deduper.readTraining(f)
            else:
                self.logger.info("No existing training data found.")
                self.logger.info("Creating automated training examples...")
                
                # Create some automatic training examples based on exact matches
                training_pairs = self.create_automatic_training_pairs(data_dict)
                
                if training_pairs:
                    # Convert training pairs to dedupe format
                    formatted_training = []
                    for pair in training_pairs:
                        record_pair = (pair['record_1'], pair['record_2'])
                        if pair['match']:
                            formatted_training.append({
                                'match': record_pair,
                                'distinct': []
                            })
                        else:
                            formatted_training.append({
                                'match': [],
                                'distinct': [record_pair]
                            })
                    
                    # Write training data to file
                    with open(self.training_file, 'w') as f:
                        json.dump(training_pairs, f, indent=2)
                    
                    # Manually mark training examples
                    for pair in training_pairs:
                        if pair['match']:
                            deduper.mark_pairs({'match': [(pair['record_1'], pair['record_2'])], 'distinct': []})
                        else:
                            deduper.mark_pairs({'match': [], 'distinct': [(pair['record_1'], pair['record_2'])]})
                    
                    self.logger.info(f"Created {len(training_pairs)} automatic training examples")
                else:
                    self.logger.warning("No automatic training examples could be created")
                    # Create minimal training data to avoid errors
                    deduper.mark_pairs({'match': [], 'distinct': []})
            
            # Train the model
            self.logger.info("Training dedupe model...")
            deduper.train()
            
            # Save the trained settings
            with open(self.settings_file, 'wb') as f:
                deduper.writeSettings(f)
            
            self.logger.info("Dedupe model training complete")
        
        return deduper
    
    def create_automatic_training_pairs(self, data_dict: Dict[str, Dict]) -> List[Dict]:
        """Create automatic training pairs based on exact matches."""
        training_pairs = []
        
        # Find exact email matches between CRM and LinkedIn
        crm_emails = {}
        linkedin_emails = {}
        
        for record_id, record in data_dict.items():
            email = record.get('email', '').strip()
            if email and '@' in email:
                if record['source'] == 'crm':
                    crm_emails[email] = record_id
                else:
                    linkedin_emails[email] = record_id
        
        # Create positive examples from email matches
        for email in crm_emails:
            if email in linkedin_emails:
                crm_id = crm_emails[email]
                linkedin_id = linkedin_emails[email]
                
                training_pairs.append({
                    'match': True,
                    'record_1': data_dict[crm_id],
                    'record_2': data_dict[linkedin_id]
                })
        
        # Create negative examples from obviously different records
        crm_records = [r for r in data_dict.values() if r['source'] == 'crm']
        linkedin_records = [r for r in data_dict.values() if r['source'] == 'linkedin']
        
        negative_count = 0
        for crm_record in crm_records[:10]:  # Limited to avoid too many examples
            for linkedin_record in linkedin_records[:10]:
                # Check if they're obviously different
                crm_name = crm_record.get('full_name', '').lower()
                linkedin_name = linkedin_record.get('full_name', '').lower()
                
                if (crm_name and linkedin_name and 
                    len(crm_name) > 3 and len(linkedin_name) > 3 and
                    not any(word in linkedin_name for word in crm_name.split() if len(word) > 2)):
                    
                    training_pairs.append({
                        'match': False,
                        'record_1': crm_record,
                        'record_2': linkedin_record
                    })
                    
                    negative_count += 1
                    if negative_count >= 20:  # Limit negative examples
                        break
            
            if negative_count >= 20:
                break
        
        return training_pairs
    
    def find_duplicates(self, data_dict: Dict[str, Dict], deduper: dedupe.Dedupe) -> List[Tuple]:
        """Find duplicate pairs using the trained model."""
        self.logger.info("Finding duplicates...")
        
        # Set threshold for matching
        threshold = deduper.threshold(data_dict, recall_weight=1)
        self.logger.info(f"Using threshold: {threshold}")
        
        # Find duplicates
        clustered_dupes = deduper.match(data_dict, threshold)
        
        self.logger.info(f"Found {len(clustered_dupes)} duplicate clusters")
        return clustered_dupes
    
    def analyze_duplicates(self, clustered_dupes: List[Tuple], data_dict: Dict[str, Dict]) -> List[Dict]:
        """Analyze and format duplicate results."""
        self.logger.info("Analyzing duplicate results...")
        
        results = []
        cross_platform_matches = 0
        
        for cluster, scores in clustered_dupes:
            cluster_records = [data_dict[record_id] for record_id in cluster]
            
            # Check if this cluster contains both CRM and LinkedIn records
            sources = {record['source'] for record in cluster_records}
            
            if 'crm' in sources and 'linkedin' in sources:
                cross_platform_matches += 1
                
                # Find the CRM and LinkedIn records
                crm_records = [r for r in cluster_records if r['source'] == 'crm']
                linkedin_records = [r for r in cluster_records if r['source'] == 'linkedin']
                
                for crm_record in crm_records:
                    for linkedin_record in linkedin_records:
                        # Calculate confidence score
                        confidence = max(scores) if scores else 0.0
                        
                        match_result = {
                            'confidence_score': confidence,
                            'crm_contact': {
                                'id': crm_record['record_id'],
                                'full_name': crm_record.get('full_name', ''),
                                'email': crm_record.get('email', ''),
                                'company': crm_record.get('company', ''),
                                'job_title': crm_record.get('job_title', ''),
                                'phone': crm_record.get('phone', ''),
                                'source_data': crm_record['original_data']
                            },
                            'linkedin_profile': {
                                'id': linkedin_record['record_id'],
                                'full_name': linkedin_record.get('full_name', ''),
                                'email': linkedin_record.get('email', ''),
                                'company': linkedin_record.get('company', ''),
                                'job_title': linkedin_record.get('job_title', ''),
                                'profile_url': linkedin_record['original_data'].get('profile_url', ''),
                                'source_data': linkedin_record['original_data']
                            },
                            'match_reasons': self.analyze_match_reasons(crm_record, linkedin_record)
                        }
                        
                        results.append(match_result)
        
        self.logger.info(f"Found {cross_platform_matches} cross-platform matches")
        self.logger.info(f"Total match pairs: {len(results)}")
        
        # Sort by confidence score
        results.sort(key=lambda x: x['confidence_score'], reverse=True)
        
        return results
    
    def analyze_match_reasons(self, crm_record: Dict, linkedin_record: Dict) -> List[str]:
        """Analyze why two records were matched."""
        reasons = []
        
        # Check name similarity
        crm_name = crm_record.get('full_name', '').lower()
        linkedin_name = linkedin_record.get('full_name', '').lower()
        
        if crm_name and linkedin_name:
            if crm_name == linkedin_name:
                reasons.append("Exact name match")
            elif crm_name in linkedin_name or linkedin_name in crm_name:
                reasons.append("Partial name match")
            elif any(word in linkedin_name for word in crm_name.split() if len(word) > 2):
                reasons.append("Name words match")
        
        # Check email similarity
        crm_email = crm_record.get('email', '').lower()
        linkedin_email = linkedin_record.get('email', '').lower()
        
        if crm_email and linkedin_email:
            if crm_email == linkedin_email:
                reasons.append("Exact email match")
            elif crm_email.split('@')[0] == linkedin_email.split('@')[0]:
                reasons.append("Email username match")
        
        # Check company similarity
        crm_company = crm_record.get('company', '').lower()
        linkedin_company = linkedin_record.get('company', '').lower()
        
        if crm_company and linkedin_company:
            if crm_company == linkedin_company:
                reasons.append("Exact company match")
            elif crm_company in linkedin_company or linkedin_company in crm_company:
                reasons.append("Partial company match")
        
        # Check job title similarity
        crm_title = crm_record.get('job_title', '').lower()
        linkedin_title = linkedin_record.get('job_title', '').lower()
        
        if crm_title and linkedin_title:
            if crm_title == linkedin_title:
                reasons.append("Exact job title match")
            elif any(word in linkedin_title for word in crm_title.split() if len(word) > 3):
                reasons.append("Job title words match")
        
        return reasons
    
    def save_results(self, results: List[Dict]):
        """Save duplicate detection results to JSON file."""
        output_file = Path("data/duplicate_detection_results.json")
        
        # Create summary statistics
        summary = {
            'total_matches_found': len(results),
            'high_confidence_matches': len([r for r in results if r['confidence_score'] > 0.8]),
            'medium_confidence_matches': len([r for r in results if 0.5 <= r['confidence_score'] <= 0.8]),
            'low_confidence_matches': len([r for r in results if r['confidence_score'] < 0.5]),
            'top_match_reasons': self.get_top_match_reasons(results)
        }
        
        output_data = {
            'analysis_timestamp': self.get_timestamp(),
            'summary': summary,
            'matches': results
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        
        file_size = output_file.stat().st_size / 1024 / 1024
        self.logger.info(f"Results saved to {output_file} ({file_size:.1f} MB)")
        
        return output_file
    
    def get_top_match_reasons(self, results: List[Dict]) -> Dict[str, int]:
        """Get statistics on match reasons."""
        reason_counts = {}
        
        for result in results:
            for reason in result.get('match_reasons', []):
                reason_counts[reason] = reason_counts.get(reason, 0) + 1
        
        # Sort by count and return top 10
        sorted_reasons = sorted(reason_counts.items(), key=lambda x: x[1], reverse=True)
        return dict(sorted_reasons[:10])
    
    def get_timestamp(self) -> str:
        """Get current timestamp."""
        from datetime import datetime
        return datetime.now().isoformat()
    
    def print_sample_results(self, results: List[Dict], num_samples: int = 5):
        """Print sample results to console."""
        print(f"\n📊 Duplicate Detection Results Summary")
        print("=" * 50)
        
        if not results:
            print("❌ No duplicates found")
            return
        
        high_conf = [r for r in results if r['confidence_score'] > 0.8]
        medium_conf = [r for r in results if 0.5 <= r['confidence_score'] <= 0.8]
        low_conf = [r for r in results if r['confidence_score'] < 0.5]
        
        print(f"✅ Total matches found: {len(results)}")
        print(f"🔥 High confidence (>80%): {len(high_conf)}")
        print(f"⚡ Medium confidence (50-80%): {len(medium_conf)}")
        print(f"⚠️  Low confidence (<50%): {len(low_conf)}")
        
        print(f"\n📝 Top {num_samples} Matches:")
        print("-" * 40)
        
        for i, result in enumerate(results[:num_samples]):
            crm = result['crm_contact']
            linkedin = result['linkedin_profile']
            
            print(f"\n{i+1}. Confidence: {result['confidence_score']:.1%}")
            print(f"   CRM: {crm['full_name']} | {crm['email']} | {crm['company']}")
            print(f"   LinkedIn: {linkedin['full_name']} | {linkedin['email']} | {linkedin['company']}")
            print(f"   Profile: {linkedin['profile_url']}")
            print(f"   Reasons: {', '.join(result['match_reasons'])}")


async def main():
    """Main function to run duplicate detection."""
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('data/duplicate_detection.log', mode='a')
        ]
    )
    
    logger = logging.getLogger(__name__)
    
    print("🔍 CRM & LinkedIn Duplicate Detection")
    print("=" * 50)
    
    # Check if dedupe is installed
    try:
        import dedupe
        logger.info("✅ dedupe library found")
    except ImportError:
        print("❌ dedupe library not found. Install with: pip install dedupe")
        return False
    
    # Check if data files exist
    finder = DuplicateFinder()
    
    if not finder.crm_file.exists():
        print(f"❌ CRM data file not found: {finder.crm_file}")
        return False
    
    if not finder.linkedin_file.exists():
        print(f"❌ LinkedIn data file not found: {finder.linkedin_file}")
        return False
    
    try:
        # Load data
        crm_contacts, linkedin_profiles = finder.load_data()
        
        if not crm_contacts:
            print("❌ No CRM contacts found")
            return False
        
        if not linkedin_profiles:
            print("❌ No LinkedIn profiles found")
            return False
        
        # Prepare data for dedupe
        data_dict = finder.prepare_data_for_dedupe(crm_contacts, linkedin_profiles)
        
        # Train or load dedupe model
        deduper = finder.train_dedupe_model(data_dict)
        
        # Find duplicates
        clustered_dupes = finder.find_duplicates(data_dict, deduper)
        
        # Analyze results
        results = finder.analyze_duplicates(clustered_dupes, data_dict)
        
        # Save results
        output_file = finder.save_results(results)
        
        # Print sample results
        finder.print_sample_results(results, num_samples=10)
        
        print(f"\n✅ Duplicate detection complete!")
        print(f"📁 Full results saved to: {output_file}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error in duplicate detection: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    import asyncio
    success = asyncio.run(main())
    exit(0 if success else 1)