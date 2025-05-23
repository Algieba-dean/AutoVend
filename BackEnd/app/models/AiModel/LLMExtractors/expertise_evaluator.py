import json
import openai
import os
from utils import get_openai_client, get_openai_model, timer_decorator, clean_thinking_output

# Define the path to the project's root directory if needed, or ensure correct relative paths
# For example, if LLMExtractors is a sub-module and Config is a sibling to its parent.
# CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
# CONFIG_PATH = os.path.join(CURRENT_DIR, "../Config/QueryLabels.json") 
# Fallback for general case, assuming Config is a sibling of the script's parent directory (LLMExtractors)

class ExpertiseEvaluator:
    """
    Module for evaluating user's expertise in car knowledge from chat messages.
    Uses OpenAI to analyze user messages and rate expertise on a scale of 0-10.
    """
    
    def __init__(self, api_key=None, model=None):
        """
        Initialize the ExpertiseEvaluator.
        
        Args:
            api_key (str, optional): OpenAI API key. Defaults to environment variable.
            model (str, optional): OpenAI model to use. Defaults to environment variable.
        """
        self.client = get_openai_client()
        self.model = model or get_openai_model()
        self.max_expertise_level = 3 # Default starting max, can be updated by LLM response
        
        # Construct the path to QueryLabels.json relative to this file's location
        config_file_path = os.path.join(os.path.dirname(__file__), "../Config/QueryLabels.json")
        
        if not os.path.exists(config_file_path):
            # Fallback if run from parent directory (e.g. AiModel) and Config is a direct subdir of it
            current_working_dir_config_path = "./Config/QueryLabels.json"
            if os.path.exists(current_working_dir_config_path):
                config_file_path = current_working_dir_config_path
            # else: the original __file__ based path will be used, and likely fail in open(), handled by try-except

        try:
            with open(config_file_path, "r") as f:
                self.query_labels = json.load(f)
        except FileNotFoundError as e:
            print(f"Error: QueryLabels.json not found in ExpertiseEvaluator. Attempted path: {os.path.abspath(config_file_path)}. Error: {e}")
            self.query_labels = {} # Default to empty dict if not found
            # Consider re-raising or more robust error handling if this file is critical
            # raise FileNotFoundError(f"QueryLabels.json is critical and was not found. Path: {os.path.abspath(config_file_path)}") from e
    
    @timer_decorator
    def evaluate_expertise(self, user_message):
        """
        Evaluate user's car expertise from their message.
        
        Args:
            user_message (str): The user's message to analyze
            
        Returns:
            dict: Dictionary containing expertise score (0-10)
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
            temperature=0.9
        )
        
        content = response.choices[0].message.content
        content = clean_thinking_output(content)
        # Parse and return the expertise score
        try:
            expertise_data = json.loads(content)
            if "expertise" in expertise_data:
                self.max_expertise_level = max(self.max_expertise_level, int(expertise_data["expertise"]))
            expertise_data["expertise"] = self.max_expertise_level

            return expertise_data
        except json.JSONDecodeError:
            return {"expertise": self.max_expertise_level}
    
    def _create_system_message(self):
        """Create the system message with instructions for the AI."""
        # Extract some key car terms from QueryLabels to help with evaluation
        car_terms = []
        for category, data in self.query_labels.items():
            car_terms.append(category)
            if "candidates" in data:
                car_terms.extend(data["candidates"][:3])  # Just add a few samples
        
        car_terms = ", ".join(car_terms[:50])  # Limit to a reasonable number of terms
        
        return f"""
        You are an AI assistant specializing in evaluating a user's expertise in automotive knowledge.
        
        Your task is to analyze the user's message and rate their car expertise on a scale of 0-10:
        - 0-3: Novice - Uses basic, non-technical language, asks simple questions
        - 4-6: Intermediate - Uses some industry terms correctly, shows familiarity with car categories
        - 7-8: Advanced - Uses technical terminology fluently, discusses specific car features with understanding
        - 9-10: Expert - Deep technical knowledge, discusses specialized automotive concepts, may use engineering terms
        
        Consider their use of terminology like: {car_terms}, and other automotive concepts.
        
        INSTRUCTIONS:
        1. Analyze the technical depth and accuracy of automotive terms used
        2. Consider the complexity of questions or statements made
        3. Note whether they show understanding of car specifications
        4. Return a single integer value from 0-10
        
        Return your evaluation as a JSON object: {{"expertise": "X"}} where X is the numeric score (0-10).
        """ 