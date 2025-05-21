import json
import os
import re
from pathlib import Path
from typing import Dict, List, Tuple, Set, Any, Optional

class RangeExplicitExtractor:
    """
    Extract range values from user dialogue based on QueryLabels.json.
    This extractor handles labels with value_type "range", excluding prize, passenger_space_volume, and driving_range.
    """
    
    def __init__(self):
        """
        Initialize the RangeExplicitExtractor with labels loaded from QueryLabels.json.
        """
        # Load query labels from JSON file
        base_dir = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        query_labels_path = os.path.join(base_dir, "Config", "QueryLabels.json")
        
        with open(query_labels_path, 'r', encoding='utf-8') as f:
            self.query_labels = json.load(f)
            
        # Filter labels with value_type "range" excluding prize, passenger_space_volume, and driving_range
        self.range_labels = {}
        excluded_labels = {"prize", "passenger_space_volume", "driving_range"}
        
        for label, info in self.query_labels.items():
            if info.get("value_type") == "range" and label not in excluded_labels:
                self.range_labels[label] = info
                
        # Create regex patterns for each range label
        self.label_patterns = self._create_label_patterns()
        
    def _create_label_patterns(self) -> Dict[str, Dict[str, re.Pattern]]:
        """Create regex patterns for each range label."""
        label_patterns = {}
        
        for label, info in self.range_labels.items():
            patterns = {}
            
            # Create pattern for the label itself
            label_name = label.replace("_", " ")
            patterns["label"] = re.compile(rf'\b{label_name}\b', re.IGNORECASE)
            
            # Add common synonyms based on label name
            if label == "trunk_volume":
                patterns["synonyms"] = re.compile(r'\b(trunk|boot|cargo|luggage)\s*(space|capacity|volume|size)\b', re.IGNORECASE)
            elif label == "wheelbase":
                patterns["synonyms"] = re.compile(r'\b(wheelbase|axle distance|between wheels|wheel distance)\b', re.IGNORECASE)
            elif label == "chassis_height":
                patterns["synonyms"] = re.compile(r'\b(chassis|ground|ride)\s*(height|clearance)\b', re.IGNORECASE)
            elif label == "engine_displacement":
                patterns["synonyms"] = re.compile(r'\b(engine|motor)\s*(displacement|size|volume|capacity)\b', re.IGNORECASE)
            elif label == "motor_power":
                patterns["synonyms"] = re.compile(r'\b(motor|engine)\s*(power|output)\b', re.IGNORECASE)
            elif label == "battery_capacity":
                patterns["synonyms"] = re.compile(r'\b(battery|power)\s*(capacity|size|storage)\b', re.IGNORECASE)
            elif label == "fuel_tank_capacity":
                patterns["synonyms"] = re.compile(r'\b(fuel|gas|petrol|diesel)\s*(tank|capacity|volume)\b', re.IGNORECASE)
            elif label == "horsepower":
                patterns["synonyms"] = re.compile(r'\b(horse\s*power|hp|power|bhp)\b', re.IGNORECASE)
            elif label == "torque":
                patterns["synonyms"] = re.compile(r'\b(torque|nm|newton meter|newton-meter|n·m|pulling power)\b', re.IGNORECASE)
            elif label == "zero_to_one_hundred_km_h_acceleration_time":
                patterns["synonyms"] = re.compile(r'\b(0\s*-\s*100|zero to hundred|0 to 100|acceleration(\s*time)?|0\s*-\s*60|zero to sixty)\b', re.IGNORECASE)
            elif label == "top_speed":
                patterns["synonyms"] = re.compile(r'\b(top|max|maximum)\s*(speed|velocity)\b', re.IGNORECASE)
            elif label == "fuel_consumption":
                patterns["synonyms"] = re.compile(r'\b(fuel|gas|petrol|diesel)\s*(consumption|economy|efficiency|mileage)\b', re.IGNORECASE)
            elif label == "electric_consumption":
                patterns["synonyms"] = re.compile(r'\b(electric|electricity|energy)\s*(consumption|usage|efficiency)\b', re.IGNORECASE)
                
            # Create patterns for range values
            # Extract units and create patterns for specific units
            unit_pattern = self._extract_unit_pattern(label, info["candidates"][0])
            patterns["unit"] = unit_pattern
            
            # Create pattern for numeric values
            patterns["numeric"] = re.compile(r'(\d+(?:\.\d+)?)\s*(?:-|to|~)\s*(\d+(?:\.\d+)?)', re.IGNORECASE)
            patterns["single_numeric"] = re.compile(r'(\d+(?:\.\d+)?)', re.IGNORECASE)
            
            # Create patterns for specific candidates
            patterns["candidates"] = []
            for candidate in info["candidates"]:
                if candidate.lower() == "none":
                    continue
                # Escape special regex characters
                escaped_candidate = re.escape(candidate)
                patterns["candidates"].append(re.compile(rf'\b{escaped_candidate}\b', re.IGNORECASE))
                
            label_patterns[label] = patterns
            
        return label_patterns
    
    def _extract_unit_pattern(self, label: str, candidate: str) -> re.Pattern:
        """Extract the unit pattern from a candidate value."""
        # Define default units for common labels
        default_units = {
            "trunk_volume": r'l|liter|litre|liters|litres',
            "wheelbase": r'mm|millimeter|millimetre|millimeters|millimetres',
            "chassis_height": r'mm|millimeter|millimetre|millimeters|millimetres',
            "engine_displacement": r'l|liter|litre|liters|litres',
            "motor_power": r'kw|kilowatt|kilowatts',
            "battery_capacity": r'kwh|kw\s*h|kilowatt\s*hour|kilowatt-hour|kilowatt\s*hours|kilowatt-hours',
            "fuel_tank_capacity": r'l|liter|litre|liters|litres',
            "horsepower": r'hp|horsepower',
            "torque": r'n·m|nm|newton\s*meter|newton-meter|newton\s*meters|newton-meters',
            "zero_to_one_hundred_km_h_acceleration_time": r's|sec|second|seconds',
            "top_speed": r'km/h|kmh|kph|kilometers?\s*per\s*hour|kilometres?\s*per\s*hour',
            "fuel_consumption": r'l/100km|liters?\s*per\s*100km|litres?\s*per\s*100km',
            "electric_consumption": r'kwh/100km|kilowatt\s*hours?\s*per\s*100km|kilowatt-hours?\s*per\s*100km'
        }
        
        if label in default_units:
            return re.compile(rf'\b({default_units[label]})\b', re.IGNORECASE)
        
        # If no default unit, try to extract from candidate
        unit_match = re.search(r'[a-zA-Z·/]+$', candidate)
        if unit_match:
            unit = unit_match.group(0)
            return re.compile(rf'\b({re.escape(unit)})\b', re.IGNORECASE)
        
        # Fallback to simple pattern
        return re.compile(r'\b([a-zA-Z·/]+)\b', re.IGNORECASE)
    
    def _normalize_to_range(self, label: str, value: float) -> List[str]:
        """
        Normalize a single value to matching range candidates.
        
        Args:
            label: The label name
            value: The numeric value to normalize
        
        Returns:
            List of matching candidate ranges
        """
        matching_candidates = []
        
        for candidate in self.range_labels[label]["candidates"]:
            if candidate.lower() == "none":
                continue
                
            # Extract the numeric range from the candidate
            range_match = re.search(r'([\d.]+)(?:\s*-|~|\s+to\s+)([\d.]+)', candidate)
            below_match = re.search(r'below\s+([\d.]+)', candidate)
            above_match = re.search(r'above\s+([\d.]+)', candidate)
            
            if range_match:
                range_min = float(range_match.group(1).replace(',', ''))
                range_max = float(range_match.group(2).replace(',', ''))
                
                if range_min <= value <= range_max:
                    matching_candidates.append(candidate)
            elif below_match:
                threshold = float(below_match.group(1).replace(',', ''))
                if value < threshold:
                    matching_candidates.append(candidate)
            elif above_match:
                threshold = float(above_match.group(1).replace(',', ''))
                if value > threshold:
                    matching_candidates.append(candidate)
        
        return matching_candidates
    
    def _normalize_to_range_pair(self, label: str, min_value: float, max_value: float) -> List[str]:
        """
        Normalize a range of values to matching range candidates.
        
        Args:
            label: The label name
            min_value: The minimum value in the range
            max_value: The maximum value in the range
        
        Returns:
            List of matching candidate ranges
        """
        matching_candidates = []
        
        for candidate in self.range_labels[label]["candidates"]:
            if candidate.lower() == "none":
                continue
                
            # Extract the numeric range from the candidate
            range_match = re.search(r'([\d.]+)(?:\s*-|~|\s+to\s+)([\d.]+)', candidate)
            below_match = re.search(r'below\s+([\d.]+)', candidate)
            above_match = re.search(r'above\s+([\d.]+)', candidate)
            
            if range_match:
                range_min = float(range_match.group(1).replace(',', ''))
                range_max = float(range_match.group(2).replace(',', ''))
                
                # If ranges overlap
                if not (max_value < range_min or min_value > range_max):
                    matching_candidates.append(candidate)
            elif below_match:
                threshold = float(below_match.group(1).replace(',', ''))
                if min_value < threshold:
                    matching_candidates.append(candidate)
            elif above_match:
                threshold = float(above_match.group(1).replace(',', ''))
                if max_value > threshold:
                    matching_candidates.append(candidate)
        
        return matching_candidates
    
    def extract_range_explicit_needs(self, user_input: str) -> Dict[str, List[str]]:
        """
        Extract range values from user dialogue.
        
        Args:
            user_input: User dialogue text
        
        Returns:
            Dictionary of label names and their extracted values
        """
        extracted_values = {}
        
        # Analyze text for each range label
        for label, patterns in self.label_patterns.items():
            label_values = set()
            deduct_from_value = self.range_labels[label].get("deduct_from_value", False)
            
            # Check if the label or its synonyms are mentioned
            label_mentioned = patterns["label"].search(user_input) is not None
            synonyms_mentioned = "synonyms" in patterns and patterns["synonyms"].search(user_input) is not None
            
            # Special case for 0-100 acceleration, check if the conversation includes acceleration phrases
            if label == "zero_to_one_hundred_km_h_acceleration_time" and re.search(r'0[\s-]*100|acceleration', user_input, re.IGNORECASE):
                synonyms_mentioned = True
                
            # Special case for torque which might be referred to indirectly
            if label == "torque" and re.search(r'(pulling|pulling power)', user_input, re.IGNORECASE):
                synonyms_mentioned = True
                
            # Special case for horsepower which is often just mentioned as power
            if label == "horsepower" and re.search(r'\bpower\b', user_input, re.IGNORECASE):
                synonyms_mentioned = True
                
            # Special handling for complex cases
            if label == "engine_displacement" and re.search(r'(engine|motor).{1,20}(size|capacity|volume|displacement|about|around|approximately).{1,10}\d+\s*l', user_input, re.IGNORECASE):
                synonyms_mentioned = True
                
            if label == "battery_capacity" and re.search(r'battery.{1,20}(capacity|size).{1,10}\d+\s*kwh', user_input, re.IGNORECASE):
                synonyms_mentioned = True
                
            if label_mentioned or synonyms_mentioned:
                # First check if any candidates are explicitly mentioned
                for candidate_pattern in patterns["candidates"]:
                    if candidate_pattern.search(user_input):
                        candidate_value = candidate_pattern.pattern.replace(r'\b', '')
                        if '\\' in candidate_value:
                            # Clean up escaped characters in the pattern
                            candidate_value = re.sub(r'\\(.)', r'\1', candidate_value)
                        label_values.add(candidate_value)
                
                # Expand the context window for detecting units
                window_size = 50
                
                # If no explicit candidates found, look for numeric values
                if not label_values or not deduct_from_value:
                    # Look for range specifications (e.g., "200-300 hp")
                    for match in patterns["numeric"].finditer(user_input):
                        min_val = float(match.group(1))
                        max_val = float(match.group(2))
                        
                        # Check if a unit is specified near the range
                        range_start_pos = match.start()
                        range_end_pos = match.end()
                        context = user_input[max(0, range_start_pos - window_size):min(len(user_input), range_end_pos + window_size)]
                        
                        # Check if the context includes relevant label mentions
                        context_relevant = label_mentioned or (
                            "synonyms" in patterns and patterns["synonyms"].search(context)
                        )
                        
                        unit_match = patterns["unit"].search(context)
                        if unit_match or context_relevant:
                            # Normalize the range to candidate values
                            matching_candidates = self._normalize_to_range_pair(label, min_val, max_val)
                            label_values.update(matching_candidates)
                    
                    # Look for single values that might imply ranges
                    for match in patterns["single_numeric"].finditer(user_input):
                        value = float(match.group(1))
                        
                        # Check if a unit is specified near the value
                        val_start_pos = match.start()
                        val_end_pos = match.end()
                        context = user_input[max(0, val_start_pos - window_size):min(len(user_input), val_end_pos + window_size)]
                        
                        # Check if the context includes relevant label mentions
                        context_relevant = label_mentioned or (
                            "synonyms" in patterns and patterns["synonyms"].search(context)
                        )
                        
                        # Check for qualifiers like "at least", "below", "above", etc.
                        below_qualifier = re.search(r'\b(less than|below|under|not more than|lower than|no more than|smaller than)\b', context, re.IGNORECASE)
                        above_qualifier = re.search(r'\b(more than|above|over|at least|exceeding|greater than|higher than)\b', context, re.IGNORECASE)
                        
                        unit_match = patterns["unit"].search(context)
                        if unit_match or context_relevant:
                            if below_qualifier:
                                # For "below X", use normalized range checking
                                below_candidates = [c for c in self.range_labels[label]["candidates"] 
                                                if "below" in c.lower() or 
                                                (re.search(r'([\d.]+)(?:\s*-|~|\s+to\s+)([\d.]+)', c) and 
                                                float(re.search(r'([\d.]+)(?:\s*-|~|\s+to\s+)([\d.]+)', c).group(2).replace(',', '')) <= value)]
                                label_values.update(below_candidates)
                            elif above_qualifier:
                                # For "above X", use normalized range checking
                                above_candidates = [c for c in self.range_labels[label]["candidates"] 
                                                 if "above" in c.lower() or 
                                                 (re.search(r'([\d.]+)(?:\s*-|~|\s+to\s+)([\d.]+)', c) and 
                                                 float(re.search(r'([\d.]+)(?:\s*-|~|\s+to\s+)([\d.]+)', c).group(1).replace(',', '')) >= value)]
                                label_values.update(above_candidates)
                            else:
                                # For single values, find all candidate ranges that include this value
                                matching_candidates = self._normalize_to_range(label, value)
                                label_values.update(matching_candidates)
            
            if label_values:
                extracted_values[label] = list(label_values)
                
        return extracted_values


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


