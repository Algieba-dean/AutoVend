import json
import re
import os
from pathlib import Path
from basic_explicit_extractor import BasicExplicitExtractor

def run_test(test_name, test_func):
    """
    Run a test function and print the result.
    
    Args:
        test_name (str): The name of the test
        test_func (callable): The test function to run
    """
    try:
        test_func()
        print(f"✅ {test_name} passed")
    except AssertionError as e:
        print(f"❌ {test_name} failed: {e}")
    except Exception as e:
        print(f"❌ {test_name} failed with error: {e}")
    print("-" * 80)

def test_price_extraction():
    """Test extraction of price values."""
    extractor = BasicExplicitExtractor()
    
    # Test case 1: Direct price mention
    case_1 = "I want a car around $25,000"
    print(f"Input: {case_1}")
    result1 = extractor.extract_basic_explicit_needs(case_1)
    print(f"Output: {result1}")
    expected1 = {"prize": ["20,000 ~ 30,000"]}
    print(f"Expected: {expected1}")
    
    assert "prize" in result1, "Should extract price from direct mention"
    assert (
        "20,000 ~ 30,000" in result1["prize"]
    ), "Should map $25,000 to 20,000 ~ 30,000 range"
    
    print()
    
    # Test case 2: Price with 'k' notation
    case_2 = "My budget is 35k"
    print(f"Input: {case_2}")
    result2 = extractor.extract_basic_explicit_needs(case_2)
    print(f"Output: {result2}")
    expected2 = {"prize": ["30,000 ~ 40,000"]}
    print(f"Expected: {expected2}")
    
    assert "prize" in result2, "Should extract price from 'k' notation"
    assert (
        "30,000 ~ 40,000" in result2["prize"]
    ), "Should map 35k to 30,000 ~ 40,000 range"

def test_vehicle_category_extraction():
    """Test extraction of vehicle categories with hierarchy."""
    extractor = BasicExplicitExtractor()
    
    # Test case 1: Bottom-level category
    case_1 = "I'm looking for a compact SUV"
    print(f"Input: {case_1}")
    result1 = extractor.extract_basic_explicit_needs(case_1)
    print(f"Output: {result1}")
    expected1 = {
        "vehicle_category_bottom": ["compact suv"],
        "vehicle_category_middle": ["crossover suv"],
        "vehicle_category_top": ["suv"]
    }
    print(f"Expected: {expected1}")
    
    assert "vehicle_category_bottom" in result1, "Should extract bottom-level category"
    assert (
        "compact suv" in result1["vehicle_category_bottom"]
    ), "Should extract 'compact suv'"
    assert "vehicle_category_middle" in result1, "Should derive middle-level category"
    assert (
        "crossover suv" in result1["vehicle_category_middle"]
    ), "Should derive 'crossover suv'"
    assert "vehicle_category_top" in result1, "Should derive top-level category"
    assert "suv" in result1["vehicle_category_top"], "Should derive 'suv'"
    
    print()
    
    # Test case 2: Middle-level category
    case_2 = "I prefer a mid-size sedan"
    print(f"Input: {case_2}")
    result2 = extractor.extract_basic_explicit_needs(case_2)
    print(f"Output: {result2}")
    expected2 = {
        "vehicle_category_middle": ["mid-size sedan"],
        "vehicle_category_top": ["sedan"]
    }
    print(f"Expected: {expected2}")
    
    assert "vehicle_category_middle" in result2, "Should extract middle-level category"
    assert (
        "mid-size sedan" in result2["vehicle_category_middle"]
    ), "Should extract 'mid-size sedan'"
    assert "vehicle_category_top" in result2, "Should derive top-level category"
    assert "sedan" in result2["vehicle_category_top"], "Should derive 'sedan'"

