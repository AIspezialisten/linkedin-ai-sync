#!/usr/bin/env python3
"""
Show detailed example of AI duplicate detection with timing information.
"""

import asyncio
import os
import time
from pathlib import Path
from dotenv import load_dotenv
from typing import Dict, Any
import logging

# Load environment variables
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    load_dotenv(env_path)

from sync.ai_duplicate_detection import DuplicateDetectionService


class TimingContext:
    """Context manager for timing operations."""
    
    def __init__(self, operation_name: str):
        self.operation_name = operation_name
        self.start_time = None
        self.end_time = None
    
    def __enter__(self):
        self.start_time = time.perf_counter()
        print(f"⏱️  Starting: {self.operation_name}...")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end_time = time.perf_counter()
        duration = self.end_time - self.start_time
        
        if exc_type is None:
            print(f"✅ Completed: {self.operation_name} in {duration:.3f}s")
        else:
            print(f"❌ Failed: {self.operation_name} after {duration:.3f}s")
        
        return False  # Don't suppress exceptions
    
    @property
    def duration(self) -> float:
        """Get the duration in seconds."""
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return 0.0


async def timed_ai_analysis(detector: DuplicateDetectionService, linkedin_contact: Dict[str, Any], crm_contact: Dict[str, Any]):
    """Perform AI analysis with detailed timing."""
    
    timing_results = {}
    
    # Time the overall AI analysis
    with TimingContext("AI Duplicate Detection Analysis") as timer:
        # Time individual components if possible
        print("  🧠 Initializing AI model...")
        model_start = time.perf_counter()
        
        # The actual comparison call
        print("  📊 Running contact comparison...")
        comparison_start = time.perf_counter()
        
        result = await detector.detector.compare_contacts(linkedin_contact, crm_contact)
        
        comparison_time = time.perf_counter() - comparison_start
        total_time = timer.duration if timer.end_time else time.perf_counter() - timer.start_time
        
        timing_results = {
            "total_analysis_time": total_time,
            "comparison_time": comparison_time,
            "model_overhead": total_time - comparison_time
        }
    
    return result, timing_results


