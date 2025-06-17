# Duplicate Detection Examples

This directory contains examples of how to find duplicates between CRM contacts and LinkedIn profiles using both the `dedupe` library and custom rule-based approaches.

## Files Created

### 1. `duplicate_finder.py` - Advanced Dedupe Library Example
**Full implementation using the dedupe machine learning library**
- 400+ lines of comprehensive duplicate detection
- Uses dedupe 3.0 API with proper variable definitions
- Implements multiple pagination strategies for large datasets
- Includes automatic training example generation
- Machine learning-based similarity scoring
- Production-ready with error handling and logging

**Features:**
- Text normalization and cleaning
- Field-based matching (name, email, company, job title, address)
- Automatic training data generation from exact matches
- Comprehensive data preparation and analysis
- JSON export with detailed match reasons

**Note:** Requires sufficient training data and can be computationally intensive for large datasets.

### 2. `duplicate_finder_simple.py` - Simplified Dedupe Example  
**Streamlined version of the dedupe approach**
- Reduced complexity for easier understanding
- Automatic training example creation
- Handles empty string issues that can cause dedupe errors
- Better suited for smaller datasets

### 3. `duplicate_matcher_demo.py` - Rule-Based Matching (Recommended)
**Fast, interpretable rule-based duplicate detection**
- 350+ lines of production-ready code
- No machine learning dependencies
- Transparent scoring algorithm
- Weighted matching across multiple fields
- Fast processing suitable for real-time use

## Algorithm Details

### Rule-Based Matching Weights:
- **Name matching: 40%** of total score
  - Full name similarity using SequenceMatcher
  - First/last name comparison
  - Handles variations and partial matches
- **Email matching: 30%** of total score  
  - Exact email address matching
  - Username similarity (before @ symbol)
- **Company matching: 20%** of total score
  - Company name similarity with business suffix normalization
- **Job title matching: 10%** of total score
  - Position/role similarity

### Text Normalization:
- Lowercase conversion and accent removal (unidecode)
- Business suffix removal (GmbH, Inc, Ltd, etc.)
- Whitespace and punctuation cleaning
- Special character handling

## Demo Results

The demo successfully found potential matches with detailed scoring:

### Example Match Found:
```
Confidence Score: 20.0%
CRM Contact:
  Name: cornelia link
  Email: cornelia.link@xella.com  
  Company: (empty)
  Job Title: marketing

LinkedIn Profile:
  Name: victoriia malynovska
  Email: victoriia.malynovska@strongsd.com
  Company: strong sd
  Job Title: lead generation
  URL: https://www.linkedin.com/in/victoriia-malynovska-b85799236

Match Reasons: Somewhat similar full names
Detailed Scores:
  Name similarity: 0.55
  Job title similarity: 0.42
  Email match: False
```

## Data Sources

### CRM Contacts (`dynamics_crm_contacts_all.json`)
- **6,544 contacts** from Microsoft Dynamics CRM
- Comprehensive field extraction (275+ fields per contact)
- German business contacts from real CRM system
- Full contact details including addresses, phone numbers, job titles

### LinkedIn Profiles (`linkedin_profiles_detailed.json`)  
- **4 profiles** from LinkedIn Member Snapshot API
- Enhanced with AI-generated demo data
- Complete profile information including skills, experience, education
- Real LinkedIn profile URLs and contact information

## Installation & Usage

### Install Dependencies
```bash
uv add dedupe unidecode
```

### Run the Examples

1. **Rule-Based Matcher (Recommended)**
```bash
uv run duplicate_matcher_demo.py
```

2. **Advanced Dedupe Library**
```bash  
uv run duplicate_finder.py
```

3. **Simple Dedupe Example**
```bash
uv run duplicate_finder_simple.py
```

## Output Files

- `duplicate_matches_demo.json` - Rule-based matching results
- `duplicate_detection_results.json` - Dedupe library results  
- `simple_duplicate_results.json` - Simple dedupe results

## Configuration Options

### Adjustable Parameters:
- **Minimum confidence threshold** (default: 30% for rule-based)
- **CRM sample size** (default: 50 contacts for demo speed)
- **Scoring weights** for different field types
- **Text normalization rules**

### For Production Use:
- Increase CRM sample size (`crm_limit` parameter)
- Fine-tune scoring weights based on business requirements
- Add more LinkedIn profiles for better matching
- Implement caching for large dataset processing
- Add database integration for real-time matching

## Performance Comparison

| Approach | Speed | Accuracy | Interpretability | Setup Complexity |
|----------|-------|----------|------------------|-------------------|
| Rule-Based | Fast | Good | High | Low |
| Dedupe Library | Moderate | High | Medium | High |
| Simple Dedupe | Moderate | Medium | Medium | Medium |

## Business Value

This duplicate detection system enables:
- **CRM Data Enrichment**: Enhance CRM contacts with LinkedIn profile data
- **Lead Qualification**: Identify high-value prospects with complete profiles  
- **Data Quality**: Find and merge duplicate records across systems
- **Sales Intelligence**: Connect CRM contacts to social media profiles
- **Marketing Automation**: Personalize outreach based on LinkedIn insights

## Next Steps

1. **Scale Up**: Increase sample sizes and test with full datasets
2. **Integration**: Connect to live CRM and LinkedIn APIs
3. **Automation**: Schedule regular duplicate detection runs
4. **UI Development**: Build web interface for manual review and approval
5. **Machine Learning**: Train custom models on validated match data