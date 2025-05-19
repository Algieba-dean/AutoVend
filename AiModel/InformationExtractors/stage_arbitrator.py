import json
from typing import List, Dict, Any, Optional, Set
import re


class StageArbitrator:
    """
    StageArbitrator is responsible for determining the current stage of the conversation
    based on the user's profile, needs, matched car models, reservation info, and current input.
    """

    # Define all possible stages
    STAGES = {
        "initial",
        "welcome",
        "profile_analysis",
        "needs_analysis",
        "car_selection_confirmation",
        "reservation4s",
        "reservation_confirmation",
        "farewell"
    }

    def __init__(self):
        """Initialize the StageArbitrator with default values."""
        self.previous_stage = "initial"
        self.current_stage = "initial"
        self.stage_history = ["initial"]
        
    def _is_profile_complete(self, profile: Dict[str, Any]) -> bool:
        """Check if the essential profile information is complete."""
        if not profile:
            return False
            
        required_fields = ["user_title", "name", "target_driver"]
        for field in required_fields:
            if field not in profile or not profile[field]:
                return False
                
        return True
        
    def _is_reservation_info_complete(self, reservation_info: Dict[str, Any]) -> bool:
        """Check if the reservation information is complete."""
        if not reservation_info:
            return False
            
        required_fields = [
            "test_driver", 
            "reservation_date", 
            "selected_car_model",
            "reservation_time", 
            "reservation_location", 
            "reservation_phone_number"
        ]
        
        for field in required_fields:
            if field not in reservation_info or not reservation_info[field]:
                return False
                
        return True
        
    def _contains_needs_keywords(self, user_input: str) -> bool:
        """Check if the user input contains keywords related to needs analysis."""
        needs_keywords = [
            # General needs expressions
            "need", "want", "like", "hope", "expect", "consider", 
            "purchase", "buy", "looking for", "interested in", "prefer", "would like",
            
            # Price related
            "budget", "price", "cost", "affordable", "cheap", "economy", "expensive",
            "mid-range", "high-end", "luxury", "below 10,000", "10,000", "20,000", "30,000",
            "40,000", "60,000", "100,000", "prize",
            
            # Vehicle categories
            "sedan", "suv", "mpv", "sports car", "crossover", "compact", "mid-size",
            "large", "small", "b-segment", "c-segment", "d-segment", "off-road",
            "all-terrain", "two-door", "four-door", "convertible", "hardtop",
            
            # Brand related
            "brand", "european", "american", "asian", "germany", "france", "united kingdom",
            "usa", "japan", "korea", "china", "volkswagen", "audi", "porsche", "bentley",
            "bmw", "mercedes-benz", "peugeot", "jaguar", "land rover", "volvo", "chevrolet",
            "buick", "ford", "tesla", "toyota", "honda", "nissan", "mazda", "hyundai", 
            "byd", "geely", "nio", "xpeng",
            
            # Powertrain types
            "electric", "gas", "hybrid", "gasoline engine", "diesel engine", 
            "hybrid electric vehicle", "plug-in hybrid", "battery electric vehicle", "range-extended",
            
            # Space and size
            "space", "size", "passenger space", "trunk volume", "cargo", "wheelbase",
            "small", "medium", "large", "spacious", "chassis height", "ride height",
            
            # Performance
            "performance", "power", "horsepower", "motor power", "battery capacity",
            "fuel tank", "acceleration", "top speed", "zero to hundred", "torque",
            "slow", "fast", "extreme", "high performance",
            
            # Efficiency
            "fuel efficiency", "economy", "consumption", "fuel consumption", 
            "electric consumption", "range", "driving range", "above 800km", "400-800km",
            "300-400km", "endurance", "efficiency",
            
            # Drive and handling
            "drive", "front-wheel drive", "rear-wheel drive", "all-wheel drive",
            "suspension", "passability", "off-road capability", "handling",
            
            # Features
            "safety", "features", "technology", "airbag", "abs", "esp", "leather", "fabric",
            "noise insulation", "voice interaction", "ota updates", "autonomous driving",
            "adaptive cruise control", "traffic jam assist", "emergency braking",
            "lane keep assist", "remote parking", "auto parking", "blind spot detection",
            
            # Usage scenarios
            "family", "city commuting", "highway", "long distance", "off-road",
            "cargo capability", "cold resistance", "heat resistance", "usability",
            "comfort", "smartness", "family friendliness"
        ]
        
        user_input_lower = user_input.lower()
        for keyword in needs_keywords:
            if keyword.lower() in user_input_lower:
                return True
                
        return False
        
    def _contains_car_selection_keywords(self, user_input: str) -> bool:
        """Check if the user input contains keywords related to car selection."""
        selection_keywords = [
            "choose", "select", "this model", "that model", "this one", "that one",
            "confirm", "go with", "sounds good", "looks good", "satisfied",
            "like this", "interested in", "prefer this", "this car",
            "this vehicle", "that vehicle", "decide on", "decided",
            "perfect", "ideal", "right for me", "matches my needs",
            "good choice", "great option"
        ]
        
        user_input_lower = user_input.lower()
        for keyword in selection_keywords:
            if keyword.lower() in user_input_lower:
                return True
                
        return False
        
    def _contains_test_drive_keywords(self, user_input: str) -> bool:
        """Check if the user input contains keywords related to test drive."""
        test_drive_keywords = [
            "test drive", "drive", "experience", "appointment", "schedule",
            "booking", "reserve", "when", "where", "dealership", "dealer",
            "store", "location", "phone", "contact", "available", "availability",
            "time", "date", "visit", "try", "try out", "feel",
            "behind the wheel", "drive it", "check it out", "see it in person",
            "book a slot", "test it"
        ]
        
        user_input_lower = user_input.lower()
        for keyword in test_drive_keywords:
            if keyword.lower() in user_input_lower:
                return True
                
        return False
        
    def _contains_farewell_keywords(self, user_input: str) -> bool:
        """Check if the user input contains farewell keywords."""
        farewell_keywords = [
            "thank", "thanks", "goodbye", "bye", "end", "finished",
            "complete", "talk later", "no more questions", "all set",
            "that's all", "that will be all", "done", "satisfied",
            "enough information", "good day", "see you later",
            "appreciate your help", "helpful", "good enough"
        ]
        
        user_input_lower = user_input.lower()
        for keyword in farewell_keywords:
            if keyword.lower() in user_input_lower:
                return True
                
        return False

    def determine_stage(self, 
                        user_input: str, 
                        profile: Optional[Dict[str, Any]] = None,
                        needs: Optional[Dict[str, Any]] = None,
                        matched_car_models: Optional[List[str]] = None,
                        reservation_info: Optional[Dict[str, Any]] = None) -> str:
        """
        Determine the current stage based on user input and context data.
        
        Args:
            user_input: The current input from the user
            profile: User profile information
            needs: User needs information
            matched_car_models: List of matched car models
            reservation_info: Reservation information
            
        Returns:
            str: The determined stage
        """
        self.previous_stage = self.current_stage
        
        # Initial state logic - this is usually the entry point
        if self.current_stage == "initial":
            self.current_stage = "welcome"
            
        # Welcome stage logic - typically moves to profile analysis
        elif self.current_stage == "welcome":
            if not self._is_profile_complete(profile):
                self.current_stage = "profile_analysis"
            elif self._contains_needs_keywords(user_input):
                self.current_stage = "needs_analysis"
                
        # Profile analysis logic
        elif self.current_stage == "profile_analysis":
            if self._is_profile_complete(profile):
                if self._contains_needs_keywords(user_input):
                    self.current_stage = "needs_analysis"
            
        # Needs analysis logic        
        elif self.current_stage == "needs_analysis":
            if needs and matched_car_models and (self._contains_car_selection_keywords(user_input) or len(matched_car_models) > 0):
                self.current_stage = "car_selection_confirmation"
                
        # Car selection confirmation logic
        elif self.current_stage == "car_selection_confirmation":
            if self._contains_needs_keywords(user_input):
                # User wants to reconsider their needs
                self.current_stage = "needs_analysis"
            elif self._contains_test_drive_keywords(user_input):
                self.current_stage = "reservation4s"
                
        # Reservation (4S) logic
        elif self.current_stage == "reservation4s":
            if reservation_info and self._is_reservation_info_complete(reservation_info):
                self.current_stage = "reservation_confirmation"
                
        # Reservation confirmation logic
        elif self.current_stage == "reservation_confirmation":
            if self._contains_farewell_keywords(user_input):
                self.current_stage = "farewell"
                
        # Handle transitions from any stage
        
        # If user wants to talk about needs at any point
        if self.current_stage not in ["needs_analysis", "initial", "welcome"] and self._contains_needs_keywords(user_input):
            self.current_stage = "needs_analysis"
            
        # If user wants to book test drive at any point after needs analysis
        if self.current_stage not in ["reservation4s", "reservation_confirmation", "farewell", "initial", "welcome"] and self._contains_test_drive_keywords(user_input):
            self.current_stage = "reservation4s"
            
        # If user explicitly says goodbye at any point
        if self._contains_farewell_keywords(user_input) and self.current_stage != "farewell":
            self.current_stage = "farewell"
            
        # Update stage history if stage has changed
        if self.current_stage != self.previous_stage:
            self.stage_history.append(self.current_stage)
            
        return self.current_stage
    
    def get_stage_history(self) -> List[str]:
        """Return the history of stages."""
        return self.stage_history
        
    def reset(self) -> None:
        """Reset the arbitrator to initial state."""
        self.previous_stage = "initial"
        self.current_stage = "initial"
        self.stage_history = ["initial"]
        
    def __str__(self) -> str:
        """String representation of the current state."""
        return f"Current stage: {self.current_stage}, Previous stage: {self.previous_stage}"


