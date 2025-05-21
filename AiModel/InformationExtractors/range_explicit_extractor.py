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
            
            # Create pattern for qualifiers
            patterns["at_least"] = re.compile(r'\b(at\s+least|minimum|minimum\s+of|no\s+less\s+than|not\s+less\s+than)\b', re.IGNORECASE)
            patterns["at_most"] = re.compile(r'\b(at\s+most|maximum|maximum\s+of|no\s+more\s+than|not\s+more\s+than)\b', re.IGNORECASE)
            patterns["more_than"] = re.compile(r'\b(more\s+than|above|over|exceeding|greater\s+than|higher\s+than)\b', re.IGNORECASE)
            patterns["less_than"] = re.compile(r'\b(less\s+than|below|under|lower\s+than|smaller\s+than)\b', re.IGNORECASE)
            
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
    
    def _normalize_with_qualifier(self, label: str, value: float, qualifier_type: str) -> List[str]:
        """
        Normalize a value with a qualifier (at least, at most, more than, less than) to matching range candidates.
        
        Args:
            label: The label name
            value: The numeric value
            qualifier_type: The type of qualifier ("at_least", "at_most", "more_than", "less_than")
            
        Returns:
            List of matching candidate ranges based on the qualifier logic
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
                
                if qualifier_type in ("at_least", "more_than"):
                    # For "at least X", include ranges where min >= X OR where X falls within the range
                    if (qualifier_type == "at_least" and (range_min >= value or (range_min <= value <= range_max))):
                        matching_candidates.append(candidate)
                    # For "more than X", include ranges where min > X OR where X < range_max
                    elif qualifier_type == "more_than" and (range_min > value or range_max > value):
                        matching_candidates.append(candidate)
                elif qualifier_type in ("at_most", "less_than"):
                    # For "at most X", include ranges where max <= X OR where X falls within the range
                    if (qualifier_type == "at_most" and (range_max <= value or (range_min <= value <= range_max))):
                        matching_candidates.append(candidate)
                    # For "less than X", include ranges where max < X OR where X > range_min
                    elif qualifier_type == "less_than" and (range_max < value or range_min < value):
                        matching_candidates.append(candidate)
            elif below_match:
                threshold = float(below_match.group(1).replace(',', ''))
                # For "below X" candidate
                if qualifier_type in ("at_most", "less_than"):
                    # Always include "below X" for at_most and less_than
                    matching_candidates.append(candidate)
                elif qualifier_type in ("at_least", "more_than") and value < threshold:
                    matching_candidates.append(candidate)
            elif above_match:
                threshold = float(above_match.group(1).replace(',', ''))
                # For "above X" candidate
                if qualifier_type in ("at_least", "more_than"):
                    # Always include "above X" for at_least and more_than
                    matching_candidates.append(candidate)
                elif qualifier_type in ("at_most", "less_than") and value > threshold:
                    matching_candidates.append(candidate)
        
        # Special case to include "below X" ranges for "at_most Y" qualifiers
        if qualifier_type == "at_most":
            for candidate in self.range_labels[label]["candidates"]:
                if "below" in candidate.lower():
                    below_match = re.search(r'below\s+([\d.]+)', candidate)
                    if below_match:
                        below_value = float(below_match.group(1).replace(',', ''))
                        if below_value > value:
                            matching_candidates.append(candidate)
        
        # Special case to include "above X" ranges for "at_least Y" qualifiers
        if qualifier_type == "at_least":
            for candidate in self.range_labels[label]["candidates"]:
                if "above" in candidate.lower():
                    above_match = re.search(r'above\s+([\d.]+)', candidate)
                    if above_match:
                        above_value = float(above_match.group(1).replace(',', ''))
                        if above_value < value:
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
                
            # Special case for ground clearance as a synonym for chassis height
            if label == "chassis_height" and re.search(r'ground\s*clearance', user_input, re.IGNORECASE):
                synonyms_mentioned = True
                
            # Special case for fuel efficiency as a synonym for fuel consumption
            if label == "fuel_consumption" and re.search(r'(fuel|gas)\s*(efficiency|economy|mileage)', user_input, re.IGNORECASE):
                synonyms_mentioned = True
            
            # Enhanced detection for fuel consumption in complex descriptions
            if label == "fuel_consumption" and re.search(r'(efficient|efficiency|economical).{1,30}(fuel|gas|petrol|diesel)', user_input, re.IGNORECASE):
                synonyms_mentioned = True
            
            # Enhanced detection for fuel consumption with specific values
            if label == "fuel_consumption" and re.search(r'(under|below|less than|no more than).{1,10}\d+\s*(l|liter|litre)s?\s*(per|\/)\s*100\s*km', user_input, re.IGNORECASE):
                synonyms_mentioned = True
                
            # Special case for top speed variations
            if label == "top_speed" and re.search(r'(top|maximum|max)\s*(speed|velocity)', user_input, re.IGNORECASE):
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
                            # Check for qualifiers that might modify the range interpretation
                            at_least_qualifier = patterns["at_least"].search(context)
                            at_most_qualifier = patterns["at_most"].search(context)
                            more_than_qualifier = patterns["more_than"].search(context)
                            less_than_qualifier = patterns["less_than"].search(context)
                            
                            if at_least_qualifier:
                                # For "at least X-Y", use lower bound
                                matching_candidates = self._normalize_with_qualifier(label, min_val, "at_least")
                                label_values.update(matching_candidates)
                            elif at_most_qualifier:
                                # For "at most X-Y", use upper bound
                                matching_candidates = self._normalize_with_qualifier(label, max_val, "at_most")
                                label_values.update(matching_candidates)
                            elif more_than_qualifier:
                                # For "more than X-Y", use lower bound
                                matching_candidates = self._normalize_with_qualifier(label, min_val, "more_than")
                                label_values.update(matching_candidates)
                            elif less_than_qualifier:
                                # For "less than X-Y", use upper bound
                                matching_candidates = self._normalize_with_qualifier(label, max_val, "less_than")
                                label_values.update(matching_candidates)
                            else:
                                # Normal range without qualifiers
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
                        
                        unit_match = patterns["unit"].search(context)
                        if unit_match or context_relevant:
                            # Check for qualifiers that modify how we interpret the value
                            at_least_qualifier = patterns["at_least"].search(context)
                            at_most_qualifier = patterns["at_most"].search(context)
                            more_than_qualifier = patterns["more_than"].search(context)
                            less_than_qualifier = patterns["less_than"].search(context)
                            
                            if at_least_qualifier:
                                # For "at least X", find ranges where min value >= X
                                matching_candidates = self._normalize_with_qualifier(label, value, "at_least")
                                label_values.update(matching_candidates)
                            elif at_most_qualifier:
                                # For "at most X", find ranges where max value <= X
                                matching_candidates = self._normalize_with_qualifier(label, value, "at_most")
                                label_values.update(matching_candidates)
                            elif more_than_qualifier:
                                # For "more than X", find ranges strictly above X
                                matching_candidates = self._normalize_with_qualifier(label, value, "more_than")
                                label_values.update(matching_candidates)
                            elif less_than_qualifier:
                                # For "less than X", find ranges strictly below X
                                matching_candidates = self._normalize_with_qualifier(label, value, "less_than")
                                label_values.update(matching_candidates)
                            else:
                                # For single values without qualifiers, find ranges that include this value
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


# Additional test cases for enhanced qualifier handling
def test_enhanced_qualifier_handling():
    """Test enhanced handling of qualifiers like at least, at most, more than, no more than."""
    extractor = RangeExplicitExtractor()
    
    # Test case 1: "at least" qualifier
    case_1 = "I need a car with at least 250 horsepower."
    print(f"Input: {case_1}")
    result1 = extractor.extract_range_explicit_needs(case_1)
    print(f"Output: {result1}")
    expected1 = {"horsepower": ["200-300 hp", "300-400 hp", "above 400 hp"]}
    print(f"Expected: {expected1}")
    
    assert "horsepower" in result1, "Should extract horsepower with 'at least' qualifier"
    assert "200-300 hp" in result1["horsepower"], "Should include 200-300 hp range for 'at least 250 hp'"
    assert "300-400 hp" in result1["horsepower"], "Should include 300-400 hp range for 'at least 250 hp'"
    assert "100-200 hp" not in result1["horsepower"], "Should NOT include 100-200 hp range for 'at least 250 hp'"
    
    print()
    
    # Test case 2: "at most" qualifier
    case_2 = "I want a car with at most 150 horsepower."
    print(f"Input: {case_2}")
    result2 = extractor.extract_range_explicit_needs(case_2)
    print(f"Output: {result2}")
    expected2 = {"horsepower": ["100-200 hp", "below 100 hp"]}
    print(f"Expected: {expected2}")
    
    assert "horsepower" in result2, "Should extract horsepower with 'at most' qualifier"
    assert "100-200 hp" in result2["horsepower"], "Should include 100-200 hp range for 'at most 150 hp'"
    assert "below 100 hp" in result2["horsepower"], "Should include below 100 hp range for 'at most 150 hp'"
    assert "200-300 hp" not in result2["horsepower"], "Should NOT include 200-300 hp range for 'at most 150 hp'"
    
    print()
    
    # Test case 3: "more than" qualifier
    case_3 = "I'm looking for an EV with more than 80kwh battery capacity."
    print(f"Input: {case_3}")
    result3 = extractor.extract_range_explicit_needs(case_3)
    print(f"Output: {result3}")
    expected3 = {"battery_capacity": ["80-100kwh", "above 100kwh"]}
    print(f"Expected: {expected3}")
    
    assert "battery_capacity" in result3, "Should extract battery capacity with 'more than' qualifier"
    assert "80-100kwh" in result3["battery_capacity"], "Should include 80-100kwh range for 'more than 80kwh'"
    assert "above 100kwh" in result3["battery_capacity"], "Should include above 100kwh range for 'more than 80kwh'"
    assert "50-80kwh" not in result3["battery_capacity"], "Should NOT include 50-80kwh range for 'more than 80kwh'"
    
    print()
    
    # Test case 4: "no more than" qualifier
    case_4 = "I need a car with no more than 7l/100km fuel consumption."
    print(f"Input: {case_4}")
    result4 = extractor.extract_range_explicit_needs(case_4)
    print(f"Output: {result4}")
    expected4 = {"fuel_consumption": ["6-8l/100km", "4-6l/100km", "below 4l/100km"]}
    print(f"Expected: {expected4}")
    
    assert "fuel_consumption" in result4, "Should extract fuel consumption with 'no more than' qualifier"
    assert "6-8l/100km" in result4["fuel_consumption"], "Should include 6-8l/100km range for 'no more than 7l/100km'"
    assert "4-6l/100km" in result4["fuel_consumption"], "Should include 4-6l/100km range for 'no more than 7l/100km'"
    assert "8-10l/100km" not in result4["fuel_consumption"], "Should NOT include 8-10l/100km range for 'no more than 7l/100km'"


def test_complex_multi_label_extraction():
    """Test extraction of multiple labels with various qualifiers in a single query."""
    extractor = RangeExplicitExtractor()
    
    complex_case = """I'm looking for a car with at least 300 horsepower, 
                     fuel consumption no more than 8l/100km, 
                     trunk volume of about 450-500 liters, 
                     and acceleration from 0-100 in at most 6 seconds.
                     It should also have a ground clearance of at least 180mm."""
    
    print(f"Input: {complex_case}")
    result = extractor.extract_range_explicit_needs(complex_case)
    print(f"Output: {result}")
    
    expected = {
        "horsepower": ["300-400 hp", "above 400 hp"],
        "fuel_consumption": ["6-8l/100km", "4-6l/100km", "below 4l/100km"],
        "trunk_volume": ["400-500l"],
        "zero_to_one_hundred_km_h_acceleration_time": ["4-6s", "below 4s"],
        "chassis_height": ["150-200mm", "above 200mm"]
    }
    
    print(f"Expected: {expected}")
    
    assert "horsepower" in result, "Should extract horsepower with 'at least' qualifier"
    assert "300-400 hp" in result["horsepower"], "Should include 300-400 hp for 'at least 300 hp'"
    
    assert "fuel_consumption" in result, "Should extract fuel consumption with 'no more than' qualifier"
    assert "6-8l/100km" in result["fuel_consumption"], "Should include 6-8l/100km for 'no more than 8l/100km'"
    
    assert "trunk_volume" in result, "Should extract trunk volume from range"
    assert "400-500l" in result["trunk_volume"], "Should include 400-500l for 'trunk volume of about 450-500 liters'"
    
    assert "zero_to_one_hundred_km_h_acceleration_time" in result, "Should extract acceleration time with 'at most' qualifier"
    assert "4-6s" in result["zero_to_one_hundred_km_h_acceleration_time"], "Should include 4-6s for 'at most 6 seconds'"
    
    assert "chassis_height" in result, "Should extract chassis height with 'at least' qualifier"
    assert any("180" in r or "150-200" in r for r in result["chassis_height"]), "Should include appropriate range for 'ground clearance of at least 180mm'"


# Main test runner
if __name__ == "__main__":
    print("Starting RangeExplicitExtractor tests...\n")
    
    # Run original tests
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
    
    # Run new tests for enhanced features
    run_test("Test 12: Enhanced Qualifier Handling", test_enhanced_qualifier_handling)
    run_test("Test 13: Complex Multi-Label Extraction", test_complex_multi_label_extraction)
    
    print("\nAll tests completed.") 