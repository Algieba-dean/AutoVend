import json
import openai
import os
from utils import get_openai_client, get_openai_model

class ProfileExtractor:
    """
    Module for extracting user profile information from chat messages.
    Uses OpenAI to process user messages and extract relevant profile details.
    """
    
    def __init__(self, api_key=None, model=None):
        """
        Initialize the ProfileExtractor.
        
        Args:
            api_key (str, optional): OpenAI API key. Defaults to environment variable.
            model (str, optional): OpenAI model to use. Defaults to environment variable.
        """
        self.client = get_openai_client()
        self.model = model or get_openai_model()
        
        # Load user profile template
        with open("UserProfile.json", "r") as f:
            self.profile_template = json.load(f)
    
    def extract_profile(self, user_message):
        """
        Extract profile information from a user message.
        
        Args:
            user_message (str): The user's message to analyze
            
        Returns:
            dict: Dictionary containing extracted profile information
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
        
        # Parse and return the extracted profile information
        try:
            extracted_data = json.loads(response.choices[0].message.content)
            return extracted_data
        except json.JSONDecodeError:
            return {}
    
    def _create_system_message(self):
        """Create the system message with instructions for the AI."""
        profile_structure = json.dumps(self.profile_template, indent=2)
        
        return f"""
        You are an AI assistant specializing in extracting user profile information from conversations.
        
        Your task is to analyze the user message and extract relevant profile information according to this structure:
        {profile_structure}
        
        INSTRUCTIONS:
        1. Extract only information that is EXPLICITLY mentioned or can be CLEARLY inferred from the message.
        2. Return information in a flat dictionary format with field names matching the template.
        3. For fields with candidates, only use values from the allowed list.
        4. If you can infer information (like price sensitivity from budget comments), include those inferences.
        5. If no relevant profile information is found, return an empty dictionary {{}}.
        
        EXAMPLE RESPONSES:
        - For "My name is Zhang Wei, you can call me Mr. Zhang", return: {{"name": "Zhang Wei", "user_title": "Mr."}}
        - For "I want to buy a car for my son", return: {{"target_driver": "Son"}}
        - For "My budget is limited", return: {{"price_sensitivity": "High"}}
        
        Only return the JSON object with extracted information. Do not include explanations.
        """ 