def test_brand_country_extraction():
    """Test extraction of brand country values."""
    extractor = BasicExplicitExtractor()
    
    # Test case 1: Direct mention
    case_1 = "I want a Japanese car"
    print(f"Input: {case_1}")
    result1 = extractor.extract_basic_explicit_needs(case_1)
    print(f"Output: {result1}")
    expected1 = {"brand_country": ["japan"]}
    print(f"Expected: {expected1}")
    
    assert "brand_country" in result1, "Should extract brand country"
    assert "japan" in result1["brand_country"], "Should extract 'japan' from 'Japanese'"
    
    print()
    
    # Test case 2: Multiple countries
    case_2 = "I want a Japanese or German car"
    print(f"Input: {case_2}")
    result2 = extractor.extract_basic_explicit_needs(case_2)
    print(f"Output: {result2}")
    expected2 = {"brand_country": ["germany", "japan"]}
    print(f"Expected: {expected2}")
    
    assert "brand_country" in result2, "Should extract brand countries"
    assert "japan" in result2["brand_country"], "Should extract 'japan'"
    assert "germany" in result2["brand_country"], "Should extract 'germany'"

def test_powertrain_type_extraction():
    """Test extraction of powertrain types."""
    extractor = BasicExplicitExtractor()
    
    # Test case 1: Direct mention
    case_1 = "I want an electric car"
    print(f"Input: {case_1}")
    result1 = extractor.extract_basic_explicit_needs(case_1)
    print(f"Output: {result1}")
    expected1 = {"powertrain_type": ["battery electric vehicle"]}
    print(f"Expected: {expected1}")
    
    assert "powertrain_type" in result1, "Should extract powertrain type"
    assert (
        "battery electric vehicle" in result1["powertrain_type"]
    ), "Should extract 'battery electric vehicle' from 'electric car'"
    
    print()
    
    # Test case 2: Abbreviation
    case_2 = "Looking for EVs with good range"
    print(f"Input: {case_2}")
    result2 = extractor.extract_basic_explicit_needs(case_2)
    print(f"Output: {result2}")
    expected2 = {"powertrain_type": ["battery electric vehicle"]}
    print(f"Expected: {expected2}")
    
    assert (
        "powertrain_type" in result2
    ), "Should extract powertrain type from abbreviation"
    assert (
        "battery electric vehicle" in result2["powertrain_type"]
    ), "Should extract 'battery electric vehicle' from 'EV'"

def test_driving_range_extraction():
    """Test extraction of driving range values."""
    extractor = BasicExplicitExtractor()
    
    # Test case 1: Direct range mention
    case_1 = "I need a car with at least 500km range"
    print(f"Input: {case_1}")
    result1 = extractor.extract_basic_explicit_needs(case_1)
    print(f"Output: {result1}")
    expected1 = {"driving_range": ["400-800km"]}
    print(f"Expected: {expected1}")
    
    assert "driving_range" in result1, "Should extract driving range"
    assert (
        "400-800km" in result1["driving_range"]
    ), "Should map 500km to 400-800km range"
    
    print()
    
    # Test case 2: Range with 'above' expression
    case_2 = "Looking for a car that can go more than 800 kilometers"
    print(f"Input: {case_2}")
    result2 = extractor.extract_basic_explicit_needs(case_2)
    print(f"Output: {result2}")
    expected2 = {"driving_range": ["above 800km"]}
    print(f"Expected: {expected2}")
    
    assert "driving_range" in result2, "Should extract driving range"
    assert "above 800km" in result2["driving_range"], "Should extract 'above 800km'"

def test_energy_consumption_extraction():
    """Test extraction of energy consumption level."""
    extractor = BasicExplicitExtractor()
    
    # Test case: Direct mention
    case_1 = "I want a car with low energy consumption"
    print(f"Input: {case_1}")
    result1 = extractor.extract_basic_explicit_needs(case_1)
    print(f"Output: {result1}")
    expected1 = {"energy_consumption_level": ["low"]}
    print(f"Expected: {expected1}")
    
    assert (
        "energy_consumption_level" in result1
    ), "Should extract energy consumption level"
    assert (
        "low" in result1["energy_consumption_level"]
    ), "Should extract 'low' energy consumption level"

