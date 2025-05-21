import json
import re
import os
from pathlib import Path


class ExactExplicitExtractor:
    """
    A class for extracting exact explicit labels from user conversations based on
    predefined labels in QueryLabels.json.
    
    This extractor specifically handles labels with value_type 'exact' excluding:
    - vehicle_category_top
    - vehicle_category_middle
    - vehicle_category_bottom
    - brand_area
    - brand_country
    - brand
    """

    def __init__(self):
        """
        Initialize the ExactExplicitExtractor with labels loaded from QueryLabels.json.
        """
        # Load query labels from JSON file
        base_dir = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        query_labels_path = os.path.join(base_dir, "Config", "QueryLabels.json")

        with open(query_labels_path, "r", encoding="utf-8") as f:
            self.query_labels = json.load(f)

        # Get all labels with value_type 'exact', excluding specific categories
        self.excluded_labels = [
            "vehicle_category_top",
            "vehicle_category_middle",
            "vehicle_category_bottom",
            "brand_area",
            "brand_country",
            "brand",
        ]

        # Filter labels with value_type 'exact' excluding the ones in excluded_labels
        self.exact_labels = []
        for label, info in self.query_labels.items():
            if info.get("value_type") == "exact" and label not in self.excluded_labels:
                self.exact_labels.append(label)
        
        # Create a mapping of synonyms for labels and candidates
        self.label_synonyms = self._create_label_synonyms()
        self.candidate_synonyms = self._create_candidate_synonyms()

    def _create_label_synonyms(self):
        """
        Create a dictionary mapping each label to its possible synonyms.

        Returns:
            dict: Dictionary mapping labels to their synonyms
        """
        synonyms = {}

        # Define synonyms for each exact label
        for label in self.exact_labels:
            # Add the label itself as a synonym
            label_synonyms = [label.lower()]

            # Add label with underscores replaced by spaces
            label_synonyms.append(label.replace("_", " ").lower())

            # Define specific synonyms for various labels
            if label == "powertrain_type":
                label_synonyms.extend([
                    "engine type", "power source", "drive system", "propulsion",
                    "motor type", "drivetrain", "power unit", "engine option"
                ])
            elif label == "design_style":
                label_synonyms.extend([
                    "styling", "appearance", "look", "design", "style", 
                    "design language", "aesthetic", "visual appeal"
                ])
            elif label == "color":
                label_synonyms.extend([
                    "color", "colour", "paint", "shade", "paint color", 
                    "car color", "exterior color", "paint option"
                ])
            elif label == "interior_material_texture":
                label_synonyms.extend([
                    "interior material", "cabin materials", "dashboard material",
                    "interior finish", "interior trim", "cabin trim",
                    "interior decoration", "cabin accent"
                ])
            elif label == "airbag_count":
                label_synonyms.extend([
                    "airbags", "number of airbags", "airbag quantity", 
                    "airbag number", "safety airbags", "air bags"
                ])
            elif label == "seat_material":
                label_synonyms.extend([
                    "seat upholstery", "seat covering", "seat fabric", 
                    "upholstery", "seat type", "seat finish"
                ])
            elif label == "autonomous_driving_level":
                label_synonyms.extend([
                    "autonomous driving", "self driving", "autopilot level",
                    "driving automation", "autonomous capability"
                ])
            elif label == "drive_type":
                label_synonyms.extend([
                    "drive system", "wheel drive", "drivetrain", "drive configuration",
                    "driving wheels", "driving axle", "drive axle"
                ])
            elif label == "suspension":
                label_synonyms.extend([
                    "suspension system", "suspension type", "chassis suspension",
                    "ride suspension", "spring system"
                ])
            elif label == "seat_layout":
                label_synonyms.extend([
                    "seating", "seats", "seating capacity", "passenger capacity",
                    "seating configuration", "seating arrangement", "seat count"
                ])

            # Remove duplicates
            label_synonyms = list(set(label_synonyms))
            synonyms[label] = label_synonyms

        return synonyms

    def _create_candidate_synonyms(self):
        """
        Create a dictionary mapping each candidate value to its possible synonyms.

        Returns:
            dict: Dictionary mapping candidates to their synonyms
        """
        candidate_synonyms = {}

        # Generate synonyms for each candidate of every exact label
        for label in self.exact_labels:
            candidates = self.query_labels[label].get("candidates", [])
            
            for candidate in candidates:
                # Add the candidate itself as a synonym
                synonyms = [candidate.lower()]
                
                # Handle specific candidate synonyms based on label
                if label == "powertrain_type":
                    if candidate == "battery electric vehicle":
                        synonyms.extend([
                            "ev", "electric car", "electric vehicle", "battery powered",
                            "pure electric", "fully electric", "all-electric", "battery-electric",
                            "electric", "zero emission vehicle", "bev"
                        ])
                    elif candidate == "hybrid electric vehicle":
                        synonyms.extend([
                            "hybrid", "hybrid car", "hev", "mild hybrid", 
                            "full hybrid", "self-charging hybrid"
                        ])
                    elif candidate == "plug-in hybrid electric vehicle":
                        synonyms.extend([
                            "phev", "plug in hybrid", "plug-in", "rechargeable hybrid"
                        ])
                    elif candidate == "gasoline engine":
                        synonyms.extend([
                            "gas engine", "petrol engine", "gas", "petrol", "gasoline",
                            "gas powered", "petrol powered", "ice", "internal combustion"
                        ])
                    elif candidate == "diesel engine":
                        synonyms.extend([
                            "diesel", "diesel powered", "diesel car"
                        ])
                    elif candidate == "range-extended electric vehicle":
                        synonyms.extend([
                            "range extender", "rex", "erev", "extended range ev"
                        ])
                elif label == "design_style":
                    if candidate == "sporty":
                        synonyms.extend([
                            "athletic", "dynamic", "aggressive", "performance oriented", 
                            "sporty looking", "racing inspired", "aggressive styling"
                        ])
                    elif candidate == "business":
                        synonyms.extend([
                            "professional", "executive", "formal", "conservative",
                            "elegant", "sophisticated", "classy", "business like"
                        ])
                elif label == "color":
                    if candidate == "bright colors":
                        synonyms.extend([
                            "bright", "vibrant", "bold colors", "vibrant colors", 
                            "colorful", "eye catching colors", "flashy colors", 
                            "loud colors", "strong colors", "red", "yellow", "blue"
                        ])
                    elif candidate == "neutral colors":
                        synonyms.extend([
                            "neutral", "subdued colors", "subtle colors", "muted colors",
                            "moderate colors", "balanced colors", "white", "silver", "gray", "grey"
                        ])
                    elif candidate == "dark colors":
                        synonyms.extend([
                            "dark", "deep colors", "rich colors", "black", "navy", "dark grey", 
                            "charcoal", "deep colors", "sophisticated colors"
                        ])
                elif label == "interior_material_texture":
                    if candidate == "wood trim":
                        synonyms.extend([
                            "wooden", "wood panels", "wood accents", "wood finish",
                            "timber trim", "wooden decoration", "wood interior"
                        ])
                    elif candidate == "metal trim":
                        synonyms.extend([
                            "metallic", "aluminum trim", "aluminium trim", "metal accents",
                            "metal finish", "metal decoration", "metal panels", "chrome trim"
                        ])
                elif label == "airbag_count":
                    # Add numeric expressions
                    if candidate == "2":
                        synonyms.extend(["two", "dual", "pair of", "couple of"])
                    elif candidate == "4":
                        synonyms.extend(["four", "quad"])
                    elif candidate == "6":
                        synonyms.extend(["six"])
                    elif candidate == "8":
                        synonyms.extend(["eight"])
                    elif candidate == "10":
                        synonyms.extend(["ten"])
                    elif candidate == "above 10":
                        synonyms.extend([
                            "more than 10", "over 10", "11+", "11 or more", "many airbags",
                            "lots of airbags", "multiple airbags", "comprehensive airbag system"
                        ])
                elif label == "seat_material":
                    if candidate == "leather":
                        synonyms.extend([
                            "leather seats", "leather upholstery", "leather interior",
                            "leather trimmed", "premium leather", "leatherette", "synthetic leather"
                        ])
                    elif candidate == "fabric":
                        synonyms.extend([
                            "cloth", "cloth seats", "fabric seats", "textile", "cloth upholstery",
                            "fabric upholstery", "textile seats", "cloth interior"
                        ])
                elif label == "autonomous_driving_level":
                    if candidate == "l2":
                        synonyms.extend([
                            "level 2", "level two", "partial automation", "driver assistance"
                        ])
                    elif candidate == "l3":
                        synonyms.extend([
                            "level 3", "level three", "conditional automation", "eyes off"
                        ])
                elif label == "drive_type":
                    if candidate == "front-wheel drive":
                        synonyms.extend([
                            "fwd", "front wheel", "front wheels", "front driven"
                        ])
                    elif candidate == "rear-wheel drive":
                        synonyms.extend([
                            "rwd", "rear wheel", "rear wheels", "rear driven"
                        ])
                    elif candidate == "all-wheel drive":
                        synonyms.extend([
                            "awd", "all wheel", "4wd", "four-wheel drive", "four wheel drive", 
                            "4x4", "all wheels", "four wheels"
                        ])
                elif label == "suspension":
                    if candidate == "suspension":
                        synonyms.extend([
                            "independent suspension", "independent", "soft suspension",
                            "comfort suspension", "adaptive suspension"
                        ])
                    elif candidate == "non-independent":
                        synonyms.extend([
                            "solid axle", "rigid axle", "beam axle", "torsion beam",
                            "non independent"
                        ])
                elif label == "seat_layout":
                    # Add variations for seat numbers
                    if candidate == "2-seat":
                        synonyms.extend([
                            "two seat", "two seater", "2 seater", "two seats", "2 seats"
                        ])
                    elif candidate == "4-seat":
                        synonyms.extend([
                            "four seat", "four seater", "4 seater", "four seats", "4 seats"
                        ])
                    elif candidate == "5-seat":
                        synonyms.extend([
                            "five seat", "five seater", "5 seater", "five seats", "5 seats"
                        ])
                    elif candidate == "6-seat":
                        synonyms.extend([
                            "six seat", "six seater", "6 seater", "six seats", "6 seats"
                        ])
                    elif candidate == "7-seat":
                        synonyms.extend([
                            "seven seat", "seven seater", "7 seater", "seven seats", "7 seats"
                        ])
                
                # Remove duplicates
                synonyms = list(set(synonyms))
                candidate_synonyms[candidate] = synonyms
                
        return candidate_synonyms

    def _extract_exact_label_from_text(self, text, label):
        """
        Extract values for a specific exact label from text.

        Args:
            text (str): The input text
            label (str): The label to extract values for

        Returns:
            list: List of extracted values for the label
        """
        if label not in self.query_labels:
            return []

        extracted_values = []
        label_data = self.query_labels[label]
        candidates = label_data["candidates"]
        deduct_from_value = label_data.get("deduct_from_value", False)

        # Check for each candidate and its synonyms in the text
        for candidate in candidates:
            # Get all possible patterns to look for
            patterns = [re.escape(candidate.lower())]
            if candidate in self.candidate_synonyms:
                patterns.extend([
                    re.escape(syn.lower()) for syn in self.candidate_synonyms[candidate]
                ])

            for pattern in patterns:
                # Look for direct mention or positive expressions
                positive_patterns = [
                    rf"\b{pattern}\b",  # Direct mention
                    rf"(?:want|need|looking for|prefer|like|interested in|considering)\s+(?:a|an|the|some)?\s*(?:car|vehicle|model|option)?(?:\s+with)?\s*(?:that has|that comes with|with)?\s*(?:a|an|the)?\s*\b{pattern}\b",
                    rf"\b{pattern}\b.*?(?:would be good|would be nice|would be great|is important|is essential|is crucial|is necessary)",
                    rf"(?:how about|what about)\s+(?:a|an|the)?\s*\b{pattern}\b",
                    rf"(?:should have|must have|has to have)\s+(?:a|an|the)?\s*\b{pattern}\b"
                ]
                
                # For airbags, add specific patterns to detect expressions like "at least 4 airbags"
                if label == "airbag_count":
                    quantity = candidate
                    if quantity.isdigit() or quantity in ["above 10"]:
                        num = quantity if quantity.isdigit() else "10"
                        at_least_patterns = [
                            rf"(?:at least|minimum|no less than|minimum of)\s+{num}\s+airbags?",
                            rf"(?:at least|minimum|no less than|minimum of)\s+{self._number_to_word(num)}\s+airbags?"
                        ]
                        positive_patterns.extend(at_least_patterns)
                
                # Special handling for seat layout label
                if label == "seat_layout":
                    # Extract the number from the candidate (e.g., "5" from "5-seat")
                    seat_num = candidate.split("-")[0]
                    seat_word = self._number_to_word(seat_num)
                    
                    # Add patterns to match expressions like "5-seater", "5 seats", etc.
                    seat_patterns = [
                        rf"\b{seat_num}[-\s]?seat(?:er|s)?\b",  # 5-seat, 5 seats, 5 seater
                        rf"\b{seat_word}[-\s]?seat(?:er|s)?\b",  # five-seat, five seats, five seater
                        rf"\b{seat_num}\s+passenger\b",          # 5 passenger
                        rf"\b{seat_word}\s+passenger\b"          # five passenger
                    ]
                    positive_patterns.extend(seat_patterns)
                
                # For deduct_from_value true labels, check if candidates are directly mentioned
                found_match = False
                for pos_pattern in positive_patterns:
                    if re.search(pos_pattern, text.lower()):
                        if candidate not in extracted_values:
                            extracted_values.append(candidate)
                            found_match = True
                            break
                
                if found_match:
                    break

        return extracted_values
    
    def _number_to_word(self, number):
        """
        Convert a number to its word representation.
        
        Args:
            number (str): Number to convert
            
        Returns:
            str: Word representation of the number
        """
        word_map = {
            "1": "one", "2": "two", "3": "three", "4": "four", "5": "five",
            "6": "six", "7": "seven", "8": "eight", "9": "nine", "10": "ten"
        }
        return word_map.get(number, number)

    def extract_exact_explicit_values(self, user_input):
        """
        Extract exact explicit values from user input for all exact labels
        (excluding vehicle categories, brand area, brand country, and brand).

        Args:
            user_input (str): The input text from the user

        Returns:
            dict: Dictionary containing extracted exact label values
        """
        extracted_values = {}

        # Extract values for each exact label
        for label in self.exact_labels:
            values = self._extract_exact_label_from_text(user_input, label)
            if values:
                extracted_values[label] = values

        return extracted_values


