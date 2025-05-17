import json
import openai
import os
from utils import get_openai_client, get_openai_model

class ConversationModule:
    """
    Module for handling conversations with users during the car sales process.
    Uses OpenAI to generate contextually appropriate responses based on various inputs.
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
        # Add user message to conversation history
        self.conversation_history.append({"role": "user", "content": user_message})
        
        # Prepare system message with instructions and context
        system_message = self._create_system_message(user_profile, explicit_needs, 
                                                    implicit_needs, test_drive_info, 
                                                    matched_car_models, current_stage)
        
        # Prepare the conversation for the API call
        messages = [
            {"role": "system", "content": system_message}
        ]
        
        # Add conversation history (limited to last 10 messages to save tokens)
        messages.extend(self.conversation_history[-10:])
        
        # Call OpenAI API
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages
        )
        
        # Get assistant response
        assistant_response = response.choices[0].message.content
        
        # Add assistant response to conversation history
        self.conversation_history.append({"role": "assistant", "content": assistant_response})
        
        return assistant_response
    
    def _create_system_message(self, user_profile, explicit_needs, implicit_needs, 
                              test_drive_info, matched_car_models, current_stage):
        """Create the system message with instructions and context for the AI."""
        # Convert dictionaries to JSON strings for the prompt
        profile_json = json.dumps(user_profile, indent=2, ensure_ascii=False)
        explicit_needs_json = json.dumps(explicit_needs, indent=2, ensure_ascii=False)
        implicit_needs_json = json.dumps(implicit_needs, indent=2, ensure_ascii=False)
        test_drive_json = json.dumps(test_drive_info, indent=2, ensure_ascii=False)
        matched_cars_json = json.dumps(matched_car_models, indent=2, ensure_ascii=False)
        
        # Get stage description
        stage_description = self.STAGES.get(current_stage, "Unknown stage")
        
        return f"""
        You are AutoVend, an AI car sales assistant helping customers find their ideal vehicle.
        You should sound professional, knowledgeable, and friendly.
        
        CURRENT CONTEXT:
        - Current stage: {current_stage} - {stage_description}
        - User profile information: {profile_json}
        - User's explicit car requirements: {explicit_needs_json}
        - User's inferred car requirements: {implicit_needs_json}
        - Test drive information: {test_drive_json}
        - Matched car models: {matched_cars_json}
        
        STAGE-SPECIFIC INSTRUCTIONS:
        - welcome: Greet the user professionally and ask about their car needs. If profile information is lacking, try to collect basic details in a conversational manner.
        - profile_analysis: Focus on gathering more information about the user, their lifestyle, and car usage patterns.
        - needs_analysis: Inquire about specific car requirements, preferences, and deal-breakers.
        - car_selection_confirmation: Present car recommendations based on gathered information and confirm if they meet expectations. Refer specifically to the matched car models in your response and highlight their features.
        - reservation4s: Help the user schedule a test drive, collecting necessary information in a friendly way.
        - reservation_confirmation: Confirm test drive details and provide next steps.
        - farewell: Thank the user, summarize the interaction, and provide closure with contact information.
        
        WHEN DISCUSSING CAR MODELS:
        - Only refer to car models that are in the "matched_car_models" list
        - Highlight features that specifically match the user's requirements
        - If asked about a specific model, provide accurate information about it
        - If uncertain about specific details of a car model, suggest the user verify with the dealership
        
        Please keep your response concise, conversational, and focused on the current stage.
        Your expertise level should match the user's assessed expertise level.
        
        Respond in the same language as the user's message.
        """
    
    def clear_history(self):
        """Clear the conversation history."""
        self.conversation_history = [] 