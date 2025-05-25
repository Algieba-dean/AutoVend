# AutoVend AI Car Sales Assistant

AutoVend is an AI-powered car sales assistant that helps customers find their ideal vehicle through natural language conversations. The system uses LLM API (with support for OpenAI and DeepSeek) to analyze customer messages, extract relevant information, and guide the conversation through different stages of the car buying process.

## Features

- **Profile Extraction**: Extracts user information such as name, age, car expertise level, etc.
- **Expertise Evaluation**: Assesses the user's knowledge about cars on a scale of 0-10
- **Explicit Needs Extraction**: Identifies directly stated car requirements
- **Implicit Needs Inference**: Infers indirectly implied car requirements based on user's lifestyle and preferences
- **Test Drive Information Collection**: Extracts and validates test drive reservation details
- **Conversational Interface**: Provides natural, contextually appropriate responses based on the conversation stage
- **Multiple LLM Support**: Works with OpenAI APIs and DeepSeek APIs

## Architecture

The system consists of several modules:

1. **ProfileExtractor**: Extracts user profile information from conversations
2. **ExpertiseEvaluator**: Evaluates user's car knowledge level
3. **ExplicitNeedsExtractor**: Extracts directly mentioned car requirements
4. **ImplicitNeedsInferrer**: Infers implied car requirements
5. **TestDriveExtractor**: Extracts test drive reservation information
6. **ConversationModule**: Handles the conversation flow and generates responses
7. **AutoVend**: Main class that orchestrates all modules

## Conversation Stages

The system guides the conversation through different stages:

- **welcome**: Initial greeting and introduction
- **profile_analysis**: Collecting user information
- **needs_analysis**: Analyzing car requirements
- **car_selection_confirmation**: Confirming selected car models
- **reservation4s**: Setting up a test drive at a 4S store
- **reservation_confirmation**: Confirming test drive details
- **farewell**: Conversation closing

## Setup

1. Clone the repository
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Set environment variables:
   ```
   # For OpenAI
   export OPENAI_API_KEY=your_api_key_here
   export OPENAI_MODEL=gpt-4o  # optional, defaults to deepseek-chat
   
   # For DeepSeek (default)
   export OPENAI_API_KEY=your_deepseek_api_key_here  
   export OPENAI_MODEL=deepseek-chat  # optional, defaults to deepseek-chat
   export OPENAI_URL=https://api.deepseek.com/v1  # optional, defaults to https://api.deepseek.com/v1
   ```
4. Run the application:
   ```
   python main.py
   ```

## Example Usage

```python
from autovend import AutoVend

# Initialize the assistant
assistant = AutoVend()

# Process a user message
result = assistant.process_message("I'm looking for a family SUV with good fuel economy")

# Get the assistant's response
print(result["response"])

# Access extracted information
print(result["explicit_needs"])
print(result["implicit_needs"])
```

## Configuration Files

- **UserProfile.json**: Contains the structure for user profile information
- **QueryLabels.json**: Contains the car specifications and features that can be extracted

## Requirements

- Python 3.7+
- OpenAI compatible API key (OpenAI or DeepSeek)
- openai Python package 