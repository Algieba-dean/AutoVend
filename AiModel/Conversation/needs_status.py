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
    
