import json
from utils import get_openai_client, get_openai_model
from model_client_manager import ModelClientManager

class BatchProcessor:
    """
    Process multiple LLM tasks in a single API call.
    Reduces overhead and improves response time for related tasks.
    """
    
    def __init__(self):
        """Initialize the batch processor"""
        self.client_manager = ModelClientManager()
        self.default_model = get_openai_model()
        
    def process_module_decisions(self, user_message, current_stage):
        """
        Process module activation decisions in a batch request.
        
        Args:
            user_message (str): User message
            current_stage (str): Current conversation stage
            
        Returns:
            dict: Module decisions
        """
        # Create a specialized prompt for module decisions
        prompt = f"""You are analyzing a user message to determine which processing modules should be activated. Based on the message content and conversation stage, determine which of the following modules need to be activated:

1. PROFILE_EXTRACTOR: Extract user profile information (name, age, occupation, family size, etc.)
2. EXPERTISE_EVALUATOR: Evaluate user's car knowledge level
3. EXPLICIT_NEEDS_EXTRACTOR: Extract directly stated car requirements
4. IMPLICIT_NEEDS_INFERRER: Infer implied car requirements
5. TEST_DRIVE_EXTRACTOR: Extract test drive reservation information

Current conversation stage: {current_stage}

User message: "{user_message}"

Respond with a JSON object containing true/false values for each module:
"""
        
        # Make a targeted API call
        response = self.client_manager.get_client().chat.completions.create(
            model=self.default_model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=150
        )
        
        response_text = response.choices[0].message.content
        
        try:
            # Extract the JSON part
            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}') + 1
            
            if start_idx >= 0 and end_idx > start_idx:
                json_str = response_text[start_idx:end_idx]
                decisions = json.loads(json_str)
            else:
                # Default decisions
                decisions = self._get_default_decisions()
        except (json.JSONDecodeError, IndexError):
            decisions = self._get_default_decisions()
            
        # Ensure all required keys are present
        for key in ["profile_extractor", "expertise_evaluator", "explicit_needs_extractor", 
                   "implicit_needs_inferrer", "test_drive_extractor"]:
            if key not in decisions:
                decisions[key] = True
                
        return decisions
    
    def process_extraction_batch(self, user_message, extractions_needed):
        """
        Process multiple extractions in a single call when possible.
        
        Args:
            user_message (str): User message
            extractions_needed (dict): Dictionary of needed extractions
            
        Returns:
            dict: Results for each extraction
        """
        # Create tasks that can be processed together
        tasks = []
        task_types = []
        
        extraction_prompts = {
            "profile_extractor": "Extract user profile information like name, age, gender, occupation, family situation, etc. Format as JSON.",
            "expertise_evaluator": "Evaluate the user's car knowledge level on a scale of 0-10. Format as JSON with the key 'expertise'.",
            "explicit_needs_extractor": "Extract explicitly stated car requirements like type, brand, features, price range, etc. Format as JSON.",
            "implicit_needs_extractor": "Infer implied car requirements based on lifestyle, preferences, etc. Format as JSON.",
            "test_drive_extractor": "Extract test drive information like preferred date, time, location, car model, etc. Format as JSON."
        }
        
        # Create a combined task prompt
        system_prompt = "Process multiple extraction tasks on the following user message. For each task, return a JSON formatted result."
        
        # Add active extractions
        for ext_type, needed in extractions_needed.items():
            if needed and ext_type in extraction_prompts:
                task_types.append(ext_type)
                tasks.append(extraction_prompts[ext_type])
        
        # If no tasks, return empty results
        if not tasks:
            return {}
            
        # Create the combined prompt
        combined_prompt = f"USER MESSAGE: '{user_message}'\n\n"
        for i, task in enumerate(tasks):
            combined_prompt += f"TASK {i+1}: {task}\n\n"
            
        # Make a single API call
        response = self.client_manager.get_client().chat.completions.create(
            model=self.default_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": combined_prompt}
            ],
            temperature=0.2,
            max_tokens=1000
        )
        
        response_text = response.choices[0].message.content
        
        # Parse the results - this is complex as we need to extract multiple JSON objects
        return self._parse_batch_results(response_text, task_types)
    
    def _parse_batch_results(self, response_text, task_types):
        """Parse batch results from response text"""
        results = {}
        
        # Look for task indicators and JSON objects
        current_task = None
        json_content = ""
        in_json = False
        
        # Split by lines for easier processing
        lines = response_text.split('\n')
        
        for i, line in enumerate(lines):
            # Check for task indicators
            for j, task_type in enumerate(task_types):
                if f"TASK {j+1}" in line or task_type.upper() in line:
                    # Save previous task if any
                    if current_task and json_content:
                        try:
                            results[current_task] = json.loads(json_content)
                        except json.JSONDecodeError:
                            pass
                    # Start new task
                    current_task = task_type
                    json_content = ""
                    in_json = False
            
            # Check for JSON start/end
            if '{' in line:
                in_json = True
            
            if in_json:
                json_content += line
            
            if in_json and '}' in line and current_task:
                # Try to extract just the JSON part
                try:
                    start = json_content.find('{')
                    end = json_content.rfind('}') + 1
                    if start >= 0 and end > start:
                        json_str = json_content[start:end]
                        results[current_task] = json.loads(json_str)
                except json.JSONDecodeError:
                    pass
                in_json = False
        
        # Process any remaining JSON content
        if current_task and json_content and current_task not in results:
            try:
                start = json_content.find('{')
                end = json_content.rfind('}') + 1
                if start >= 0 and end > start:
                    json_str = json_content[start:end]
                    results[current_task] = json.loads(json_str)
            except json.JSONDecodeError:
                pass
        
        return results
                
    def _get_default_decisions(self):
        """Get default module decisions"""
        return {
            "profile_extractor": True,
            "expertise_evaluator": True, 
            "explicit_needs_extractor": True,
            "implicit_needs_inferrer": True,
            "test_drive_extractor": True
        } 