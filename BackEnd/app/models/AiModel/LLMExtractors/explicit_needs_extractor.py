import json
import openai
import os
from utils import get_openai_client, get_openai_model, timer_decorator, clean_thinking_output

class ExplicitNeedsExtractor:
    """
    Module for extracting explicit user car needs from chat messages.
    Extracts only directly mentioned requirements based on QueryLabels.json.
    """
    
    def __init__(self, api_key, model=None):
        """
        Initialize the ExplicitNeedsExtractor.
        
        Args:
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
            print(f"Error: QueryLabels.json not found in ExplicitNeedsExtractor. Attempted path: {os.path.abspath(config_file_path)}. Error: {e}")
            self.query_labels = {}
            # raise FileNotFoundError(f"QueryLabels.json is critical and was not found. Path: {os.path.abspath(config_file_path)}") from e

    
    @timer_decorator
    def extract_explicit_needs(self, user_message):
        """
        Extract explicit car needs from a user message.
        
        Args:
            user_message (str): The user's message to analyze
            
        Returns:
            dict: Dictionary containing extracted car requirements
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
            temperature=0.1
        )
        
        # Parse and return the extracted needs
        try:
            content = response.choices[0].message.content
            content = clean_thinking_output(content)
            extracted_needs = json.loads(content)
            return self._validate_and_filter_needs(extracted_needs)
        except json.JSONDecodeError:
            return {}
    
    def _validate_and_filter_needs(self, extracted_needs):
        """
        Validate extracted needs against QueryLabels and filter out invalid ones.
        """
        if not isinstance(extracted_needs, dict):
            return {}

        valid_needs = {}
        for key, value in extracted_needs.items():
            if key not in self.query_labels:
                # Key not defined in QueryLabels, skip
                continue

            if "candidates" not in self.query_labels[key]:
                # Key is defined but has no candidates to validate against, skip (should ideally not happen with good config)
                # Or, if we want to be strict, we can add it if it's a known key.
                # For now, let's assume keys without candidates shouldn't have values extracted.
                continue

            candidates = self.query_labels[key]["candidates"]
            
            if isinstance(value, list):
                # If value is a list, filter its items
                valid_list_values = [v for v in value if v in candidates]
                if valid_list_values: # Only add if there's at least one valid value
                    if len(valid_list_values) == 1 and self.query_labels[key].get("value_type") not in ["range", "multiple_choice"]: # Check for types that inherently can be lists
                        valid_needs[key] = valid_list_values[0]
                    else:
                        valid_needs[key] = valid_list_values
            elif isinstance(value, str):
                # If value is a string, check if it's in candidates
                if value in candidates:
                    valid_needs[key] = value
            # Other types are ignored (e.g. int, bool if not stringified by LLM as per prompt)
            
        return valid_needs

    def _create_system_message(self):
        """Create the system message with instructions for the AI."""
        # Prepare simplified labels structure for the prompt
        labels_structure = {}
        for label, data in self.query_labels.items():
            if "candidates" in data:
                labels_structure[label] = data["candidates"]
        
        labels_json = json.dumps(labels_structure, indent=2)
        
        return f"""
        You are an AI assistant specializing in extracting EXPLICIT car requirements from user messages.
        
        Your task is to analyze the user message and extract car requirements that are DIRECTLY MENTIONED,
        based on these available categories and their potential candidate values:
        {labels_json}
        
        INSTRUCTIONS:
        - ONLY extract requirements that are EXPLICITLY mentioned by the user.
        - DO NOT infer requirements that aren't directly stated.
        - For each identified requirement, use the exact key from the provided categories.
        - The value for a key should be based on the candidate values provided for that category.
           - If the user explicitly mentions MULTIPLE candidate values for the SAME category that all apply, collect these values into a LIST for that key.
           - If the user mentions a single value, use that single value directly (not in a list).
           - For value_type is "range", please be careful, if it covered multiple values, you should return a list of string values.
           - For value_type is "range" or "exact", please be careful about the statement, like "more than", "no more than", "at most", "at least", "below". your value should match that, and take care of the value boundary. 
        - Return the extracted requirements as a flat JSON object. Keys should map to either a single string value or a list of string values.
        - If no explicit requirements are mentioned, return an empty object {{}}.
        
        EXAMPLES:
        - When user says "I want a sedan with good fuel economy.", you should return {{"vehicle_category_top": "sedan", "fuel_consumption_alias": "low"}}
        - When user says "I need a car with 7 seats.", you should return {{"seat_layout": "7-seat"}}
        - When user says "My budget is below 30000", you should return {{"prize": ["below 10,000", "10,000~20,000", "20,000~30,000"]}}
        - When user says "My ideal car should have at least 4 airbags", you should return {{"airbag_count": ["4", "6", "8", "10", "above 10"]}}
        - When user says "I'm looking for a Japanese or a German car.", you should return {{"brand_country": ["japan", "germany"]}}
        - When user says "I'd like to have a car with high cold resistance", you should return {{"cold_resistance": "high"}}, as it's explicitly mentioned by the user
        NEGATIVE EXAMPLES:
        - When user says "I'm not good at parking", you should not return {{"remote_parking": "yes"}} or {{"auto_parking": "yes"}} as it's not explicitly mentioned by the user
        - When user says "I live in a cold country", you should not return {{"cold_resistance": "yes"}} as it's not explicitly mentioned by the user
        
        Only return the JSON object with extracted requirements. Do not include explanations.
        """