def test_horsepower_extraction():
    """Test extraction of horsepower values."""
    extractor = RangeExplicitExtractor()
    
    # Test case 1: Direct range mention
    case_1 = "I need a car with horsepower between 150 to 250 hp."
    print(f"Input: {case_1}")
    result1 = extractor.extract_range_explicit_needs(case_1)
    print(f"Output: {result1}")
    expected1 = {"horsepower": ["100-200 hp", "200-300 hp"]}
    print(f"Expected: {expected1}")
    
    assert "horsepower" in result1, "Should extract horsepower from direct range mention"
    assert len(result1["horsepower"]) == 2, "Should extract two overlapping horsepower ranges"
    assert "100-200 hp" in result1["horsepower"], "Should include 100-200 hp range"
    assert "200-300 hp" in result1["horsepower"], "Should include 200-300 hp range"
    
    print()
    
    # Test case 2: Using 'power' as synonym
    case_2 = "I'm looking for a car with power of about 350 hp."
    print(f"Input: {case_2}")
    result2 = extractor.extract_range_explicit_needs(case_2)
    print(f"Output: {result2}")
    expected2 = {"horsepower": ["300-400 hp"]}
    print(f"Expected: {expected2}")
    
    assert "horsepower" in result2, "Should extract horsepower from 'power' synonym"
    assert "300-400 hp" in result2["horsepower"], "Should map 350 hp to 300-400 hp range"


