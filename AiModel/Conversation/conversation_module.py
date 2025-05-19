import json
import random
import os
from utils import get_openai_client, get_openai_model, timer_decorator, clean_thinking_output
from prompt_manager import PromptManager
from Conversation.welcome_message import get_welcome_message
from Conversation.ask_basic_informaton_messages import get_ask_name_message,get_ask_title_message,get_ask_target_driver_message
from Conversation.ask_reservation_information_messages import get_congratulation_message,get_ask_test_driver_message,get_ask_reservation_date_message,get_ask_reservation_time_message,get_ask_reservation_location_message

class ConversationModule:
    """
    Module for handling conversations with users during the car sales process.
    Uses OpenAI to generate contextually appropriate responses based on various inputs.
    Optimized with external prompt templates for better performance.
    """
    
    # Define conversation stages
    STAGES = {
        "welcome": "Initial greeting stage",
        "profile_analysis": "Collecting or analyzing user profile information name, name title, target driver, and use the profile to generate a personalized greeting. Specially, if the user is a new customer, you should ask for the user's name and title. And ask their target driver",
        "needs_analysis": "Collecting or analyzing car requirements, if the user has not provided the car requirements, you should ask for the car requirements",
        "car_selection_confirmation": "Confirming selected car models",
        "reservation4s": "Setting up 4S store test drive,  ",
        "reservation_confirmation": "Confirming test drive reservation details",
        "farewell": "Conversation closing stage"
    }
    
    # Predefined welcome messages
    
    
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
        self.__basic_information = {
            "name":False, 
            "user_title":False, 
            "target_driver":False
            }
    def get_initial_response(self, user_profile:dict):
        """
        Get the initial response , for warning the user that the chat will be recorded for training and improvement, randomly pick one from the WELCOME_MESSAGES.
        If user name and title are provided, use them to generate a personalized greeting.
        """
        personalized_greeting = "Hi!"
        if user_profile.get("name") :
            personalized_greeting = f"Hi {user_profile.get("user_title","")} {user_profile.get("name")} !"
        return f"{personalized_greeting} {get_welcome_message()}"
    
    def get_ask_basic_info_response(self, user_profile:dict):
        """
        Get the response from the conversation module when asking for basic info.
        """
        user_name = user_profile.get("name","")
        user_title = user_profile.get("user_title","")
        target_driver = user_profile.get("target_driver","")
        if not user_name:
            return random.choice(get_ask_name_messages())
        if not user_title:
            return random.choice(get_ask_title_messages())
        if not target_driver:
            return f"Hi {user_title} {user_name} ! {get_ask_target_driver_messages()}"
        return f"Hi {user_title} {user_name} ! {get_ask_target_driver_messages()}"
    
    def get_ask_reservation_response(self, user_profile:dict, reservation_info:dict):
        """
        Get the response from the conversation module when asking for reservation.
        """
        test_driver = reservation_info.get("test_driver","")
        reservation_date = reservation_info.get("reservation_date","")
        reservation_time = reservation_info.get("reservation_time","")
        reservation_location = reservation_info.get("reservation_location","")
        reservation_phone_number = reservation_info.get("reservation_phone_number","")
        salesman = reservation_info.get("salesman","")
        selected_car_model = reservation_info.get("selected_car_model","")
        return f"Hi {user_profile.get("user_title","")} {user_profile.get("name")} ! {get_ask_target_driver_messages()}"
    
    @timer_decorator
    def generate_response(self, user_message, user_profile, explicit_needs, 
                           implicit_needs, test_drive_info, matched_car_models, matched_car_model_infos,
                           current_stage):
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
            return get_welcome_message()
            
        # Add user message to conversation history
        self.conversation_history.append({"role": "user", "content": user_message})
        
        # Create simplified system message with optimized prompts
        system_message = self._create_simplified_system_message(
            user_profile, explicit_needs, implicit_needs, 
            test_drive_info, matched_car_models, matched_car_model_infos, current_stage
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
            max_tokens=500# Limit response length
        )
        
        # Get assistant response
        assistant_response = response.choices[0].message.content
        assistant_response = clean_thinking_output(assistant_response)
        
        # Add assistant response to conversation history
        self.conversation_history.append({"role": "assistant", "content": assistant_response})
        
        return assistant_response
    
    def _create_simplified_system_message(self, user_profile, explicit_needs, implicit_needs, 
                                         test_drive_info, matched_car_models, matched_car_model_infos, current_stage):
        """
        Create a simplified system message with optimized prompts.
        
        Args:
            user_profile (dict): User profile information
            explicit_needs (dict): Explicitly stated car requirements
            implicit_needs (dict): Inferred car requirements
            test_drive_info (dict): Test drive reservation information
            matched_car_models (list): Matched car models based on user requirements
            matched_car_model_infos (list): Matched car model infos based on user requirements
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
        context["explicit_needs_keys"] = list(explicit_needs.keys())
        context["implicit_needs_keys"] = list(implicit_needs.keys())[:5]  # Limit to top 5
        
        # Include only essential test drive information
        if test_drive_info:
            context["has_test_drive_info"] = True
            context["test_drive_count"] = len(test_drive_info)
        
        # Include only model names from matched car models
        if len(matched_car_models) <=0:
            context["car_models"] = []
        elif len(matched_car_models) > 3:
            context["car_models"] = matched_car_models[:3] # pick the top 3 car models
        else:
            context["car_models"] = matched_car_models
        
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