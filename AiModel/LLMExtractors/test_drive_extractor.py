import json
import openai
import os
import re
from datetime import datetime
from utils import get_openai_client, get_openai_model

class TestDriveExtractor:
    """
    Module for extracting test drive reservation information from chat messages.
    Extracts details like test driver, date, time, location, phone number, and salesman.
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
        
        # Reservation info template
        self.reservation_template = {
            "test_driver": "",
            "reservation_date": "",
            "reservation_time": "",
            "reservation_location": "",
            "reservation_phone_number": "",
            "salesman": ""
        }
    
    def extract_test_drive_info(self, user_message):
        """
        Extract test drive reservation information from a user message.
        
        Args:
            user_message (str): The user's message to analyze
            
        Returns:
            dict: Dictionary containing extracted test drive information
        """
        # Prepare system message with instructions
        system_message = self._create_system_message()
        
        # Call OpenAI API
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_message}
            ],
            response_format={"type": "json_object"}
        )
        
        # Parse and return the extracted test drive information
        try:
            extracted_info = json.loads(response.choices[0].message.content)
            return self._validate_test_drive_info(extracted_info)
        except json.JSONDecodeError:
            return {}
    
    def _validate_test_drive_info(self, extracted_info):
        """Validate and clean up extracted test drive information."""
        validated_info = {}
        
        # Validate date format (if present)
        if "reservation_date" in extracted_info and extracted_info["reservation_date"]:
            try:
                # Try to parse the date to validate it
                date_str = extracted_info["reservation_date"]
                # Allow flexible date formats
                for fmt in ["%Y-%m-%d", "%Y/%m/%d", "%m/%d/%Y", "%d/%m/%Y", "%B %d, %Y"]:
                    try:
                        parsed_date = datetime.strptime(date_str, fmt)
                        # Convert to standard format
                        validated_info["reservation_date"] = parsed_date.strftime("%Y-%m-%d")
                        break
                    except ValueError:
                        continue
            except:
                # If date validation fails, keep original
                validated_info["reservation_date"] = extracted_info["reservation_date"]
        
        # Validate phone number (if present)
        if "reservation_phone_number" in extracted_info and extracted_info["reservation_phone_number"]:
            phone = extracted_info["reservation_phone_number"]
            # Keep only digits and common separators
            clean_phone = re.sub(r'[^\d\+\-\(\) ]', '', phone)
            validated_info["reservation_phone_number"] = clean_phone
        
        # Copy other fields directly
        for field in ["test_driver", "reservation_time", "reservation_location", "salesman"]:
            if field in extracted_info:
                validated_info[field] = extracted_info[field]
        
        return validated_info
    
    def _create_system_message(self):
        """Create the system message with instructions for the AI."""
        template_json = json.dumps(self.reservation_template, indent=2)
        
        return f"""
        You are an AI assistant specializing in extracting test drive reservation information from conversations.
        
        Your task is to analyze the user message and extract any test drive reservation details according to this structure:
        {template_json}
        
        INSTRUCTIONS:
        1. Extract only information that is EXPLICITLY mentioned in the message.
        2. For each field:
           - test_driver: The person who will test drive the car (name or relationship)
           - reservation_date: The date for the test drive in YYYY-MM-DD format
           - reservation_time: The time for the test drive
           - reservation_location: The dealership or location for the test drive
           - reservation_phone_number: Contact phone number
           - salesman: Name of the salesperson (if mentioned)
        3. Return information in a dictionary format matching the template.
        4. Only include fields that have information in the message.
        5. If no test drive information is found, return an empty dictionary {{{{}}}}.
        
        EXAMPLE RESPONSES:
        - For "I'd like to schedule a test drive for next Monday at 2pm, my name is John Smith", return: 
          {{"test_driver": "John Smith", "reservation_date": "YYYY-MM-DD", "reservation_time": "2:00 PM"}}
        
        Only return the JSON object with extracted information. Do not include explanations.
        """ 