def test_engine_displacement_extraction():
    """Test extraction of engine displacement values."""
    extractor = RangeExplicitExtractor()
    
    # Test case 1: Direct mention
    case_1 = "I'm looking for a car with engine displacement around 2.0l."
    print(f"Input: {case_1}")
    result1 = extractor.extract_range_explicit_needs(case_1)
    print(f"Output: {result1}")
    expected1 = {"engine_displacement": ["1.6-2.0l", "2.0-2.5l"]}
    print(f"Expected: {expected1}")
    
    assert "engine_displacement" in result1, "Should extract engine displacement"
    assert any("2.0" in r for r in result1["engine_displacement"]), "Should find a range containing 2.0"
    
    print()
    
    # Test case 2: Using synonym
    case_2 = "What about a motor size of 1.4 liters?"
    print(f"Input: {case_2}")
    result2 = extractor.extract_range_explicit_needs(case_2)
    print(f"Output: {result2}")
    expected2 = {"engine_displacement": ["1.0-1.6l"]}
    print(f"Expected: {expected2}")
    
    assert "engine_displacement" in result2, "Should extract engine displacement from 'motor size' synonym"
    assert "1.0-1.6l" in result2["engine_displacement"], "Should map 1.4l to 1.0-1.6l range"


def test_battery_capacity_extraction():
    """Test extraction of battery capacity values."""
    extractor = RangeExplicitExtractor()
    
    # Test case 1: Direct mention
    case_1 = "I need a car with battery capacity of 70kwh."
    print(f"Input: {case_1}")
    result1 = extractor.extract_range_explicit_needs(case_1)
    print(f"Output: {result1}")
    expected1 = {"battery_capacity": ["50-80kwh"]}
    print(f"Expected: {expected1}")
    
    assert "battery_capacity" in result1, "Should extract battery capacity"
    assert "50-80kwh" in result1["battery_capacity"], "Should map 70kwh to 50-80kwh range"
    
    print()
    
    # Test case 2: Range mention
    case_2 = "Looking for a car with battery capacity between 90 and 120 kwh."
    print(f"Input: {case_2}")
    result2 = extractor.extract_range_explicit_needs(case_2)
    print(f"Output: {result2}")
    expected2 = {"battery_capacity": ["80-100kwh", "above 100kwh"]}
    print(f"Expected: {expected2}")
    
    assert "battery_capacity" in result2, "Should extract battery capacity from range"
    assert set(result2["battery_capacity"]) == set(["80-100kwh", "above 100kwh"]), "Should map range to correct candidates"


