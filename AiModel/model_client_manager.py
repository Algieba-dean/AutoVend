import os
import openai
from time import sleep
from typing import Dict, Any

class ModelClientManager:
    """
    Singleton manager for LLM API clients.
    Ensures only one client is created per configuration and handles request optimization.
    """
    
    _instance = None
    _clients = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ModelClientManager, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        """Initialize the manager with default settings"""
        self._clients = {}
        self._default_config = {
            "api_key": os.getenv("OPENAI_API_KEY", "sk-40f9ea6f41bd4cbbae8a9d4adb07fbf8"),
            "base_url": os.getenv("OPENAI_URL", "https://api.deepseek.com/v1"),
            "model": os.getenv("OPENAI_MODEL", "deepseek-chat")
        }
        
        # Create the default client
        self._default_client = self._create_client(
            self._default_config["api_key"], 
            self._default_config["base_url"]
        )
    
    def _create_client(self, api_key, base_url):
        """Create a client with specific configuration"""
        client_key = f"{api_key}:{base_url}"
        
        if client_key not in self._clients:
            # Create new client with retry logic
            self._clients[client_key] = self._create_client_with_retry(api_key, base_url)
            
        return self._clients[client_key]
    
    def _create_client_with_retry(self, api_key, base_url, max_retries=3):
        """Create client with retry logic for better reliability"""
        for attempt in range(max_retries):
            try:
                client = openai.OpenAI(
                    api_key=api_key,
                    base_url=base_url,
                )
                # Test the client with a minimal request
                _ = client.models.list()
                return client
            except Exception as e:
                if attempt < max_retries - 1:
                    sleep(1)  # Wait before retrying
                else:
                    print(f"Error creating client: {e}")
                    # Return a default client as fallback
                    return openai.OpenAI(
                        api_key=api_key,
                        base_url=base_url,
                    )
    
    def get_client(self, api_key=None, base_url=None):
        """
        Get or create an API client.
        
        Args:
            api_key (str, optional): API key
            base_url (str, optional): API base URL
            
        Returns:
            openai.OpenAI: API client
        """
        if not api_key:
            api_key = self._default_config["api_key"]
        
        if not base_url:
            base_url = self._default_config["base_url"]
            
        return self._create_client(api_key, base_url)
    
    def get_default_model(self):
        """Get the default model name"""
        return self._default_config["model"]
    
    def stream_completion(self, messages, model=None, **kwargs):
        """
        Create a streaming completion for faster initial response.
        
        Args:
            messages (list): Messages for the chat completion
            model (str, optional): Model to use
            **kwargs: Additional parameters for the completion
            
        Returns:
            generator: Streaming response
        """
        if not model:
            model = self._default_config["model"]
            
        # Set streaming to True for this request
        kwargs["stream"] = True
        
        # Use default client for streaming
        return self._default_client.chat.completions.create(
            model=model,
            messages=messages,
            **kwargs
        )
    
    def batch_request(self, batch_messages, model=None, **kwargs):
        """
        Process multiple related requests in a single API call when possible.
        
        Args:
            batch_messages (list): List of message groups to process
            model (str, optional): Model to use
            **kwargs: Additional parameters for the completion
            
        Returns:
            list: List of completion results
        """
        if not model:
            model = self._default_config["model"]
        
        # For simple batching, combine into a single request with JSON format
        combined_messages = [
            {"role": "system", "content": "Process multiple tasks and return results in JSON format. Each task is provided as a separate user message."}
        ]
        
        for i, message_group in enumerate(batch_messages):
            # Add a task identifier
            combined_messages.append({"role": "user", "content": f"TASK {i+1}:\n{message_group[-1]['content']}"})
        
        # Make a single API call
        response = self._default_client.chat.completions.create(
            model=model,
            messages=combined_messages,
            **kwargs
        )
        
        return response 