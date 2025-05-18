import json
import openai
import os
from utils import get_openai_client, get_openai_model, timer_decorator

class ImplicitNeedsInferrer:
    """
    Module for inferring implicit user car needs from chat messages.
    Infers likely requirements based on indirect statements using QueryLabels.json.
    """
    
    def __init__(self, api_key=None, model=None):
        """
        Initialize the ImplicitNeedsInferrer.
        
        Args:
            api_key (str, optional): OpenAI API key. Defaults to environment variable.
            model (str, optional): OpenAI model to use. Defaults to environment variable.
        """
        self.client = get_openai_client()
        self.model = model or get_openai_model()
        
        # Load car query labels
        with open("QueryLabels.json", "r") as f:
            self.query_labels = json.load(f)
    
    @timer_decorator
    def infer_implicit_needs(self, user_message):
        """
        Infer implicit car needs from a user message.
        
        Args:
            user_message (str): The user's message to analyze
            
        Returns:
            dict: Dictionary containing inferred car requirements
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
        # Parse and return the inferred needs
        try:
            inferred_needs = json.loads(response.choices[0].message.content)
            return inferred_needs
        except json.JSONDecodeError:
            return {}
    
    def _create_system_message(self):
        """Create the system message with instructions for the AI."""
        # Prepare simplified labels structure for the prompt
        labels_structure = {}
        for label, data in self.query_labels.items():
            if "candidates" in data:
                labels_structure[label] = {
                    "candidates": data["candidates"],
                    "description": data.get("description", "")
                }
        
        labels_json = json.dumps(labels_structure, indent=2)
        
        return f"""
        You are an AI assistant specializing in inferring IMPLICIT car requirements from user messages.
        
        Your task is to analyze the user message and INFER car requirements that are NOT directly mentioned
        but can be logically deduced from the user's statements, based on these available categories and values:
        {labels_json}
        
        INSTRUCTIONS:
        1. ONLY infer requirements that are NOT explicitly mentioned but can be logically deduced.
        2. Make reasonable inferences based on lifestyle, family situation, mentioned activities, etc.
        3. For each inferred requirement, use the exact key and allowed value from the provided structure.
        4. Return the inferred requirements as a flat JSON object.
        5. If no implicit requirements can be inferred, return an empty object {{}}.
        6. Use high confidence inferences only - don't overreach in your analysis.
        
        EXAMPLES:
        - For "I have a big family with 5 children", infer: {{"family_friendliness": "high", "size": "large", "seat_layout": "7-seat"}}
        - For "I live in a mountain area with lots of snow", infer: {{"off_road_capability": "high", "cold_resistance": "high"}}
        
        Only return the JSON object with inferred requirements. Do not include explanations.
        """ 