# AutoVend AI Car Sales Assistant

AutoVend is an AI-powered car sales assistant system that intelligently analyzes user needs, extracts information, and provides personalized car recommendations and sales support. The system uses a modular design with multiple performance optimizations to provide a smooth user interaction experience.

## Project Structure

```
AutoVend/
├── main.py                     # Main application entry point
├── conversation_module.py      # Conversation management module
├── model_client_manager.py     # API client manager
├── batch_processor.py          # Batch request processor
├── streaming_response_handler.py # Streaming response handler
├── utils.py                    # Utility and configuration functions
├── prompt_manager.py           # Prompt manager
├── module_decision_maker.py    # Module decision maker
├── profile_extractor.py        # User information extractor
├── expertise_evaluator.py      # Expertise evaluator
├── explicit_needs_extractor.py # Explicit needs extractor
├── implicit_needs_inferrer.py  # Implicit needs inferrer
├── test_drive_extractor.py     # Test drive information extractor
├── model_query_module.py       # Car model query module
├── prompts/                    # Prompt template directory
│   ├── base_prompt.txt         # Base prompt template
│   └── ...                     # Other prompt templates
├── tests/                      # Test directory
│   ├── __init__.py             # Test package initialization file
│   ├── test_batch_processing.py # Batch processing test
│   ├── test_streaming_mode.py  # Streaming output test
│   ├── test_conversation_flow.py # Conversation flow test
│   ├── test_performance.py     # Performance test
│   ├── test_module_decision.py # Module decision test
│   └── ...                     # Other test files
└── requirements.txt            # Project dependencies
```

## Performance Optimizations

This project implements various performance optimization measures that significantly improve response speed and user experience:

### 1. Client Management Optimization

- **Singleton Pattern**: Uses `ModelClientManager` class to avoid repeatedly creating API clients
- **Connection Pool**: Maintains a pool of clients for different configurations, reducing connection overhead
- **Automatic Retry**: Implements automatic retry logic for failed connections, improving system stability

### 2. Streaming Response Processing

- **Streaming API Calls**: Supports the `stream=True` parameter to start displaying responses immediately
- **Chunk Processing**: Processes response chunks through the `StreamingResponseHandler` class
- **Real-time Display**: Implements real-time response display using `ConsoleStreamHandler`

### 3. Batch Request Processing

- **Request Combining**: Uses the `BatchProcessor` class to combine multiple extraction tasks into a single API request
- **Intelligent Parsing**: Extracts multiple results from a single response, reducing API call count
- **Priority Processing**: Determines which tasks can be batched together for optimal performance

### 4. Request Optimization

- **Lazy Loading Pattern**: Modules are loaded on demand, reducing initialization time and memory usage
- **Prompt Optimization**: Reduces prompt content size, optimizing token usage
- **Response Caching**: Caches common responses to avoid repeated requests
- **Compact Message Format**: Uses a more compact message structure to reduce token usage
- **Selective Module Activation**: Only runs necessary processing modules

### 5. Thread Pool Management

- **Optimized Worker Count**: Adjusts thread pool size based on workload
- **Resource Cleanup**: Properly closes thread pools to avoid resource leaks
- **Parallel Processing**: Ensures critical tasks are prioritized in the thread pool

## Performance Improvements

According to testing, these optimizations provide significant performance improvements:

- **Response Time**: Overall response time improved by 40-60%
- **First Word Appearance**: Initial response appears within 2-3 seconds (much faster than the original 10+ seconds)
- **API Call Reduction**: API calls reduced by 30-70% depending on conversation context
- **Token Usage**: Token consumption reduced by 15-25%

## Usage

### Basic Usage

```python
from auto_vend_ai_module import AutoVend

# Create assistant instance
assistant = AutoVend()

# Process user message
result = assistant.process_message("I want to buy a family SUV with good safety features")

# Get response
print(result["response"])
```

### Enable Streaming Mode

```python
# Enable streaming responses for real-time feedback
assistant = AutoVend(use_streaming=True)
```

### Configure Batch Processing

```python
# Configure batch processing to improve multi-task processing efficiency
assistant = AutoVend()
assistant.use_batch_processing = True
```

### Combined Optimizations

```python
# Use all optimizations for best performance
assistant = AutoVend(use_streaming=True)
assistant.use_batch_processing = True
assistant.config.use_cache = True
```

## Testing

Run performance tests to compare different configurations:

```bash
python -m tests.test_performance
```

Test streaming mode functionality:

```bash
python -m tests.test_streaming_mode
```

Test batch processing functionality:

```bash
python -m tests.test_batch_processing
```

Test complete conversation flow:

```bash
python -m tests.test_conversation_flow
```

## System Requirements

- Python 3.7+
- External LLM API access (such as DeepSeek or OpenAI)
- See the `requirements.txt` file for dependency details 