def test_complex_extraction():
    """Test extraction from complex sentences with multiple needs."""
    extractor = BasicExplicitExtractor()
    
    case = (
        "I'm looking for a mid-size sedan around $35,000. "
        "I prefer Japanese or German brands with good fuel efficiency. "
        "Electric vehicles are also interesting if they have at least 400km range."
    )
    print(f"Input: {case}")
    
    result = extractor.extract_basic_explicit_needs(case)
    print(f"Output: {result}")
    
    expected = {
        "vehicle_category_middle": ["mid-size sedan"],
        "vehicle_category_top": ["sedan"],
        "prize": ["30,000 ~ 40,000"],
        "brand_country": ["japan", "germany"],
        "energy_consumption_level": ["low"],
        "powertrain_type": ["battery electric vehicle"],
        "driving_range": ["400-800km"]
    }
    print(f"Expected: {expected}")
    
    assert "prize" in result, "Should extract price"
    assert "vehicle_category_middle" in result, "Should extract vehicle category"
    assert "brand_country" in result, "Should extract brand countries"
    assert (
        "energy_consumption_level" in result
    ), "Should extract energy consumption level"
    assert "powertrain_type" in result, "Should extract powertrain type"
    assert "driving_range" in result, "Should extract driving range"

def test_advanced_complex_extraction():
    """Test extraction from highly complex sentences with multiple needs expressed in varied ways."""
    extractor = BasicExplicitExtractor()
    
    case = (
        "I'm considering either a compact SUV or a crossover with good passenger space. "
        "My budget is flexible but preferably below $40k, though I could go up to $45,000 for the right vehicle. "
        "I want something fuel-efficient, possibly a hybrid or even a full electric if it has at least 500km range. "
        "I'm interested in European brands, especially German engineering, though Japanese reliability is appealing too. "
        "For daily commuting in the city with occasional long-distance weekend trips."
    )
    print(f"Input: {case}")
    
    result = extractor.extract_basic_explicit_needs(case)
    print(f"Output: {result}")
    
    expected = {
        "prize": ["30,000 ~ 40,000"],
        "vehicle_category_bottom": ["compact suv"],
        "vehicle_category_middle": ["crossover suv"],
        "vehicle_category_top": ["suv"],
        "brand_area": ["european"],
        "brand_country": ["germany", "japan"],
        "energy_consumption_level": ["low"],
        "driving_range": ["400-800km"]
    }
    print(f"Expected: {expected}")
    
    assert "prize" in result, "Should extract price range"
    assert "30,000 ~ 40,000" in result["prize"], "Should correctly map budget to range"
    
    assert "vehicle_category_bottom" in result, "Should extract bottom-level category"
    assert (
        "compact suv" in result["vehicle_category_bottom"]
    ), "Should extract compact SUV"
    
    assert "vehicle_category_middle" in result, "Should extract middle-level category"
    assert (
        "crossover suv" in result["vehicle_category_middle"]
    ), "Should extract crossover SUV"
    
    assert "vehicle_category_top" in result, "Should extract top-level category"
    assert "suv" in result["vehicle_category_top"], "Should extract SUV"
    
    assert "brand_area" in result, "Should extract brand area"
    assert "european" in result["brand_area"], "Should extract European area"
    
    assert "brand_country" in result, "Should extract brand country"
    assert "germany" in result["brand_country"], "Should extract Germany"
    assert "japan" in result["brand_country"], "Should extract Japan"
    
    assert (
        "energy_consumption_level" in result
    ), "Should extract energy consumption level"
    assert (
        "low" in result["energy_consumption_level"]
    ), "Should extract low energy consumption"
    
    assert "driving_range" in result, "Should extract driving range"
    assert "400-800km" in result["driving_range"], "Should extract correct range"