def test_fuel_consumption_extraction():
    """Test extraction of fuel consumption values."""
    extractor = RangeExplicitExtractor()
    
    # Test case 1: With 'under' qualifier
    case_1 = "I'm looking for a car with fuel consumption under 6l/100km."
    print(f"Input: {case_1}")
    result1 = extractor.extract_range_explicit_needs(case_1)
    print(f"Output: {result1}")
    expected1 = {"fuel_consumption": ["4-6l/100km"]}
    print(f"Expected: {expected1}")
    
    assert "fuel_consumption" in result1, "Should extract fuel consumption"
    assert "4-6l/100km" in result1["fuel_consumption"], "Should map 'under 6l/100km' to 4-6l/100km range"
    
    print()
    
    # Test case 2: Synonym usage
    case_2 = "I prefer a car with good gas mileage, around 7 liters per 100km."
    print(f"Input: {case_2}")
    result2 = extractor.extract_range_explicit_needs(case_2)
    print(f"Output: {result2}")
    expected2 = {"fuel_consumption": ["6-8l/100km"]}
    print(f"Expected: {expected2}")
    
    assert "fuel_consumption" in result2, "Should extract fuel consumption from 'gas mileage' synonym"
    assert "6-8l/100km" in result2["fuel_consumption"], "Should map 7l/100km to 6-8l/100km range"


