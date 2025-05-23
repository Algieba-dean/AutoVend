import json
import random
import os
from utils import get_openai_client, get_openai_model, timer_decorator, clean_thinking_output
from Conversation.prompt_loader import PromptLoader
from Conversation.needs_status import NeedsStatus
from Conversation.static_message import get_welcome_message, get_initial_message
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

    
    def get_history_for_llm_arbitrator(self):
        """
        Get the conversation history for the LLM arbitrator.
        """
        return self.conversation_history
    
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
<<<<<<< HEAD
            personalized_greeting = f"Hi {user_profile.get('user_title','')} {user_profile.get('name')} !"
=======
            personalized_greeting = f'Hi {user_profile.get("user_title","")} {user_profile.get("name")} !'
>>>>>>> 63870f1 (feat: fix a welcome loading message)
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
            prompt_type = "" # Default to empty
            # Check for missing budget information
            if not explicit_needs.get("prize") and not explicit_needs.get("prize_alias"):
                prompt_type = "no_budget"
            # Check for missing model category information
            elif not explicit_needs.get("vehicle_category_top") and \
                 not explicit_needs.get("vehicle_category_middle") and \
                 not explicit_needs.get("vehicle_category_bottom"):
                prompt_type = "no_model_category"
            # Check for missing brand information
            elif not explicit_needs.get("brand_area") and \
                 not explicit_needs.get("brand_country") and \
                 not explicit_needs.get("brand"):
                prompt_type = "no_brand"
            # Check for missing powertrain type information
            elif not explicit_needs.get("powertrain_type"):
                prompt_type = "no_powertrain_type"
            
            # If a prompt_type was determined, render the specific prompt
            if prompt_type:
                prompt = self.prompt_loader.render_needs_analysis_prompt(prompt_type,expertise,user_name,user_title,**needs_package_info)
            else:
                # TODO: Handle cases where all essential needs are present or a different logic is required
                # For now, it will use the default_prompt if no specific prompt_type is matched.
                # Consider what should happen if all initial checks pass.
                # Maybe a general needs confirmation or moving to a different stage/prompt.
                pass # Or assign a different default prompt for this situation
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
        else:
            prompt = self.prompt_loader.render_needs_analysis_prompt("no_budget",expertise,user_name,user_title,**{})
        
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

        prompt_type = None
        if not test_drive_info.get("test_driver"):
            prompt_type = "ask_test_driver"
        elif not test_drive_info.get("test_driver_name") or not test_drive_info.get("reservation_phone_number"):
            prompt_type = "ask_test_driver_name_and_phone"
        elif not test_drive_info.get("reservation_location"):
            prompt_type = "ask_location"
        elif not test_drive_info.get("reservation_date"):
            prompt_type = "ask_date"
        elif not test_drive_info.get("reservation_time"):
            prompt_type = "ask_time"
        elif not test_drive_info.get("salesman"):
            prompt_type = "ask_salesman"
        else:
            prompt_type = "finished_reservation"

        if prompt_type:
            prompt = self.prompt_loader.render_test_drive_prompt(
                prompt_type=prompt_type,
                user_name=user_name,
                user_title=user_title,
                **test_drive_package
            )

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

    def generate_response_for_big_needs_llm(self, 
                                            user_message, 
                                            user_profile, 
                                            explicit_needs, 
                                            implicit_needs, 
                                            test_drive_info, 
                                            matched_car_models, 
                                            matched_car_model_infos, 
                                            current_stage):
        """
        Generate a response for complex needs scenarios, tailored for when LLM extractors were used.
        """
        expertise = user_profile.get("expertise", "")
        user_name = user_profile.get("name","")
        user_title = user_profile.get("user_title","")
        # clean matched_car_model_infos, only keep the explict mentioned 
        filtered_out_matched_informations = self.needs_status.get_car_model_comment_infos(explicit_needs, matched_car_model_infos)
        
        prompt = self.prompt_loader.render_llm_needs_analysis_prompt(expertise, user_name, user_title, explicit_needs, implicit_needs, matched_car_models, filtered_out_matched_informations)
        
        # --- Actual LLM Call ---
        if not prompt: # Safety check if prompt somehow ended up empty
            return "I'm sorry, I encountered an issue preparing my thoughts. Could you please try rephrasing?"

        try:
            # Assuming 'prompt' contains the full instruction set for the LLM
            # The role can be "system" if the prompt is a directive to the LLM,
            # or "user" if it's phrased as user input for a conversational LLM.
            # Given prompt_loader, it's likely a system-level instruction.
            messages = [{"role": "system", "content": prompt}]
            
            llm_response = self.client.chat.completions.create(
                model=self.model, # Ensure self.model is initialized in ConversationModule
                messages=messages,
                temperature=0.7, # Adjust as needed
                max_tokens=1000    # Adjust as needed
            )
            assistant_response = llm_response.choices[0].message.content
            
            # Assuming clean_thinking_output is available and imported if needed
            if hasattr(self, 'clean_thinking_output'): # Or directly from utils if imported
                 assistant_response = self.clean_thinking_output(assistant_response)
            # from utils import clean_thinking_output # if you prefer to call it directly
            # assistant_response = clean_thinking_output(assistant_response)


            # Add to history (if you have an add_message method)
            # self.add_message("assistant", assistant_response) 
            return assistant_response
        except Exception as e:
            print(f"Error during LLM call in generate_response_for_big_needs_llm: {e}")
            return "I'm having a little trouble processing that request right now. Please try again shortly."

    def generate_response_for_big_needs_traditional(self, user_profile, explicit_needs, implicit_needs, test_drive_info, matched_car_models, matched_car_model_infos, current_stage):
        """
        Generate a response for complex needs scenarios, tailored for when Traditional extractors were used.
        For now, duplicates the LLM version's logic. Customize as needed.
        """
        expertise = user_profile.get("expertise", "")
        user_name = user_profile.get("name","")
        user_title = user_profile.get("user_title","")
        # target_driver = user_profile.get("target_driver","")

        needs_package_info = {
            "model_category_list" :[""], 
            "powertrain_type_candidates":[""],
            "matched_car_models": matched_car_models,
            "explict_needs": explicit_needs,
            "matched_car_model": "", 
            "explict_needs_descriptions": "",
            "implicit_needs": implicit_needs,
            "selected_car_model": "", 
            "details": ""
        }
        
        default_prompt_parts = []
        if hasattr(self.prompt_loader, 'render_base_prompt'):
            default_prompt_parts.append(self.prompt_loader.render_base_prompt())
        if hasattr(self.prompt_loader, 'render_expertise_prompt'):
            default_prompt_parts.append(self.prompt_loader.render_expertise_prompt(expertise=expertise))
        if hasattr(self.prompt_loader, 'render_common_endding'): # Assuming 'endding' is a typo for 'ending'
            default_prompt_parts.append(self.prompt_loader.render_common_endding())
        default_prompt = "".join(default_prompt_parts)

        prompt = default_prompt
        
        if current_stage == "needs_analysis":
            prompt_type = ""
            if not explicit_needs.get("prize") and not explicit_needs.get("prize_alias"):
                prompt_type = "no_budget"
            elif not explicit_needs.get("vehicle_category_top") and \
                 not explicit_needs.get("vehicle_category_middle") and \
                 not explicit_needs.get("vehicle_category_bottom"):
                prompt_type = "no_model_category"
            elif not explicit_needs.get("brand_area") and \
                 not explicit_needs.get("brand_country") and \
                 not explicit_needs.get("brand"):
                prompt_type = "no_brand"
            elif not explicit_needs.get("powertrain_type"):
                prompt_type = "no_powertrain_type"

            if prompt_type and hasattr(self.prompt_loader, 'render_needs_analysis_prompt'):
                prompt = self.prompt_loader.render_needs_analysis_prompt(prompt_type, expertise, user_name, user_title, **needs_package_info)
        
        elif current_stage in ["car_selection_confirmation", "implicit_confirmation", "model_introduction"]:
            prompt_type = "" 
            if hasattr(self.prompt_loader, 'render_needs_analysis_prompt'):
                prompt = self.prompt_loader.render_needs_analysis_prompt(prompt_type, expertise, user_name, user_title, **needs_package_info)

        if not prompt:
            return "I'm sorry, I encountered an issue preparing my thoughts. Could you please try rephrasing?"

        try:
            messages = [{"role": "system", "content": prompt}]
            
            llm_response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.7,
                max_tokens=1000 
            )
            assistant_response = llm_response.choices[0].message.content
            
            if hasattr(self, 'clean_thinking_output'):
                 assistant_response = self.clean_thinking_output(assistant_response)
            # from utils import clean_thinking_output
            # assistant_response = clean_thinking_output(assistant_response)
            
            # self.add_message("assistant", assistant_response)
            return assistant_response
        except Exception as e:
            print(f"Error during LLM call in generate_response_for_big_needs_traditional: {e}")
            return "I'm having a little trouble processing that request right now. Please try again shortly."

    # ... (The rest of your ConversationModule class, including the 
    #      get_history_for_llm_arbitrator and generate_response_for_stage methods 
    #      that we discussed/implemented previously) ... 