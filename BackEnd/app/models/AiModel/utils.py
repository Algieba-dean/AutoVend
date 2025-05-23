import os
import openai
import time
from datetime import datetime
from functools import wraps
import re

def clean_thinking_output(output):
    """
    Clean the thinking output from the model.
    """
    cleaned_text = re.sub(r'<think>.*?</think>', '', output, flags=re.DOTALL)
    return cleaned_text

def timer_decorator(func):
    """
    A decorator that measures the execution time of a function.
    Outputs the start time, end time, time spent, and function name.
    
    Args:
        func: The function to be decorated
        
    Returns:
        wrapper: The wrapped function with timing functionality
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        if os.getenv("DEBUG", "false").lower() == "false":
            return func(*args, **kwargs)
        # Record start time
        start_time = datetime.now()
        start_time_str = start_time.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        
        # Execute the function
        result = func(*args, **kwargs)
        
        # Record end time
        end_time = datetime.now()
        end_time_str = end_time.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        
        # Calculate time difference
        time_spent = end_time - start_time
        
        # Output timing information
        print("-" * 50)
        print(f"Function: {func.__name__}")
        print(f"Start Time: {start_time_str}")
        print(f"End Time: {end_time_str}")
        print(f"Time Spent: {time_spent.total_seconds():.4f} seconds")
        print("-" * 50)
        print("\n")
        
        return result
    
    return wrapper

def get_current_time():
    """
    Get the current time in the format of YYYY-MM-DD HH:MM:SS
    """
    return datetime.now().time().strftime("%H:%M:%S")

def get_current_date():
    """
    Get the current date in the format of YYYY-MM-DD
    """
    return datetime.now().strftime("%Y-%m-%d")

def get_openai_client():
    """
    Get an OpenAI client with the configured API key and base URL.
    
    Returns:
        openai.OpenAI: Configured OpenAI client
    """
    # OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/v1")
    # OLLAMA_API_KEY = os.getenv("OLLAMA_API_KEY", "ollama")
    # OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", OLLAMA_API_KEY)
    # OPENAI_URL = os.getenv("OPENAI_URL", OLLAMA_URL)
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
    QWEN_MODEL_A3B = "modelscope.cn/unsloth/Qwen3-30B-A3B-128K-GGUF"
    QWEN_MODEL_32B = "modelscope.cn/unsloth/Qwen3-32B-128K-GGUF"
    OPENAI_MODEL = "deepseek-chat"
    OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", QWEN_MODEL_A3B)
    return os.getenv("OPENAI_MODEL", OPENAI_MODEL) 