def test_trunk_volume_extraction():
    """Test extraction of trunk volume values."""
    extractor = RangeExplicitExtractor()
    
    # Test case 1: With 'at least' qualifier
    case_1 = "The trunk volume should be at least 400 liters."
    print(f"Input: {case_1}")
    result1 = extractor.extract_range_explicit_needs(case_1)
    print(f"Output: {result1}")
    expected1 = {"trunk_volume": ["400-500l", "above 500l"]}
    print(f"Expected: {expected1}")
    
    assert "trunk_volume" in result1, "Should extract trunk volume"
    assert any("400" in r for r in result1["trunk_volume"]), "Should find a range containing 400"
    
    print()
    
    # Test case 2: Synonym usage
    case_2 = "I need a car with decent luggage space, maybe 350l or so."
    print(f"Input: {case_2}")
    result2 = extractor.extract_range_explicit_needs(case_2)
    print(f"Output: {result2}")
    expected2 = {"trunk_volume": ["300-400l"]}
    print(f"Expected: {expected2}")
    
    assert "trunk_volume" in result2, "Should extract trunk volume from 'luggage space' synonym"
    assert "300-400l" in result2["trunk_volume"], "Should map 350l to 300-400l range"


def test_top_speed_extraction():
    """Test extraction of top speed values."""
    extractor = RangeExplicitExtractor()
    
    # Test case 1: With 'above' qualifier
    case_1 = "I want something with a top speed above 200km/h."
    print(f"Input: {case_1}")
    result1 = extractor.extract_range_explicit_needs(case_1)
    print(f"Output: {result1}")
    expected1 = {"top_speed": ["200-240km/h", "240-300km/h", "above 300km/h"]}
    print(f"Expected: {expected1}")
    
    assert "top_speed" in result1, "Should extract top speed"
    assert any("200" in r for r in result1["top_speed"]), "Should include ranges above 200km/h"
    
    print()
    
    # Test case 2: Synonym usage
    case_2 = "What's the maximum velocity of this car? I need at least 180 kph."
    print(f"Input: {case_2}")
    result2 = extractor.extract_range_explicit_needs(case_2)
    print(f"Output: {result2}")
    expected2 = {"top_speed": ["160-200km/h", "200-240km/h", "240-300km/h", "above 300km/h"]}
    print(f"Expected: {expected2}")
    
    assert "top_speed" in result2, "Should extract top speed from 'maximum velocity' synonym"
    assert any("180" in r or "160-200" in r for r in result2["top_speed"]), "Should include a range containing 180 kph"


