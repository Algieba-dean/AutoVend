import os
import openai

def get_openai_client():
    """
    Get an OpenAI client with the configured API key and base URL.
    
    Returns:
        openai.OpenAI: Configured OpenAI client
    """
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "sk-40f9ea6f41bd4cbbae8a9d4adb07fbf8")
    OPENAI_URL = os.getenv("OPENAI_URL", "https://api.deepseek.com/v1")
    
    client = openai.OpenAI(
        api_key=OPENAI_API_KEY,
        base_url=OPENAI_URL,
    )
    
    return client

def get_openai_model():
    """
    Get the configured OpenAI model name.
    
    Returns:
        str: Model name
    """
    return os.getenv("OPENAI_MODEL", "deepseek-chat") 