"""
LLM Factory for AutoVend
"""

from typing import Optional

from src.utils.config import config

from .base_llm import BaseLLM
from .mock_llm import MockLLM
from .openai_llm import OpenAILLM


class LLMFactory:
    """Factory for creating LLM instances"""

    @staticmethod
    def create_llm(
        provider: Optional[str] = None,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
        use_mock: bool = False,
    ) -> BaseLLM:
        """Create an LLM instance based on configuration"""

        if use_mock:
            return MockLLM()

        # Fall back to the single source of truth (src.utils.config), which already
        # resolves LLM_* / GROQ_* aliases and auto-selects mock when no key is present.
        provider = provider or config.llm_provider
        api_key = api_key or config.llm_api_key
        model = model or config.llm_model
        base_url = base_url or config.llm_base_url

        # Create LLM based on provider
        if provider == "mock":
            return MockLLM(model=model, api_key="mock-key")
        elif provider in ["groq", "openai", "anthropic", "together"]:
            # These providers use OpenAI-compatible API
            if not api_key:
                raise ValueError(f"API key required for provider: {provider}")

            # Set default base URLs for different providers
            provider_urls = {
                "groq": "https://api.groq.com/openai/v1",
                "openai": "https://api.openai.com/v1",
                "anthropic": "https://api.anthropic.com/v1",
                "together": "https://api.together.xyz/v1",
            }

            base_url = base_url or provider_urls.get(provider)

            return OpenAILLM(model=model, api_key=api_key, base_url=base_url)
        else:
            raise ValueError(f"Unsupported LLM provider: {provider}")

    @staticmethod
    def get_available_providers() -> list:
        """Get list of available providers"""
        return ["mock", "groq", "openai", "anthropic", "together"]

    @staticmethod
    def test_connection(llm: BaseLLM) -> bool:
        """Test connection to LLM"""
        try:
            return llm.is_available()
        except Exception:
            return False