# Test examples
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

def test_powertrain_type_extraction():
    """Test powertrain type extraction."""
    extractor = ExactExplicitExtractor()
    
    # Test case 1: Electric vehicle
    input_text = "I'm looking for an electric car with good range."
    result = extractor.extract_exact_explicit_values(input_text)
    assert "powertrain_type" in result, "Should detect powertrain_type"
    assert "battery electric vehicle" in result["powertrain_type"], "Should detect battery electric vehicle"
    
    # Test case 2: Hybrid vehicle
    input_text = "I prefer a hybrid that's good on gas."
    result = extractor.extract_exact_explicit_values(input_text)
    assert "powertrain_type" in result, "Should detect powertrain_type"
    assert "hybrid electric vehicle" in result["powertrain_type"], "Should detect hybrid electric vehicle"
    
    # Test case 3: Diesel engine
    input_text = "I want a car with a diesel engine for better fuel economy."
    result = extractor.extract_exact_explicit_values(input_text)
    assert "powertrain_type" in result, "Should detect powertrain_type"
    assert "diesel engine" in result["powertrain_type"], "Should detect diesel engine"

def test_design_style_extraction():
    """Test design style extraction."""
    extractor = ExactExplicitExtractor()
    
    # Test case 1: Sporty design
    input_text = "I want a car with a sporty design that looks aggressive."
    result = extractor.extract_exact_explicit_values(input_text)
    assert "design_style" in result, "Should detect design_style"
    assert "sporty" in result["design_style"], "Should detect sporty design"
    
    # Test case 2: Business design
    input_text = "I need a business-like car for professional use."
    result = extractor.extract_exact_explicit_values(input_text)
    assert "design_style" in result, "Should detect design_style"
    assert "business" in result["design_style"], "Should detect business design"

