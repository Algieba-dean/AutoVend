"""
Base LLM Interface for AutoVend
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any

class BaseLLM(ABC):
    """Base class for all LLM implementations"""
    
    def __init__(
        self,
        model: str,
        api_key: str,
        base_url: Optional[str] = None,
        **kwargs
    ):
        self.model = model
        self.api_key = api_key
        self.base_url = base_url
        self.kwargs = kwargs
    
    @abstractmethod
    def complete(self, prompt: str, **kwargs) -> str:
        """Complete a text prompt"""
        pass
    
    @abstractmethod
    def chat(self, messages: list, **kwargs) -> str:
        """Chat with a list of messages"""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if the LLM service is available"""
        pass
    
    def get_config(self) -> Dict[str, Any]:
        """Get LLM configuration"""
        return {
            "model": self.model,
            "base_url": self.base_url,
            "kwargs": self.kwargs
        }
