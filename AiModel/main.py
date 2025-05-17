import os
import json
import time
import concurrent.futures
from utils import get_openai_client, get_openai_model
from profile_extractor import ProfileExtractor
from expertise_evaluator import ExpertiseEvaluator
from explicit_needs_extractor import ExplicitNeedsExtractor
from implicit_needs_inferrer import ImplicitNeedsInferrer
from test_drive_extractor import TestDriveExtractor
from model_query_module import CarModelQuery
from conversation_module import ConversationModule
from prompt_manager import PromptManager
from module_decision_maker import ModuleDecisionMaker
from batch_processor import BatchProcessor
from streaming_response_handler import ConsoleStreamHandler

class AutoVend:
    """
    Main AutoVend AI car sales assistant class.
    Integrates all modules to process user messages and generate responses.
    """
    
    def __init__(self, api_key=None, model=None, use_streaming=False):
        """
        Initialize the AutoVend assistant.
        
        Args:
            api_key (str, optional): OpenAI API key. Defaults to environment variable.
            model (str, optional): OpenAI model to use. Defaults to environment variable.
            use_streaming (bool): Whether to use streaming responses. Defaults to False.
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
        self.conversation_module = ConversationModule(api_key=api_key, model=self.model, use_streaming=use_streaming)
        
        # Initialize the module decision maker
        self.module_decision_maker = ModuleDecisionMaker(api_key=api_key, model=self.model)
        
        # Initialize batch processor
        self.batch_processor = BatchProcessor()
        
        # Initialize state
        self.current_stage = "welcome"
        self.user_profile = {}
        self.explicit_needs = {}
        self.implicit_needs = {}
        self.test_drive_info = {}
        self.matched_car_models = {}
        
        # Performance configuration
        self.use_streaming = use_streaming
        self.use_batch_processing = True
        
        # Create a thread pool executor
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=5)
    
    def process_message(self, user_message):
        """
        Process a user message through all modules in parallel and generate a response.
        
        Args:
            user_message (str): The user's message
            
        Returns:
            dict: Dictionary containing the assistant's response and all extracted data
        """
        start_time = time.time()
        
        # First, decide which modules to activate - using batch processor for better performance
        if self.use_batch_processing:
            module_decisions = self.batch_processor.process_module_decisions(user_message, self.current_stage)
        else:
            module_decisions = self.module_decision_maker.decide_modules(
                user_message, 
                self.conversation_module.conversation_history,
                self.current_stage
            )
        
        # Store futures and results
        futures = {}
        results = {
            "profile_info": {},
            "expertise_info": {},
            "explicit_needs_info": {},
            "implicit_needs_info": {},
            "test_drive_info": {}
        }
        
        # If batch processing is enabled, try to batch compatible extractions
        if self.use_batch_processing and sum(1 for v in module_decisions.values() if v) >= 2:
            # Extract data using batch processor
            batch_results = self.batch_processor.process_extraction_batch(
                user_message, 
                module_decisions
            )
            
            # Update results with batch results
            if "profile_extractor" in batch_results:
                results["profile_info"] = batch_results["profile_extractor"]
                
            if "expertise_evaluator" in batch_results:
                results["expertise_info"] = batch_results["expertise_evaluator"]
                
            if "explicit_needs_extractor" in batch_results:
                results["explicit_needs_info"] = batch_results["explicit_needs_extractor"]
                
            if "implicit_needs_inferrer" in batch_results:
                results["implicit_needs_info"] = batch_results["implicit_needs_inferrer"]
                
            if "test_drive_extractor" in batch_results:
                results["test_drive_info"] = batch_results["test_drive_extractor"]
        else:
            # Fall back to individual module processing for more complex cases
            # Only activate modules as determined by the decision maker
            if module_decisions.get("profile_extractor", True):
                futures["profile"] = self.executor.submit(self.profile_extractor.extract_profile, user_message)
            
            if module_decisions.get("expertise_evaluator", True):
                futures["expertise"] = self.executor.submit(self.expertise_evaluator.evaluate_expertise, user_message)
            
            if module_decisions.get("explicit_needs_extractor", True):
                futures["explicit_needs"] = self.executor.submit(self.explicit_needs_extractor.extract_explicit_needs, user_message)
            
            if module_decisions.get("implicit_needs_inferrer", True):
                futures["implicit_needs"] = self.executor.submit(self.implicit_needs_inferrer.infer_implicit_needs, user_message)
            
            if module_decisions.get("test_drive_extractor", True):
                futures["test_drive"] = self.executor.submit(self.test_drive_extractor.extract_test_drive_info, user_message)
            
            # Collect results from the futures
            if "profile" in futures:
                results["profile_info"] = futures["profile"].result()
            
            if "expertise" in futures:
                results["expertise_info"] = futures["expertise"].result() or {}
            
            if "explicit_needs" in futures:
                results["explicit_needs_info"] = futures["explicit_needs"].result()
            
            if "implicit_needs" in futures:
                results["implicit_needs_info"] = futures["implicit_needs"].result()
            
            if "test_drive" in futures:
                results["test_drive_info"] = futures["test_drive"].result()
        
        # Update state with results
        if results["profile_info"]:
            self.user_profile.update(results["profile_info"])
        
        if "expertise" in results["expertise_info"]:
            self.user_profile["expertise"] = results["expertise_info"]["expertise"]
        
        if results["explicit_needs_info"]:
            self.explicit_needs.update(results["explicit_needs_info"])
        
        if results["implicit_needs_info"]:
            self.implicit_needs.update(results["implicit_needs_info"])
        
        if results["test_drive_info"]:
            self.test_drive_info.update(results["test_drive_info"])
            # If test drive info is being collected, update stage
            if self.current_stage in ["car_selection_confirmation", "needs_analysis"] and len(results["test_drive_info"]) > 0:
                self.current_stage = "reservation4s"
        
        # Once we have needs information, query matching car models
        # This depends on the results of the extractors, so it cannot be parallelized with them
        if self.explicit_needs or self.implicit_needs:
            # Combine explicit and implicit needs
            combined_needs = {**self.explicit_needs, **self.implicit_needs}
            # Use existing query_car_model method
            car_models = self.car_model_query.query_car_model(combined_needs)
            # Construct matched car models information
            self.matched_car_models = {
                "matched_models": [
                    self.car_model_query.get_car_model_info(model) for model in car_models
                ]
            }
                
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
            self.current_stage
        )
        
        # Calculate processing time
        processing_time = time.time() - start_time
        
        # Return complete result with all data
        return {
            "response": response,
            "extracted_profile": results["profile_info"],
            "expertise_evaluation": results["expertise_info"] if "expertise" in results["expertise_info"] else {},
            "explicit_needs": results["explicit_needs_info"],
            "implicit_needs": results["implicit_needs_info"],
            "test_drive_info": results["test_drive_info"],
            "matched_car_models": self.matched_car_models,
            "current_stage": self.current_stage,
            "accumulated_profile": self.user_profile,
            "accumulated_explicit_needs": self.explicit_needs,
            "accumulated_implicit_needs": self.implicit_needs,
            "accumulated_test_drive_info": self.test_drive_info,
            "activated_modules": module_decisions,
            "processing_time": processing_time
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
        self.matched_car_models = {}
        self.conversation_module.clear_history()
    
    def __del__(self):
        """Clean up resources on object deletion."""
        self.executor.shutdown(wait=False)


# Example usage
if __name__ == "__main__":
    # Initialize the AutoVend assistant
    assistant = AutoVend(use_streaming=False)
    
    print("AutoVend AI Car Sales Assistant")
    print("Type 'exit' to quit")
    print("Type 'stream on' to enable streaming mode")
    print("Type 'stream off' to disable streaming mode")
    print("-" * 50)
    
    while True:
        user_input = input("\nYou: ")
        if user_input.lower() == 'exit':
            break
        
        # Handle streaming mode commands
        if user_input.lower() == 'stream on':
            assistant.use_streaming = True
            assistant.conversation_module.use_streaming = True
            print("Streaming mode enabled.")
            continue
        elif user_input.lower() == 'stream off':
            assistant.use_streaming = False
            assistant.conversation_module.use_streaming = False
            print("Streaming mode disabled.")
            continue
            
        # Start timing
        start_time = time.time()
        
        # Process the message and get results
        result = assistant.process_message(user_input)
        
        # End timing (note: with streaming, response appears earlier)
        total_time = time.time() - start_time
        
        # Debug information - comment out for production
        print("\n--- Debug Info ---")
        print(f"Stage: {result['current_stage']}")
        print(f"Processing time: {result['processing_time']:.2f}s (total: {total_time:.2f}s)")
        print(f"Activated modules: {json.dumps(result['activated_modules'], indent=2)}")
        
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
        
        if result.get('matched_car_models', {}).get('matched_models'):
            print(f"Matched Car Models: {json.dumps(result['matched_car_models']['matched_models'], ensure_ascii=False)[:200]}...")
            
        print("-" * 50) 