def test_acceleration_time_extraction():
    """Test extraction of acceleration time values."""
    extractor = RangeExplicitExtractor()
    
    # Test case 1: With seconds unit
    case_1 = "I need something with good acceleration, maybe 0-100 in 5 seconds?"
    print(f"Input: {case_1}")
    result1 = extractor.extract_range_explicit_needs(case_1)
    print(f"Output: {result1}")
    expected1 = {"zero_to_one_hundred_km_h_acceleration_time": ["4-6s"]}
    print(f"Expected: {expected1}")
    
    assert "zero_to_one_hundred_km_h_acceleration_time" in result1, "Should extract acceleration time"
    assert "4-6s" in result1["zero_to_one_hundred_km_h_acceleration_time"], "Should map 5s to 4-6s range"
    
    print()
    
    # Test case 2: With 'below' qualifier
    case_2 = "I prefer a car with acceleration time below 8 seconds."
    print(f"Input: {case_2}")
    result2 = extractor.extract_range_explicit_needs(case_2)
    print(f"Output: {result2}")
    expected2 = {"zero_to_one_hundred_km_h_acceleration_time": ["6-8s", "4-6s", "below 4s"]}
    print(f"Expected: {expected2}")
    
    assert "zero_to_one_hundred_km_h_acceleration_time" in result2, "Should extract acceleration time with 'below' qualifier"
    assert "6-8s" in result2["zero_to_one_hundred_km_h_acceleration_time"], "Should include 6-8s range"


def test_multiple_range_extraction():
    """Test extraction of multiple range values from a single input."""
    extractor = RangeExplicitExtractor()
    
    # Test with multiple ranges in the same input
    case = "I'd like a car with horsepower between 200-300 hp, fuel consumption below 7l/100km, and a trunk volume of at least 400 liters."
    print(f"Input: {case}")
    result = extractor.extract_range_explicit_needs(case)
    print(f"Output: {result}")
    expected = {
        "horsepower": ["200-300 hp"],
        "fuel_consumption": ["4-6l/100km", "6-8l/100km"],
        "trunk_volume": ["400-500l", "above 500l"]
    }
    print(f"Expected: {expected}")
    
    assert "horsepower" in result, "Should extract horsepower"
    assert "200-300 hp" in result["horsepower"], "Should extract correct horsepower range"
    
    assert "fuel_consumption" in result, "Should extract fuel consumption"
    assert any("7" in r or "6-8" in r for r in result["fuel_consumption"]), "Should extract correct fuel consumption range"
    
    assert "trunk_volume" in result, "Should extract trunk volume"
    assert any("400" in r for r in result["trunk_volume"]), "Should extract correct trunk volume range"


def test_overlapping_ranges():
    """Test extraction of overlapping range values."""
    extractor = RangeExplicitExtractor()
    
    # Test case: Range that overlaps multiple candidates
    case = "I want a car with horsepower from 100 to 300"
    print(f"Input: {case}")
    result = extractor.extract_range_explicit_needs(case)
    print(f"Output: {result}")
    expected = {"horsepower": ["100-200 hp", "200-300 hp"]}
    print(f"Expected: {expected}")
    
    assert "horsepower" in result, "Should extract horsepower"
    assert len(result["horsepower"]) >= 2, "Should extract multiple overlapping ranges"
    assert "100-200 hp" in result["horsepower"], "Should include 100-200 hp range"
    assert "200-300 hp" in result["horsepower"], "Should include 200-300 hp range"