async def show_duplicate_example():
    """Show a detailed example of duplicate detection with comprehensive timing."""
    overall_start = time.perf_counter()
    
    print("🔍 AI Duplicate Detection Example with Timing")
    print("=" * 60)
    
    # Time data preparation
    with TimingContext("Data Preparation") as prep_timer:
        # Create realistic test contacts that might be duplicates
        linkedin_contact = {
            "First Name": "John",
            "Last Name": "Smith",
            "Company": "Microsoft Corporation",
            "Position": "Senior Software Engineer",
            "URL": "https://www.linkedin.com/in/john-smith-123",
            "Email Address": "",
            "Connected On": "2024-01-15"
        }
        
        crm_contact = {
            "contactid": "12345-abcd-6789",
            "firstname": "John",
            "lastname": "Smith",
            "fullname": "John Smith",
            "emailaddress1": "j.smith@microsoft.com",
            "jobtitle": "Software Engineer",
            "telephone1": "+1-555-0123",
            "address1_city": "Seattle",
            "address1_country": "USA"
        }
    
    print("\n📝 Contact Comparison:")
    print()
    print("LinkedIn Contact:")
    print(f"  Name: {linkedin_contact['First Name']} {linkedin_contact['Last Name']}")
    print(f"  Company: {linkedin_contact['Company']}")
    print(f"  Position: {linkedin_contact['Position']}")
    print(f"  Email: {linkedin_contact['Email Address'] or 'Not provided'}")
    print()
    print("CRM Contact:")
    print(f"  Name: {crm_contact['firstname']} {crm_contact['lastname']}")
    print(f"  Job Title: {crm_contact['jobtitle']}")
    print(f"  Email: {crm_contact['emailaddress1']}")
    print(f"  Phone: {crm_contact['telephone1']}")
    print(f"  Location: {crm_contact['address1_city']}, {crm_contact['address1_country']}")
    
    try:
        # Time service initialization
        with TimingContext("Service Initialization") as init_timer:
            detector = DuplicateDetectionService()
        
        print("\n🤖 AI Analysis in Progress...")
        
        # Perform timed AI analysis
        result, timing_results = await timed_ai_analysis(detector, linkedin_contact, crm_contact)
        
        # Display results
        print(f"\n📊 AI Analysis Results:")
        print(f"  🎯 Duplicate Found: {'YES' if result.is_duplicate else 'NO'}")
        print(f"  🎚️  Confidence Level: {result.confidence.value.upper()}")
        print(f"  📈 Similarity Score: {result.similarity_score:.2f} / 1.00")
        print(f"  💭 AI Reasoning: {result.reasoning}")
        
        if result.matching_fields:
            print(f"  ✅ Matching Fields: {', '.join(result.matching_fields)}")
        
        if result.conflicting_fields:
            print(f"  ❌ Conflicting Fields: {', '.join(result.conflicting_fields)}")
        
        # Display detailed timing information
        overall_time = time.perf_counter() - overall_start
        
        print(f"\n⏱️  Performance Analysis:")
        print(f"  📊 Total Execution Time: {overall_time:.3f}s")
        print(f"  🔧 Data Preparation: {prep_timer.duration:.3f}s ({prep_timer.duration/overall_time*100:.1f}%)")
        print(f"  🚀 Service Initialization: {init_timer.duration:.3f}s ({init_timer.duration/overall_time*100:.1f}%)")
        print(f"  🧠 AI Analysis: {timing_results['total_analysis_time']:.3f}s ({timing_results['total_analysis_time']/overall_time*100:.1f}%)")
        print(f"  📈 Core Comparison: {timing_results['comparison_time']:.3f}s ({timing_results['comparison_time']/overall_time*100:.1f}%)")
        print(f"  ⚙️  Model Overhead: {timing_results['model_overhead']:.3f}s ({timing_results['model_overhead']/overall_time*100:.1f}%)")
        
        # Performance insights
        print(f"\n🔍 Performance Insights:")
        if timing_results['total_analysis_time'] < 1.0:
            print("  ✅ Excellent: AI analysis completed in under 1 second")
        elif timing_results['total_analysis_time'] < 3.0:
            print("  👍 Good: AI analysis completed in reasonable time")
        elif timing_results['total_analysis_time'] < 10.0:
            print("  ⚠️  Acceptable: AI analysis took several seconds")
        else:
            print("  🐌 Slow: AI analysis took longer than expected")
        
        if timing_results['model_overhead'] > timing_results['comparison_time']:
            print("  📝 Note: Model initialization/overhead is significant")
        else:
            print("  📝 Note: Core comparison is the main time consumer")
        
        # Throughput estimation
        throughput = 1 / timing_results['total_analysis_time']
        print(f"  📈 Estimated Throughput: {throughput:.1f} comparisons/second")
        print(f"  📊 Batch Processing: ~{throughput * 60:.0f} comparisons/minute")
        
        print(f"\n🎯 Conclusion:")
        if result.confidence.value == "high":
            print("  → These contacts are very likely the same person")
        elif result.confidence.value == "medium":
            print("  → These contacts are probably the same person")
        elif result.confidence.value == "low":
            print("  → These contacts might be the same person")
        else:
            print("  → These contacts are different people")
        
        return result, timing_results
        
    except Exception as e:
        error_time = time.perf_counter() - overall_start
        print(f"❌ Error in AI analysis after {error_time:.3f}s: {str(e)}")
        return None, None


