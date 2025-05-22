import json
import random
import os
from utils import get_openai_client, get_openai_model, timer_decorator, clean_thinking_output
from Conversation.prompt_loader import PromptLoader
from Conversation.needs_status import NeedsStatus
from Conversation.static_message import get_welcome_message, get_initial_message
from Conversation.ask_basic_informaton_messages import get_ask_name_message,get_ask_title_message,get_ask_target_driver_message
from Conversation.ask_reservation_information_messages import get_congratulation_message,get_ask_test_driver_message,get_ask_reservation_date_message,get_ask_reservation_time_message,get_ask_reservation_location_message
from Conversation.mocked_information import MockedInformation

class ConversationModule:
    """
    Module for handling conversations with users during the car sales process.
    Uses OpenAI to generate contextually appropriate responses based on various inputs.
    Optimized with external prompt templates for better performance.
    """
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
        
        
        self.prompt_loader = PromptLoader()
        self.needs_status = NeedsStatus()
        self.mocked_information = MockedInformation()
        self.init_prompt = self.prompt_loader.render_base_prompt() +  self.prompt_loader.render_common_endding()
        self.get_message_from_model("Hello you are AutoVend", self.init_prompt, no_add_history=True) # connect to the model to get the first response

    
    def add_message(self, role, message):
        """
        Add a message to the conversation history.
        """
        self.conversation_history.append({"role": role, "content": message})

    def generate_welcome_message(self, user_profile):
        """
        Generate a welcome message based on the user's profile.
        """
        # For welcome stage with first interaction, use predefined welcome message
        # Should directly ask user name, title, target driver at end of welcome message
        personalized_greeting = "Hi!"
        if user_profile.get("name") :
            personalized_greeting = f"Hi {user_profile.get("user_title","")} {user_profile.get("name")} !"
        response = f"{personalized_greeting} {get_welcome_message()}"
        self.add_message("assistant", response)
        return response

    def generate_initial_message(self):
        """
        Generate an initial message for the conversation.
        """
        # For initial stage, use predefined initial message
        return get_initial_message()
    def get_message_from_model(self,user_message, prompt, no_add_history=False)->str:
        # Add user message to conversation history
        self.add_message("user", user_message)
        
        # Prepare the conversation for the API call
        messages = [
            {"role": "system", "content": prompt}
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
        if not no_add_history:
            self.add_message("assistant", assistant_response)
        return assistant_response

    def generate_response_for_big_needs(self, user_profile, explicit_needs, implicit_needs, test_drive_info, matched_car_models, matched_car_model_infos, current_stage):
        """
        Generate a response for big needs.
        """
        expertise = user_profile.get("expertise", "")
        user_name = user_profile.get("name","")
        user_title = user_profile.get("user_title","")
        target_driver = user_profile.get("target_driver","")
        # needs analysis stage, multi turns conversation might needed
        needs_package_info = {
            "model_category_list" :[""],
            "powertrain_type_candidates":[""],
            "matched_car_models":matched_car_models,
            "explict_needs":explicit_needs, # should filter out from needs_status
            "matched_car_model":"", # TODO, should be the single matched car model from all matched car models, multi turns conversation
            "explict_needs_descriptions":"", # the descriptions of all filtered explict needs
            "implicit_needs":implicit_needs,
            "selected_car_model":"", # the model user point our to introduce more
            "details":"" # the key details of the selected car model

        }
        default_prompt = self.prompt_loader.render_base_prompt() + self.prompt_loader.render_expertise_prompt(expertise=expertise) + self.prompt_loader.render_common_endding()
        prompt = default_prompt
        if current_stage == "needs_analysis":
            # TODO
            prompt_type = ""
            prompt = self.prompt_loader.render_needs_analysis_prompt(prompt_type,expertise,user_name,user_title,**needs_package_info)
        if current_stage == "car_selection_confirmation":
            prompt_type = ""
            prompt = self.prompt_loader.render_needs_analysis_prompt(prompt_type,expertise,user_name,user_title,**needs_package_info)
        if current_stage =="implicit_confirmation":
            prompt_type = ""
            prompt = self.prompt_loader.render_needs_analysis_prompt(prompt_type,expertise,user_name,user_title,**needs_package_info)
        if current_stage == "car_selection_confirmation":
            prompt_type = ""
            prompt = self.prompt_loader.render_needs_analysis_prompt(prompt_type,expertise,user_name,user_title,**needs_package_info)
        if current_stage == "model_introduction":
            prompt_type = ""
            prompt = self.prompt_loader.render_needs_analysis_prompt(prompt_type,expertise,user_name,user_title,**needs_package_info)
    
    def generate_profile_response(self, user_message, user_profile, explicit_needs, 
                           implicit_needs, test_drive_info, matched_car_models, matched_car_model_infos,
                           current_stage):
        expertise = user_profile.get("expertise", "")
        user_name = user_profile.get("name","")
        user_title = user_profile.get("user_title","")
        target_driver = user_profile.get("target_driver","")
        # profile analysis stage
        default_prompt = self.prompt_loader.render_base_prompt() + self.prompt_loader.render_expertise_prompt(expertise=expertise) + self.prompt_loader.render_common_endding()
        prompt = default_prompt
        prompt_type = ""
        basic_profile = {
            "user_name":user_name, 
            "user_title":user_title, 
            "target_driver":target_driver,
            }
        if not user_profile.get("name"):
            prompt_type = "no_name"
            prompt = self.prompt_loader.render_profile_analysis_prompt(prompt_type, **basic_profile)
        elif not user_profile.get("user_title"):
            prompt = self.prompt_loader.render_profile_analysis_prompt("no_title",**basic_profile)
        elif not user_profile.get("target_driver"):
            prompt = self.prompt_loader.render_profile_analysis_prompt("no_target_driver",**basic_profile)
        
        assistant_response = self.get_message_from_model(user_message, prompt)
        return assistant_response
        
    def generate_reservation_response(self, user_message, user_profile, explicit_needs, 
                           implicit_needs, test_drive_info, matched_car_models, matched_car_model_infos,
                           current_stage):
        """
        Generate a response based on the user message and contextual information.
        """

        expertise = user_profile.get("expertise", "")
        user_name = user_profile.get("name","")
        user_title = user_profile.get("user_title","")
        target_driver = user_profile.get("target_driver","")
        target_driver_name = test_drive_info.get("target_driver_name","")

        # profile analysis stage
        default_prompt = self.prompt_loader.render_base_prompt() + self.prompt_loader.render_expertise_prompt(expertise=expertise) + self.prompt_loader.render_common_endding()
        prompt = default_prompt
        test_drive_package = {
            "target_driver" : "Your"+target_driver, # should convert into human readable format, 
            "stores_list" : self.mocked_information.get_random_stores(3), # need mock data
            "available_date_list":self.mocked_information.get_random_appointment_dates(3), # need mock data
            "salesman_list":self.mocked_information.get_random_salesmen(2), # need mock data
            "store":test_drive_info.get("reservation_location",""),
            "date":test_drive_info.get("reservation_date",""),
            "time":test_drive_info.get("reservation_time",""),
            "test_driver":test_drive_info.get("test_driver_name",""),
            "phone_number":test_drive_info.get("reservation_phone_number",""),
        }

        if current_stage == "reservation4s":
            if not test_drive_info.get("date"):
                prompt_type = "no_date"
                prompt = self.prompt_loader.render_test_drive_prompt(
                    prompt_type=prompt_type,
                    user_name=user_name,
                    user_title=user_title,
                    **test_drive_info)
        elif current_stage == "reservation_confirmation":
                prompt = self.prompt_loader.render_test_drive_prompt(
                    prompt_type="finished_reservation",
                    user_name=user_name,
                    user_title=user_title,
                    **test_drive_info)

        assistant_response = self.get_message_from_model(user_message, prompt)
        return assistant_response
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
        if current_stage == "initial":
            # initial warning message no need to be recorded in conversation history
            return get_initial_message()

        if current_stage == "welcome":
            # initial warning message no need to be recorded in conversation history
            return self.generate_welcome_message(user_profile)


        if current_stage =="profile_analysis":
            return self.generate_profile_response(user_message, user_profile, explicit_needs,
                           implicit_needs, test_drive_info, matched_car_models, matched_car_model_infos,
                           current_stage)

        if current_stage in ["needs_analysis","car_selection_confirmation","implicit_confirmation","model_introduction"]:
            return self.generate_response_for_big_needs(user_profile, explicit_needs, implicit_needs, test_drive_info, matched_car_models, matched_car_model_infos, current_stage)
        if current_stage in ["reservation4s","reservation_confirmation"]:
            return self.generate_reservation_response(user_message, user_profile, explicit_needs,
                           implicit_needs, test_drive_info, matched_car_models, matched_car_model_infos,
                           current_stage)
        
        empty_response = f"Unkown Stage :{current_stage}"
        return empty_response
    
    def clear_history(self):
        """Clear the conversation history."""
        self.conversation_history = [] 