def test_mixed_preferences_extraction():
    """Test extraction with mixed preferences, including negations and specific requirements."""
    extractor = BasicExplicitExtractor()
    
    case = (
        "I'm in the market for a new car around $25k-$30k. "
        "I definitely want an EV with good range - at least 400km, preferably more. "
        "I don't need a large vehicle, something like a compact or mid-size would be perfect. "
        "I prefer Asian manufacturers, especially Japanese brands for their reliability. "
        "Efficiency is really important to me, as I'm conscious about energy consumption."
    )
    print(f"Input: {case}")
    
    result = extractor.extract_basic_explicit_needs(case)
    print(f"Output: {result}")
    
    expected = {
        "prize": ["20,000 ~ 30,000"],
        "powertrain_type": ["battery electric vehicle"],
        "driving_range": ["400-800km"],
        "brand_area": ["asian"],
        "brand_country": ["japan"],
        "energy_consumption_level": ["low"]
    }
    print(f"Expected: {expected}")
    
    assert "prize" in result, "Should extract price"
    assert "20,000 ~ 30,000" in result["prize"], "Should extract correct price range"
    
    assert "powertrain_type" in result, "Should extract powertrain type"
    assert (
        "battery electric vehicle" in result["powertrain_type"]
    ), "Should extract EV powertrain"
    
    assert "driving_range" in result, "Should extract driving range"
    assert (
        "400-800km" in result["driving_range"]
    ), "Should extract correct range based on 'at least 400km'"
    
    assert (
        "brand_area" in result or "brand_country" in result
    ), "Should extract brand origin"
    if "brand_area" in result:
        assert "asian" in result["brand_area"], "Should extract Asian manufacturers"
    if "brand_country" in result:
        assert "japan" in result["brand_country"], "Should extract Japanese brands"
    
    assert "energy_consumption_level" in result, "Should extract energy consumption"
    assert (
        "low" in result["energy_consumption_level"]
    ), "Should extract low energy consumption"

def test_contextual_extraction():
    """Test extraction that requires understanding contextual clues."""
    extractor = BasicExplicitExtractor()
    
    case = (
        "I'm looking for something practical for a family of four. "
        "Ideally around $35,000, but I could stretch to $40k for the right vehicle. "
        "I need good interior space and cargo capacity. "
        "I've heard electric vehicles are good these days, especially with driving ranges over 500km. "
        "Fuel efficiency is important since I drive a lot for work."
    )
    print(f"Input: {case}")
    
    result = extractor.extract_basic_explicit_needs(case)
    print(f"Output: {result}")
    
    expected = {
        "prize": ["30,000 ~ 40,000"],
        "powertrain_type": ["battery electric vehicle"],
        "driving_range": ["400-800km"],
        "energy_consumption_level": ["low"]
    }
    print(f"Expected: {expected}")
    
    assert "prize" in result, "Should extract price range"
    assert "30,000 ~ 40,000" in result["prize"], "Should extract correct price range"
    
    assert "powertrain_type" in result, "Should extract powertrain"
    assert (
        "battery electric vehicle" in result["powertrain_type"]
    ), "Should extract EV from context"
    
    assert "driving_range" in result, "Should extract driving range"
    assert (
        "400-800km" in result["driving_range"]
    ), "Should extract appropriate range from '500km' mention"
    
    assert "energy_consumption_level" in result, "Should extract energy consumption"
    assert (
        "low" in result["energy_consumption_level"]
    ), "Should extract low consumption from fuel efficiency context"

def test_synonym_expressions():
    """Test extraction from various synonymous expressions for the same preferences."""
    extractor = BasicExplicitExtractor()
    
    # Test synonyms for price
    price_case = (
        "My spending limit is twenty-five thousand. "
        "I don't want to shell out more than 25 grand for a car."
    )
    print(f"Input: {price_case}")
    price_result = extractor.extract_basic_explicit_needs(price_case)
    print(f"Output: {price_result}")
    price_expected = {"prize": ["20,000 ~ 30,000"]}
    print(f"Expected: {price_expected}")
    
    assert "prize" in price_result, "Should extract price from alternative expressions"
    assert (
        "20,000 ~ 30,000" in price_result["prize"]
    ), "Should map alternative price expressions correctly"
    
    print()
    
    # Test synonyms for vehicle categories
    category_case = (
        "I'm in the market for a people carrier that's good for family trips. "
        "Something like a minivan or family hauler would be ideal."
    )
    print(f"Input: {category_case}")
    category_result = extractor.extract_basic_explicit_needs(category_case)
    print(f"Output: {category_result}")
    category_expected = {"vehicle_category_top": ["mpv"]}
    print(f"Expected: {category_expected}")
    
    assert (
        "vehicle_category_top" in category_result
    ), "Should extract top category from synonyms"
    assert (
        "mpv" in category_result["vehicle_category_top"]
    ), "Should recognize 'people carrier' as MPV"
    
    print()
    
    # Test synonyms for powertrain
    powertrain_case = (
        "I'm interested in a battery-powered automobile. "
        "Something that runs on electricity rather than petrol."
    )
    print(f"Input: {powertrain_case}")
    powertrain_result = extractor.extract_basic_explicit_needs(powertrain_case)
    print(f"Output: {powertrain_result}")
    powertrain_expected = {"powertrain_type": ["battery electric vehicle"]}
    print(f"Expected: {powertrain_expected}")
    
    assert (
        "powertrain_type" in powertrain_result
    ), "Should extract powertrain from synonyms"
    assert (
        "battery electric vehicle" in powertrain_result["powertrain_type"]
    ), "Should recognize electric synonyms"
    
    print()
    
    # Test synonyms for efficiency
    efficiency_case = (
        "I want something that sips fuel and is economical to run. "
        "A car that doesn't guzzle gas would be perfect."
    )
    print(f"Input: {efficiency_case}")
    efficiency_result = extractor.extract_basic_explicit_needs(efficiency_case)
    print(f"Output: {efficiency_result}")
    efficiency_expected = {"energy_consumption_level": ["low"]}
    print(f"Expected: {efficiency_expected}")
    
    assert (
        "energy_consumption_level" in efficiency_result
    ), "Should extract energy consumption from synonyms"
    assert (
        "low" in efficiency_result["energy_consumption_level"]
    ), "Should map economy expressions to low consumption"

