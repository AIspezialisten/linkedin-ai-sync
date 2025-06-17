#!/usr/bin/env python3
"""
Debug script to test PydanticAI with Ollama step by step.
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


async def test_basic_ollama():
    """Test basic Ollama connection with PydanticAI."""
    print("🔍 Testing basic Ollama connection with PydanticAI...")
    
    try:
        # Create Ollama model
        ollama_model = OpenAIModel(
            model_name='mistral-small:24b',
            provider=OpenAIProvider(base_url='http://localhost:11434/v1')
        )
        
        # Create simple agent
        agent = Agent(model=ollama_model, result_type=TestResult)
        
        # Test simple query
        result = await agent.run('Respond with a message "Hello from AI" and confidence 0.9')
        
        print(f"✅ Success!")
        print(f"   Message: {result.output.message}")
        print(f"   Confidence: {result.output.confidence}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def test_with_system_prompt():
    """Test with system prompt like our duplicate detection."""
    print("\n🔍 Testing with system prompt...")
    
    try:
        # Create Ollama model
        ollama_model = OpenAIModel(
            model_name='mistral-small:24b',
            provider=OpenAIProvider(base_url='http://localhost:11434/v1')
        )
        
        # Create agent with system prompt
        agent = Agent(
            model=ollama_model, 
            result_type=TestResult,
            system_prompt="You are a helpful assistant that responds with structured data."
        )
        
        # Test query
        result = await agent.run('Give me a test message with confidence 0.75')
        
        print(f"✅ Success!")
        print(f"   Message: {result.data.message}")
        print(f"   Confidence: {result.data.confidence}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run debug tests."""
    print("🚀 PydanticAI + Ollama Debug Tests")
    print("=" * 50)
    
    # Test 1: Basic connection
    success1 = await test_basic_ollama()
    
    # Test 2: With system prompt
    success2 = await test_with_system_prompt()
    
    # Summary
    print(f"\n" + "=" * 50)
    print("📊 Debug Results:")
    print(f"   Basic connection: {'✅' if success1 else '❌'}")
    print(f"   System prompt: {'✅' if success2 else '❌'}")
    
    if success1 and success2:
        print("\n🎉 PydanticAI + Ollama integration is working!")
        print("   The issue might be in our duplicate detection logic.")
    else:
        print("\n❌ There's an issue with the PydanticAI + Ollama setup.")


if __name__ == "__main__":
    asyncio.run(main())