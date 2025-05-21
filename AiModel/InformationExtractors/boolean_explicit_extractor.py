import json
import os
import re
from typing import Dict, List, Any, Set, Optional, Tuple, Union


class BooleanExplicitExtractor:
    """
    BooleanExplicitExtractor extracts boolean explicit labels from user input.
    It focuses on extracting values for labels with value_type 'boolean' from the QueryLabels configuration.
    """

    def __init__(self, config_file_path: str = "../Config/QueryLabels.json"):
        """
        Initialize the BooleanExplicitExtractor with the QueryLabels configuration.
        
        Args:
            config_file_path (str): Path to the QueryLabels configuration file
        """
        self.config = {}
        self.boolean_labels = set()
        self.positive_expressions = {
            "general": [
                r"(?:want|need|looking for|would like|require|must have|should have|prefer|hope|expect|desire|wish for)",
                r"(?:important|necessary|essential|critical|vital|key|significant)",
                r"(?:good|great|excellent|awesome|fantastic|amazing|impressive|outstanding)",
                r"(?:definitely|absolutely|certainly|surely|undoubtedly)",
                r"(?:should include|should come with|should feature)",
                r"(?:would be better with|would be nice to have|would be helpful|would be beneficial|would be useful)",
                r"(?:interested in|curious about|keen on)",
                r"(?:does it have|will it have|has|with|including|includes|that has|equipped with|comes with)"
            ],
            "affirmative": [
                r"(?:yes|yeah|yep|sure|correct|right|indeed|exactly|precisely|absolutely|definitely|certainly)"
            ],
            "safety": [
                r"(?:safe|safer|safety|protect|protection|secure|reliable|prevent accidents|avoid collisions)"
            ],
            "convenience": [
                r"(?:convenient|convenience|handy|practical|useful|helpful|beneficial|ease|simple|easy to use)"
            ],
            "preference": [
                r"(?:like|love|enjoy|appreciate|value|prefer|fond of|favor|ideal|perfect for me)"
            ]
        }
        self.negative_expressions = [
            r"(?:don't want|don't need|not looking for|wouldn't like|don't require)",
            r"(?:not important|unnecessary|not essential|not critical)",
            r"(?:bad|poor|terrible|awful|mediocre|subpar)",
            r"(?:definitely not|absolutely not|certainly not|surely not)",
            r"(?:shouldn't include|shouldn't come with|shouldn't feature)",
            r"(?:would be worse with|don't care about|don't care for)",
            r"(?:not interested in|not curious about)",
            r"(?:doesn't have|won't have|hasn't|without|excluding|doesn't include)",
            r"(?:no|nope|nah|not|never|can do without|can live without)"
        ]
        
        # Synonyms for boolean features
        self.feature_synonyms = {
            "abs": [
                r"abs",
                r"anti[ -]lock braking system",
                r"anti[ -]lock brakes",
                r"anti[ -]skid braking",
                r"brake assistance",
                r"advanced braking"
            ],
            "esp": [
                r"esp",
                r"electronic stability program",
                r"electronic stability control",
                r"esc",
                r"stability control",
                r"traction control",
                r"tcs",
                r"vehicle stability",
                r"anti[ -]skid system"
            ],
            "voice_interaction": [
                r"voice interaction",
                r"voice control",
                r"voice assistant",
                r"voice recognition",
                r"voice commands",
                r"speech recognition",
                r"voice operated",
                r"talk to the car",
                r"voice activation",
                r"voice interface",
                r"speak to the car",
                r"voice technology",
                r"verbal commands",
                r"voice-controlled system"
            ],
            "ota_updates": [
                r"ota updates",
                r"over[ -]the[ -]air updates",
                r"wireless updates",
                r"remote updates",
                r"software updates",
                r"remote software updates",
                r"online updates",
                r"system updates",
                r"digital updates",
                r"automatic updates"
            ],
            "adaptive_cruise_control": [
                r"adaptive cruise control",
                r"acc",
                r"smart cruise control",
                r"intelligent cruise control",
                r"dynamic cruise control",
                r"radar cruise control",
                r"autonomous cruise control",
                r"distance-based cruise control",
                r"adaptive cruise",
                r"traffic-aware cruise"
            ],
            "traffic_jam_assist": [
                r"traffic jam assist",
                r"traffic assist",
                r"congestion assist",
                r"jam assist",
                r"queue assist",
                r"traffic jam pilot",
                r"traffic crawl",
                r"congestion pilot",
                r"traffic helper"
            ],
            "automatic_emergency_braking": [
                r"automatic emergency braking",
                r"aeb",
                r"emergency braking",
                r"collision avoidance",
                r"collision prevention",
                r"crash prevention",
                r"automatic braking",
                r"emergency brake assist",
                r"collision mitigation",
                r"crash avoidance",
                r"emergency stop",
                r"autonomous emergency braking"
            ],
            "lane_keep_assist": [
                r"lane keep assist",
                r"lane keeping",
                r"lane assistance",
                r"lane departure prevention",
                r"lane centering",
                r"lane support",
                r"lane tracking",
                r"stay in lane",
                r"lane guidance",
                r"lane departure warning",
                r"lane monitoring"
            ],
            "remote_parking": [
                r"remote parking",
                r"remote park assist",
                r"smartphone parking",
                r"park from phone",
                r"app parking",
                r"parking from outside",
                r"remote controlled parking",
                r"remote control parking",
                r"phone parking",
                r"park it remotely",
                r"parkable via phone"
            ],
            "auto_parking": [
                r"auto parking",
                r"automatic parking",
                r"self parking",
                r"automated parking",
                r"parking assist",
                r"hands free parking",
                r"park itself",
                r"parks itself",
                r"autonomous parking",
                r"self-park",
                r"park by itself",
                r"automatic park"
            ],
            "blind_spot_detection": [
                r"blind spot detection",
                r"blind spot monitoring",
                r"bsd",
                r"bsm",
                r"blind spot alert",
                r"blind spot warning",
                r"blind spot information",
                r"side detection",
                r"blind area monitoring",
                r"blind zone alert"
            ],
            "fatigue_driving_detection": [
                r"fatigue driving detection",
                r"drowsiness detection",
                r"driver attention monitor",
                r"driver alertness",
                r"tiredness detection",
                r"attentiveness monitoring",
                r"driver monitoring system",
                r"sleepiness detection",
                r"fatigue alerts",
                r"drowsy driver detection",
                r"attention warning",
                r"tired driver alert",
                r"detects when you're tired",
                r"monitors driver alertness"
            ],
            "city_commuting": [
                r"city commuting",
                r"urban driving",
                r"city driving",
                r"urban commuting",
                r"city traffic",
                r"city friendly",
                r"good for city",
                r"easy to drive in city",
                r"city use",
                r"downtown driving",
                r"metropolitan driving",
                r"urban traffic",
                r"city environment",
                r"city streets",
                r"daily commute"
            ],
            "highway_long_distance": [
                r"highway long distance",
                r"highway driving",
                r"long distance travel",
                r"highway cruising",
                r"road trip",
                r"interstate driving",
                r"long journeys",
                r"extended trips",
                r"long hauls",
                r"highway comfort",
                r"long drives",
                r"highway performance",
                r"motorway driving",
                r"expressway use",
                r"long-distance comfort"
            ],
            "cargo_capability": [
                r"cargo capability",
                r"cargo capacity",
                r"loading capacity",
                r"hauling capability",
                r"storage space",
                r"trunk space",
                r"cargo room",
                r"luggage space",
                r"storage capacity",
                r"carrying capacity",
                r"boot space",
                r"loading space",
                r"stowage capacity",
                r"transport capacity"
            ]
        }
        
        # Additional context-specific patterns
        self.safety_features = [
            "abs", "esp", "automatic_emergency_braking", 
            "lane_keep_assist", "blind_spot_detection"
        ]
        
        self.convenience_features = [
            "voice_interaction", "ota_updates", "adaptive_cruise_control", 
            "traffic_jam_assist", "remote_parking", "auto_parking"
        ]
        
        self.driver_monitoring_features = [
            "fatigue_driving_detection"
        ]
        
        self._load_config(config_file_path)
        self._compile_regex_patterns()
        
    def _load_config(self, config_path: str) -> None:
        """
        Load the QueryLabels configuration from the specified file path.
        
        Args:
            config_path (str): Path to the configuration file
        """
        try:
            # Adjust path if needed
            if not os.path.isfile(config_path):
                base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                config_path = os.path.join(base_dir, "Config", "QueryLabels.json")
                
            with open(config_path, 'r') as file:
                self.config = json.load(file)
                
            # Extract boolean labels from the configuration
            self.boolean_labels = {
                label for label, info in self.config.items() 
                if "value_type" in info and info["value_type"] == "boolean"
            }
        except Exception as e:
            print(f"Error loading config file: {e}")
            self.config = {}
            self.boolean_labels = set()
            
    def _compile_regex_patterns(self) -> None:
        """
        Compile regex patterns for faster matching.
        """
        # Compile positive expressions
        self.positive_patterns = {
            category: [re.compile(pattern, re.IGNORECASE) for pattern in patterns]
            for category, patterns in self.positive_expressions.items()
        }
        
        # Compile negative expressions
        self.negative_patterns = [
            re.compile(pattern, re.IGNORECASE) for pattern in self.negative_expressions
        ]
        
        # Compile feature synonyms
        self.feature_patterns = {
            label: [re.compile(r"\b" + pattern + r"\b", re.IGNORECASE) for pattern in patterns]
            for label, patterns in self.feature_synonyms.items()
        }
        
    def extract_bool_values(self, text: str) -> Dict[str, str]:
        """
        Extract boolean values from the provided text.
        
        Args:
            text (str): User input text
            
        Returns:
            Dict[str, str]: Dictionary mapping boolean labels to their values ("yes" or "no")
        """
        extracted_values = {}
        
        # First, look for explicit negations in the whole text
        explicit_negations = {}
        for label in self.boolean_labels:
            if label in self.feature_patterns:
                for pattern in self.feature_patterns[label]:
                    for match in pattern.finditer(text):
                        start_pos = max(0, match.start() - 50)
                        end_pos = min(len(text), match.end() + 50)
                        context = text[start_pos:end_pos]
                        
                        # Check for negative expressions
                        if any(neg_pattern.search(context) for neg_pattern in self.negative_patterns):
                            explicit_negations[label] = "no"
                            break
        
        # Then do regular extraction, respecting explicit negations
        for label in self.boolean_labels:
            if label in self.feature_patterns:
                # If we've already found an explicit negation, use it
                if label in explicit_negations:
                    extracted_values[label] = explicit_negations[label]
                else:
                    value = self._extract_single_bool_value(text, label)
                    if value:
                        extracted_values[label] = value
                    
        # Look for implicit mentions of features through context
        self._extract_implicit_features(text, extracted_values)
        
        return extracted_values
        
    def _extract_single_bool_value(self, text: str, label: str) -> Optional[str]:
        """
        Extract a boolean value for a single label from the text.
        
        Args:
            text (str): User input text
            label (str): The boolean label to extract
            
        Returns:
            Optional[str]: "yes", "no", or None if no value can be determined
        """
        if label not in self.feature_patterns:
            return None
            
        # Check for mentions of the feature
        feature_mentioned = False
        feature_patterns = self.feature_patterns[label]
        
        for pattern in feature_patterns:
            matches = list(pattern.finditer(text))
            if matches:
                feature_mentioned = True
                
                # Look for positive or negative context around the match
                for match in matches:
                    start_pos = max(0, match.start() - 50)
                    end_pos = min(len(text), match.end() + 50)
                    context = text[start_pos:end_pos]
                    
                    # Check for negative expressions first
                    is_negative = any(neg_pattern.search(context) for neg_pattern in self.negative_patterns)
                    if is_negative:
                        return "no"
                    
                    # Check for explicit positive expressions
                    is_affirmative = any(
                        pos_pattern.search(context)
                        for pos_pattern in self.positive_patterns["affirmative"]
                    )
                    if is_affirmative:
                        return "yes"
                    
                    # Check for general positive expressions
                    is_positive = any(
                        pos_pattern.search(context)
                        for category in ["general", "preference", "convenience", "safety"]
                        for pos_pattern in self.positive_patterns.get(category, [])
                    )
                    if is_positive:
                        return "yes"
                    
                    # Check for feature-specific context
                    if label in self.safety_features and any(
                        safety_pattern.search(context) for safety_pattern in self.positive_patterns["safety"]
                    ):
                        return "yes"
                        
                    if label in self.convenience_features and any(
                        convenience_pattern.search(context) for convenience_pattern in self.positive_patterns["convenience"]
                    ):
                        return "yes"
        
        # If the feature is mentioned but without clear positive/negative context
        if feature_mentioned:
            # Default to "yes" for mentioned features, as users typically mention features they want
            return "yes"
            
        return None
        
    def _extract_implicit_features(self, text: str, extracted_values: Dict[str, str]) -> None:
        """
        Extract implicit mentions of features based on context.
        
        Args:
            text (str): User input text
            extracted_values: Dictionary to update with extracted values
        """
        # City commuting pattern
        city_patterns = [
            re.compile(r"(?:in the city|city driving|urban|downtown|city streets|traffic|commute|commuting)", re.IGNORECASE)
        ]
        
        # Highway long distance pattern
        highway_patterns = [
            re.compile(r"(?:highway|motorway|interstate|road trip|long distance|journey|long haul|extended travel)", re.IGNORECASE)
        ]
        
        # Check for city commuting context
        if "city_commuting" not in extracted_values:
            city_context = any(pattern.search(text) for pattern in city_patterns)
            if city_context:
                # Look for positive indicators around city mentions
                for pattern in city_patterns:
                    matches = list(pattern.finditer(text))
                    for match in matches:
                        start_pos = max(0, match.start() - 30)
                        end_pos = min(len(text), match.end() + 30)
                        context = text[start_pos:end_pos]
                        
                        if any(pos_pattern.search(context) for category in ["general", "preference"] 
                              for pos_pattern in self.positive_patterns.get(category, [])):
                            extracted_values["city_commuting"] = "yes"
                            break
        
        # Check for highway long distance context
        if "highway_long_distance" not in extracted_values:
            highway_context = any(pattern.search(text) for pattern in highway_patterns)
            if highway_context:
                # Look for positive indicators around highway mentions
                for pattern in highway_patterns:
                    matches = list(pattern.finditer(text))
                    for match in matches:
                        start_pos = max(0, match.start() - 30)
                        end_pos = min(len(text), match.end() + 30)
                        context = text[start_pos:end_pos]
                        
                        if any(pos_pattern.search(context) for category in ["general", "preference"] 
                              for pos_pattern in self.positive_patterns.get(category, [])):
                            extracted_values["highway_long_distance"] = "yes"
                            break
                            
        # Check for safety-related context
        safety_context = any(pattern.search(text) for pattern in self.positive_patterns["safety"])
        if safety_context:
            for safety_feature in self.safety_features:
                # Only add if not already extracted
                if safety_feature not in extracted_values:
                    # Check if the safety feature is mentioned in the text
                    feature_mentioned = False
                    for pattern in self.feature_patterns.get(safety_feature, []):
                        if pattern.search(text):
                            feature_mentioned = True
                            extracted_values[safety_feature] = "yes"
                            break
                            
        # Check for fatigue driving detection through implicit mentions
        fatigue_patterns = [
            re.compile(r"(?:tired|drowsy|sleepy|fatigue|alertness|attention|drowsiness|falling asleep)", re.IGNORECASE)
        ]
        
        if "fatigue_driving_detection" not in extracted_values:
            fatigue_context = any(pattern.search(text) for pattern in fatigue_patterns)
            if fatigue_context:
                for pattern in fatigue_patterns:
                    matches = list(pattern.finditer(text))
                    for match in matches:
                        start_pos = max(0, match.start() - 40)
                        end_pos = min(len(text), match.end() + 40)
                        context = text[start_pos:end_pos]
                        
                        detect_patterns = [
                            re.compile(r"(?:detect|monitor|alert|warn|notify|sense)", re.IGNORECASE)
                        ]
                        
                        if any(detect_pattern.search(context) for detect_pattern in detect_patterns):
                            extracted_values["fatigue_driving_detection"] = "yes"
                            break
    
    def extract_all_values(self, text: str) -> Dict[str, Any]:
        """
        Main method to extract all boolean values from text.
        This follows the interface pattern of basic_explicit_extractor.
        
        Args:
            text (str): User input text
            
        Returns:
            Dict[str, Any]: Dictionary containing all extracted boolean values
        """
        return self.extract_bool_values(text)


