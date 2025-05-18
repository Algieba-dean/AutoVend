import os
import openai
import json
from typing import List, Dict, Any, Optional
from model_client_manager import ModelClientManager

class Config:
    """Configuration class for AutoVend system settings"""
    
    # Default settings
    DEFAULT_MODEL = "deepseek-chat"
    DEFAULT_API_KEY = "sk-40f9ea6f41bd4cbbae8a9d4adb07fbf8"
    DEFAULT_API_URL = "https://api.deepseek.com/v1"
    DEFAULT_MAX_WORKERS = 5
    DEFAULT_USE_STREAMING = False
    DEFAULT_USE_BATCH = True
    DEFAULT_USE_CACHE = True
    DEFAULT_CACHE_SIZE = 100
    
    # Global instance (singleton)
    _instance = None
    
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = Config()
        return cls._instance
    
    def __init__(self):
        """Initialize configuration with environment variables or defaults"""
        self.model = os.getenv("OPENAI_MODEL", self.DEFAULT_MODEL)
        self.api_key = os.getenv("OPENAI_API_KEY", self.DEFAULT_API_KEY)
        self.api_url = os.getenv("OPENAI_URL", self.DEFAULT_API_URL)
        self.max_workers = int(os.getenv("MAX_WORKERS", self.DEFAULT_MAX_WORKERS))
        self.use_streaming = self.DEFAULT_USE_STREAMING
        self.use_batch = self.DEFAULT_USE_BATCH
        self.use_cache = self.DEFAULT_USE_CACHE
        self.cache_size = int(os.getenv("CACHE_SIZE", self.DEFAULT_CACHE_SIZE))


# Cache management
_response_cache = {}

def get_from_cache(cache_key: str) -> Optional[str]:
    """Get a response from cache if available"""
    if cache_key in _response_cache:
        return _response_cache[cache_key]
    return None

def add_to_cache(cache_key: str, value: str) -> None:
    """Add a response to cache with LRU eviction"""
    config = Config.get_instance()
    if not config.use_cache:
        return
        
    _response_cache[cache_key] = value
    
    # Limit cache size with LRU eviction policy
    if len(_response_cache) > config.cache_size:
        # Remove oldest entries (first 20% of cache)
        items_to_remove = int(config.cache_size * 0.2)
        keys_to_remove = list(_response_cache.keys())[:items_to_remove]
        for key in keys_to_remove:
            _response_cache.pop(key, None)

def clear_cache() -> None:
    """Clear the entire response cache"""
    _response_cache.clear()


def get_openai_client():
    """
    Get an OpenAI client with the configured API key and base URL.
    
    Returns:
        openai.OpenAI: Configured OpenAI client
    """
    config = Config.get_instance()
    return openai.OpenAI(
        api_key=config.api_key,
        base_url=config.api_url,
    )

def get_openai_model():
    """
    Get the configured OpenAI model name.
    
    Returns:
        str: Model name
    """
    return Config.get_instance().model

def get_stream_client():
    """
    Get a client configured for streaming responses.
    
    Returns:
        ModelClientManager: Client manager with streaming capability
    """
    config = Config.get_instance()
    return openai.OpenAI(
        api_key=config.api_key,
        base_url=config.api_url,
    )

def create_optimized_messages(system_message: str, user_message: str, conversation_history: List[Dict[str, str]], max_history: int = 4) -> List[Dict[str, str]]:
    """
    Create optimized message structure for API calls to reduce token usage.
    
    Args:
        system_message: System message with instructions
        user_message: Current user message
        conversation_history: Full conversation history
        max_history: Maximum number of history messages to include
    
    Returns:
        List of messages in OpenAI API format
    """
    # Start with system message
    messages = [{"role": "system", "content": system_message}]
    
    # Get the most relevant history (last N messages before current message)
    history_count = min(max_history, len(conversation_history) - 1) if len(conversation_history) > 0 else 0
    
    # Add relevant history context - skip the current user message which we'll add later
    if history_count > 0:
        relevant_history = conversation_history[-(history_count+1):-1]
        for message in relevant_history:
            # Compress messages by removing unnecessary whitespace
            content = message["content"].strip()
            messages.append({"role": message["role"], "content": content})
    
    # Add current user message
    messages.append({"role": "user", "content": user_message})
    
    return messages 