def test_complex_descriptions():
    """Test extraction from complex descriptions with multiple needs and synonyms."""
    extractor = RangeExplicitExtractor()
    
    case = "I need a good commuter car with decent trunk capacity, maybe around 400 liters. It should be efficient with fuel, preferably under 6 liters per 100km. I don't need anything too powerful, maybe around 150 horse power would be fine. Also, I'd prefer a car with reasonable ground clearance, perhaps 160mm or so."
    print(f"Input: {case}")
    result = extractor.extract_range_explicit_needs(case)
    print(f"Output: {result}")
    expected = {
        "trunk_volume": ["400-500l"],
        "fuel_consumption": ["4-6l/100km"],
        "horsepower": ["100-200 hp"],
        "chassis_height": ["150-200mm"]
    }
    print(f"Expected: {expected}")
    
    assert "trunk_volume" in result, "Should extract trunk volume from complex description"
    assert "fuel_consumption" in result, "Should extract fuel consumption from complex description"
    assert "horsepower" in result, "Should extract horsepower from complex description"
    assert "chassis_height" in result, "Should extract chassis height from complex description"


def test_synonym_variations():
    """Test extraction using various synonyms for the same label."""
    extractor = RangeExplicitExtractor()
    
    # Test case 1: Engine displacement synonyms
    case_1 = "I'm looking for a car with motor capacity of about 2.2 liters."
    print(f"Input: {case_1}")
    result1 = extractor.extract_range_explicit_needs(case_1)
    print(f"Output: {result1}")
    expected1 = {"engine_displacement": ["2.0-2.5l"]}
    print(f"Expected: {expected1}")
    
    assert "engine_displacement" in result1, "Should extract engine displacement from 'motor capacity' synonym"
    assert "2.0-2.5l" in result1["engine_displacement"], "Should map 2.2l to 2.0-2.5l range"
    
    print()
    
    # Test case 2: Chassis height synonyms
    case_2 = "I need good ground clearance, at least 180mm for off-roading."
    print(f"Input: {case_2}")
    result2 = extractor.extract_range_explicit_needs(case_2)
    print(f"Output: {result2}")
    expected2 = {"chassis_height": ["150-200mm", "above 200mm"]}
    print(f"Expected: {expected2}")
    
    assert "chassis_height" in result2, "Should extract chassis height from 'ground clearance' synonym"
    assert any("180" in r or "150-200" in r for r in result2["chassis_height"]), "Should extract correct chassis height range"
    
    print()
    
    # Test case 3: Torque synonyms
    case_3 = "The car needs good pulling power, at least 400 nm of torque."
    print(f"Input: {case_3}")
    result3 = extractor.extract_range_explicit_needs(case_3)
    print(f"Output: {result3}")
    expected3 = {"torque": ["400-500 n·m", "above 500 n·m"]}
    print(f"Expected: {expected3}")
    
    assert "torque" in result3, "Should extract torque"
    assert any("400" in r for r in result3["torque"]), "Should extract correct torque range"


# Main test runner
if __name__ == "__main__":
    print("Starting RangeExplicitExtractor tests...\n")
    
    run_test("Test 1: Horsepower Extraction", test_horsepower_extraction)
    run_test("Test 2: Engine Displacement Extraction", test_engine_displacement_extraction)
    run_test("Test 3: Battery Capacity Extraction", test_battery_capacity_extraction)
    run_test("Test 4: Fuel Consumption Extraction", test_fuel_consumption_extraction)
    run_test("Test 5: Trunk Volume Extraction", test_trunk_volume_extraction)
    run_test("Test 6: Top Speed Extraction", test_top_speed_extraction)
    run_test("Test 7: Acceleration Time Extraction", test_acceleration_time_extraction)
    run_test("Test 8: Multiple Range Extraction", test_multiple_range_extraction)
    run_test("Test 9: Overlapping Ranges", test_overlapping_ranges)
    run_test("Test 10: Complex Descriptions", test_complex_descriptions)
    run_test("Test 11: Synonym Variations", test_synonym_variations)
    
    print("\nAll tests completed.") 