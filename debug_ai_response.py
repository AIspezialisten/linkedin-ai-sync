#!/usr/bin/env python3
"""
Debug script to see what the AI model is actually returning.
"""

import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    load_dotenv(env_path)

from pydantic import BaseModel
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider


class TestResult(BaseModel):
    message: str
    confidence: float


async def test_raw_response():
    """Test what the AI model actually returns."""
    print("🔍 Testing raw AI response...")
    
    try:
        # Create Ollama model
        ollama_model = OpenAIModel(
            model_name='mistral-small:24b',
            provider=OpenAIProvider(base_url='http://localhost:11434/v1')
        )
        
        # Create agent
        agent = Agent(model=ollama_model, result_type=TestResult)
        
        # Test simple query
        prompt = 'Return a JSON object with "message" set to "test" and "confidence" set to 0.5'
        result = await agent.run(prompt)
        
        print(f"✅ Success!")
        print(f"   Raw result type: {type(result)}")
        print(f"   Result: {result}")
        print(f"   Output: {result.output}")
        print(f"   Message: {result.output.message}")
        print(f"   Confidence: {result.output.confidence}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def test_duplicate_format():
    """Test the exact format we need for duplicate detection."""
    print("\\n🔍 Testing duplicate detection format...")
    
    try:
        from sync.ai_duplicate_detection import ComparisonResult, MatchConfidence
        
        # Create Ollama model
        ollama_model = OpenAIModel(
            model_name='mistral-small:24b',
            provider=OpenAIProvider(base_url='http://localhost:11434/v1')
        )
        
        # Create agent with duplicate detection result type
        agent = Agent(model=ollama_model, result_type=ComparisonResult)
        
        # Test with simplified prompt
        prompt = '''
Please return a comparison result with these fields:
- is_duplicate: false
- confidence: "none"
- similarity_score: 0.0
- reasoning: "Test response"
- matching_fields: []
- conflicting_fields: ["different people"]
'''
        
        result = await agent.run(prompt)
        
        print(f"✅ Success!")
        print(f"   Is duplicate: {result.output.is_duplicate}")
        print(f"   Confidence: {result.output.confidence}")
        print(f"   Score: {result.output.similarity_score}")
        print(f"   Reasoning: {result.output.reasoning}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run debug tests."""
    print("🚀 AI Response Debug Tests")
    print("=" * 50)
    
    # Test 1: Simple response
    success1 = await test_raw_response()
    
    # Test 2: Duplicate detection format
    success2 = await test_duplicate_format()
    
    # Summary
    print(f"\\n" + "=" * 50)
    print("📊 Debug Results:")
    print(f"   Simple response: {'✅' if success1 else '❌'}")
    print(f"   Duplicate format: {'✅' if success2 else '❌'}")


if __name__ == "__main__":
    asyncio.run(main())