async def benchmark_multiple_comparisons():
    """Benchmark multiple comparisons to test performance consistency."""
    print("\n🏃 Performance Benchmark - Multiple Comparisons")
    print("=" * 55)
    
    # Create multiple test cases
    test_cases = [
        {
            "name": "Exact Match",
            "linkedin": {
                "First Name": "Alice",
                "Last Name": "Johnson",
                "Company": "Google",
                "Position": "Software Engineer",
                "Email Address": "alice.johnson@google.com"
            },
            "crm": {
                "firstname": "Alice",
                "lastname": "Johnson",
                "emailaddress1": "alice.johnson@google.com",
                "jobtitle": "Software Engineer"
            }
        },
        {
            "name": "Similar Names",
            "linkedin": {
                "First Name": "Bob",
                "Last Name": "Smith",
                "Company": "Apple Inc",
                "Position": "Product Manager",
                "Email Address": ""
            },
            "crm": {
                "firstname": "Robert",
                "lastname": "Smith",
                "emailaddress1": "bob.smith@apple.com",
                "jobtitle": "Senior Product Manager"
            }
        },
        {
            "name": "Different People",
            "linkedin": {
                "First Name": "Charlie",
                "Last Name": "Brown",
                "Company": "Microsoft",
                "Position": "Designer",
                "Email Address": ""
            },
            "crm": {
                "firstname": "David",
                "lastname": "Wilson",
                "emailaddress1": "david.wilson@oracle.com",
                "jobtitle": "Developer"
            }
        }
    ]
    
    detector = DuplicateDetectionService()
    all_timings = []
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n📊 Test Case {i}: {test_case['name']}")
        
        start_time = time.perf_counter()
        result = await detector.detector.compare_contacts(
            test_case['linkedin'], 
            test_case['crm']
        )
        duration = time.perf_counter() - start_time
        
        all_timings.append(duration)
        
        print(f"  ⏱️  Time: {duration:.3f}s")
        print(f"  🎯 Result: {'Duplicate' if result.is_duplicate else 'Not Duplicate'}")
        print(f"  📈 Score: {result.similarity_score:.2f}")
        print(f"  🎚️  Confidence: {result.confidence.value}")
    
    # Performance statistics
    avg_time = sum(all_timings) / len(all_timings)
    min_time = min(all_timings)
    max_time = max(all_timings)
    
    print(f"\n📈 Performance Statistics:")
    print(f"  📊 Average Time: {avg_time:.3f}s")
    print(f"  ⚡ Fastest: {min_time:.3f}s")
    print(f"  🐌 Slowest: {max_time:.3f}s")
    print(f"  📏 Variance: {max_time - min_time:.3f}s")
    print(f"  🔄 Total for {len(test_cases)} comparisons: {sum(all_timings):.3f}s")
    
    return all_timings


async def main():
    """Main function with comprehensive timing analysis."""
    main_start = time.perf_counter()
    
    print("🔍 AI Duplicate Detection with Comprehensive Timing")
    print("=" * 65)
    
    # Run the main example
    result, timing_results = await show_duplicate_example()
    
    if result and timing_results:
        print(f"\n✅ Successfully demonstrated AI duplicate detection!")
        
        # Run benchmark if the main example worked
        print(f"\n" + "="*65)
        benchmark_timings = await benchmark_multiple_comparisons()
        
        if benchmark_timings:
            main_example_time = timing_results['total_analysis_time']
            benchmark_avg = sum(benchmark_timings) / len(benchmark_timings)
            
            print(f"\n🔬 Comparative Analysis:")
            print(f"  📊 Main Example: {main_example_time:.3f}s")
            print(f"  📊 Benchmark Average: {benchmark_avg:.3f}s")
            
            if abs(main_example_time - benchmark_avg) < 0.1:
                print("  ✅ Consistent performance across tests")
            else:
                print("  ⚠️  Performance varies between tests")
    else:
        print(f"\n❌ Failed to run AI duplicate detection.")
    
    total_time = time.perf_counter() - main_start
    print(f"\n⏱️  Total Script Execution: {total_time:.3f}s")


if __name__ == "__main__":
    asyncio.run(main())