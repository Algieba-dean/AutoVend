"""
Mock LLM implementation for development and testing
"""

import time
import random
from typing import List, Dict
from .base_llm import BaseLLM

class MockLLM(BaseLLM):
    """Mock LLM for development and testing"""
    
    def __init__(self, model: str = "mock-model", api_key: str = "mock-key", **kwargs):
        super().__init__(model, api_key, **kwargs)
        self.response_templates = {
            "greeting": [
                "Hello! I'm an AI assistant ready to help you find your perfect vehicle.",
                "Hi there! I'm here to assist you with your car search.",
                "Welcome! I'm your automotive advisor, ready to help you find the right vehicle."
            ],
            "vehicle_search": [
                "Based on your requirements, I'd recommend considering several options that match your needs.",
                "I found some great vehicles that might be perfect for you. Let me share the details.",
                "Here are some excellent vehicle options that align with what you're looking for."
            ],
            "general": [
                "I'm here to help you with your automotive needs. What specific information would you like?",
                "As your AI assistant, I can provide vehicle recommendations and answer your questions.",
                "I'm designed to help you find the perfect vehicle. How can I assist you today?"
            ]
        }
    
    def complete(self, prompt: str, **kwargs) -> str:
        """Complete a text prompt"""
        # Simulate processing time
        time.sleep(random.uniform(0.5, 2.0))
        
        # Generate contextual response
        prompt_lower = prompt.lower()
        
        if any(word in prompt_lower for word in ["hello", "hi", "hey"]):
            return random.choice(self.response_templates["greeting"])
        elif any(word in prompt_lower for word in ["car", "vehicle", "suv", "truck"]):
            return random.choice(self.response_templates["vehicle_search"])
        else:
            return random.choice(self.response_templates["general"])
    
    def chat(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """Chat with a list of messages"""
        # Get the last user message
        if messages:
            last_message = messages[-1].get("content", "")
            return self.complete(last_message, **kwargs)
        else:
            return "Hello! I'm ready to help you find your perfect vehicle."
    
    def is_available(self) -> bool:
        """Mock LLM is always available"""
        return True
    
    def get_config(self) -> Dict:
        """Get mock LLM configuration"""
        return {
            "model": self.model,
            "type": "mock",
            "status": "always_available"
        }
