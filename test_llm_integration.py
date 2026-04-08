#!/usr/bin/env python3
"""
Test LLM integration with AutoVend
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_llm_integration():
    """Test LLM integration"""
    from src.llm import LLMFactory
    
    print("Testing LLM Integration")
    print("=" * 50)
    
    # Test 1: Mock LLM (always works)
    print("1. Testing Mock LLM...")
    try:
        mock_llm = LLMFactory.create_llm(use_mock=True)
        response = mock_llm.complete("Hello, introduce yourself")
        print(f"Mock LLM Response: {response}")
        print("Mock LLM: OK")
    except Exception as e:
        print(f"Mock LLM Error: {e}")
    
    # Test 2: Real LLM (if API key is provided)
    api_key = os.getenv("LLM_API_KEY")
    if api_key and api_key != "your_llm_api_key_here":
        print("\n2. Testing Real LLM...")
        try:
            real_llm = LLMFactory.create_llm()
            if real_llm.is_available():
                response = real_llm.complete("Hello, introduce yourself in one sentence")
                print(f"Real LLM Response: {response}")
                print("Real LLM: OK")
            else:
                print("Real LLM: Not available")
        except Exception as e:
            print(f"Real LLM Error: {e}")
    else:
        print("\n2. Real LLM test skipped (no API key)")
    
    # Test 3: Factory methods
    print("\n3. Testing Factory Methods...")
    try:
        providers = LLMFactory.get_available_providers()
        print(f"Available providers: {providers}")
        
        # Test different providers
        for provider in ["mock", "groq", "openai"]:
            try:
                llm = LLMFactory.create_llm(provider=provider, use_mock=True)
                print(f"Provider {provider}: OK")
            except Exception as e:
                print(f"Provider {provider}: Error - {e}")
                
    except Exception as e:
        print(f"Factory Error: {e}")
    
    print("\nLLM Integration Test Completed!")

if __name__ == "__main__":
    test_llm_integration()