def test_color_extraction():
    """Test color extraction."""
    extractor = ExactExplicitExtractor()
    
    # Test case 1: Dark colors
    input_text = "I prefer a car in dark colors like black or navy."
    result = extractor.extract_exact_explicit_values(input_text)
    assert "color" in result, "Should detect color"
    assert "dark colors" in result["color"], "Should detect dark colors"
    
    # Test case 2: Bright colors
    input_text = "I want a vehicle with vibrant colors that stand out."
    result = extractor.extract_exact_explicit_values(input_text)
    assert "color" in result, "Should detect color"
    assert "bright colors" in result["color"], "Should detect bright colors"

def test_interior_material_extraction():
    """Test interior material extraction."""
    extractor = ExactExplicitExtractor()
    
    # Test case 1: Wood trim
    input_text = "I'd like a car with wood trim in the interior."
    result = extractor.extract_exact_explicit_values(input_text)
    assert "interior_material_texture" in result, "Should detect interior_material_texture"
    assert "wood trim" in result["interior_material_texture"], "Should detect wood trim"
    
    # Test case 2: Metal trim
    input_text = "A car with aluminum trim would be nice."
    result = extractor.extract_exact_explicit_values(input_text)
    assert "interior_material_texture" in result, "Should detect interior_material_texture"
    assert "metal trim" in result["interior_material_texture"], "Should detect metal trim"

