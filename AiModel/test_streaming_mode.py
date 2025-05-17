import time
from main import AutoVend

def test_streaming_mode():
    """Test the streaming mode toggle functionality"""
    print("=== AutoVend Streaming Mode Test ===\n")
    
    # Initialize assistant with streaming disabled (default)
    assistant = AutoVend()
    
    # Test messages to send
    test_message = "I'm looking for a family SUV with good safety features and fuel economy"
    
    # First test without streaming
    print("\n[TEST 1: Without Streaming (Default)]\n")
    print("Processing message...")
    start_time = time.time()
    
    # Call process_message and track when first output appears
    result = assistant.process_message(test_message)
    
    # Measure total time
    total_time = time.time() - start_time
    print(f"\nResponse: {result['response'][:100]}...")
    print(f"Total processing time: {total_time:.2f} seconds")
    
    # Now enable streaming and test again
    print("\n[TEST 2: With Streaming Enabled]\n")
    assistant.use_streaming = True
    assistant.conversation_module.use_streaming = True
    print("Streaming mode enabled")
    print("Processing message...")
    
    start_time = time.time()
    print("Response: ", end="", flush=True)  # Prepare for streaming output
    
    # Process message (streaming output will appear in real time)
    result = assistant.process_message(test_message)
    
    # Measure total time
    total_time = time.time() - start_time
    print(f"\nTotal processing time: {total_time:.2f} seconds")
    
    # Reset state
    assistant.reset()
    
    # Test toggle functionality
    print("\n[TEST 3: Toggle Streaming Mode]\n")
    
    # Turn off streaming
    assistant.use_streaming = False
    assistant.conversation_module.use_streaming = False
    print("Streaming mode disabled")
    
    # Test with streaming off
    start_time = time.time()
    print("Processing with streaming OFF...")
    result1 = assistant.process_message("Tell me about electric vehicles")
    time1 = time.time() - start_time
    print(f"Response received after {time1:.2f} seconds")
    
    # Turn on streaming
    assistant.use_streaming = True
    assistant.conversation_module.use_streaming = True
    print("\nStreaming mode enabled")
    
    # Test with streaming on
    start_time = time.time()
    print("Processing with streaming ON...")
    result2 = assistant.process_message("Tell me about hybrid vehicles")
    time2 = time.time() - start_time
    print(f"Response completed after {time2:.2f} seconds")
    
    print("\n=== Test Complete ===\n")
    print("NOTE: With streaming mode ON, you should see partial responses appear immediately,")
    print("      while with streaming OFF, you must wait for the full response to be generated.")

if __name__ == "__main__":
    test_streaming_mode() 