class NeedsStatus:
    def __init__(self):
        self.introduced_explicit_needs = dict() # for each matched car model, will record the needs which is already mentioned by us
        self.asked_implicit_needs = dict() # for each matched car model, will record the needs which is asked by us
        self.no_comments_needs = ["vehicle_category_top","vehicle_category_middle","brand_area","brand_country"] # no comments, can't introduce
        self.ignore_introduction_needs = ["brand",] # too easy to introduce

    def mapping_alias_needs(self,needs):
        if "_alias" not in needs:
            return needs
        return str(needs).replace("_alias","")

    def should_explicit_introduce(self,needs_name,car_model):
        mappinged_needs_name = self.mapping_alias_needs(needs_name)
        if mappinged_needs_name in self.no_comments_needs:
            return False
        if mappinged_needs_name in self.ignore_introduction_needs:
            return False

        if car_model not in self.introduced_explicit_needs:
            self.introduced_explicit_needs[car_model] = []
        if needs_name in self.introduced_explicit_needs.get(car_model,[]):
            return False
        return True
    def introduce_explicit_needs(self,needs_name,car_model):
        self.introduced_explicit_needs[car_model].append(needs_name)

    def should_implicit_ask(self,needs_name, needs_value):
        if needs_name not in self.asked_implicit_needs:
            return True
        if self.asked_implicit_needs.get(needs_name) != needs_value:
            return True
        return False
    def ask_implicit_needs(self,needs_name, needs_value):
        self.asked_implicit_needs[needs_name] = needs_value

    def get_car_model_comment_infos(self, explicit_needs: dict, car_model_infos: list[dict]) -> list[dict]:
        """Filters car_model_infos to keep only explicit needs and the car_model.

        For each info object in car_model_infos:
        - Always keeps the top-level 'car_model' label.
        - Flattens the structure: sub-labels from 'PriciseLabels', 'AmbiguousLabels',
          and 'KeyDetails' are brought to the top level of the new dictionary
          if their label name matches a key in explicit_needs.
        """
        filtered_results = []
        if not car_model_infos:
            return filtered_results

        explicit_need_comments = set( )
        for key, value in explicit_needs.items():
            mappinged_key = self.mapping_alias_needs(key)
            if mappinged_key in self.no_comments_needs:
                continue
            if mappinged_key in self.ignore_introduction_needs:
                continue
            explicit_need_comments.add(mappinged_key+"_comments")
        
        # Define the nested sections to check for explicit needs
        for info_dict in car_model_infos:
            filtered_info = {}
            filtered_info["car_model"] = info_dict["car_model"]

            pricise_infos = info_dict.get("PriciseLabels",{})
            ambiguous_infos = info_dict.get("AmbiguousLabels",{})
            key_details = info_dict.get("KeyDetails",{})

            for label, value in pricise_infos.items():
                if label not in explicit_need_comments:
                    continue
                filtered_info[label]=value
            for label, value in ambiguous_infos.items():
                if label not in explicit_need_comments:
                    continue
                filtered_info[label]=value

            filtered_info["key_details"] = key_details["key_details"]
            
            filtered_results.append(filtered_info)
            
        return filtered_results

