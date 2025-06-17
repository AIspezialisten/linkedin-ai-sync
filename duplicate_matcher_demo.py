#!/usr/bin/env python3
"""
Simple duplicate matching demo without machine learning.

This demonstrates how to find potential duplicates between CRM contacts 
and LinkedIn profiles using rule-based matching criteria.
"""

import json
import logging
import re
from pathlib import Path
from typing import Dict, List, Any, Tuple
from unidecode import unidecode
from difflib import SequenceMatcher


class SimpleDuplicateMatcher:
    """Simple duplicate matcher using rule-based approaches."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.crm_file = Path("data/dynamics_crm_contacts_all.json")
        self.linkedin_file = Path("data/linkedin_profiles_detailed.json")
        
    def load_data(self, crm_limit: int = 100) -> Tuple[List[Dict], List[Dict]]:
        """Load CRM contacts and LinkedIn profiles."""
        self.logger.info("Loading CRM contacts...")
        with open(self.crm_file, 'r', encoding='utf-8') as f:
            crm_data = json.load(f)
        
        crm_contacts = crm_data.get('contacts', [])[:crm_limit]
        self.logger.info(f"Loaded {len(crm_contacts)} CRM contacts (limited for demo)")
        
        self.logger.info("Loading LinkedIn profiles...")
        with open(self.linkedin_file, 'r', encoding='utf-8') as f:
            linkedin_data = json.load(f)
        
        linkedin_profiles = linkedin_data.get('profiles', [])
        self.logger.info(f"Loaded {len(linkedin_profiles)} LinkedIn profiles")
        
        return crm_contacts, linkedin_profiles
    
    def normalize_text(self, text: str) -> str:
        """Normalize text for comparison."""
        if not text:
            return ""
        
        # Convert to lowercase and remove accents
        text = unidecode(text.lower())
        
        # Remove extra whitespace and punctuation
        text = re.sub(r'[^\w\s]', ' ', text)
        text = re.sub(r'\s+', ' ', text).strip()
        
        # Remove common business suffixes
        text = re.sub(r'\b(gmbh|ag|ltd|inc|corp|llc|co|company)\b', '', text)
        
        return text.strip()
    
    def extract_name_parts(self, full_name: str) -> Dict[str, str]:
        """Extract first, last, and middle names."""
        parts = self.normalize_text(full_name).split()
        
        if not parts:
            return {'first': '', 'last': '', 'middle': ''}
        elif len(parts) == 1:
            return {'first': parts[0], 'last': '', 'middle': ''}
        elif len(parts) == 2:
            return {'first': parts[0], 'last': parts[1], 'middle': ''}
        else:
            return {'first': parts[0], 'last': parts[-1], 'middle': ' '.join(parts[1:-1])}
    
    def calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity between two text strings."""
        if not text1 or not text2:
            return 0.0
        
        return SequenceMatcher(None, text1, text2).ratio()
    
    def prepare_crm_record(self, contact: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare CRM contact for matching."""
        full_name = self.normalize_text(contact.get('fullname', ''))
        name_parts = self.extract_name_parts(full_name)
        
        email = self.normalize_text(contact.get('emailaddress1', ''))
        phone = self.normalize_text(contact.get('telephone1', '') or contact.get('mobilephone', ''))
        company = self.normalize_text(contact.get('companyname', ''))
        job_title = self.normalize_text(contact.get('jobtitle', ''))
        
        # Create address
        address_parts = [
            contact.get('address1_line1', ''),
            contact.get('address1_city', ''),
            contact.get('address1_country', '')
        ]
        address = self.normalize_text(' '.join(filter(None, address_parts)))
        
        return {
            'source': 'crm',
            'full_name': full_name,
            'first_name': name_parts['first'],
            'last_name': name_parts['last'],
            'email': email,
            'phone': phone,
            'company': company,
            'job_title': job_title,
            'address': address,
            'original': contact
        }
    
    def prepare_linkedin_record(self, profile: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare LinkedIn profile for matching."""
        full_name = self.normalize_text(profile.get('full_name', ''))
        name_parts = self.extract_name_parts(full_name)
        
        # Extract email from contact info
        contact_info = profile.get('contact_info', [])
        email = ''
        if contact_info:
            email = self.normalize_text(contact_info[0])
        
        # Extract company from current position
        current_position = profile.get('current_position', '')
        company = ''
        if current_position and ' at ' in current_position:
            company = self.normalize_text(current_position.split(' at ')[-1])
        
        job_title = self.normalize_text(profile.get('headline', ''))
        location = self.normalize_text(profile.get('location', ''))
        
        return {
            'source': 'linkedin',
            'full_name': full_name,
            'first_name': name_parts['first'],
            'last_name': name_parts['last'],
            'email': email,
            'phone': '',  # LinkedIn doesn't typically have phone
            'company': company,
            'job_title': job_title,
            'address': location,
            'original': profile
        }
    
    def match_records(self, crm_record: Dict, linkedin_record: Dict) -> Dict[str, Any]:
        """Match a CRM record against a LinkedIn record."""
        match_score = 0.0
        match_reasons = []
        detailed_scores = {}
        
        # Name matching (40% of total score)
        name_score = 0.0
        
        # Full name comparison
        full_name_sim = self.calculate_similarity(crm_record['full_name'], linkedin_record['full_name'])
        detailed_scores['full_name_similarity'] = full_name_sim
        
        if full_name_sim > 0.9:
            name_score += 0.4
            match_reasons.append("Very similar full names")
        elif full_name_sim > 0.7:
            name_score += 0.3
            match_reasons.append("Similar full names")
        elif full_name_sim > 0.5:
            name_score += 0.2
            match_reasons.append("Somewhat similar full names")
        
        # First/Last name comparison
        first_name_sim = self.calculate_similarity(crm_record['first_name'], linkedin_record['first_name'])
        last_name_sim = self.calculate_similarity(crm_record['last_name'], linkedin_record['last_name'])
        
        detailed_scores['first_name_similarity'] = first_name_sim
        detailed_scores['last_name_similarity'] = last_name_sim
        
        if first_name_sim > 0.8 and last_name_sim > 0.8:
            name_score = max(name_score, 0.35)
            if "similar full names" not in ' '.join(match_reasons):
                match_reasons.append("Matching first and last names")
        
        match_score += name_score
        
        # Email matching (30% of total score)
        email_score = 0.0
        if crm_record['email'] and linkedin_record['email']:
            if crm_record['email'] == linkedin_record['email']:
                email_score = 0.3
                match_reasons.append("Exact email match")
            else:
                # Check if email usernames match
                crm_username = crm_record['email'].split('@')[0] if '@' in crm_record['email'] else ''
                linkedin_username = linkedin_record['email'].split('@')[0] if '@' in linkedin_record['email'] else ''
                
                if crm_username and linkedin_username and crm_username == linkedin_username:
                    email_score = 0.2
                    match_reasons.append("Email username match")
                elif crm_username and linkedin_username:
                    username_sim = self.calculate_similarity(crm_username, linkedin_username)
                    if username_sim > 0.7:
                        email_score = 0.1
                        match_reasons.append("Similar email usernames")
        
        detailed_scores['email_match'] = email_score > 0
        match_score += email_score
        
        # Company matching (20% of total score)
        company_score = 0.0
        if crm_record['company'] and linkedin_record['company']:
            company_sim = self.calculate_similarity(crm_record['company'], linkedin_record['company'])
            detailed_scores['company_similarity'] = company_sim
            
            if company_sim > 0.9:
                company_score = 0.2
                match_reasons.append("Very similar company")
            elif company_sim > 0.7:
                company_score = 0.15
                match_reasons.append("Similar company")
            elif company_sim > 0.5:
                company_score = 0.1
                match_reasons.append("Somewhat similar company")
        
        match_score += company_score
        
        # Job title matching (10% of total score)
        job_title_score = 0.0
        if crm_record['job_title'] and linkedin_record['job_title']:
            title_sim = self.calculate_similarity(crm_record['job_title'], linkedin_record['job_title'])
            detailed_scores['job_title_similarity'] = title_sim
            
            if title_sim > 0.8:
                job_title_score = 0.1
                match_reasons.append("Similar job title")
            elif title_sim > 0.6:
                job_title_score = 0.05
                match_reasons.append("Somewhat similar job title")
        
        match_score += job_title_score
        
        return {
            'overall_score': match_score,
            'detailed_scores': detailed_scores,
            'match_reasons': match_reasons,
            'crm_record': crm_record,
            'linkedin_record': linkedin_record
        }
    
    def find_all_matches(self, crm_contacts: List[Dict], linkedin_profiles: List[Dict], 
                        min_score: float = 0.3) -> List[Dict]:
        """Find all potential matches between CRM contacts and LinkedIn profiles."""
        self.logger.info(f"Finding matches with minimum score: {min_score}")
        
        matches = []
        
        # Prepare records
        prepared_crm = [self.prepare_crm_record(contact) for contact in crm_contacts]
        prepared_linkedin = [self.prepare_linkedin_record(profile) for profile in linkedin_profiles]
        
        # Compare each CRM contact with each LinkedIn profile
        for i, crm_record in enumerate(prepared_crm):
            self.logger.info(f"Processing CRM contact {i+1}/{len(prepared_crm)}: {crm_record['full_name']}")
            
            for linkedin_record in prepared_linkedin:
                match_result = self.match_records(crm_record, linkedin_record)
                
                if match_result['overall_score'] >= min_score:
                    matches.append(match_result)
        
        # Sort by score (highest first)
        matches.sort(key=lambda x: x['overall_score'], reverse=True)
        
        self.logger.info(f"Found {len(matches)} potential matches")
        return matches
    
    def save_results(self, matches: List[Dict]) -> Path:
        """Save match results to JSON file."""
        output_file = Path("data/duplicate_matches_demo.json")
        
        # Create summary
        summary = {
            'total_matches': len(matches),
            'high_confidence_matches': len([m for m in matches if m['overall_score'] >= 0.7]),
            'medium_confidence_matches': len([m for m in matches if 0.5 <= m['overall_score'] < 0.7]),
            'low_confidence_matches': len([m for m in matches if 0.3 <= m['overall_score'] < 0.5]),
            'matching_method': 'Rule-based similarity matching'
        }
        
        # Format matches for output
        formatted_matches = []
        for match in matches:
            crm = match['crm_record']
            linkedin = match['linkedin_record']
            
            formatted_match = {
                'confidence_score': match['overall_score'],
                'match_reasons': match['match_reasons'],
                'detailed_scores': match['detailed_scores'],
                'crm_contact': {
                    'full_name': crm['full_name'],
                    'email': crm['email'],
                    'phone': crm['phone'],
                    'company': crm['company'],
                    'job_title': crm['job_title'],
                    'address': crm['address'],
                    'original_data': crm['original']
                },
                'linkedin_profile': {
                    'full_name': linkedin['full_name'],
                    'email': linkedin['email'],
                    'company': linkedin['company'],
                    'job_title': linkedin['job_title'],
                    'location': linkedin['address'],
                    'profile_url': linkedin['original'].get('profile_url', ''),
                    'original_data': linkedin['original']
                }
            }
            
            formatted_matches.append(formatted_match)
        
        output_data = {
            'analysis_timestamp': self.get_timestamp(),
            'summary': summary,
            'matches': formatted_matches
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        
        file_size = output_file.stat().st_size / 1024
        self.logger.info(f"Results saved to {output_file} ({file_size:.1f} KB)")
        
        return output_file
    
    def get_timestamp(self) -> str:
        """Get current timestamp."""
        from datetime import datetime
        return datetime.now().isoformat()
    
    def print_results(self, matches: List[Dict], num_display: int = 10):
        """Print match results to console."""
        print(f"\n🔍 Duplicate Matching Results")
        print("=" * 60)
        
        if not matches:
            print("❌ No matches found above the minimum threshold")
            return
        
        high_conf = [m for m in matches if m['overall_score'] >= 0.7]
        medium_conf = [m for m in matches if 0.5 <= m['overall_score'] < 0.7]
        low_conf = [m for m in matches if 0.3 <= m['overall_score'] < 0.5]
        
        print(f"✅ Total potential matches: {len(matches)}")
        print(f"🔥 High confidence (≥70%): {len(high_conf)}")
        print(f"⚡ Medium confidence (50-69%): {len(medium_conf)}")
        print(f"⚠️  Low confidence (30-49%): {len(low_conf)}")
        
        print(f"\n📝 Top {min(num_display, len(matches))} Matches:")
        print("-" * 60)
        
        for i, match in enumerate(matches[:num_display]):
            crm = match['crm_record']
            linkedin = match['linkedin_record']
            
            print(f"\n{i+1}. Confidence Score: {match['overall_score']:.1%}")
            print(f"   CRM Contact:")
            print(f"     Name: {crm['full_name']}")
            print(f"     Email: {crm['email']}")
            print(f"     Company: {crm['company']}")
            print(f"     Job Title: {crm['job_title']}")
            
            print(f"   LinkedIn Profile:")
            print(f"     Name: {linkedin['full_name']}")
            print(f"     Email: {linkedin['email']}")
            print(f"     Company: {linkedin['company']}")
            print(f"     Job Title: {linkedin['job_title']}")
            print(f"     URL: {linkedin['original'].get('profile_url', 'N/A')}")
            
            print(f"   Match Reasons: {', '.join(match['match_reasons'])}")
            
            # Show detailed scores
            scores = match['detailed_scores']
            print(f"   Detailed Scores:")
            if 'full_name_similarity' in scores:
                print(f"     Name similarity: {scores['full_name_similarity']:.2f}")
            if 'company_similarity' in scores:
                print(f"     Company similarity: {scores['company_similarity']:.2f}")
            if 'job_title_similarity' in scores:
                print(f"     Job title similarity: {scores['job_title_similarity']:.2f}")
            if 'email_match' in scores:
                print(f"     Email match: {scores['email_match']}")


def main():
    """Main function."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("🔍 CRM & LinkedIn Duplicate Matching Demo")
    print("=" * 50)
    print("This demo uses rule-based matching to find potential duplicates")
    print("between CRM contacts and LinkedIn profiles.")
    
    matcher = SimpleDuplicateMatcher()
    
    try:
        # Load data (limit CRM contacts for demo speed)
        crm_contacts, linkedin_profiles = matcher.load_data(crm_limit=50)
        
        if not crm_contacts:
            print("❌ No CRM contacts found")
            return False
        
        if not linkedin_profiles:
            print("❌ No LinkedIn profiles found")
            return False
        
        # Find matches with lower threshold to show algorithm working
        matches = matcher.find_all_matches(crm_contacts, linkedin_profiles, min_score=0.1)
        
        # Save results
        output_file = matcher.save_results(matches)
        
        # Display results
        matcher.print_results(matches, num_display=5)
        
        print(f"\n✅ Duplicate matching complete!")
        print(f"📁 Full results saved to: {output_file}")
        print(f"\n💡 Matching Algorithm Explanation:")
        print(f"   • Name matching: 40% of total score")
        print(f"   • Email matching: 30% of total score")
        print(f"   • Company matching: 20% of total score")
        print(f"   • Job title matching: 10% of total score")
        print(f"   • Minimum threshold: 30% for potential match")
        print(f"\n🔧 To improve matching:")
        print(f"   • Increase CRM sample size (crm_limit parameter)")
        print(f"   • Adjust minimum score threshold")
        print(f"   • Add more LinkedIn profiles")
        print(f"   • Fine-tune scoring weights")
        
        return True
        
    except Exception as e:
        logging.error(f"Error in duplicate matching: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)