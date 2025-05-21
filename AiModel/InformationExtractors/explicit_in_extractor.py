import json
import os
import re
from pathlib import Path
from typing import Dict, List, Any, Set, Optional
from concurrent.futures import ThreadPoolExecutor

# Don't use relative imports as they cause linter errors
# We'll use absolute imports for normal module usage
from InformationExtractors.range_explicit_extractor import RangeExplicitExtractor
from InformationExtractors.boolean_explicit_extractor import BooleanExplicitExtractor
from InformationExtractors.basic_explicit_extractor import BasicExplicitExtractor
from InformationExtractors.exact_explicit_extractor import ExactExplicitExtractor

class ExplicitInOneExtractor:
    """
    A unified extractor that combines RangeExplicitExtractor, BooleanExplicitExtractor,
    BasicExplicitExtractor, and ExactExplicitExtractor to extract all explicit needs 
    from user input in parallel.
    
    This extractor wraps all individual extractors into a single interface and
    merges their results to provide a comprehensive set of extracted labels.
    """
    
    def __init__(self):
        """
        Initialize all extractors (range, boolean, basic, and exact)
        """
        self.range_extractor = RangeExplicitExtractor()
        self.boolean_extractor = BooleanExplicitExtractor()
        self.basic_extractor = BasicExplicitExtractor()
        self.exact_extractor = ExactExplicitExtractor()
        
        # Load query labels from JSON file for reference
        base_dir = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        query_labels_path = os.path.join(base_dir, "Config", "QueryLabels.json")
        
        with open(query_labels_path, "r", encoding="utf-8") as f:
            self.query_labels = json.load(f)
            
    def extract_explicit_needs(self, user_input: str) -> Dict[str, Any]:
        """
        Extract all explicit needs from user input using all extractors in parallel.
        
        Args:
            user_input (str): The input text from the user
            
        Returns:
            Dict[str, Any]: Dictionary containing all extracted needs from all extractors
        """
        # Use ThreadPoolExecutor to run extractors in parallel
        with ThreadPoolExecutor(max_workers=4) as executor:
            # Submit extraction tasks
            range_future = executor.submit(self.range_extractor.extract_range_explicit_needs, user_input)
            boolean_future = executor.submit(self.boolean_extractor.extract_all_values, user_input)
            basic_future = executor.submit(self.basic_extractor.extract_basic_explicit_needs, user_input)
            exact_future = executor.submit(self.exact_extractor.extract_exact_explicit_values, user_input)
            
            # Get results
            range_needs = range_future.result()
            boolean_needs = boolean_future.result()
            basic_needs = basic_future.result()
            exact_needs = exact_future.result()
        
        # Merge all extracted needs with conflict resolution
        merged_needs = self._merge_extracted_needs(basic_needs, boolean_needs, range_needs, exact_needs, user_input)
        
        return merged_needs
        
    def _merge_extracted_needs(self, basic_needs: Dict[str, Any], boolean_needs: Dict[str, Any], 
                              range_needs: Dict[str, Any], exact_needs: Dict[str, Any], 
                              user_input: str) -> Dict[str, Any]:
        """
        Merge results from different extractors with conflict resolution.
        
        Args:
            basic_needs (Dict[str, Any]): Results from BasicExplicitExtractor
            boolean_needs (Dict[str, Any]): Results from BooleanExplicitExtractor
            range_needs (Dict[str, Any]): Results from RangeExplicitExtractor
            exact_needs (Dict[str, Any]): Results from ExactExplicitExtractor
            user_input (str): The original user input text
            
        Returns:
            Dict[str, Any]: Dictionary containing merged results
        """
        merged_needs = {}
        
        # Process basic needs first (they provide foundation)
        merged_needs.update(basic_needs)
        
        # Add range needs carefully to avoid conflicts
        for label, values in range_needs.items():
            if label in merged_needs:
                # For range labels, combine values from both sources
                existing_values = merged_needs[label]
                if isinstance(existing_values, list) and isinstance(values, list):
                    # Combine lists and remove duplicates
                    merged_values = list(set(existing_values + values))
                    merged_needs[label] = merged_values
                # Otherwise use the more detailed source
                elif len(str(values)) > len(str(existing_values)):
                    merged_needs[label] = values
            else:
                merged_needs[label] = values
                
        # Add exact needs
        for label, values in exact_needs.items():
            if label in merged_needs:
                # For design_style, handle special case (sporty vs. sports car)
                if label == "design_style" and values == ["sporty"] and merged_needs[label] == ["sports car"]:
                    continue  # Keep "sports car" as it's more specific
                
                # Combine values if both are lists
                if isinstance(merged_needs[label], list) and isinstance(values, list):
                    merged_values = list(set(merged_needs[label] + values))
                    merged_needs[label] = merged_values
                elif isinstance(values, list) and len(values) > 0:
                    merged_needs[label] = values
            else:
                merged_needs[label] = values
                
        # Direct checks for specific boolean features in the text
        # These explicit checks override the extractor results when needed
        
        # Check for lane keeping assist/guidance
        lane_keep_positive = False
        if (re.search(r"lane\s*keep", user_input.lower()) or
            re.search(r"lane\s*guidance", user_input.lower()) or
            re.search(r"lane\s*assist", user_input.lower()) or
            re.search(r"keeping\s*assist", user_input.lower())):
            # Check if there are negations
            if not (re.search(r"don't\s*need\s*lane", user_input.lower()) or
                    re.search(r"don't\s*want\s*lane", user_input.lower()) or
                    re.search(r"without\s*lane", user_input.lower())):
                lane_keep_positive = True
                
        # Check for blind spot detection/monitoring
        blind_spot_positive = False
        if (re.search(r"blind\s*spot", user_input.lower()) or
            re.search(r"blind\s*area", user_input.lower()) or
            re.search(r"monitor\s*blind", user_input.lower())):
            # Check if there are negations
            if not (re.search(r"don't\s*need\s*blind", user_input.lower()) or
                    re.search(r"don't\s*want\s*blind", user_input.lower()) or
                    re.search(r"without\s*blind", user_input.lower())):
                blind_spot_positive = True
                
        # Check for ESP/stability control
        esp_positive = False
        if (re.search(r"stability\s*control", user_input.lower()) or
            re.search(r"electronic\s*stability", user_input.lower()) or
            re.search(r"stability\s*program", user_input.lower()) or
            re.search(r"\bESP\b", user_input) or
            re.search(r"\bESC\b", user_input)):
            # Check if there are negations
            if not (re.search(r"don't\s*need\s*stab", user_input.lower()) or
                    re.search(r"don't\s*want\s*stab", user_input.lower()) or
                    re.search(r"without\s*stab", user_input.lower())):
                esp_positive = True
                
        # Check for auto parking
        auto_parking_negative = False
        if (re.search(r"don't\s*need\s*auto\s*park", user_input.lower()) or
            re.search(r"don't\s*want\s*auto\s*park", user_input.lower()) or
            re.search(r"don't\s*want\s*the\s*car\s*to\s*park\s*itself", user_input.lower()) or
            re.search(r"without\s*auto\s*parking", user_input.lower())):
            auto_parking_negative = True
        
        # Design style special cases
        sports_car_design = False
        if (re.search(r"sports\s*car\s*design", user_input.lower()) or
            re.search(r"sporty\s*design", user_input.lower()) or
            re.search(r"sports\s*car\s*style", user_input.lower())):
            sports_car_design = True
        
        # Apply the direct checks to override the extractor results
        if lane_keep_positive:
            merged_needs["lane_keep_assist"] = "yes"
        
        if blind_spot_positive:
            merged_needs["blind_spot_detection"] = "yes"
            
        if esp_positive:
            merged_needs["esp"] = "yes"
            
        if auto_parking_negative:
            merged_needs["auto_parking"] = "no"
            
        if sports_car_design:
            merged_needs["design_style"] = ["sports car"]
        
        # Now process the boolean needs for anything not handled by direct checks
        for label, value in boolean_needs.items():
            # Skip if already set by direct checks
            if label in ["lane_keep_assist", "blind_spot_detection", "esp", "auto_parking"] and label in merged_needs:
                continue
                
            # Add or update the value
            merged_needs[label] = value
            
        # Post-processing to handle specific label conflicts
        
        # Handle design_style case
        if "design_style" not in merged_needs and sports_car_design:
            merged_needs["design_style"] = ["sports car"]
        elif "design_style" in exact_needs and exact_needs["design_style"] == ["sporty"]:
            merged_needs["design_style"] = ["sports car"]
            
        # Handle seat_layout special cases
        if "seat_layout" in exact_needs:
            merged_needs["seat_layout"] = exact_needs["seat_layout"]
        elif "7-seat" in user_input.lower() or "seven seat" in user_input.lower():
            merged_needs["seat_layout"] = ["7-seat"]
        elif "5-seat" in user_input.lower() or "five seat" in user_input.lower():
            merged_needs["seat_layout"] = ["5-seat"]
            
        return merged_needs
        
    def get_needs_by_priority_range(self, low: int = 1, high: int = 99) -> List[str]:
        """
        Get label names within a specified priority range.
        This maintains compatibility with explicit_needs_extractor interface.
        
        Args:
            low (int): The lower bound of the priority range (inclusive)
            high (int): The upper bound of the priority range (inclusive)
            
        Returns:
            List[str]: List of label names within the specified priority range
        """
        needs = []
        
        for label, info in self.query_labels.items():
            priority = info.get("priority", 50)  # Default priority is 50
            if low <= priority <= high:
                needs.append(label)
                
        return needs
        
    def get_mentioned_needs(self, user_input: str) -> Dict[str, Any]:
        """
        Get needs that are explicitly mentioned in the user input.
        This is an alias for extract_explicit_needs to maintain compatibility.
        
        Args:
            user_input (str): The input text from the user
            
        Returns:
            Dict[str, Any]: Dictionary containing explicitly mentioned needs
        """
        return self.extract_explicit_needs(user_input)
        
    def _merge_range_values(self, values: List[str]) -> List[str]:
        """
        Merge overlapping range values to avoid redundancy.
        This is a helper method for future enhancement.
        
        Args:
            values (List[str]): List of range values to merge
            
        Returns:
            List[str]: Merged list with redundant values removed
        """
        # This could be implemented in the future to handle overlapping ranges
        # For now, just return the original values
        return values


# Only run this if the script is executed directly (not imported)
if __name__ == "__main__":
    # For direct script execution, we need to adjust the path
    import sys
    from pathlib import Path
    
    # Add the parent directory to sys.path to allow imports to work
    current_dir = Path(__file__).parent
    parent_dir = current_dir.parent
    sys.path.insert(0, str(parent_dir))
    
    try:
        # Example usage
        extractor = ExplicitInOneExtractor()
        
        # Test with a sample user input
        test_input = "I'm looking for a luxury electric SUV with good range, maybe 500km or more. It should have lane keep assist and blind spot detection, but I don't need auto parking. My budget is around $50,000."
        
        extracted_needs = extractor.extract_explicit_needs(test_input)
        
        print("Extracted needs:")
        for label, values in extracted_needs.items():
            print(f"{label}: {values}")
    except Exception as e:
        print(f"Error during testing: {e}")