if __name__ == "__main__":
    # Initialize test instance
    needs_status = NeedsStatus()
    
    # Test case 1: mapping_alias_needs
    print("\nTest Case 1: mapping_alias_needs")
    test_needs = "color_alias"
    expected = "color"
    result = needs_status.mapping_alias_needs(test_needs)
    print(f"Input: {test_needs}")
    print(f"Expected: {expected}")
    print(f"Actual: {result}")
    assert result == expected, "Test case 1 failed"
    
    # Test case 2: should_explicit_introduce
    print("\nTest Case 2: should_explicit_introduce")
    car_model = "Model_A"
    needs_name = "color"
    expected = True
    result = needs_status.should_explicit_introduce(needs_name, car_model)
    print(f"Input: needs_name={needs_name}, car_model={car_model}")
    print(f"Expected: {expected}")
    print(f"Actual: {result}")
    assert result == expected, "Test case 2.1 failed"
    
    # Test no_comments_needs case
    needs_name = "vehicle_category_top"
    expected = False
    result = needs_status.should_explicit_introduce(needs_name, car_model)
    print(f"\nInput: needs_name={needs_name}, car_model={car_model}")
    print(f"Expected: {expected}")
    print(f"Actual: {result}")
    assert result == expected, "Test case 2.2 failed"
    
    # Test case 3: should_implicit_ask
    print("\nTest Case 3: should_implicit_ask")
    needs_name = "price"
    needs_value = "high"
    expected = True
    result = needs_status.should_implicit_ask(needs_name, needs_value)
    print(f"Input: needs_name={needs_name}, needs_value={needs_value}")
    print(f"Expected: {expected}")
    print(f"Actual: {result}")
    assert result == expected, "Test case 3.1 failed"
    
    # Test same value case
    needs_status.ask_implicit_needs(needs_name, needs_value)
    result = needs_status.should_implicit_ask(needs_name, needs_value)
    expected = False
    print(f"\nInput: needs_name={needs_name}, needs_value={needs_value} (after asking)")
    print(f"Expected: {expected}")
    print(f"Actual: {result}")
    assert result == expected, "Test case 3.2 failed"
    
    print("\nAll test cases passed successfully!")

    print("\nTest Case 4: get_car_model_comment_infos")
    needs_status_for_comments = NeedsStatus()

    explicit_needs_for_test = {
        "prize": "high", 
        "powertrain_type": "gasoline", 
        "brand": "Audi",  # This will be ignored for _comments due to ignore_introduction_needs
        "color": "black"  # A regular need to generate a _comments entry
    }
    car_model_infos_for_test = [
        {
            'car_model': 'Audi-Q7',
            'PriciseLabels': {
                'prize': '60,000~100,000', # Original value, not directly used by this function's logic for selection
                'prize_comments': 'Prize comments for Q7', # Should be picked
                'color': 'Black',
                'color_comments': 'Color comments for Q7', # Should be picked
                'brand_comments': 'Brand comments for Q7 (should NOT be picked)',
                'fuel_type_comments': 'Fuel comments (not in explicit_needs_for_test, so fuel_type_comments not in set)'
            },
            'AmbiguousLabels': {
                'size': 'Large', # Should be picked
                'size_comments': 'Size comments for Q7', # Should be picked
                'comfort_level': 'High', # Should be picked
                'comfort_level_comments': 'Comfort comments for Q7' # Should be picked
            },
            'KeyDetails': {
                'key_details': 'Key details for Audi-Q7', # Should be picked
                'some_other_detail': 'This other detail in KeyDetails is not picked up'
            }
        },
        {
            'car_model': 'BMW-X5',
            'PriciseLabels': {
                'prize_comments': 'Prize comments for X5', # Should be picked
                'color_comments': 'Color comments for X5',   # Should be picked
                'powertrain_type_comments': 'Powertrain comments for X5', # Should be picked
                'another_label_comments': 'Another comments (not relevant to explicit_needs_for_test)'
            },
            'AmbiguousLabels': {
                'performance': 'High',
                'performance_comments': 'Performance comments for X5'
            },
            'KeyDetails': {
                'key_details': 'Key details for BMW-X5'
            }
        },
        {
             'car_model': 'Mercedes-GLE',
             'PriciseLabels': { # No matching _comments for explicit_needs_for_test
                'luxury_feature_comments': 'Luxury details'
             },
             'AmbiguousLabels':{
                'style_comments': 'Style for GLE'
             },
             'KeyDetails':{
                'key_details': 'Details for GLE'
             }
        }
    ]

    # Expected explicit_need_comments based on explicit_needs_for_test:
    # "prize" -> "prize_comments"
    # "powertrain_type" -> "powertrain_type_comments"
    # "brand" -> ignored by ignore_introduction_needs
    # "color" -> "color_comments"
    # So, set = {"prize_comments", "powertrain_type_comments", "color_comments"}

    expected_output_for_test = [
        {
            "car_model": "Audi-Q7",
            "key_details": "Key details for Audi-Q7",
            "prize_comments": "Prize comments for Q7",
            "color_comments": "Color comments for Q7",
            "size": "Large",
            "size_comments": "Size comments for Q7",
            "comfort_level": "High",
            "comfort_level_comments": "Comfort comments for Q7"
        },
        {
            "car_model": "BMW-X5",
            "key_details": "Key details for BMW-X5",
            "prize_comments": "Prize comments for X5",
            "color_comments": "Color comments for X5",
            "powertrain_type_comments": "Powertrain comments for X5",
            "performance": "High",
            "performance_comments": "Performance comments for X5"
        },
        {
            "car_model": "Mercedes-GLE",
            "key_details": "Details for GLE",
            "style_comments": "Style for GLE" # Only from AmbiguousLabels, as no PriciseLabels matched
        }
    ]

    actual_output = needs_status_for_comments.get_car_model_comment_infos(explicit_needs_for_test, car_model_infos_for_test)
    
    print(f"\n--- Test Case 4: get_car_model_comment_infos ---")
    # print(f"Input explicit_needs: {explicit_needs_for_test}")
    # print(f"Input car_model_infos: {car_model_infos_for_test}")
    print(f"Expected output: {expected_output_for_test}")
    print(f"Actual output:   {actual_output}")

    assert len(actual_output) == len(expected_output_for_test), \
        f"Test Case 4 failed: Length mismatch. Expected {len(expected_output_for_test)}, got {len(actual_output)}"
    
    for i in range(len(actual_output)):
        # Comparing dictionaries directly works if keys and values are identical, regardless of order of keys within dict.
        assert actual_output[i] == expected_output_for_test[i], \
            f"Test Case 4 failed: Item {i} mismatch.\nExpected: {expected_output_for_test[i]}\nGot:      {actual_output[i]}"
    
    print("Test Case 4: get_car_model_comment_infos passed successfully!")

    