# Example usage and testing
if __name__ == "__main__":
    extractor = BooleanExplicitExtractor()
    
    # Test cases for different boolean features
    test_cases = [
        # Test for ABS
        "I want a car with ABS, that's very important for safety.",
        
        # Test for ESP
        "Electronic stability control is a must-have feature for me.",
        
        # Test for voice interaction
        "I'd like a car where I can use voice commands to control things.",
        
        # Test for OTA updates
        "Does it support over-the-air updates? That would be great.",
        
        # Test for adaptive cruise control
        "Adaptive cruise control would be nice for long highway drives.",
        
        # Test for multiple features with mixed sentiments
        "I need lane keeping assist and blind spot detection, but I don't really care about auto parking.",
        
        # Test for traffic jam assist
        "Traffic jam assist would be really helpful for my daily commute.",
        
        # Test for automatic emergency braking
        "Safety is my priority, so automatic emergency braking is essential.",
        
        # Test for remote parking
        "I don't think I need the feature where you can park the car using your phone.",
        
        # Test for fatigue driving detection
        "Does it have a system that alerts you when you're getting tired? That would be beneficial.",
        
        # Test for city commuting
        "I mostly drive in the city, so I need a car that's good for urban environments.",
        
        # Test for highway long distance
        "We take a lot of road trips, so highway comfort is important.",
        
        # Test for cargo capability
        "I need good cargo space to transport my sports equipment.",
        
        # Test for negations
        "I don't want lane keep assist, it's annoying to me.",
        
        # Test for affirmative preferences
        "Yes, blind spot detection is definitely something I want.",
        
        # Test for indirect expressions
        "A car that helps prevent accidents would be ideal.",
        
        # Test for ambiguous expressions
        "I've heard about these self-parking features. Interesting concept.",
        
        # Test for multiple features in one sentence
        "I'd prefer a model with ABS, ESP, and good traction control for winter driving."
    ]
    
    print("Testing BooleanExplicitExtractor with various inputs:\n")
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"Test Case {i}: {test_case}")
        results = extractor.extract_all_values(test_case)
        
        if results:
            print("Extracted values:")
            for label, value in results.items():
                print(f"  - {label}: {value}")
        else:
            print("No boolean values extracted.")
        print("-" * 60)
    
    # Testing for systematic coverage of all boolean labels
    coverage_tests = {
        "abs": "I definitely want a car with ABS, it's crucial for safety.",
        "esp": "Having ESP or electronic stability control is non-negotiable for me.",
        "voice_interaction": "I love the idea of talking to my car with voice commands.",
        "ota_updates": "The car should support OTA updates to keep the software current.",
        "adaptive_cruise_control": "Adaptive cruise control would make highway driving much easier.",
        "traffic_jam_assist": "Traffic jam assist would help with my daily commute in congested areas.",
        "automatic_emergency_braking": "Auto emergency braking is a safety feature I can't do without.",
        "lane_keep_assist": "Lane keeping assistance would be helpful on long trips.",
        "remote_parking": "I don't think I need remote parking capabilities.",
        "auto_parking": "Self-parking feature would be nice for tight parking spots in the city.",
        "blind_spot_detection": "Blind spot monitoring is essential for changing lanes safely.",
        "fatigue_driving_detection": "Driver alertness monitoring would be good for long drives.",
        "city_commuting": "The car should be good for city driving since that's my daily use.",
        "highway_long_distance": "I need a car that performs well on the highway for road trips.",
        "cargo_capability": "Good cargo capacity is important for my lifestyle."
    }
    
    print("\nTesting coverage for all boolean labels:\n")
    
    all_boolean_labels = set(extractor.boolean_labels)
    covered_labels = set()
    
    for label, test_text in coverage_tests.items():
        print(f"Testing {label}: {test_text}")
        results = extractor.extract_all_values(test_text)
        
        if results:
            print("Extracted values:")
            for result_label, value in results.items():
                print(f"  - {result_label}: {value}")
                covered_labels.add(result_label)
        else:
            print("No boolean values extracted.")
        print("-" * 60)
    
    # Check if all boolean labels were covered
    print("\nCoverage Summary:")
    if covered_labels == all_boolean_labels:
        print("✅ All boolean labels were successfully covered in tests.")
    else:
        missed_labels = all_boolean_labels - covered_labels
        print(f"❌ Some boolean labels were not covered in tests: {missed_labels}")
    
    # Additional tests for synonym variations
    synonym_tests = [
        ("ABS", "I'd like a car with anti-lock brakes for better control."),
        ("ESP", "The car should have traction control for slippery conditions."),
        ("voice_interaction", "Can I speak to the car to change radio stations?"),
        ("ota_updates", "Wireless software updates would be convenient."),
        ("adaptive_cruise_control", "Smart cruise control that adjusts to traffic would be nice."),
        ("traffic_jam_assist", "A feature that helps in congestion would save me stress."),
        ("automatic_emergency_braking", "I want collision prevention technology."),
        ("lane_keep_assist", "Lane departure prevention is a must for highway driving."),
        ("remote_parking", "Being able to park the car using my smartphone would be cool."),
        ("auto_parking", "A car that parks itself would help me in tight spaces."),
        ("blind_spot_detection", "Side detection alerts would make lane changes safer."),
        ("fatigue_driving_detection", "I want a system that detects when I'm getting tired."),
        ("city_commuting", "The car should be good for urban driving."),
        ("highway_long_distance", "I need a car that's comfortable for long hauls."),
        ("cargo_capability", "Good trunk space is essential for my shopping trips.")
    ]
    
    print("\nTesting synonym variations:\n")
    
    for label, test_text in synonym_tests:
        print(f"Testing synonym for {label}: {test_text}")
        results = extractor.extract_all_values(test_text)
        
        if results:
            print("Extracted values:")
            for result_label, value in results.items():
                print(f"  - {result_label}: {value}")
        else:
            print("No boolean values extracted.")
        print("-" * 60)
    
    # Testing negation handling
    negation_tests = [
        "I don't need remote parking, it seems unnecessary.",
        "I can do without auto parking, I'm good at parking myself.",
        "I don't want the car to have voice interaction, I prefer physical controls.",
        "Automatic emergency braking is not necessary for me.",
        "I would rather not have lane keep assist, I prefer to control the car myself."
    ]
    
    print("\nTesting negation handling:\n")
    
    for i, test_text in enumerate(negation_tests, 1):
        print(f"Negation Test {i}: {test_text}")
        results = extractor.extract_all_values(test_text)
        
        if results:
            print("Extracted values:")
            for label, value in results.items():
                print(f"  - {label}: {value}")
        else:
            print("No boolean values extracted.")
        print("-" * 60)
    
    # Test for implicit feature extraction
    implicit_tests = [
        "I want a car that monitors when the driver is sleepy and alerts them.",
        "Safety is important to me, especially features that prevent accidents.",
        "I drive in the city a lot, so I need something that handles urban roads well.",
        "We frequently go on long road trips, so highway performance matters.",
        "I need to carry a lot of equipment for my job, so space is a priority."
    ]
    
    print("\nTesting implicit feature extraction:\n")
    
    for i, test_text in enumerate(implicit_tests, 1):
        print(f"Implicit Test {i}: {test_text}")
        results = extractor.extract_all_values(test_text)
        
        if results:
            print("Extracted values:")
            for label, value in results.items():
                print(f"  - {label}: {value}")
        else:
            print("No boolean values extracted.")
        print("-" * 60)
    
    print("All tests completed.") 