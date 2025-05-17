import json
from utils import get_openai_client, get_openai_model
from prompt_manager import PromptManager

class ModuleDecisionMaker:
    """
    A class that decides which modules to activate based on the current conversation.
    Uses LLM to determine which modules are relevant to process the current user message.
    """
    
    def __init__(self, api_key=None, model=None):
        """
        Initialize the ModuleDecisionMaker.
        
        Args:
            api_key (str, optional): API key for LLM. Defaults to environment variable.
            model (str, optional): Model to use. Defaults to environment variable.
        """
        self.client = get_openai_client()
        self.model = model or get_openai_model()
        self.prompt_manager = PromptManager()
        self.conversation_history = []
        
    def decide_modules(self, user_message, conversation_history=None, current_stage="welcome"):
        """
        Decide which modules to activate for the current user message.
        
        Args:
            user_message (str): The current user message
            conversation_history (list, optional): Conversation history
            current_stage (str, optional): Current conversation stage
            
        Returns:
            dict: Dictionary with boolean values for each module
        """
        # Use provided conversation history or stored history
        history = conversation_history or self.conversation_history
        
        # Store the user message in conversation history
        if user_message not in [msg.get("content", "") for msg in history if msg.get("role") == "user"]:
            self.conversation_history.append({"role": "user", "content": user_message})
        
        # Create the prompt for module decision
        system_message = self._create_system_message(current_stage)
        
        # Prepare messages for the API call
        messages = [
            {"role": "system", "content": system_message}
        ]
        
        # Add conversation history (limited to last 4 messages to save tokens)
        if history:
            messages.extend(history[-4:])
        else:
            messages.append({"role": "user", "content": user_message})
        
        # Call API with optimal parameters for this task
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.1,  # Low temperature for more consistent decision making
            max_tokens=150    # Short response is enough for a JSON structure
        )
        
        # Extract and parse response
        try:
            response_text = response.choices[0].message.content
            # Find the JSON part of the response
            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}') + 1
            
            if start_idx >= 0 and end_idx > start_idx:
                json_str = response_text[start_idx:end_idx]
                module_decisions = json.loads(json_str)
            else:
                # Fallback if JSON parsing fails
                module_decisions = self._get_default_module_decisions()
                
        except (json.JSONDecodeError, IndexError):
            # Default to enabling all modules if parsing fails
            module_decisions = self._get_default_module_decisions()
        
        # Ensure all required keys are present
        for key in ["profile_extractor", "expertise_evaluator", "explicit_needs_extractor", 
                    "implicit_needs_inferrer", "test_drive_extractor"]:
            if key not in module_decisions:
                module_decisions[key] = True  # Default to True if missing
        
        # Apply stage-specific adjustments
        self._adjust_by_stage(module_decisions, current_stage)
        
        return module_decisions
    
    def _create_system_message(self, current_stage):
        """
        Create the system message for the module decision API call.
        
        Args:
            current_stage (str): Current conversation stage
            
        Returns:
            str: System message
        """
        # Get the module decision prompt
        module_decision_prompt = self.prompt_manager.templates.get("module_decision", {}).get("content", "")
        
        # Include the current stage for context
        stage_context = f"\n\nCurrent conversation stage: {current_stage}."
        
        # Add stage-specific guidance
        if current_stage == "welcome":
            stage_context += "\nIn the welcome stage, profile extraction and expertise evaluation are particularly important."
        elif current_stage == "profile_analysis":
            stage_context += "\nIn the profile analysis stage, continue extracting profile information and implicit needs."
        elif current_stage == "needs_analysis":
            stage_context += "\nIn the needs analysis stage, focus on explicit and implicit needs extraction."
        elif current_stage == "car_selection_confirmation":
            stage_context += "\nIn the car selection stage, evaluate expertise based on reactions and look for additional needs."
        elif current_stage in ["reservation4s", "reservation_confirmation"]:
            stage_context += "\nIn this reservation stage, the test drive extractor is critical."
        
        return module_decision_prompt + stage_context
    
    def _get_default_module_decisions(self):
        """
        Get default module decisions (all enabled).
        
        Returns:
            dict: Dictionary with all modules enabled
        """
        return {
            "profile_extractor": True,
            "expertise_evaluator": True,
            "explicit_needs_extractor": True,
            "implicit_needs_inferrer": True,
            "test_drive_extractor": True
        }
    
    def _adjust_by_stage(self, module_decisions, current_stage):
        """
        Adjust module decisions based on the current conversation stage.
        Some modules are critical in certain stages regardless of content.
        
        Args:
            module_decisions (dict): The current module decisions
            current_stage (str): Current conversation stage
        """
        # Always enable profile extractor in welcome and profile_analysis stages
        if current_stage in ["welcome", "profile_analysis"]:
            module_decisions["profile_extractor"] = True
        
        # Always enable needs extractors in needs_analysis stage
        if current_stage == "needs_analysis":
            module_decisions["explicit_needs_extractor"] = True
            module_decisions["implicit_needs_inferrer"] = True
        
        # Always enable test drive extractor in reservation stages
        if current_stage in ["reservation4s", "reservation_confirmation"]:
            module_decisions["test_drive_extractor"] = True 