def test_generalized_expressions():
    """Test extraction from generalized and vague expressions that should still map to specific attributes."""
    extractor = BasicExplicitExtractor()
    
    # Test generalized price references
    price_case = (
        "I'm looking for something in the mid-price range, not too expensive but not entry-level either."
    )
    print(f"Input: {price_case}")
    price_result = extractor.extract_basic_explicit_needs(price_case)
    print(f"Output: {price_result}")
    price_expected = {"prize_alias": ["mid-range"]}
    print(f"Expected: {price_expected}")
    
    assert (
        "prize_alias" in price_result
    ), "Should extract price alias from generalized expressions"
    
    print()
    
    # Test generalized category references
    category_case = (
        "I need a bigger vehicle with room for the whole family, but not something huge."
    )
    print(f"Input: {category_case}")
    category_result = extractor.extract_basic_explicit_needs(category_case)
    print(f"Output: {category_result}")
    print(f"Expected: Might not extract specific category")
    
    print()
    
    # Test generalized origin preferences
    origin_case = (
        "I tend to prefer cars from across the Atlantic. Something with European flair."
    )
    print(f"Input: {origin_case}")
    origin_result = extractor.extract_basic_explicit_needs(origin_case)
    print(f"Output: {origin_result}")
    origin_expected = {"brand_area": ["european"]}
    print(f"Expected: {origin_expected}")
    
    assert (
        "brand_area" in origin_result
    ), "Should extract brand area from generalized geographic references"
    assert (
        "european" in origin_result["brand_area"]
    ), "Should recognize European reference"
    
    print()
    
    # Test generalized efficiency expressions
    efficiency_case = (
        "I'm concerned about the environment and want something that's gentle on resources."
    )
    print(f"Input: {efficiency_case}")
    efficiency_result = extractor.extract_basic_explicit_needs(efficiency_case)
    print(f"Output: {efficiency_result}")
    efficiency_expected = {"energy_consumption_level": ["low"]}
    print(f"Expected: {efficiency_expected}")
    
    assert (
        "energy_consumption_level" in efficiency_result
    ), "Should extract energy level from environmental concerns"
    assert (
        "low" in efficiency_result["energy_consumption_level"]
    ), "Should map environmental concerns to low consumption"