def test_airbag_count_extraction():
    """Test airbag count extraction."""
    extractor = ExactExplicitExtractor()
    
    # Test case 1: Explicit number
    input_text = "I want a car with 6 airbags."
    result = extractor.extract_exact_explicit_values(input_text)
    assert "airbag_count" in result, "Should detect airbag_count"
    assert "6" in result["airbag_count"], "Should detect 6 airbags"
    
    # Test case 2: At least expression
    input_text = "The car should have at least 4 airbags for safety."
    result = extractor.extract_exact_explicit_values(input_text)
    assert "airbag_count" in result, "Should detect airbag_count"
    assert "4" in result["airbag_count"], "Should detect 4 airbags"
    
    # Test case 3: Word number
    input_text = "I prefer a car with eight airbags for maximum safety."
    result = extractor.extract_exact_explicit_values(input_text)
    assert "airbag_count" in result, "Should detect airbag_count"
    assert "8" in result["airbag_count"], "Should detect 8 airbags"

def test_seat_material_extraction():
    """Test seat material extraction."""
    extractor = ExactExplicitExtractor()
    
    # Test case 1: Leather seats
    input_text = "I want a car with leather seats."
    result = extractor.extract_exact_explicit_values(input_text)
    assert "seat_material" in result, "Should detect seat_material"
    assert "leather" in result["seat_material"], "Should detect leather seats"
    
    # Test case 2: Fabric seats
    input_text = "I prefer a car with fabric upholstery."
    result = extractor.extract_exact_explicit_values(input_text)
    assert "seat_material" in result, "Should detect seat_material"
    assert "fabric" in result["seat_material"], "Should detect fabric seats"

