import os
import json
import concurrent.futures
from utils import get_openai_client, get_openai_model, timer_decorator
from profile_extractor import ProfileExtractor
from expertise_evaluator import ExpertiseEvaluator
from explicit_needs_extractor import ExplicitNeedsExtractor
from implicit_needs_inferrer import ImplicitNeedsInferrer
from test_drive_extractor import TestDriveExtractor
from model_query_module import CarModelQuery
from conversation_module import ConversationModule
from prompt_manager import PromptManager

class AutoVend:
    """
    Main AutoVend AI car sales assistant class.
    Integrates all modules to process user messages and generate responses.
    """
    
    def __init__(self, api_key=None, model=None):
        """
        Initialize the AutoVend assistant.
        
        Args:
            api_key (str, optional): OpenAI API key. Defaults to environment variable.
            model (str, optional): OpenAI model to use. Defaults to environment variable.
        """
        # Get OpenAI model name
        self.model = model or get_openai_model()
        
        # Initialize all modules
        self.profile_extractor = ProfileExtractor(api_key=api_key, model=self.model)
        self.expertise_evaluator = ExpertiseEvaluator(api_key=api_key, model=self.model)
        self.explicit_needs_extractor = ExplicitNeedsExtractor(api_key=api_key, model=self.model)
        self.implicit_needs_inferrer = ImplicitNeedsInferrer(api_key=api_key, model=self.model)
        self.test_drive_extractor = TestDriveExtractor(api_key=api_key, model=self.model)
        self.car_model_query = CarModelQuery()
        self.conversation_module = ConversationModule(api_key=api_key, model=self.model)
        
        # Initialize state
        self.current_stage = "welcome"
        self.user_profile = {}
        self.explicit_needs = {}
        self.implicit_needs = {}
        self.test_drive_info = {}
        self.matched_car_models = []
        self.matched_car_model_infos = []
        
        # Create a thread pool executor
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=5)
    
    @timer_decorator
    def process_message(self, user_message):
        """
        Process a user message through all modules in parallel and generate a response.
        
        Args:
            user_message (str): The user's message
            
        Returns:
            dict: Dictionary containing the assistant's response and all extracted data
        """
        # Use thread pool to run all extractors in parallel
        future_profile = self.executor.submit(self.profile_extractor.extract_profile, user_message)
        future_expertise = self.executor.submit(self.expertise_evaluator.evaluate_expertise, user_message)
        future_explicit_needs = self.executor.submit(self.explicit_needs_extractor.extract_explicit_needs, user_message)
        future_implicit_needs = self.executor.submit(self.implicit_needs_inferrer.infer_implicit_needs, user_message)
        future_test_drive = self.executor.submit(self.test_drive_extractor.extract_test_drive_info, user_message)
        
        # Wait for all futures to complete and collect results
        profile_info = future_profile.result()
        expertise_info = future_expertise.result()
        explicit_needs_info = future_explicit_needs.result()
        implicit_needs_info = future_implicit_needs.result()
        test_drive_info = future_test_drive.result()
        
        # Update state with results
        if profile_info:
            self.user_profile.update(profile_info)
        
        if expertise_info and "expertise" in expertise_info:
            self.user_profile["expertise"] = expertise_info["expertise"]
        
        if explicit_needs_info:
            self.explicit_needs.update(explicit_needs_info)
        
        if implicit_needs_info:
            self.implicit_needs.update(implicit_needs_info)
        
        if test_drive_info:
            self.test_drive_info.update(test_drive_info)
            # If test drive info is being collected, update stage
            if self.current_stage in ["car_selection_confirmation", "needs_analysis"] and len(test_drive_info) > 0:
                self.current_stage = "reservation4s"
        
        # Once we have needs information, query matching car models
        # This depends on the results of the extractors, so it cannot be parallelized with them
        if self.explicit_needs or self.implicit_needs:
            # Combine explicit and implicit needs
            combined_needs = {**self.explicit_needs, **self.implicit_needs}
            # Use existing query_car_model method
            car_models = self.car_model_query.query_car_model(combined_needs)
            # Construct matched car models information
            self.matched_car_models = car_models
            self.matched_car_model_infos = [self.car_model_query.get_car_model_info(model) for model in car_models]
                
        # Determine next stage based on current information
        self._update_stage()
        
        # Generate response (this still needs to be sequential after we have all the extracted info)
        response = self.conversation_module.generate_response(
            user_message,
            self.user_profile,
            self.explicit_needs,
            self.implicit_needs,
            self.test_drive_info,
            self.matched_car_models,
            self.matched_car_model_infos,
            self.current_stage
        )
        
        # Return complete result with all data
        return {
            "response": response,
            "extracted_profile": profile_info,
            "expertise_evaluation": expertise_info if "expertise" in expertise_info else {},
            "explicit_needs": explicit_needs_info,
            "implicit_needs": implicit_needs_info,
            "test_drive_info": test_drive_info,
            "matched_car_models": self.matched_car_models,
            "current_stage": self.current_stage,
            "accumulated_profile": self.user_profile,
            "accumulated_explicit_needs": self.explicit_needs,
            "accumulated_implicit_needs": self.implicit_needs,
            "accumulated_test_drive_info": self.test_drive_info
        }
    
    def _update_stage(self):
        """Update the conversation stage based on current information."""
        # Basic stage progression logic
        if self.current_stage == "welcome":
            # If we have some profile info but not enough about car needs
            if self.user_profile and len(self.user_profile) >= 2:
                self.current_stage = "profile_analysis"
        
        elif self.current_stage == "profile_analysis":
            # If we have enough profile info and some needs are identified
            if len(self.user_profile) >= 3 and (self.explicit_needs or self.implicit_needs):
                self.current_stage = "needs_analysis"
        
        elif self.current_stage == "needs_analysis":
            # If we have a good amount of needs identified and matched car models
            if len(self.explicit_needs) + len(self.implicit_needs) >= 5 and self.matched_car_models.get("matched_models"):
                self.current_stage = "car_selection_confirmation"
        
        elif self.current_stage == "reservation4s":
            # If we have most test drive details
            if len(self.test_drive_info) >= 4:
                self.current_stage = "reservation_confirmation"
        
        elif self.current_stage == "reservation_confirmation":
            # If all test drive details are complete
            if len(self.test_drive_info) >= 5:
                self.current_stage = "farewell"
    
    def get_car_model_details(self, model_name):
        """
        Get detailed information about a specific car model.
        
        Args:
            model_name (str): Name of the car model
            
        Returns:
            dict: Dictionary containing detailed information about the car model
        """
        return self.car_model_query.get_car_model_info(model_name)
    
    def reset(self):
        """Reset the assistant state."""
        self.current_stage = "welcome"
        self.user_profile = {}
        self.explicit_needs = {}
        self.implicit_needs = {}
        self.test_drive_info = {}
        self.matched_car_models = []
        self.matched_car_model_infos = []
        self.conversation_module.clear_history()
    
    def __del__(self):
        """Clean up resources on object deletion."""
        self.executor.shutdown(wait=False)


