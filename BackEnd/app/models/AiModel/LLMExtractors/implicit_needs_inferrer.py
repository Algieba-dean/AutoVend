import json
import openai
import os
from utils import get_openai_client, get_openai_model, timer_decorator, clean_thinking_output

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
        
        # Load car query labels from the Config directory
        config_file_path = os.path.join(os.path.dirname(__file__), "../Config/QueryLabels.json")

        if not os.path.exists(config_file_path):
            # Fallback if run from parent directory (e.g. AiModel) and Config is a direct subdir of it
            config_file_path = "./Config/QueryLabels.json"

        try:
            with open(config_file_path, "r") as f:
                self.query_labels = json.load(f)
        except FileNotFoundError as e:
            print(f"Error: QueryLabels.json not found in ImplicitNeedsInferrer. Attempted path: {os.path.abspath(config_file_path)}. Error: {e}")
            self.query_labels = {}
            # raise FileNotFoundError(f"QueryLabels.json is critical and was not found. Path: {os.path.abspath(config_file_path)}") from e
    
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
            response_format={"type": "json_object"},
            temperature=0.1,
            seed=213
        )
        # Parse and return the inferred needs
        try:
            content = response.choices[0].message.content
            content = clean_thinking_output(content)
            inferred_needs = json.loads(content)
            return self._validate_and_filter_needs(inferred_needs)
        except json.JSONDecodeError:
            return {}
    
    def _validate_and_filter_needs(self, inferred_needs):
        """
        Validate inferred needs against QueryLabels and filter out invalid ones.
        Only keeps keys that have implicit_support: true in QueryLabels.
        """
        if not isinstance(inferred_needs, dict):
            return {}

        valid_needs = {}
        for key, value in inferred_needs.items():
            if key not in self.query_labels:
                # Key not defined in QueryLabels, skip
                continue

            label_data = self.query_labels[key]
            # Crucially, for implicit needs, we only consider if implicit_support is true
            if not label_data.get("implicit_support") is True:
                continue

            if "candidates" not in label_data:
                # Key is valid for implicit support but has no candidates, skip.
                continue

            candidates = label_data["candidates"]
            
            if isinstance(value, list):
                # If value is a list, filter its items
                valid_list_values = [v for v in value if v in candidates]
                if valid_list_values:
                    # If only one valid value remains, and it's not a 'range' type, use the value directly.
                    # Range types are often inherently list-like in their representation even if a single range is chosen.
                    if len(valid_list_values) == 1 and label_data.get("value_type") != "range":
                        valid_needs[key] = valid_list_values[0]
                    else:
                        valid_needs[key] = valid_list_values
            elif isinstance(value, str):
                # If value is a string, check if it's in candidates
                if value in candidates:
                    valid_needs[key] = value
            # Other types are ignored
            
        return valid_needs

    def _create_system_message(self):
        """Create the system message with instructions for the AI."""
        # Prepare simplified labels structure for the prompt
        labels_structure = {}
        for label, data in self.query_labels.items():
            # Only include labels that have implicit_support set to true
            if data.get("implicit_support") is True:
                if "candidates" in data: # Ensure candidates exist, as per original logic
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
        - ONLY infer requirements that are NOT explicitly mentioned but can be logically deduced.
        - Make reasonable inferences based on lifestyle, family situation, mentioned activities, etc.
        - For each inferred requirement, use the exact key and allowed value from the provided structure.
        - Return the inferred requirements as a flat JSON object.
        - If no implicit requirements can be inferred, return an empty object {{}}.
        - Use high confidence inferences only - don't overreach in your analysis.
        
        EXAMPLES:
        - For "I have a big family with 5 children", infer: {{"family_friendliness": "high", "size": "large", "seat_layout": "7-seat"}}
        - For "I live in a mountain area with lots of snow", infer: {{"off_road_capability": "high", "cold_resistance": "high"}}
        - For "I'm not good at parking", infer: {{"remote_parking": "yes", "auto_parking": "yes"}}

        NEGATIVE EXAMPLES:
        - For "I wanna buy a suv", do not infer: {{"size": "large"}} as it's not related to the user's statement
        - For "I'd like to have an suv below 30000 dollars", do not infer:{{"highway_long_distance":"yes}}, as it's not related to the user's statement
        - For "I'd like a battery electric car, and maybe a germany brand SUV", do not infer:{{"size": "large","highway_long_distance": "yes","family_friendliness": "medium","smartness": "high"}}, as it's not related to user's statement
        
        Only return the JSON object with inferred requirements. Do not include explanations.
        """ 