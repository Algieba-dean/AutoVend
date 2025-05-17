import os
from model_client_manager import ModelClientManager

def get_openai_client():
    """
    Get an OpenAI client with the configured API key and base URL.
    
    Returns:
        openai.OpenAI: Configured OpenAI client
    """
    # Use the singleton client manager
    return ModelClientManager().get_client()

def get_openai_model():
    """
    Get the configured OpenAI model name.
    
    Returns:
        str: Model name
    """
    return ModelClientManager().get_default_model()

def get_stream_client():
    """
    Get a client configured for streaming responses.
    
    Returns:
        ModelClientManager: Client manager with streaming capability
    """
    return ModelClientManager()

def create_optimized_messages(system_prompt, user_message, history=None, max_history=4):
    """
    Create optimized messages for API calls with reduced token usage.
    
    Args:
        system_prompt (str): System prompt
        user_message (str): User message
        history (list, optional): Conversation history
        max_history (int, optional): Maximum number of history items to include
        
    Returns:
        list: Messages for the completion API call
    """
    messages = [
        {"role": "system", "content": system_prompt}
    ]
    
    # Add selected history if provided
    if history:
        messages.extend(history[-max_history:])
    else:
        messages.append({"role": "user", "content": user_message})
        
    return messages 