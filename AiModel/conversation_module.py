import json
import random
import os
from utils import get_openai_client, get_openai_model
from prompt_manager import PromptManager

class ConversationModule:
    """
    Module for handling conversations with users during the car sales process.
    Uses OpenAI to generate contextually appropriate responses based on various inputs.
    Optimized with external prompt templates for better performance.
    """
    
    # Define conversation stages
    STAGES = {
        "welcome": "Initial greeting stage",
        "profile_analysis": "Collecting or analyzing user profile information",
        "needs_analysis": "Collecting or analyzing car requirements",
        "car_selection_confirmation": "Confirming selected car models",
        "reservation4s": "Setting up 4S store test drive",
        "reservation_confirmation": "Confirming test drive reservation details",
        "farewell": "Conversation closing stage"
    }
    
    # Predefined welcome messages
    WELCOME_MESSAGES = [
        "Hello! This is AutoVend, your intelligent car purchasing assistant. How can I help you find your ideal vehicle today?",
        "Hi there! I'm AutoVend, an AI-powered car consultant. I'm here to make your car shopping experience easier. What kind of vehicle are you looking for?",
        "Welcome to our virtual showroom! I'm AutoVend, your smart car assistant. I can help with everything from finding the right model to booking a test drive. How may I assist you?",
        "Thank you for contacting us! This is AutoVend, your personal car shopping guide. I'm here to help you find the perfect vehicle for your needs. What brings you to our service today?",
        "Good day! AutoVend at your service. I'm specialized in helping customers find their perfect car match. What type of vehicle are you interested in exploring?"
    ]
    
    def __init__(self, api_key=None, model=None):
        """
        Initialize the ConversationModule.
        
        Args:
            api_key (str, optional): OpenAI API key. Defaults to environment variable.
            model (str, optional): OpenAI model to use. Defaults to environment variable.
        """
        self.client = get_openai_client()
        self.model = model or get_openai_model()
        
        # Initialize conversation history
        self.conversation_history = []
        
        # Initialize prompt manager
        self.prompt_manager = PromptManager()
    
    def generate_response(self, user_message, user_profile={}, explicit_needs={}, 
                           implicit_needs={}, test_drive_info={}, matched_car_models={}, 
                           current_stage="welcome"):
        """
        Generate a response based on the user message and contextual information.
        
        Args:
            user_message (str): The user's message
            user_profile (dict): User profile information
            explicit_needs (dict): Explicitly stated car requirements
            implicit_needs (dict): Inferred car requirements
            test_drive_info (dict): Test drive reservation information
            matched_car_models (dict): Matched car models based on user requirements
            current_stage (str): Current conversation stage
            
        Returns:
            str: Generated assistant response
        """
        # For welcome stage with first interaction, use predefined welcome message
        if current_stage == "welcome" and not self.conversation_history:
            return random.choice(self.WELCOME_MESSAGES)
            
        # Add user message to conversation history
        self.conversation_history.append({"role": "user", "content": user_message})
        
        # Create simplified system message with optimized prompts
        system_message = self._create_simplified_system_message(
            user_profile, explicit_needs, implicit_needs, 
            test_drive_info, matched_car_models, current_stage
        )
        
        # Prepare the conversation for the API call
        messages = [
            {"role": "system", "content": system_message}
        ]
        
        # Add only the most relevant conversation history (last 6 messages to save tokens)
        messages.extend(self.conversation_history[-6:])
        
        # Call OpenAI API with optimized parameters
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.7,  # Add temperature for more consistent responses
            max_tokens=800    # Limit response length
        )
        
        # Get assistant response
        assistant_response = response.choices[0].message.content
        
        # Add assistant response to conversation history
        self.conversation_history.append({"role": "assistant", "content": assistant_response})
        
        return assistant_response
    
    def _create_simplified_system_message(self, user_profile, explicit_needs, implicit_needs, 
                                         test_drive_info, matched_car_models, current_stage):
        """
        Create a simplified system message with optimized prompts.
        
        Args:
            user_profile (dict): User profile information
            explicit_needs (dict): Explicitly stated car requirements
            implicit_needs (dict): Inferred car requirements
            test_drive_info (dict): Test drive reservation information
            matched_car_models (dict): Matched car models based on user requirements
            current_stage (str): Current conversation stage
            
        Returns:
            str: System message for the OpenAI API
        """
        # Get base prompt from prompt manager
        base_prompt = self.prompt_manager.get_base_prompt()
        
        # Extract expertise level (default to 3 if not provided)
        expertise_level = int(user_profile.get("expertise", 3))
        
        # Get expertise-specific prompt
        expertise_prompt = self.prompt_manager.get_expertise_prompt(expertise_level)
        
        # Get stage-specific prompt
        stage_prompt = self.prompt_manager.get_stage_prompt(current_stage)
        
        # Create simplified context information
        context = {
            "stage": current_stage,
            "stage_description": self.STAGES.get(current_stage, "Unknown stage"),
            "expertise_level": expertise_level
        }
        
        # Only include the most important user profile fields
        important_profile_fields = ["name", "user_title", "age", "occupation", "family_size"]
        filtered_profile = {k: v for k, v in user_profile.items() if k in important_profile_fields}
        context["user_profile"] = filtered_profile
        
        # Include only keys of needs rather than full content to save tokens
        context["explicit_needs_keys"] = list(explicit_needs.keys())[:5]  # Limit to top 5
        context["implicit_needs_keys"] = list(implicit_needs.keys())[:5]  # Limit to top 5
        
        # Include only essential test drive information
        if test_drive_info:
            context["has_test_drive_info"] = True
            context["test_drive_count"] = len(test_drive_info)
        
        # Include only model names from matched car models
        if matched_car_models and "matched_models" in matched_car_models:
            context["car_models"] = [
                model.get("car_model", "") for model in matched_car_models.get("matched_models", [])
            ]
        
        # Convert context to JSON string
        context_json = json.dumps(context, ensure_ascii=False)
        
        # Personal greeting based on profile info if available
        personalized_greeting = ""
        name = user_profile.get("name", "")
        title = user_profile.get("user_title", "")
        
        if current_stage == "profile_analysis" and (name or title):
            personalized_greeting = f"\n\nUse the customer's {'title ' + title if title else ''}{'name ' + name if name else ''} when greeting them."
        
        # Combine all prompts efficiently
        return f"{base_prompt}\n\nCONTEXT: {context_json}\n\n{expertise_prompt}\n\n{stage_prompt}{personalized_greeting}"
    
    def clear_history(self):
        """Clear the conversation history."""
        self.conversation_history = [] 