def test_autonomous_driving_level_extraction():
    """Test autonomous driving level extraction."""
    extractor = ExactExplicitExtractor()
    
    # Test case 1: Level 2
    input_text = "I want a car with level 2 autonomous driving."
    result = extractor.extract_exact_explicit_values(input_text)
    assert "autonomous_driving_level" in result, "Should detect autonomous_driving_level"
    assert "l2" in result["autonomous_driving_level"], "Should detect L2 autonomous driving"
    
    # Test case 2: Level 3
    input_text = "I'm interested in a car with level 3 self-driving capabilities."
    result = extractor.extract_exact_explicit_values(input_text)
    assert "autonomous_driving_level" in result, "Should detect autonomous_driving_level"
    assert "l3" in result["autonomous_driving_level"], "Should detect L3 autonomous driving"

def test_drive_type_extraction():
    """Test drive type extraction."""
    extractor = ExactExplicitExtractor()
    
    # Test case 1: Front wheel drive
    input_text = "I prefer a car with FWD for better fuel economy."
    result = extractor.extract_exact_explicit_values(input_text)
    assert "drive_type" in result, "Should detect drive_type"
    assert "front-wheel drive" in result["drive_type"], "Should detect front-wheel drive"
    
    # Test case 2: All wheel drive
    input_text = "I need a vehicle with AWD for winter driving."
    result = extractor.extract_exact_explicit_values(input_text)
    assert "drive_type" in result, "Should detect drive_type"
    assert "all-wheel drive" in result["drive_type"], "Should detect all-wheel drive"
    
    # Test case 3: Rear wheel drive
    input_text = "I'm looking for a sports car with rear wheel drive."
    result = extractor.extract_exact_explicit_values(input_text)
    assert "drive_type" in result, "Should detect drive_type"
    assert "rear-wheel drive" in result["drive_type"], "Should detect rear-wheel drive"

def test_suspension_extraction():
    """Test suspension extraction."""
    extractor = ExactExplicitExtractor()
    
    # Test case 1: Independent suspension
    input_text = "I want a car with independent suspension for a smoother ride."
    result = extractor.extract_exact_explicit_values(input_text)
    assert "suspension" in result, "Should detect suspension"
    assert "suspension" in result["suspension"], "Should detect independent suspension"
    
    # Test case 2: Non-independent suspension
    input_text = "I'm looking for an off-road vehicle with solid axle suspension."
    result = extractor.extract_exact_explicit_values(input_text)
    assert "suspension" in result, "Should detect suspension"
    assert "non-independent" in result["suspension"], "Should detect non-independent suspension"

