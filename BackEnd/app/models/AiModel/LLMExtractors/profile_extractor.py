import json
import openai
import os
from utils import get_openai_client, get_openai_model

class ProfileExtractor:
    """
    Module for extracting user profile information from chat messages.
    Uses OpenAI to process user messages and extract relevant profile details based on Config/UserProfile.json.
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
        
        # Load user profile template from the Config directory
        config_file_path = os.path.join(os.path.dirname(__file__), "../Config/UserProfile.json")

        if not os.path.exists(config_file_path):
            # Fallback if run from parent directory (e.g. AiModel) and Config is a direct subdir of it
            config_file_path = "./Config/UserProfile.json"
        
        try:
            with open(config_file_path, "r") as f:
                self.profile_template = json.load(f)
        except FileNotFoundError:
            print(f"Warning: UserProfile.json not found at {os.path.abspath(config_file_path)}. Using a default profile template.")
            self.profile_template = {
                "phone_number": "", "user_title": "", "name": "", "target_driver": "", "expertise": "",
                "additional_information": {"family_size": "", "price_sensitivity": "", "residence": "", "parking_conditions": ""}
                # Note: 'age' and 'connection_information' are intentionally omitted from this default based on prior requests.
            }
    
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
            response_format={"type": "json_object"},
            temperature=0.1
        )
        
        # Parse and return the extracted profile information
        try:
            extracted_data = json.loads(response.choices[0].message.content)
            
            # Validate extracted data against candidates
            validated_data = {}
            for key, value in extracted_data.items():
                if key in self.profile_template:
                    # Check if the field has candidates defined in the template
                    if "candidates" in self.profile_template[key]:
                        # If candidates are defined, check if the extracted value is among them
                        if value in self.profile_template[key]["candidates"]:
                            validated_data[key] = value
                        # If value is not in candidates, it's considered invalid for this key, so we don't add it.
                        # Optionally, we could log a warning or handle this case differently.
                    else:
                        # If no candidates are defined, accept the value as is
                        validated_data[key] = value
                else:
                    # If the key is not in the template at all, we might want to ignore it
                    # or handle it based on specific requirements. For now, let's include it.
                    # This case might indicate the LLM returned an unexpected field.
                    # Depending on strictness, we could choose to ignore these.
                    # For now, to be safe and retain all information not explicitly invalidated:
                    validated_data[key] = value # Or decide to exclude keys not in template
            
            return validated_data
        except json.JSONDecodeError:
            return {}
    
    def _create_system_message(self):
        """Create the system message with instructions for the AI."""
        # Create a deep copy of the profile template to modify it for the prompt
        # This prevents altering the original self.profile_template
        profile_template_for_prompt = json.loads(json.dumps(self.profile_template))

        # Remove 'age' if it exists in the copied template
        if "age" in profile_template_for_prompt:
            del profile_template_for_prompt["age"]
            
        # Remove 'connection_information' if it exists in the copied template
        if "connection_information" in profile_template_for_prompt:
            del profile_template_for_prompt["connection_information"]
            
        profile_structure = json.dumps(profile_template_for_prompt, indent=2)
        
        return f"""
        You are an AI assistant specializing in extracting user profile information from conversations.
        
        Your task is to analyze the user message and extract relevant profile information according to this structure:
        {profile_structure}
        
        INSTRUCTIONS:
        1. Extract only information that is EXPLICITLY mentioned or can be CLEARLY inferred from the message.
        2. Return information in a flat dictionary format with field names matching the template (excluding age and connection_information).
        3. For fields with candidates, only use values from the allowed list.
        4. If you can infer information (like price sensitivity from budget comments), include those inferences.
        5. If no relevant profile information is found, return an empty dictionary {{}}.
        
        EXAMPLE RESPONSES:
        - For "My name is Zhang Wei, you can call me Mr. Zhang", return: {{"name": "Zhang Wei", "user_title": "Mr."}}
        - For "I want to buy a car for my son", return: {{"target_driver": "Son"}}
        - For "My budget is limited", return: {{"price_sensitivity": "High"}}
        
        Only return the JSON object with extracted information. Do not include explanations.
        """ 