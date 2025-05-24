import json
import openai
import os
from utils import get_openai_client, get_openai_model, timer_decorator, clean_thinking_output

class ExplicitNeedsExtractor:
    """
    Module for extracting explicit user car needs from chat messages.
    Extracts only directly mentioned requirements based on QueryLabels.json.
    """
    
    def __init__(self, api_key=None, model=None, explicit_labels=dict()):
        """
        Initialize the ExplicitNeedsExtractor.
        
        Args:
            api_key (str, optional): OpenAI API key. Defaults to environment variable.
            model (str, optional): OpenAI model to use. Defaults to environment variable.
        """
        self.client = get_openai_client()
        self.model = model or get_openai_model()
        
        # Load car query labels from the Config directory
        config_file_path = os.path.join(os.path.dirname(__file__), "../Config/QueryLabels.json")
        
        if not os.path.exists(config_file_path):
            # Fallback if run from parent directory (e.g. AiModel) and Config is a direct subdir of it
            config_file_path = "./Config/QueryLabels.json"

        try:
            with open(config_file_path, "r") as f:
                self.query_labels = json.load(f)
        except FileNotFoundError as e:
            print(f"Error: QueryLabels.json not found in ExplicitNeedsExtractor. Attempted path: {os.path.abspath(config_file_path)}. Error: {e}")
            self.query_labels = {}
            # raise FileNotFoundError(f"QueryLabels.json is critical and was not found. Path: {os.path.abspath(config_file_path)}") from e

    
    @timer_decorator
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
            response_format={"type": "json_object"},
            temperature=0.1
        )
        
        # Parse and return the extracted needs
        try:
            content = response.choices[0].message.content
            content = clean_thinking_output(content)
            extracted_needs = json.loads(content)
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
        based on these available categories and their potential candidate values:
        {labels_json}
        
        INSTRUCTIONS:
        1. ONLY extract requirements that are EXPLICITLY mentioned by the user.
        2. DO NOT infer requirements that aren't directly stated.
        3. For each identified requirement, use the exact key from the provided categories.
        4. The value for a key should be based on the candidate values provided for that category.
           - If the user explicitly mentions MULTIPLE candidate values for the SAME category that all apply, collect these values into a LIST for that key.
           - If the user mentions a single value, use that single value directly (not in a list).
        5. Return the extracted requirements as a flat JSON object. Keys should map to either a single string value or a list of string values.
        6. If no explicit requirements are mentioned, return an empty object {{}}.
        
        EXAMPLES:
        - User: "I want a sedan with good fuel economy."
          Assistant: {{"vehicle_category_top": "sedan", "fuel_consumption_alias": "low"}}
        - User: "I need a car with 7 seats."
          Assistant: {{"seat_layout": "7-seat"}}
        - User: "I'm looking for a Japanese or a German car."
          Assistant: {{"brand_country": ["japan", "germany"]}}
        - User: "I'd prefer a blue or red car."
          Assistant: {{"color": ["blue", "red"]}}
        
        Only return the JSON object with extracted requirements. Do not include explanations.
        """ 