import os
import json
import time
import concurrent.futures
from utils import Config, clear_cache
from prompt_manager import PromptManager
from batch_processor import BatchProcessor
from profile_extractor import ProfileExtractor
from expertise_evaluator import ExpertiseEvaluator
from explicit_needs_extractor import ExplicitNeedsExtractor
from implicit_needs_inferrer import ImplicitNeedsInferrer
from test_drive_extractor import TestDriveExtractor
from model_query_module import CarModelQuery
from conversation_module import ConversationModule
from module_decision_maker import ModuleDecisionMaker

class AutoVend:
    """
    Main AutoVend AI car sales assistant class.
    Integrates all modules to process user messages and generate responses.
    Uses lazy loading for better memory usage and faster initialization.
    """
    
    def __init__(self, api_key=None, model=None, use_streaming=False):
        """
        Initialize the AutoVend assistant.
        
        Args:
            api_key (str, optional): OpenAI API key. Defaults to environment variable.
            model (str, optional): OpenAI model to use. Defaults to environment variable.
            use_streaming (bool): Whether to use streaming responses. Defaults to False.
        """
        # Get configuration instance
        self.config = Config.get_instance()
        self.config.use_streaming = use_streaming
        
        # Set model if provided
        self.model = model or self.config.model
        
        # Initialize state
        self.current_stage = "welcome"
        self.previous_stage = ""
        self.user_profile = {
            "phone_number": "",
            "age": "",
            "user_title": "",
            "name": "",
            "target_driver": "",
            "expertise": "",
            "additional_information": {
                "family_size": "",
                "price_sensitivity": "",
                "residence": "",
                "parking_conditions": ""
            },
            "connection_information": {
                "connection_phone_number": "",
                "connection_id_relationship": ""
            }
        }
        self.explicit_needs = dict()
        self.implicit_needs = dict()
        self.needs = {
            "explicit": self.explicit_needs,
            "implicit": self.implicit_needs
        }
        self.test_drive_info = {
            "test_driver": "",
            "reservation_date": "",
            "reservation_time": "",
            "reservation_location": "",
            "reservation_phone_number": "",
            "salesman": ""
        }
        # matched_car_models should not be accumulated updated, only use current latest list
        self.matched_car_models = list()

        # matched car infos should be updated here, and use only for conversation agent
        self.matched_car_model_infos = list()
        
        # Performance configuration
        self.use_streaming = use_streaming
        self.use_batch_processing = self.config.use_batch
        
        # Initialize batch processor (lightweight)
        self._batch_processor = BatchProcessor()
        
        self._profile_extractor = ProfileExtractor(model=self.model)
        self._expertise_evaluator = ExpertiseEvaluator(model=self.model)
        self._explicit_needs_extractor = ExplicitNeedsExtractor(model=self.model)
        self._implicit_needs_inferrer = ImplicitNeedsInferrer(model=self.model)
        self._test_drive_extractor = TestDriveExtractor(model=self.model)
        self._car_model_query = CarModelQuery()
        self._conversation_module = ConversationModule(model=self.model, use_streaming=self.use_streaming)
        self._module_decision_maker = ModuleDecisionMaker(model=self.model)
        
        # Create a thread pool executor with optimal worker count
        self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=self.config.max_workers)
    @property
    def profile_extractor(self):
        return self._profile_extractor
    
    @property
    def expertise_evaluator(self):
        return self._expertise_evaluator
    
    @property
    def explicit_needs_extractor(self):
        return self._explicit_needs_extractor
    
    @property
    def implicit_needs_inferrer(self):
        return self._implicit_needs_inferrer
    
    @property
    def test_drive_extractor(self):
        return self._test_drive_extractor
    
    @property
    def car_model_query(self):
        return self._car_model_query
    
    @property
    def conversation_module(self):
        return self._conversation_module
    
    @property
    def module_decision_maker(self):
        return self._module_decision_maker
    @property
    def batch_processor(self):
        return self._batch_processor
    
    @property
    def executor(self):
        return self._executor

    def update_extraction(self, results:dict):
        """
        Process a user message through all modules in parallel and generate a response.

        Args:
            results (dict): the extracted result after multi information extraction

        Returns:
        """
        # Update state with results
        if results["profile_info"]:
            self.user_profile.update(results["profile_info"])

        # use max expertise value, no need to use current expertise value
        if "expertise" in results["expertise_info"]:
            self.user_profile["expertise"] = results["expertise_info"]["expertise"]

        if results["explicit_needs_info"]:
            self.explicit_needs.update(results["explicit_needs_info"])

        if results["implicit_needs_info"]:
            self.implicit_needs.update(results["implicit_needs_info"])

        if results["test_drive_info"]:
            self.test_drive_info.update(results["test_drive_info"])
            # If test drive info is being collected, update stage
            if self.current_stage in ["car_selection_confirmation", "needs_analysis"] and len(
                    results["test_drive_info"]) > 0:
                self.current_stage = "reservation4s"
    def query_matched_car_models(self):
        ...
    
    def process_message(self, user_message, profile:dict, needs:dict,matched_car_models:dict,stage:dict,reservation_info:dict):
        """
        Process a user message through all modules in parallel and generate a response.
        
        Args:
            user_message (str): The user's message
            
        Returns:
            dict: Dictionary containing the assistant's response and all extracted data
        """
        start_time = time.time()
        
        # First, decide which modules to activate - using batch processor for better performance

        # current stage, means stage before response
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
        
        # Count how many modules are activated
        activated_count = sum(1 for v in module_decisions.values() if v)
        
        # If batch processing is enabled and multiple modules are activated, use batch
        if self.use_batch_processing and activated_count >= 2:
            # Extract data using batch processor
            batch_results = self.batch_processor.process_extraction_batch(
                user_message, 
                module_decisions
            )
            
            # Update results with batch results
            for module, result in batch_results.items():
                if module == "profile_extractor":
                    results["profile_info"] = result
                elif module == "expertise_evaluator":
                    results["expertise_info"] = result
                elif module == "explicit_needs_extractor": 
                    results["explicit_needs_info"] = result
                elif module == "implicit_needs_inferrer":
                    results["implicit_needs_info"] = result
                elif module == "test_drive_extractor":
                    results["test_drive_info"] = result
        else:
            # Fall back to individual module processing 
            # Use a dictionary to map module names to their processing functions
            extraction_functions = {}
            
            # Only prepare functions for activated modules
            if module_decisions.get("profile_extractor", True):
                extraction_functions["profile"] = lambda: self.profile_extractor.extract_profile(user_message)
            
            if module_decisions.get("expertise_evaluator", True):
                extraction_functions["expertise"] = lambda: self.expertise_evaluator.evaluate_expertise(user_message)
            
            if module_decisions.get("explicit_needs_extractor", True):
                extraction_functions["explicit_needs"] = lambda: self.explicit_needs_extractor.extract_explicit_needs(user_message)
            
            if module_decisions.get("implicit_needs_inferrer", True):
                extraction_functions["implicit_needs"] = lambda: self.implicit_needs_inferrer.infer_implicit_needs(user_message)
            
            if module_decisions.get("test_drive_extractor", True):
                extraction_functions["test_drive"] = lambda: self.test_drive_extractor.extract_test_drive_info(user_message)
            
            # Submit all functions to the executor
            for name, func in extraction_functions.items():
                futures[name] = self.executor.submit(func)
            
            # Collect results from futures
            for name, future in futures.items():
                if name == "profile":
                    results["profile_info"] = future.result() or {}
                elif name == "expertise":
                    results["expertise_info"] = future.result() or {}
                elif name == "explicit_needs":
                    results["explicit_needs_info"] = future.result() or {}
                elif name == "implicit_needs":
                    results["implicit_needs_info"] = future.result() or {}
                elif name == "test_drive":
                    results["test_drive_info"] = future.result() or {}
        

        # Once we have needs information, query matching car models
        self.update_extraction(results)

        # query matched car models according both explict and implicit needs
        self.query_matched_car_models()

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
        clear_cache()
        if self._conversation_module:
            self.conversation_module.clear_history()
    
    def __del__(self):
        """Clean up resources on object deletion."""
        if self._executor:
            self._executor.shutdown(wait=False)


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