# Example usage
if __name__ == "__main__":
    # Initialize the AutoVend assistant
    assistant = AutoVend()
    
    print("AutoVend AI Car Sales Assistant")
    print("Type 'exit' to quit")
    print("-" * 50)
    
    while True:
        user_input = input("\nYou: ")
        if user_input.lower() == 'exit':
            break
        
        # Process the message and get results
        result = assistant.process_message(user_input)
        
        # Print the assistant's response
        print(f"\nAutoVend: {result['response']}")
        
        # Debug information - comment out for production
        print("\n--- Debug Info ---")
        print(f"Stage: {result['current_stage']}")
        
        if result['extracted_profile']:
            print(f"Extracted Profile: {json.dumps(result['extracted_profile'], ensure_ascii=False)}")
        
        if result.get('expertise_evaluation'):
            print(f"Expertise: {json.dumps(result['expertise_evaluation'], ensure_ascii=False)}")
            
        if result['explicit_needs']:
            print(f"Explicit Needs: {json.dumps(result['explicit_needs'], ensure_ascii=False)}")
            
        if result['implicit_needs']:
            print(f"Implicit Needs: {json.dumps(result['implicit_needs'], ensure_ascii=False)}")
            
        if result['test_drive_info']:
            print(f"Test Drive Info: {json.dumps(result['test_drive_info'], ensure_ascii=False)}")
        
        if result.get('matched_car_models'):
            print(f"Matched Car Models: {json.dumps(result['matched_car_models'], ensure_ascii=False)[:200]}...")
            
        print("-" * 50) 