def test_seat_layout_extraction():
    """Test seat layout extraction."""
    extractor = ExactExplicitExtractor()
    
    # Test case 1: 5-seat
    input_text = "I need a 5-seat car for my family."
    result = extractor.extract_exact_explicit_values(input_text)
    assert "seat_layout" in result, "Should detect seat_layout"
    assert "5-seat" in result["seat_layout"], "Should detect 5-seat layout"
    
    # Test case 2: 7-seat
    input_text = "We're looking for a seven-seater SUV."
    result = extractor.extract_exact_explicit_values(input_text)
    assert "seat_layout" in result, "Should detect seat_layout"
    assert "7-seat" in result["seat_layout"], "Should detect 7-seat layout"
    
    # Test case 3: 2-seat
    input_text = "I want a two-seater sports car."
    result = extractor.extract_exact_explicit_values(input_text)
    assert "seat_layout" in result, "Should detect seat_layout"
    assert "2-seat" in result["seat_layout"], "Should detect 2-seat layout"

def test_multiple_label_extraction():
    """Test extraction of multiple labels from single input."""
    extractor = ExactExplicitExtractor()
    
    input_text = """
    I'm looking for an AWD electric car with leather seats and at least 6 airbags.
    I prefer a sporty design style with dark colors, and it should have Level 2 autonomous driving.
    A 5-seat layout would be ideal for my family.
    """
    
    result = extractor.extract_exact_explicit_values(input_text)
    
    assert "drive_type" in result, "Should detect drive_type"
    assert "all-wheel drive" in result["drive_type"], "Should detect AWD"
    
    assert "powertrain_type" in result, "Should detect powertrain_type"
    assert "battery electric vehicle" in result["powertrain_type"], "Should detect EV"
    
    assert "seat_material" in result, "Should detect seat_material"
    assert "leather" in result["seat_material"], "Should detect leather seats"
    
    assert "airbag_count" in result, "Should detect airbag_count"
    assert "6" in result["airbag_count"], "Should detect 6 airbags"
    
    assert "design_style" in result, "Should detect design_style"
    assert "sporty" in result["design_style"], "Should detect sporty design"
    
    assert "color" in result, "Should detect color"
    assert "dark colors" in result["color"], "Should detect dark colors"
    
    assert "autonomous_driving_level" in result, "Should detect autonomous_driving_level"
    assert "l2" in result["autonomous_driving_level"], "Should detect L2"
    
    assert "seat_layout" in result, "Should detect seat_layout"
    assert "5-seat" in result["seat_layout"], "Should detect 5-seat layout"

def test_alias_synonym_extraction():
    """Test extraction using various synonyms and aliases."""
    extractor = ExactExplicitExtractor()
    
    # Test case for powertrain synonyms
    input_text = "I need a zero emission vehicle with pure electric propulsion."
    result = extractor.extract_exact_explicit_values(input_text)
    assert "powertrain_type" in result, "Should detect powertrain_type"
    assert "battery electric vehicle" in result["powertrain_type"], "Should detect BEV from synonyms"
    
    # Test case for drive type synonyms
    input_text = "I'm looking for a 4x4 with great off-road capability."
    result = extractor.extract_exact_explicit_values(input_text)
    assert "drive_type" in result, "Should detect drive_type"
    assert "all-wheel drive" in result["drive_type"], "Should detect AWD from 4x4 synonym"
    
    # Test case for airbag count with word numbers
    input_text = "Safety is important to me, so I need a car with at least ten airbags."
    result = extractor.extract_exact_explicit_values(input_text)
    assert "airbag_count" in result, "Should detect airbag_count"
    assert "10" in result["airbag_count"], "Should detect 10 airbags from 'ten' word"


if __name__ == "__main__":
    # Run all tests
    run_test("Powertrain Type Extraction", test_powertrain_type_extraction)
    run_test("Design Style Extraction", test_design_style_extraction)
    run_test("Color Extraction", test_color_extraction)
    run_test("Interior Material Extraction", test_interior_material_extraction)
    run_test("Airbag Count Extraction", test_airbag_count_extraction)
    run_test("Seat Material Extraction", test_seat_material_extraction)
    run_test("Autonomous Driving Level Extraction", test_autonomous_driving_level_extraction)
    run_test("Drive Type Extraction", test_drive_type_extraction)
    run_test("Suspension Extraction", test_suspension_extraction)
    run_test("Seat Layout Extraction", test_seat_layout_extraction)
    run_test("Multiple Label Extraction", test_multiple_label_extraction)
    run_test("Alias & Synonym Extraction", test_alias_synonym_extraction) 