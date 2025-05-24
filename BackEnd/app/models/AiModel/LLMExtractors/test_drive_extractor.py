import json
import openai
import os
import re
from datetime import datetime

from Conversation.mocked_information import mocked_information
from InformationExtractors.date_extractor import DateExtractor
from InformationExtractors.time_extractor import TimeExtractor
from utils import get_openai_client, get_openai_model

class TestDriveExtractor:
    """
    Module for extracting test drive reservation information from chat messages.
    Extracts details based on Config/ReservationInfo.json.
    """
    
    def __init__(self, api_key=None, model=None):
        """
        Initialize the TestDriveExtractor.
        
        Args:
            api_key (str, optional): OpenAI API key. Defaults to environment variable.
            model (str, optional): OpenAI model to use. Defaults to environment variable.
        """
        self.client = get_openai_client()
        self.model = model or get_openai_model()
        self.date_extractor = DateExtractor()
        self.time_extractor = TimeExtractor()
        # Load reservation info fields from JSON file
        # Adjust path if Config directory is not in the current working directory of execution
        # e.g., os.path.join(os.path.dirname(__file__), "../Config/ReservationInfo.json")
        try:
            # Assuming Config folder is in the same directory as the one from which the script is run,
            # or an appropriate parent directory if this script is in a subfolder.
            # For LLMExtractors/test_drive_extractor.py, if Config is sibling to LLMExtractors:
            config_path = os.path.join(os.path.dirname(__file__), "../Config/ReservationInfo.json")
            if not os.path.exists(config_path):
                 # Fallback if not found at ../Config, try ./Config (e.g. if run from AiModel directory)
                config_path = "./Config/ReservationInfo.json"

            with open(config_path, "r") as f:
                self.reservation_info_fields = json.load(f)
        except FileNotFoundError:
            print(f"Warning: ReservationInfo.json not found at {config_path} or ./Config/ReservationInfo.json. Using a default template.")
            # Default template if file is not found, including new fields
            self.reservation_info_fields = {
                "test_driver": {"candidates": ["self", "wife", "husband", "son", "daughter", "mom", "dad", "friend"], "description": "the driver of the test drive"},
                "test_driver_name": {"description": "the name of the test driver"},
                "reservation_date": {"description": "the date of the test drive"},
                "selected_car_model": {"description": "the car model of the test drive"},
                "reservation_time": {"description": "the time of the test drive"},
                "reservation_location": {"description": "the location of the test drive"},
                "reservation_phone_number": {"description": "the phone number of the test drive"},
                "salesman": {"description": "the salesman of the test drive"}
            }

    def extract_test_drive_info(self, user_message):
        """
        Extract test drive reservation information from a user message.
        
        Args:
            user_message (str): The user's message to analyze
            
        Returns:
            dict: Dictionary containing extracted test drive information
        """
        system_message = self._create_system_message()
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_message}
            ],
            response_format={"type": "json_object"},
            temperature=0.1
        )
        
        try:
            extracted_info = json.loads(response.choices[0].message.content)
            return self._validate_test_drive_info(extracted_info)
        except json.JSONDecodeError:
            return {}
    
    def _validate_test_drive_info(self, extracted_info):
        """Validate and clean up extracted test drive information."""
        validated_info = {}
        
        if "test_driver" in extracted_info and extracted_info["test_driver"]:
            candidates = self.reservation_info_fields.get("test_driver", {}).get("candidates")
            if candidates and extracted_info["test_driver"] in candidates:
                validated_info["test_driver"] = extracted_info["test_driver"]
            # else: # Optional: handle cases where test_driver is not in candidates
                # print(f"Warning: Extracted test_driver '{extracted_info['test_driver']}' not in predefined candidates.")
                # validated_info["test_driver"] = None # Or some default or keep original
        
        if "reservation_date" in extracted_info and extracted_info["reservation_date"]:
            try:
                date_str = extracted_info["reservation_date"]
                extracted_data = self.date_extractor.extract_dates(date_str)
                if len(extracted_data) > 0:
                    validated_info["reservation_date"] = extracted_data[0].strftime("%Y-%m-%d")
                else:
                    validated_info["reservation_date"] = date_str.strftime("%Y-%m-%d")
            except Exception as e:
                print(f"Error parsing date: {date_str}, Error: {e}")
                validated_info["reservation_date"] = extracted_info["reservation_date"]
        
        if "reservation_phone_number" in extracted_info and extracted_info["reservation_phone_number"]:
            phone = str(extracted_info["reservation_phone_number"])
            validated_info["reservation_phone_number"] = phone 
        
        if "reservation_time" in extracted_info and extracted_info["reservation_time"]:
            time_str = self.time_extractor.extract_times(extracted_info["reservation_time"])
            if len(time_str) > 0:
                validated_info["reservation_time"] = time_str[0].strftime("%H:%M")
            else:
                validated_info["reservation_time"] = extracted_info["reservation_time"]

        # Copy other fields defined in reservation_info_fields directly or with simple validation
        for field in self.reservation_info_fields.keys():
            if field not in validated_info and field in extracted_info: # Avoid overwriting already validated fields
                validated_info[field] = extracted_info[field]
        
        return validated_info
    
    def _create_system_message(self):
        """Create the system message with instructions for the AI."""
        # Create a simple dictionary for the LLM prompt (key: description)
        fields_for_prompt = {key: value.get("description", "") for key, value in self.reservation_info_fields.items()}
        template_json_for_llm = json.dumps(fields_for_prompt, indent=2)
        
        field_details = []
        for key, details in self.reservation_info_fields.items():
            description = details.get("description", "No description available.")
            candidates = details.get("candidates")
            detail_str = f"           - {key}: {description}"
            if candidates:
                detail_str += f" (Expected values from: {json.dumps(candidates)})"
            field_details.append(detail_str)
        fields_description_for_llm = "\n".join(field_details)

        return f"""
        You are an AI assistant specializing in extracting test drive reservation information from conversations.
        
        Your task is to analyze the user message and extract any test drive reservation details according to the fields listed below.
        Only return the fields for which you find information in the user's message.

        The salesmen names are: {mocked_information.salesman_names}
        The stores are: {mocked_information.mocked_stores}
        The dates are: {mocked_information.mocked_dates}
        
        Available fields to extract:
{template_json_for_llm}

        Detailed instructions for each field:
{fields_description_for_llm}


        INSTRUCTIONS:
        1. Extract only information that is EXPLICITLY mentioned in the message.
        2. For 'reservation_date', try to format it as YYYY-MM-DD if possible, otherwise keep the user's format.
        3. For 'test_driver', if the user mentions a relationship (e.g., 'my son'), use the value from the candidates list if available.
        4. Return information as a JSON object. Only include fields for which information was found.
        5. If no test drive information is found, return an empty JSON object {{}}.
        
        EXAMPLE RESPONSES:
        - For "I'd like to schedule a test drive for my son, John, for next Monday at 2pm. My number is 123-456-7890.", return: 
          {json.dumps({"test_driver": "son", "test_driver_name": "John", "reservation_date": "YYYY-MM-DD (actual date for next Monday)", "reservation_time": "2:00 PM", "reservation_phone_number": "123-456-7890"}, indent=2)}
        
        Only return the JSON object with extracted information. Do not include explanations.
        """ 