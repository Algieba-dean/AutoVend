# AutoVend Refactoring

This document outlines the refactoring work done to optimize the AutoVend AI Car Sales Assistant for better performance and maintainability.

## Key Changes

### 1. Extracted Prompts to External Files

All prompts have been extracted from code into JSON template files in the `prompts/` directory:

- `base.json`: Core conversation guidelines and basic instructions
- `expertise.json`: Customer expertise level-specific prompts (novice, intermediate, advanced, expert)
- `stages.json`: Conversation stage-specific prompts
- `examples.json`: Example conversations for different scenarios

### 2. Added Prompt Manager

Created a new `PromptManager` class that:
- Loads prompt templates from JSON files
- Provides methods to access specific prompts based on context
- Reduces memory footprint by loading only necessary prompt components

### 3. Optimized ConversationModule

The `ConversationModule` was refactored to:
- Use the `PromptManager` to load prompts
- Create simplified system messages with only essential context
- Limit conversation history to the most recent 6 messages (down from 10)
- Add temperature and max_tokens parameters to the API call for more consistent responses

### 4. Simplified Context Information

Context information sent to the API is now:
- Filtered to include only important user profile fields
- Limited to only keys of needs rather than full content
- Shortened to include only essential test drive information
- Optimized to include only car model names rather than full details

## How to Use the New Structure

1. **Adding or Modifying Prompts**:
   - Edit the JSON files in the `prompts/` directory
   - No need to modify code when changing prompt content

2. **Adding New Expertise Levels**:
   - Add a new entry to `expertise.json`
   - Update the `get_expertise_prompt()` method in `PromptManager` if needed

3. **Adding New Conversation Stages**:
   - Add a new entry to `stages.json`
   - Update the `STAGES` dictionary in `ConversationModule`
   - Update the `_update_stage()` method in `AutoVend` class

## Performance Benefits

This refactoring provides several performance improvements:

1. **Reduced Token Usage**: By sending more concise prompts to the API
2. **Faster Response Time**: Due to smaller payloads and optimized processing
3. **Better Consistency**: Through temperature parameter and example templates
4. **Lower Memory Usage**: By loading only necessary prompt components

## Future Improvements

Potential next steps for further optimization:

1. Implement caching for frequently used prompt combinations
2. Create a prompt versioning system
3. Add metrics collection to track prompt performance
4. Implement A/B testing for different prompt strategies 