def test_mixed_synonym_generalized_expressions():
    """Test extraction from a mix of synonym and generalized expressions."""
    extractor = BasicExplicitExtractor()
    
    case = (
        "I'm after something that won't break the bank - thinking under $30K. "
        "A sleek four-door would be nice, but I'm open to a crossover too. "
        "It should have decent get-up-and-go without being a gas guzzler. "
        "I've always been partial to those reliable Japanese brands, but German engineering is solid too. "
        "Zero emissions would be a huge plus if it can go the distance."
    )
    print(f"Input: {case}")
    
    result = extractor.extract_basic_explicit_needs(case)
    print(f"Output: {result}")
    
    expected = {
        "prize": ["20,000 ~ 30,000"],
        "vehicle_category_top": ["sedan"],
        "vehicle_category_middle": ["crossover suv"],
        "energy_consumption_level": ["low"],
        "brand_country": ["japan", "germany"],
        "powertrain_type": ["battery electric vehicle"]
    }
    print(f"Expected: {expected}")
    
    # Price checks
    assert "prize" in result, "Should extract price from colloquial expression"
    
    # Vehicle category checks
    assert (
        "vehicle_category_top" in result
    ), "Should extract vehicle category from alternative expressions"
    assert "sedan" in result["vehicle_category_top"] or "crossover suv" in result.get(
        "vehicle_category_middle", []
    ), "Should recognize 'four-door' or 'crossover'"
    
    # Efficiency checks
    assert (
        "energy_consumption_level" in result
    ), "Should extract consumption from negative expressions"
    assert (
        "low" in result["energy_consumption_level"]
    ), "Should recognize 'gas guzzler' negation"
    
    # Brand origin checks
    assert (
        "brand_country" in result
    ), "Should extract brand countries from preference expressions"
    assert "japan" in result["brand_country"], "Should recognize Japanese reference"
    assert "germany" in result["brand_country"], "Should recognize German reference"
    
    # Powertrain checks - this is more implicit
    assert (
        "powertrain_type" in result
    ), "Should extract powertrain from emissions reference"
    assert (
        "battery electric vehicle" in result["powertrain_type"]
    ), "Should map 'zero emissions' to EV"

def test_cultural_expressions():
    """Test extraction from culturally specific or idiomatic expressions."""
    extractor = BasicExplicitExtractor()
    
    case = (
        "I'm tired of feeding the pump - gas prices are killing me. "
        "Time for something with amazing mileage or maybe a completely electric ride. "
        "Nothing flashy, just a practical daily driver that won't cost an arm and a leg. "
        "I've heard good things about those far east automakers for reliability."
    )
    print(f"Input: {case}")
    
    result = extractor.extract_basic_explicit_needs(case)
    print(f"Output: {result}")
    
    expected = {
        "brand_area": ["asian"],
        "powertrain_type": ["battery electric vehicle"],
        "energy_consumption_level": ["low"],
        "prize_alias": ["economy"]
    }
    print(f"Expected: {expected}")
    
    # Energy consumption check
    assert (
        "energy_consumption_level" in result
    ), "Should extract energy level from idioms"
    assert (
        "low" in result["energy_consumption_level"]
    ), "Should map 'amazing mileage' to low consumption"
    
    # Powertrain check
    assert (
        "powertrain_type" in result
    ), "Should extract powertrain from casual expressions"
    assert (
        "battery electric vehicle" in result["powertrain_type"]
    ), "Should recognize 'electric ride'"
    
    # Price check
    assert "prize_alias" in result, "Should extract price alias from idioms"
    
    # Origin check
    assert (
        "brand_area" in result
    ), "Should extract brand area from geographical expressions"
    assert "asian" in result["brand_area"], "Should map 'far east' to Asian"


if __name__ == "__main__":
    print("Starting BasicExplicitExtractor tests...\n")

    run_test("Test 1: Price Extraction", test_price_extraction)
    run_test("Test 2: Vehicle Category Extraction", test_vehicle_category_extraction)
    run_test("Test 3: Brand Country Extraction", test_brand_country_extraction)
    run_test("Test 4: Powertrain Type Extraction", test_powertrain_type_extraction)
    run_test("Test 5: Driving Range Extraction", test_driving_range_extraction)
    run_test(
        "Test 6: Energy Consumption Extraction", test_energy_consumption_extraction
    )
    run_test("Test 7: Complex Extraction", test_complex_extraction)
    run_test("Test 8: Advanced Complex Extraction", test_advanced_complex_extraction)
    run_test("Test 9: Mixed Preferences Extraction", test_mixed_preferences_extraction)
    run_test("Test 10: Contextual Extraction", test_contextual_extraction)
    run_test("Test 11: Synonym Expressions", test_synonym_expressions)
    run_test("Test 12: Generalized Expressions", test_generalized_expressions)
    run_test(
        "Test 13: Mixed Synonym & Generalized Expressions",
        test_mixed_synonym_generalized_expressions,
    )
    run_test("Test 14: Cultural Expressions", test_cultural_expressions)

    print("\nAll tests completed.") 