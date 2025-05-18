import json
import random
import os
from utils import get_openai_client, get_openai_model, get_stream_client, create_optimized_messages
from utils import Config, get_from_cache, add_to_cache
from prompt_manager import PromptManager
from streaming_response_handler import StreamingResponseHandler, ConsoleStreamHandler


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
        "Hello! This is AutoVend, your intelligent car purchasing assistant. Current chat will be recorded for training and improvement. Continue means you agree to this.",
        "Hi there! I'm AutoVend, an AI-powered car consultant. Current chat will be recorded for training and improvement. Continue means you agree to this.",
        "Welcome to our virtual showroom! I'm AutoVend, your smart car assistant. Current chat will be recorded for training and improvement. Continue means you agree to this.",
        "Thank you for contacting us! This is AutoVend, your personal car shopping guide. Current chat will be recorded for training and improvement. Continue means you agree to this.",
        "Good day! AutoVend at your service. Current chat will be recorded for training and improvement. Continue means you agree to this."
    ]

    def __init__(self, api_key=None, model=None, use_streaming=False):
        """
        Initialize the ConversationModule.
        
        Args:
            api_key (str, optional): OpenAI API key. Defaults to environment variable.
            model (str, optional): OpenAI model to use. Defaults to environment variable.
            use_streaming (bool): Whether to use streaming responses. Defaults to False.
        """
        # Use lazy initialization for clients
        self._client = None
        self._stream_client = None
        self.model = model or get_openai_model()

        # Initialize conversation history
        self.conversation_history = []

        # Initialize prompt manager
        self.prompt_manager = PromptManager()

        # Use config instance for settings
        self.config = Config.get_instance()
        self.use_streaming = use_streaming

    @property
    def client(self):
        """Lazy-loaded client property"""
        if self._client is None:
            self._client = get_openai_client()
        return self._client

    @property
    def stream_client(self):
        """Lazy-loaded streaming client property"""
        if self._stream_client is None:
            self._stream_client = get_stream_client()
        return self._stream_client

    def generate_response(self, user_message, user_profile=dict(), explicit_needs=dict(),
                          implicit_needs=dict(), test_drive_info=dict(), matched_car_models=list(),
                          matched_car_model_infos=list(), current_stage="welcome"):
        """
        Generate a response based on the user message and contextual information.
        
        Args:
            user_message (str): The user's message
            user_profile (dict): User profile information
            explicit_needs (dict): Explicitly stated car requirements
            implicit_needs (dict): Inferred car requirements
            test_drive_info (dict): Test drive reservation information
            matched_car_models (list): Matched car models based on user requirements
            matched_car_model_infos (list): Matched car models information
            current_stage (str): Current conversation stage
            
        Returns:
            str: Generated assistant response
        """
        # Check cache first for identical queries in the same context
        cache_key = f"{user_message}_{current_stage}"
        if user_profile is None:
            user_profile = dict()
        if explicit_needs is None:
            explicit_needs = dict()
        if implicit_needs is None:
            implicit_needs = dict()
        if test_drive_info is None:
            test_drive_info = dict()
        if matched_car_models is None:
            matched_car_models = list()
        if matched_car_model_infos is None:
            matched_car_model_infos = list()


        # Only use cache for short messages (likely common queries)
        if len(user_message) < 50:
            cached_response = get_from_cache(cache_key)
            if cached_response:
                return cached_response

        # For welcome stage with first interaction, use predefined welcome message
        if current_stage == "welcome" and not self.conversation_history:
            welcome_msg = random.choice(self.WELCOME_MESSAGES)
            # Store in cache
            add_to_cache(cache_key, welcome_msg)
            return welcome_msg

        # Add user message to conversation history
        self.conversation_history.append({"role": "user", "content": user_message})

        # Create simplified system message with optimized prompts
        system_message = self._create_simplified_system_message(
            user_profile, explicit_needs, implicit_needs,
            test_drive_info, matched_car_models, matched_car_model_infos, current_stage
        )

        # Prepare the conversation for the API call - only include relevant history
        messages = create_optimized_messages(system_message, user_message,
                                             self.conversation_history, max_history=4)

        # Generate response
        if self.use_streaming:
            # Use streaming for faster initial response
            stream = self.stream_client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.7,
                max_tokens=1024,
                stream=True  # Explicitly set streaming parameter
            )

            # Process the streaming response
            handler = ConsoleStreamHandler(prefix="AutoVend: ")
            assistant_response = handler.process_stream(stream)
        else:
            # Traditional non-streaming response
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.7,
                max_tokens=1024
            )
            assistant_response = response.choices[0].message.content

        # Add assistant response to conversation history
        self.conversation_history.append({"role": "assistant", "content": assistant_response})

        # Cache common responses for short messages
        if len(user_message) < 50:
            add_to_cache(cache_key, assistant_response)

        return assistant_response

    def _create_simplified_system_message(self, user_profile,
                                          explicit_needs, implicit_needs,
                                          test_drive_info,
                                          matched_car_models, matched_car_model_infos, current_stage):
        """
        Create a simplified system message with optimized prompts.
        
        Args:
            user_profile (dict): User profile information
            explicit_needs (dict): Explicitly stated car requirements
            implicit_needs (dict): Inferred car requirements
            test_drive_info (dict): Test drive reservation information
            matched_car_models (list): Matched car models based on user requirements
            matched_car_model_infos (list): Matched car models information
            current_stage (str): Current conversation stage
            
        Returns:
            str: System message for the OpenAI API
        """
        # Get base prompt from prompt manager
        base_prompt = self.prompt_manager.get_base_prompt()

        # Extract expertise level (default to 3 if not provided)
        expertise_level = 3
        if user_profile:
            extracted_user_profile = user_profile.get("expertise")
            if extracted_user_profile:
                expertise_level = int(extracted_user_profile)

        # Get expertise-specific prompt
        expertise_prompt = self.prompt_manager.get_expertise_prompt(expertise_level)

        # Get stage-specific prompt
        stage_prompt = self.prompt_manager.get_stage_prompt(current_stage)

        # Create minimal context object with only essential information
        context = {
            "stage": current_stage,
            "expertise": expertise_level
        }

        # Only include the most important user profile fields
        important_profile_fields = [
            "name",
            "user_title",
            "target_driver",
        ]
        # TODO, for connection user, should also load
        filtered_profile = {k: v for k, v in user_profile.items() if k in important_profile_fields}
        if filtered_profile:
            context["user"] = filtered_profile

        # Include only keys of needs rather than full content to save tokens
        needs_keys = set()
        if explicit_needs:
            needs_keys.update(list(explicit_needs.keys())[:5])  # Limit to top 5

        if implicit_needs:
            needs_keys.update(list(implicit_needs.keys())[:5])  # Limit to top 5

        if needs_keys:
            context["needs"] = list(needs_keys)

            # Include top 2 most important needs values for context
            top_needs = {}
            for key in [
                "prize",
                "vehicle_category_bottom",
                "brand",
                "size",
                "energy_consumption_level",
                "family_friendliness",
                "powertrain_type",
            ]:
                if key in explicit_needs:
                    top_needs[key] = explicit_needs[key]
                elif key in implicit_needs:
                    top_needs[key] = implicit_needs[key]
                if len(top_needs) >= 2:
                    break

            if top_needs:
                context["top_needs"] = top_needs

        # Include only essential test drive information
        if test_drive_info:
            # Only include date and time if available
            test_drive_essential = {}
            for key in [
                "test_driver",
                "reservation_date",
                "reservation_time",
                "reservation_location",
                "reservation_phone_number",
                "salesman"
                # "selected_model"
            ]:
                if key in test_drive_info:
                    test_drive_essential[key] = test_drive_info[key]

            if test_drive_essential:
                context["test_drive"] = test_drive_essential

        # Include only model names from matched car models
        if len(matched_car_models) <= 0:
            context["models"] = list()
        elif 3>= len(matched_car_models) > 0:
            context["models"] = matched_car_models[:3]
        else:
            context["models"] = matched_car_models

        # Convert context to JSON string - more compact format
        context_json = json.dumps(context, ensure_ascii=False, separators=(',', ':'))

        # Personal greeting based on profile info if available
        personalized_greeting = ""
        name = user_profile.get("name", "")
        title = user_profile.get("user_title","")

        if current_stage == "profile_analysis" and name:
            tittle_greeting = f"and use customer's title '{title}' "
            personalized_greeting = f"\n\nUse the customer's name '{name}' {tittle_greeting if title else ""} when greeting them."


        # Combine all prompts efficiently with minimal whitespace
        return f"{base_prompt}\nCONTEXT:{context_json}\n{expertise_prompt}\n{stage_prompt}{personalized_greeting}"

    def clear_history(self):
        """Clear the conversation history"""
        self.conversation_history = []