if __name__ == "__main__":
    # The ExplicitNeedsExtractor will now attempt to load QueryLabels.json 
    # from ../Config/QueryLabels.json (relative to this script's location)
    # or ./Config/QueryLabels.json (relative to current working directory) as a fallback.
    
    # Ensure QueryLabels.json exists in the correct location and has the expected content
    # for these tests to pass, especially the assertions in test_validation_cases.

    print("--- Explicit Needs Extractor Test ---")
    
    # Initialize the extractor. It will try to load QueryLabels.json as per its __init__ method.
    extractor = ExplicitNeedsExtractor()

    # If QueryLabels.json was not found or is empty, extractor.query_labels will be {}.
    # This will affect the behavior of the tests below.
    if not extractor.query_labels:
        print("\nWarning: QueryLabels.json was not loaded or is empty. Tests may not behave as expected.")
        # Constructing absolute paths for clarity in the warning message
        script_dir = os.path.dirname(__file__)
        expected_primary_path = os.path.join(script_dir, "../Config/QueryLabels.json")
        expected_fallback_path = os.path.join(os.getcwd(), "Config/QueryLabels.json")
        print(f"Attempted primary load path: {os.path.abspath(expected_primary_path)}")
        print(f"Attempted fallback load path (if primary failed or not found from script's perspective): {os.path.abspath(expected_fallback_path)}")
        print("Please ensure QueryLabels.json is correctly placed and populated for comprehensive testing.\n")

    # The test_messages will run, using the loaded query_labels (or an empty dict if load failed).
    # Results will depend on the LLM's interpretation based on the provided labels.
    test_messages = [
        {"id": 1, "message": "I want a red sedan with good fuel economy.", "note": "Simple case, two valid needs"},
        {"id": 2, "message": "I need a car with 7 seats and it must be a Japanese or a German brand.", "note": "List value for brand_country"},
        {"id": 3, "message": "My budget is below 30000, and I'd prefer an SUV. Safety is key, so at least 6 airbags.", "note": "Range for prize and airbag_count (LLM should expand)"},
        {"id": 4, "message": "I'm looking for a blue car, maybe a sports_car. Also, it must be cheap.", "note": "One valid color, one valid type, 'cheap' is not a direct candidate for 'prize' as a single word"},
        {"id": 5, "message": "I want a vehicle with automatic transmission and a sunroof.", "note": "Keys not in typical QueryLabels, should return empty or only valid if any."},
        {"id": 6, "message": "A black or white SUV, or maybe a silver pickup_truck. For power, I'm thinking electric.", "note": "Multiple valid values for color and type potential"},
        {"id": 7, "message": "I want something that's not a sedan and not too expensive.", "note": "Negative constraints, current model likely won't extract. 'not too expensive' is vague."},
        {"id": 8, "message": "A car from USA or Korea, must have 4 airbags or 6 airbags.", "note": "Multiple valid items for brand and airbags"},
        {"id": 9, "message": "I need a very_low fuel consumption car.", "note": "Specific candidate for fuel_consumption_alias"},
        {"id": 10, "message": "I need a 5-seat car, but the color should be purple and the price around 25,000.", "note": "Valid seat, invalid color, 'around 25000' needs LLM to map to prize candidate."},
        {"id": 11, "message": "A car that can seat more_than_7_seats and has 2 airbags.", "note": "Using candidates directly if they are in QueryLabels."},
        {"id": 12, "message": "I need a hybrid with medium fuel_consumption_alias and from france.", "note": "Mixed case in key for fuel consumption, valid country if in QueryLabels."},
        {"id": 13, "message": "Just a car.", "note": "No specific needs."},
        {"id": 14, "message": "I like sports_car and pickup_truck from japan.", "note": "Multiple vehicle types, one brand if in QueryLabels."},
    ]

    print("\n--- Running Test Cases (May make OpenAI API calls) ---")
    for item in test_messages:
        print(f"\nTest Case ID: {item['id']} - Note: {item['note']}")
        print(f"User Message: \"{item['message']}\"")
        
        try:
            extracted_needs = extractor.extract_explicit_needs(item["message"])
            print(f"Extracted Needs: {extracted_needs}")
        except Exception as e:
            print(f"Error during extraction: {e}")
            if "OPENAI_API_KEY" in str(e) or "API key" in str(e):
                print("OpenAI API key not found or invalid. Skipping live API call tests.")
                print("To run these tests, ensure your OPENAI_API_KEY environment variable is set.")
                break 
            else:
                raise
                
    print("\n--- Test Scenario for _validate_and_filter_needs directly (Uses loaded QueryLabels) ---")
    # The assertions in these test_validation_cases are highly dependent on the content of the 
    # QueryLabels.json file that the extractor instance has loaded.
    # If the loaded query_labels is empty or doesn't match the structure assumed by these tests,
    # they may fail or behave unexpectedly.
    # Ensure your QueryLabels.json has at least:
    # vehicle_category_top, fuel_consumption_alias, brand_country, color, prize, airbag_count
    # with candidates similar to the original mock_query_labels_content for these tests to be meaningful.
    
    test_validation_cases = [
        {
            "name": "All valid, single values",
            "input": {"vehicle_category_top": "sedan", "fuel_consumption_alias": "low"},
            "expected": {"vehicle_category_top": "sedan", "fuel_consumption_alias": "low"}
        },
        {
            "name": "Valid list value",
            "input": {"brand_country": ["japan", "germany"]},
            "expected": {"brand_country": ["japan", "germany"]}
        },
        {
            "name": "Mixed valid/invalid in list",
            "input": {"brand_country": ["japan", "sweden", "germany"]}, # sweden would be invalid if not in loaded candidates
            "expected_if_sweden_invalid": {"brand_country": ["japan", "germany"]}, # This is the typical expectation
            "note": "Expected output depends on 'sweden' being absent from 'brand_country.candidates' in loaded QueryLabels.json"
        },
        {
            "name": "List reduced to single valid value (non-range/multiple_choice type)",
            "input": {"color": ["red", "yellow"]}, # yellow would be invalid if not in loaded candidates
            "expected_if_yellow_invalid": {"color": "red"},
            "note": "Expected output depends on 'yellow' being absent from 'color.candidates' and 'color.value_type' not being 'range' or 'multiple_choice'"
        },
        {
            "name": "List reduced to single valid value (range/multiple_choice type should remain list)",
            "input": {"prize": ["10,000~20,000", "100,000~200,000"]}, # 2nd invalid if not in candidates
            "expected_if_2nd_invalid": {"prize": ["10,000~20,000"]},
            "note": "Expected output depends on '100,000~200,000' being absent from 'prize.candidates' and 'prize.value_type' being 'range' or 'multiple_choice'"
        },
        {
            "name": "List of one valid (range type), should remain list",
            "input": {"airbag_count": ["6"]}, 
            "expected": {"airbag_count": ["6"]},
            "note": "Expected output depends on '6' being in 'airbag_count.candidates' and its 'value_type' being 'range' or 'multiple_choice'"
        },
        {
            "name": "Single invalid value",
            "input": {"vehicle_category_top": "bicycle"}, # bicycle invalid if not in candidates
            "expected": {},
            "note": "Expected output depends on 'bicycle' being absent from 'vehicle_category_top.candidates'"
        },
        {
            "name": "Invalid key",
            "input": {"transmission_type": "automatic"}, # key itself is not in QueryLabels
            "expected": {}
        },
        {
            "name": "Empty input",
            "input": {},
            "expected": {}
        },
        {
            "name": "All invalid in list",
            "input": {"brand_country": ["sweden", "italy"]}, # both invalid if not in candidates
            "expected": {},
            "note": "Expected output depends on 'sweden' and 'italy' being absent from 'brand_country.candidates'"
        },
        {
            "name": "Non-string value in list (should be filtered out if not in string candidates)",
            "input": {"brand_country": ["japan", 123, "germany"]},
            "expected_if_123_invalid": {"brand_country": ["japan", "germany"]},
            "note": "Expected output depends on '123' (as string or type) not being a valid candidate"
        }
    ]

    # Dynamically add a test case for a key defined but without candidates in QueryLabels
    # This ensures the validation logic correctly skips such keys.
    temp_key_no_candidates = "feature_no_candidates_test"
    # Store if the key was already there to restore state later
    original_value_for_temp_key = None
    if temp_key_no_candidates in extractor.query_labels:
        original_value_for_temp_key = extractor.query_labels[temp_key_no_candidates]
    
    extractor.query_labels[temp_key_no_candidates] = {"description": "Feature without candidates (dynamically added for test)"}
    
    test_validation_cases.append({
        "name": f"Key '{temp_key_no_candidates}' with no candidates defined (dynamically added)",
        "input": {temp_key_no_candidates: "any_value"},
        "expected": {} # Should be empty as no candidates to validate against
    })
    
    print("\n--- Validating _validate_and_filter_needs directly (assertions depend on loaded QueryLabels.json content!) ---")
    all_tests_passed = True
    for case in test_validation_cases:
        print(f"\nTest: {case['name']}")
        if case.get("note"):
            print(f"Note: {case['note']}")
        print(f"Input: {case['input']}")
        
        result = extractor._validate_and_filter_needs(case["input"])
        print(f"Output: {result}")
        
        # Determine the correct expected value
        current_expected = None
        if "expected" in case:
            current_expected = case["expected"]
        elif "expected_if_sweden_invalid" in case and "sweden" not in extractor.query_labels.get("brand_country", {}).get("candidates", []):
            current_expected = case["expected_if_sweden_invalid"]
        elif "expected_if_yellow_invalid" in case and "yellow" not in extractor.query_labels.get("color", {}).get("candidates", []):
            current_expected = case["expected_if_yellow_invalid"]
        elif "expected_if_2nd_invalid" in case and "100,000~200,000" not in extractor.query_labels.get("prize", {}).get("candidates", []):
             current_expected = case["expected_if_2nd_invalid"]
        elif "expected_if_123_invalid" in case: # Assuming 123 (int or str) won't be in string candidates
             current_expected = case["expected_if_123_invalid"]

        if current_expected is not None:
            print(f"Expected: {current_expected}")
            try:
                assert result == current_expected, f"Assertion failed for {case['name']}. Output: {result}, Expected: {current_expected}. Loaded query_labels for relevant keys: brand_country: {extractor.query_labels.get('brand_country')}, color: {extractor.query_labels.get('color')}, prize: {extractor.query_labels.get('prize')}"
                print("Result: PASS")
            except AssertionError as e:
                print(f"Result: FAIL - {e}")
                all_tests_passed = False
        else:
            print("Warning: Could not determine expected value for this dynamic test case based on loaded QueryLabels.json. Skipping assertion.")


    # Clean up: Restore or remove the temporarily added key
    if original_value_for_temp_key is not None:
        extractor.query_labels[temp_key_no_candidates] = original_value_for_temp_key
    elif temp_key_no_candidates in extractor.query_labels: # If it was added by this script
        del extractor.query_labels[temp_key_no_candidates]
        
    print(f"\n--- Validation Tests Summary: {'ALL PASSED' if all_tests_passed else 'SOME FAILED'} ---")
    print("\n--- Explicit Needs Extractor Test End ---") 