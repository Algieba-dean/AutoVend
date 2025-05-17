import sys
from typing import Callable, Optional, Dict, Any

class StreamingResponseHandler:
    """
    Handler for streaming LLM responses.
    Enables showing responses as they are received rather than waiting for the entire response.
    """
    
    def __init__(self, callback: Optional[Callable] = None):
        """
        Initialize the streaming handler.
        
        Args:
            callback (callable, optional): Callback function to call with each chunk
        """
        self.callback = callback
        self.full_response = ""
        self.is_streaming = False
        self.is_complete = False
    
    def process_stream(self, stream_response):
        """
        Process a streaming response.
        
        Args:
            stream_response: Streaming response from the API
            
        Returns:
            str: The complete response once streaming is finished
        """
        self.is_streaming = True
        self.full_response = ""
        self.is_complete = False
        
        # Process each chunk in the stream
        for chunk in stream_response:
            if hasattr(chunk.choices[0].delta, "content"):
                content = chunk.choices[0].delta.content
                if content:
                    self.full_response += content
                    if self.callback:
                        self.callback(content, self.full_response)
                    else:
                        # Default implementation: print to stdout without newline
                        sys.stdout.write(content)
                        sys.stdout.flush()
        
        if not self.callback:
            # Print a newline at the end if using default implementation
            sys.stdout.write("\n")
            sys.stdout.flush()
            
        self.is_streaming = False
        self.is_complete = True
        return self.full_response
        
    def get_full_response(self):
        """
        Get the full response text.
        
        Returns:
            str: Complete response text
        """
        return self.full_response


# Implementation for console streaming
class ConsoleStreamHandler(StreamingResponseHandler):
    """Handler for streaming to console with formatting options"""
    
    def __init__(self, prefix="AI: ", colored=True):
        """
        Initialize console stream handler.
        
        Args:
            prefix (str): Text prefix for the response
            colored (bool): Whether to use colored output
        """
        self.prefix = prefix
        self.colored = colored
        self.chunks_received = 0
        super().__init__(self.console_callback)
        
        # Print the prefix before streaming starts
        sys.stdout.write(prefix)
        sys.stdout.flush()
        
    def console_callback(self, chunk, full_text):
        """Callback for console streaming"""
        # First chunk handling
        if self.chunks_received == 0:
            # Prefix already printed in __init__
            pass
            
        # Print the chunk
        if self.colored:
            # Using ANSI escape codes for light blue text
            sys.stdout.write(f"\033[94m{chunk}\033[0m")
        else:
            sys.stdout.write(chunk)
            
        sys.stdout.flush()
        self.chunks_received += 1


# Example usage:
# client = get_stream_client()
# stream = client.stream_completion(messages, max_tokens=500)
# handler = ConsoleStreamHandler(prefix="AutoVend: ")
# response_text = handler.process_stream(stream) 