if __name__ == "__main__":
    # Unit tests for StageArbitrator class
    
    def run_test(test_name, test_func):
        """Helper function to run tests and display results."""
        print(f"Running test: {test_name}")
        try:
            test_func()
            print(f"✅ {test_name} - PASSED")
        except AssertionError as e:
            print(f"❌ {test_name} - FAILED: {str(e)}")
        print("-" * 60)
    
    # Sample data for testing
    sample_profile_incomplete = {
        "phone_number": "123456789",
        "age": "20-35",
        "user_title": "Mr.",
        "name": "",  # Missing name
        "target_driver": "",  # Missing target driver
        "expertise": "6"
    }
    
    sample_profile_complete = {
        "phone_number": "123456789",
        "age": "20-35",
        "user_title": "Mr.",
        "name": "John",
        "target_driver": "Self",
        "expertise": "6"
    }
    
    sample_needs = {
        "explicit": {
            "powertrain_type": "Battery Electric Vehicle",
            "vehicle_category_bottom": "Compact SUV",
            "driving_range": "Above 800km",
            "brand": "Tesla",
            "prize": "40,000~60,000"
        },
        "implicit": {
            "energy_consumption_level": "Low",
            "size": "Medium",
            "family_friendliness": "High"
        }
    }
    
    sample_matched_car_models = ["Tesla Model Y", "Ford Mustang Mach-E"]
    
    sample_reservation_info_incomplete = {
        "test_driver": "Mr. Zhang",
        "reservation_date": "2025-06-05",
        "selected_car_model": "Tesla Model Y",
        "reservation_time": "",  # Missing time
        "reservation_location": "Tesla Beijing Haidian Store",
        "reservation_phone_number": "123456789"
    }
    
    sample_reservation_info_complete = {
        "test_driver": "Mr. Zhang",
        "reservation_date": "2025-06-05",
        "selected_car_model": "Tesla Model Y",
        "reservation_time": "14:00",
        "reservation_location": "Tesla Beijing Haidian Store",
        "reservation_phone_number": "123456789",
        "salesman": "David Chen"
    }
    
    # Test 1: Initialization and reset
    def test_initialization_and_reset():
        arbitrator = StageArbitrator()
        assert arbitrator.current_stage == "initial", f"Expected initial stage, got {arbitrator.current_stage}"
        assert arbitrator.previous_stage == "initial", f"Expected initial stage, got {arbitrator.previous_stage}"
        assert arbitrator.stage_history == ["initial"], f"Expected ['initial'], got {arbitrator.stage_history}"
        
        # Test reset functionality
        arbitrator.current_stage = "needs_analysis"
        arbitrator.previous_stage = "welcome"
        arbitrator.stage_history = ["initial", "welcome", "needs_analysis"]
        
        arbitrator.reset()
        assert arbitrator.current_stage == "initial", f"After reset, expected initial stage, got {arbitrator.current_stage}"
        assert arbitrator.previous_stage == "initial", f"After reset, expected initial stage, got {arbitrator.previous_stage}"
        assert arbitrator.stage_history == ["initial"], f"After reset, expected ['initial'], got {arbitrator.stage_history}"
    
    # Test 2: Basic flow transition - initial to welcome
    def test_initial_to_welcome_transition():
        arbitrator = StageArbitrator()
        arbitrator.determine_stage("Hello!")
        assert arbitrator.current_stage == "welcome", f"Expected welcome stage, got {arbitrator.current_stage}"
        assert arbitrator.previous_stage == "initial", f"Expected previous stage initial, got {arbitrator.previous_stage}"
        assert arbitrator.stage_history == ["initial", "welcome"], f"Expected ['initial', 'welcome'], got {arbitrator.stage_history}"
    
    # Test 3: Welcome to profile analysis transition
    def test_welcome_to_profile_analysis():
        arbitrator = StageArbitrator()
        # Move to welcome stage
        arbitrator.determine_stage("Hello!")
        # Should move to profile analysis if profile is incomplete
        arbitrator.determine_stage("Let me know about yourself", sample_profile_incomplete)
        assert arbitrator.current_stage == "profile_analysis", f"Expected profile_analysis stage, got {arbitrator.current_stage}"
    
    # Test 4: Profile analysis to needs analysis transition
    def test_profile_to_needs_analysis():
        arbitrator = StageArbitrator()
        # Setup stages
        arbitrator.determine_stage("Hello!")  # Move to welcome
        arbitrator.determine_stage("Let me know about yourself", sample_profile_incomplete)  # Move to profile_analysis
        
        # If profile is complete and user talks about needs, move to needs_analysis
        arbitrator.determine_stage("I'm looking for an electric car with good range", sample_profile_complete)
        assert arbitrator.current_stage == "needs_analysis", f"Expected needs_analysis stage, got {arbitrator.current_stage}"
    
    # Test 5: Needs analysis to car selection confirmation
    def test_needs_to_car_selection():
        arbitrator = StageArbitrator()
        # Setup stages
        arbitrator.current_stage = "needs_analysis"
        arbitrator.stage_history = ["initial", "welcome", "needs_analysis"]
        
        # If needs and matched cars are provided, and user selects a car
        arbitrator.determine_stage("I like the Tesla Model Y", sample_profile_complete, sample_needs, sample_matched_car_models)
        assert arbitrator.current_stage == "car_selection_confirmation", f"Expected car_selection_confirmation stage, got {arbitrator.current_stage}"
    
    # Test 6: Car selection to reservation
    def test_car_selection_to_reservation():
        arbitrator = StageArbitrator()
        # Setup stages
        arbitrator.current_stage = "car_selection_confirmation"
        arbitrator.stage_history = ["initial", "welcome", "needs_analysis", "car_selection_confirmation"]
        
        # If user talks about test driving
        arbitrator.determine_stage("I'd like to test drive this car", sample_profile_complete, sample_needs, sample_matched_car_models)
        assert arbitrator.current_stage == "reservation4s", f"Expected reservation4s stage, got {arbitrator.current_stage}"
    
    # Test 7: Reservation to confirmation
    def test_reservation_to_confirmation():
        arbitrator = StageArbitrator()
        # Setup stages
        arbitrator.current_stage = "reservation4s"
        arbitrator.stage_history = ["initial", "welcome", "needs_analysis", "car_selection_confirmation", "reservation4s"]
        
        # Complete reservation info should move to confirmation
        arbitrator.determine_stage("That time works for me", sample_profile_complete, sample_needs, 
                                   sample_matched_car_models, sample_reservation_info_complete)
        assert arbitrator.current_stage == "reservation_confirmation", f"Expected reservation_confirmation stage, got {arbitrator.current_stage}"
    
    # Test 8: Confirmation to farewell
    def test_confirmation_to_farewell():
        arbitrator = StageArbitrator()
        # Setup stages
        arbitrator.current_stage = "reservation_confirmation"
        arbitrator.stage_history = ["initial", "welcome", "needs_analysis", "car_selection_confirmation", 
                                  "reservation4s", "reservation_confirmation"]
        
        # Farewell message should end conversation
        arbitrator.determine_stage("Thank you for your help!", sample_profile_complete, sample_needs, 
                                   sample_matched_car_models, sample_reservation_info_complete)
        assert arbitrator.current_stage == "farewell", f"Expected farewell stage, got {arbitrator.current_stage}"
    
    # Test 9: Keyword detection for needs
    def test_needs_keywords_detection():
        arbitrator = StageArbitrator()
        assert arbitrator._contains_needs_keywords("I want a car with good fuel efficiency"), "Should detect 'want' and 'fuel efficiency'"
        assert arbitrator._contains_needs_keywords("Looking for an electric SUV"), "Should detect 'looking for', 'electric', and 'SUV'"
        assert arbitrator._contains_needs_keywords("My budget is around 40,000"), "Should detect 'budget' and '40,000'"
        assert arbitrator._contains_needs_keywords("I prefer Tesla brand"), "Should detect 'prefer' and 'Tesla'"
        assert not arbitrator._contains_needs_keywords("Hello, how are you today?"), "Should not detect needs keywords in greeting"
    
    # Test 10: Keyword detection for car selection
    def test_car_selection_keywords_detection():
        arbitrator = StageArbitrator()
        assert arbitrator._contains_car_selection_keywords("I choose the Tesla Model Y"), "Should detect 'choose'"
        assert arbitrator._contains_car_selection_keywords("This car looks good to me"), "Should detect 'looks good'"
        assert arbitrator._contains_car_selection_keywords("I've decided on the Ford Mustang"), "Should detect 'decided on'"
        assert not arbitrator._contains_car_selection_keywords("What other features does it have?"), "Should not detect car selection keywords"
    
    # Test 11: Keyword detection for test drive
    def test_test_drive_keywords_detection():
        arbitrator = StageArbitrator()
        assert arbitrator._contains_test_drive_keywords("I want to test drive this car"), "Should detect 'test drive'"
        assert arbitrator._contains_test_drive_keywords("When can I schedule an appointment?"), "Should detect 'schedule' and 'appointment'"
        assert arbitrator._contains_test_drive_keywords("Which dealership location is available?"), "Should detect 'dealership' and 'location'"
        assert not arbitrator._contains_test_drive_keywords("What color options are available?"), "Should not detect test drive keywords"
    
    # Test 12: Keyword detection for farewell
    def test_farewell_keywords_detection():
        arbitrator = StageArbitrator()
        assert arbitrator._contains_farewell_keywords("Thank you for your help"), "Should detect 'thank you'"
        assert arbitrator._contains_farewell_keywords("I'm done for now, bye"), "Should detect 'done' and 'bye'"
        assert arbitrator._contains_farewell_keywords("That's all I needed today"), "Should detect 'that's all'"
        assert not arbitrator._contains_farewell_keywords("Let me think about this more"), "Should not detect farewell keywords"
    
    # Test 13: Stage jump - from car selection back to needs
    def test_jump_back_to_needs():
        arbitrator = StageArbitrator()
        # Setup stages
        arbitrator.current_stage = "car_selection_confirmation"
        arbitrator.stage_history = ["initial", "welcome", "needs_analysis", "car_selection_confirmation"]
        
        # User wants to reconsider needs
        arbitrator.determine_stage("Actually, I prefer something with better fuel efficiency", 
                                   sample_profile_complete, sample_needs, sample_matched_car_models)
        assert arbitrator.current_stage == "needs_analysis", f"Expected needs_analysis stage, got {arbitrator.current_stage}"
    
    # Test 14: Skip to test drive from any stage
    def test_skip_to_test_drive():
        arbitrator = StageArbitrator()
        # Setup stages - start in profile analysis
        arbitrator.current_stage = "profile_analysis"
        arbitrator.stage_history = ["initial", "welcome", "profile_analysis"]
        
        # User wants to test drive immediately
        arbitrator.determine_stage("I want to schedule a test drive right now", 
                                   sample_profile_complete, sample_needs, sample_matched_car_models)
        assert arbitrator.current_stage == "reservation4s", f"Expected reservation4s stage, got {arbitrator.current_stage}"
    
    # Test 15: Skip to farewell from any stage
    def test_skip_to_farewell():
        arbitrator = StageArbitrator()
        # Setup stages - start in needs analysis
        arbitrator.current_stage = "needs_analysis"
        arbitrator.stage_history = ["initial", "welcome", "needs_analysis"]
        
        # User wants to end conversation
        arbitrator.determine_stage("Thanks, that's all I needed. Goodbye!", 
                                   sample_profile_complete, sample_needs)
        assert arbitrator.current_stage == "farewell", f"Expected farewell stage, got {arbitrator.current_stage}"
    
    # Run all tests
    print("Starting StageArbitrator unit tests...\n")
    
    run_test("Test 1: Initialization and Reset", test_initialization_and_reset)
    run_test("Test 2: Initial to Welcome Transition", test_initial_to_welcome_transition)
    run_test("Test 3: Welcome to Profile Analysis", test_welcome_to_profile_analysis)
    run_test("Test 4: Profile to Needs Analysis", test_profile_to_needs_analysis)
    run_test("Test 5: Needs to Car Selection", test_needs_to_car_selection)
    run_test("Test 6: Car Selection to Reservation", test_car_selection_to_reservation)
    run_test("Test 7: Reservation to Confirmation", test_reservation_to_confirmation)
    run_test("Test 8: Confirmation to Farewell", test_confirmation_to_farewell)
    run_test("Test 9: Needs Keywords Detection", test_needs_keywords_detection)
    run_test("Test 10: Car Selection Keywords Detection", test_car_selection_keywords_detection)
    run_test("Test 11: Test Drive Keywords Detection", test_test_drive_keywords_detection)
    run_test("Test 12: Farewell Keywords Detection", test_farewell_keywords_detection)
    run_test("Test 13: Jump Back to Needs", test_jump_back_to_needs)
    run_test("Test 14: Skip to Test Drive", test_skip_to_test_drive)
    run_test("Test 15: Skip to Farewell", test_skip_to_farewell)
    
    print("All tests completed.") 