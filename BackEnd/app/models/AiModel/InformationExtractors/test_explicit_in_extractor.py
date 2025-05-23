import sys
import os
from pathlib import Path

# Add the parent directory to sys.path to allow imports to work
current_dir = Path(__file__).parent
parent_dir = current_dir.parent
sys.path.insert(0, str(parent_dir))

from InformationExtractors.explicit_in_extractor import ExplicitInOneExtractor


def run_test(test_name, test_input, expected_outputs=None):
    """
    Run a test with the given test name and input.
    Print the results and indicate whether the test passed or failed.
    
    Args:
        test_name (str): The name of the test
        test_input (str): The user input to test
        expected_outputs (dict, optional): Expected output labels and values
    """
    print(f"\n=== Test: {test_name} ===")
    print(f"Input: \"{test_input}\"")
    
    extractor = ExplicitInOneExtractor()
    extracted_needs = extractor.extract_explicit_needs(test_input)
    
    print("\nExtracted needs:")
    if not extracted_needs:
        print("  No needs extracted")
    else:
        for label, values in extracted_needs.items():
            print(f"  {label}: {values}")
    
    if expected_outputs:
        print("\nValidation:")
        all_passed = True
        
        # Check that all expected outputs are present
        for label, expected_values in expected_outputs.items():
            if label not in extracted_needs:
                print(f"  ❌ Missing expected label: {label}")
                all_passed = False
                continue
                
            if isinstance(expected_values, list):
                # For list values, check that all expected values are present
                missing_values = [v for v in expected_values if v not in extracted_needs[label]]
                if missing_values:
                    print(f"  ❌ Missing values for {label}: {missing_values}")
                    all_passed = False
            else:
                # For single values, check exact match
                if extracted_needs[label] != expected_values:
                    print(f"  ❌ Value mismatch for {label}: expected '{expected_values}', got '{extracted_needs[label]}'")
                    all_passed = False
        
        if all_passed:
            print("  ✅ All expected values found")
        
    print("=" * 50)
    
    return extracted_needs


def test_mixed_extractors():
    """
    Test the ExplicitInOneExtractor with inputs that should trigger multiple extractors.
    """
    # Test with mixed needs to verify that all extractors are working and results are merged correctly
    mixed_test = "I'm looking for a luxury electric SUV with a driving range of 500km or more. " \
                "It should have lane keeping assist and blind spot detection, but I don't need auto parking. " \
                "My budget is around $50,000, and I prefer 6 airbags for safety. " \
                "The car should have a 5-seat layout with leather seats and a sports car design style."
    
    expected_outputs = {
        # From BasicExplicitExtractor
        "prize": ["40,000 ~ 60,000"],
        "prize_alias": ["luxury"],
        "vehicle_category_top": ["suv"],
        "powertrain_type": ["battery electric vehicle"],
        "driving_range": ["400-800km"],
        
        # From BooleanExplicitExtractor
        "lane_keep_assist": "yes",
        "blind_spot_detection": "yes",
        "auto_parking": "no",
        
        # From ExactExplicitExtractor
        "airbag_count": ["6"],
        "seat_layout": ["5-seat"],
        "seat_material": ["leather"],
        "design_style": ["sports car"],
    }
    
    return run_test("Mixed Extractors Test", mixed_test, expected_outputs)


def test_range_extractor():
    """
    Test the RangeExplicitExtractor functionality within the unified extractor.
    """
    range_test = "I need a car with horsepower between 150 to 250 hp, " \
                "trunk volume of at least 400 liters, " \
                "and fuel consumption below 7l/100km."
    
    expected_outputs = {
        "horsepower": ["100-200 hp", "200-300 hp"],
        "trunk_volume": ["400-500l", "above 500l"],
        "fuel_consumption": ["4-6l/100km", "6-8l/100km"]
    }
    
    return run_test("Range Extractor Test", range_test, expected_outputs)


def test_boolean_extractor():
    """
    Test the BooleanExplicitExtractor functionality within the unified extractor.
    """
    boolean_test = "I need lane guidance technology but don't want the car to park itself. " \
                  "Electronic stability control is a must-have feature for me, and " \
                  "I want a car that can talk to me and monitor my blind areas."
    
    expected_outputs = {
        "lane_keep_assist": "yes",
        "auto_parking": "no",
        "esp": "yes",
        "voice_interaction": "yes",
        "blind_spot_detection": "yes"
    }
    
    return run_test("Boolean Extractor Test", boolean_test, expected_outputs)


def test_basic_extractor():
    """
    Test the BasicExplicitExtractor functionality within the unified extractor.
    """
    basic_test = "I'm looking for a mid-range Japanese mid-size sedan " \
                "with a hybrid powertrain, good fuel efficiency, " \
                "and a price around $35,000."
    
    expected_outputs = {
        "prize": ["30,000 ~ 40,000"],
        "prize_alias": ["mid-range"],
        "brand_country": ["japan"],
        "vehicle_category_top": ["sedan"],
        "vehicle_category_middle": ["mid-size sedan"],
        "powertrain_type": ["hybrid electric vehicle"],
        "energy_consumption_level": ["low"]
    }
    
    return run_test("Basic Extractor Test", basic_test, expected_outputs)


def test_exact_extractor():
    """
    Test the ExactExplicitExtractor functionality within the unified extractor.
    """
    exact_test = "I need a car with 8 airbags, leather seats, " \
                "a sporty design style, all-wheel drive, " \
                "and a 7-seat layout for my large family."
    
    expected_outputs = {
        "airbag_count": ["8"],
        "seat_material": ["leather"],
        "design_style": ["sports car"],
        "drive_type": ["all-wheel drive"],
        "seat_layout": ["7-seat"]
    }
    
    return run_test("Exact Extractor Test", exact_test, expected_outputs)


def test_real_world_scenarios():
    """
    Test the unified extractor with realistic user scenarios.
    """
    scenario1 = "I'm looking for a compact SUV with a price around $30k. " \
               "It should be fuel efficient, have good trunk space, " \
               "and include modern safety features like adaptive cruise control " \
               "and lane keeping assistance."
    
    scenario2 = "I need a family vehicle with at least 7 seats, preferably with " \
               "a hybrid engine. The interior should be durable but comfortable, " \
               "and I need plenty of storage space for sports equipment. " \
               "My budget is around $45,000."
    
    scenario3 = "I want a luxury electric sedan with a range of at least 500km. " \
               "It should have advanced autonomous driving features, leather seats, " \
               "and excellent performance. Price isn't a major concern."
    
    # Run tests without specific expectations, since real-world scenarios can have varied results
    run_test("Real-world Scenario 1", scenario1)
    run_test("Real-world Scenario 2", scenario2)
    run_test("Real-world Scenario 3", scenario3)


if __name__ == "__main__":
    print("Testing ExplicitInOneExtractor...")
    
    # Run the tests
    test_mixed_extractors()
    test_range_extractor()
    test_boolean_extractor()
    test_basic_extractor()
    test_exact_extractor()
    test_real_world_scenarios()
    
    print("\nAll tests completed.") 