import json
import openai
import os
from utils import get_openai_client, get_openai_model

class ExplicitNeedsExtractor:
    """
    Module for extracting explicit user car needs from chat messages.
    Extracts only directly mentioned requirements based on QueryLabels.json.
    """
    
    def __init__(self, api_key=None, model=None):
        """
        Initialize the ExplicitNeedsExtractor.
        
        Args:
            api_key (str, optional): OpenAI API key. Defaults to environment variable.
            model (str, optional): OpenAI model to use. Defaults to environment variable.
        """
        self.client = get_openai_client()
        self.model = model or get_openai_model()
        
        # Load car query labels
        with open("QueryLabels.json", "r") as f:
            self.query_labels = json.load(f)
    
    def extract_explicit_needs(self, user_message):
        """
        Extract explicit car needs from a user message.
        
        Args:
            user_message (str): The user's message to analyze
            
        Returns:
            dict: Dictionary containing extracted car requirements
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
        
        # Parse and return the extracted needs
        try:
            extracted_needs = json.loads(response.choices[0].message.content)
            return extracted_needs
        except json.JSONDecodeError:
            return {}
    
    def _create_system_message(self):
        """Create the system message with instructions for the AI."""
        # Prepare simplified labels structure for the prompt
        labels_structure = {}
        for label, data in self.query_labels.items():
            if "candidates" in data:
                labels_structure[label] = data["candidates"]
        
        labels_json = json.dumps(labels_structure, indent=2)
        
        return f"""
        You are an AI assistant specializing in extracting EXPLICIT car requirements from user messages.
        
        Your task is to analyze the user message and extract car requirements that are DIRECTLY MENTIONED,
        based on these available categories and values:
        {labels_json}
        
        INSTRUCTIONS:
        1. ONLY extract requirements that are EXPLICITLY mentioned by the user.
        2. DO NOT infer requirements that aren't directly stated.
        3. For each identified requirement, use the exact key and allowed value from the provided structure.
        4. Return the extracted requirements as a flat JSON object.
        5. If no explicit requirements are mentioned, return an empty object {{}}.
        
        EXAMPLES:
        - For "I want a sedan with good fuel economy", extract: {{"vehicle_category_top": "sedan", "fuel_consumption_alias": "low"}}
        - For "I need a car with 7 seats", extract: {{"seat_layout": "7-seat"}}
        
        Only return the JSON object with extracted requirements. Do not include explanations.
        """ 