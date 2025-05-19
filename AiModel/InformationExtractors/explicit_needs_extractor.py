import json
import re
# from ..utils import timer_decorator
import os
from pathlib import Path

class ExplicitNeedsExtractor:
    """
    A class for extracting explicit needs from user conversations based on predefined labels
    in QueryLabels.json.
    """
    
    def __init__(self):
        """
        Initialize the ExplicitNeedsExtractor with labels loaded from QueryLabels.json.
        """
        # Load query labels from JSON file
        base_dir = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        query_labels_path = os.path.join(base_dir, "QueryLabels.json")
        
        with open(query_labels_path, 'r', encoding='utf-8') as f:
            self.query_labels = json.load(f)
        
        # Create a mapping of label synonyms for better matching
        self.label_synonyms = self._create_label_synonyms()
        
        # Create a mapping of candidate synonyms for better matching
        self.candidate_synonyms = self._create_candidate_synonyms()
        
        # Create a reverse mapping from synonyms to original label names
        self.synonym_to_label = {}
        for label, synonyms in self.label_synonyms.items():
            for synonym in synonyms:
                self.synonym_to_label[synonym] = label
        
        # Create a mapping from candidates to their labels
        self.candidate_to_label = {}
        for label, data in self.query_labels.items():
            for candidate in data.get("candidates", []):
                # Normalize the candidate for better matching
                normalized_candidate = candidate.lower()
                if normalized_candidate not in self.candidate_to_label:
                    self.candidate_to_label[normalized_candidate] = []
                self.candidate_to_label[normalized_candidate].append(label)
    
    def _create_label_synonyms(self):
        """
        Create a dictionary mapping each label to its possible synonyms.
        
        Returns:
            dict: Dictionary mapping labels to their synonyms
        """
        synonyms = {}
        
        for label, data in self.query_labels.items():
            # Add the label itself as a synonym
            label_synonyms = [label.lower()]
            
            # Add label with underscores replaced by spaces
            label_synonyms.append(label.replace("_", " ").lower())
            
            # Handle common abbreviations and variations
            variations = []
            
            # Convert "xxx_yyy" to "xxx yyy"
            if "_" in label:
                variations.append(label.replace("_", " ").lower())
            
            # Add "xxx" for "xxx_yyy" (common shorthand)
            if "_" in label:
                parts = label.split("_")
                variations.append(parts[0].lower())
            
            # Handle specific common abbreviations
            if label.lower() == "passenger_space_volume":
                variations.extend(["passenger space", "cabin space", "interior space"])
            elif label.lower() == "trunk_volume":
                variations.extend(["trunk", "boot", "cargo space"])
            elif label.lower() == "vehicle_category_top":
                variations.extend(["vehicle type", "car type", "vehicle category"])
            elif label.lower() == "powertrain_type":
                variations.extend(["engine type", "powertrain", "propulsion"])
            elif label.lower() == "autonomous_driving_level":
                variations.extend(["autonomous driving", "self driving", "autopilot"])
            elif label.lower() == "noise_insulation":
                variations.extend(["sound insulation", "sound proofing", "noise reduction"])
            
            # Add the variations to the synonyms list
            label_synonyms.extend(variations)
            
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
        
        for label, data in self.query_labels.items():
            candidates = data.get("candidates", [])
            
            for candidate in candidates:
                # Add the candidate itself as a synonym
                synonyms = [candidate.lower()]
                
                # Add specific synonyms for common values
                if candidate.lower() == "yes":
                    synonyms.extend(["available", "supported", "has", "with", "including"])
                elif candidate.lower() == "no":
                    synonyms.extend(["unavailable", "not supported", "doesn't have", "without"])
                elif candidate.lower() == "gasoline engine":
                    synonyms.extend(["gas engine", "petrol engine", "gas"])
                elif candidate.lower() == "battery electric vehicle":
                    synonyms.extend(["electric car", "ev", "battery electric", "electric vehicle"])
                elif candidate.lower() == "hybrid electric vehicle":
                    synonyms.extend(["hybrid", "hev"])
                elif candidate.lower() == "plug-in hybrid electric vehicle":
                    synonyms.extend(["plug-in hybrid", "phev"])
                
                # Remove duplicates
                synonyms = list(set(synonyms))
                
                candidate_synonyms[candidate] = synonyms
        
        return candidate_synonyms
    
    # @timer_decorator
    def get_needs_by_priority_range(self, low=1, high=99):
        """
        Get all labels that fall within the specified priority range.
        
        Args:
            low (int): Lower bound of priority range (inclusive), default is 1
            high (int): Upper bound of priority range (inclusive), default is 99
            
        Returns:
            dict: Dictionary of labels within the specified priority range
        """
        filtered_labels = {}
        
        for label, data in self.query_labels.items():
            priority = data.get("priority", 99)
            if low <= priority <= high:
                filtered_labels[label] = data
        
        return filtered_labels
    
    # @timer_decorator
    def get_mentioned_needs(self, user_input):
        """
        Extract labels mentioned in the user input.
        
        Only specific labels can be indirectly mentioned through their candidates:
        - interior_material_texture
        - design_style
        - brand
        - brand_country
        - brand_area
        - vehicle_category_bottom
        - vehicle_category_middle
        - vehicle_category_top
        - seat_layout
        - powertrain_type
        
        Other labels must be directly mentioned by name.
        
        Args:
            user_input (str): User's conversation text
            
        Returns:
            list: List of mentioned label names
        """
        # Define which labels can be indirectly mentioned through candidates
        indirect_mention_labels = {
            "interior_material_texture",
            "design_style",
            "brand",
            "brand_country", 
            "brand_area",
            "vehicle_category_bottom",
            "vehicle_category_middle",
            "vehicle_category_top",
            "seat_layout",
            "powertrain_type",
        }
        
        mentioned_labels = set()
        
        # Normalize the input
        normalized_input = user_input.lower()
        
        # Check if any label or its synonym is directly mentioned
        for label, synonyms in self.label_synonyms.items():
            for synonym in synonyms:
                if re.search(r'\b' + re.escape(synonym) + r'\b', normalized_input):
                    mentioned_labels.add(label)
                    break
        
        # Check if any candidate of allowed labels is mentioned
        for candidate, labels in self.candidate_to_label.items():
            # Filter to only include indirect_mention_labels
            relevant_labels = [label for label in labels if label in indirect_mention_labels]
            if not relevant_labels:
                continue
                
            # Check for exact match of candidate
            if re.search(r'\b' + re.escape(candidate) + r'\b', normalized_input):
                mentioned_labels.update(relevant_labels)
                continue
            
            # Check for synonyms of the candidate
            for orig_candidate, synonyms in self.candidate_synonyms.items():
                if candidate == orig_candidate.lower():
                    for synonym in synonyms:
                        if re.search(r'\b' + re.escape(synonym) + r'\b', normalized_input):
                            mentioned_labels.update(relevant_labels)
                            break
        
        return list(mentioned_labels)
    
    def _map_value_to_range(self, value, label):
        """
        Map a specific numeric value to a predefined range for range-based labels.
        
        Args:
            value (float/int): The numeric value to map
            label (str): The label to map the value against
            
        Returns:
            str: The range candidate value the numeric value falls into, or None if no match
        """
        # Remove potential currency symbols and units
        value_str = str(value).strip()
        value_str = re.sub(r'[^\d.]', '', value_str)
        
        try:
            value = float(value_str)
        except ValueError:
            return None
            
        # Define mapping rules for different labels
        if label == "prize":
            if value < 10000:
                return "below 10,000"
            elif 10000 <= value < 20000:
                return "10,000 ~ 20,000"
            elif 20000 <= value < 30000:
                return "20,000 ~ 30,000"
            elif 30000 <= value < 40000:
                return "30,000 ~ 40,000"
            elif 40000 <= value < 60000:
                return "40,000 ~ 60,000"
            elif 60000 <= value < 100000:
                return "60,000 ~ 100,000"
            else:
                return "above 100,000"
                
        elif label == "passenger_space_volume":
            # Values assumed to be in cubic meters (m³)
            if value < 3.5:
                return "2.5-3.5 m³"
            elif 3.5 <= value < 4.5:
                return "3.5-4.5 m³"
            elif 4.5 <= value < 5.5:
                return "4.5-5.5 m³"
            else:
                return "above 5.5 m³"
                
        elif label == "trunk_volume":
            # Values assumed to be in liters (l)
            if value < 300:
                return "200 - 300l"
            elif 300 <= value < 400:
                return "300-400l"
            elif 400 <= value < 500:
                return "400-500l"
            else:
                return "above 500l"
                
        elif label == "wheelbase":
            # Values assumed to be in millimeters (mm)
            if value < 2650:
                return "2300-2650mm"
            elif 2650 <= value < 2800:
                return "2650-2800mm"
            elif 2800 <= value < 2950:
                return "2800-2950mm"
            elif 2950 <= value < 3100:
                return "2950-3100mm"
            else:
                return "above 3100mm"
                
        elif label == "chassis_height":
            # Values assumed to be in millimeters (mm)
            if value < 130:
                return "100-130mm"
            elif 130 <= value < 150:
                return "130-150mm"
            elif 150 <= value < 200:
                return "150-200mm"
            else:
                return "above 200mm"
                
        elif label == "engine_displacement":
            # Values assumed to be in liters (l)
            if value < 1.0:
                return "below 1.0l"
            elif 1.0 <= value < 1.6:
                return "1.0-1.6l"
            elif 1.6 <= value < 2.0:
                return "1.6-2.0l"
            elif 2.0 <= value < 2.5:
                return "2.0-2.5l"
            elif 2.5 <= value < 3.5:
                return "2.5-3.5l"
            elif 3.5 <= value < 6.0:
                return "3.5-6.0l"
            else:
                return "above 6.0l"
                
        elif label == "motor_power":
            # Values assumed to be in kilowatts (kW)
            if value < 70:
                return "below 70kw"
            elif 70 <= value < 120:
                return "70-120kw"
            elif 120 <= value < 180:
                return "120-180kw"
            elif 180 <= value < 250:
                return "180-250kw"
            elif 250 <= value < 400:
                return "250-400kw"
            else:
                return "above 400kw"
                
        elif label == "battery_capacity":
            # Values assumed to be in kilowatt-hours (kWh)
            if value < 40:
                return "below 40kwh"
            elif 40 <= value < 60:
                return "40-60kwh"
            elif 60 <= value < 80:
                return "60-80kwh"
            elif 80 <= value < 100:
                return "80-100kwh"
            else:
                return "above 100kwh"
                
        elif label == "fuel_tank_capacity":
            # Values assumed to be in liters (l)
            if value < 45:
                return "below 45l"
            elif 45 <= value < 60:
                return "45-60l"
            elif 60 <= value < 80:
                return "60-80l"
            else:
                return "above 80l"
                
        elif label == "horsepower":
            # Values in hp
            if value < 100:
                return "below 100hp"
            elif 100 <= value < 150:
                return "100-150hp"
            elif 150 <= value < 200:
                return "150-200hp"
            elif 200 <= value < 300:
                return "200-300hp"
            elif 300 <= value < 500:
                return "300-500hp"
            else:
                return "above 500hp"
                
        elif label == "torque":
            # Values in Newton-meters (Nm)
            if value < 200:
                return "below 200nm"
            elif 200 <= value < 300:
                return "200-300nm"
            elif 300 <= value < 400:
                return "300-400nm"
            elif 400 <= value < 600:
                return "400-600nm"
            else:
                return "above 600nm"
                
        elif label == "zero_to_one_hundred_km_h_acceleration_time":
            # Values in seconds (s)
            if value < 5:
                return "below 5s"
            elif 5 <= value < 7:
                return "5-7s"
            elif 7 <= value < 9:
                return "7-9s"
            elif 9 <= value < 11:
                return "9-11s"
            else:
                return "above 11s"
                
        elif label == "top_speed":
            # Values in kilometers per hour (km/h)
            if value < 160:
                return "below 160km/h"
            elif 160 <= value < 180:
                return "160-180km/h"
            elif 180 <= value < 200:
                return "180-200km/h"
            elif 200 <= value < 250:
                return "200-250km/h"
            else:
                return "above 250km/h"
                
        elif label == "fuel_consumption":
            # Values in liters per 100 kilometers (L/100km)
            if value < 5:
                return "below 5l/100km"
            elif 5 <= value < 7:
                return "5-7l/100km"
            elif 7 <= value < 9:
                return "7-9l/100km"
            elif 9 <= value < 12:
                return "9-12l/100km"
            else:
                return "above 12l/100km"
                
        elif label == "electric_consumption":
            # Values in kilowatt-hours per 100 kilometers (kWh/100km)
            if value < 15:
                return "below 15kwh/100km"
            elif 15 <= value < 18:
                return "15-18kwh/100km"
            elif 18 <= value < 21:
                return "18-21kwh/100km"
            else:
                return "above 21kwh/100km"
                
        elif label == "driving_range":
            # Values in kilometers (km)
            if value < 300:
                return "below 300km"
            elif 300 <= value < 400:
                return "300-400km"
            elif 400 <= value < 500:
                return "400-500km"
            elif 500 <= value < 600:
                return "500-600km"
            else:
                return "above 600km"
                
        # If no matching rules or label not recognized
        return None
    
    def _extract_numeric_values(self, text):
        """
        Extract numeric values with potential units from text.
        Recognizes various expressions of the same unit type.
        
        Args:
            text (str): The text to analyze
            
        Returns:
            list: List of tuples (value, context, unit_type) where context is the surrounding text
                  and unit_type helps identify the measurement type
        """
        # Normalize text for better matching (remove extra spaces, lowercase)
        text = ' '.join(text.lower().split())
        
        # Patterns for different formats of numeric values with potential units
        patterns = [
            # Price with various formats
            # $25,000, 25,000$, 25,000 dollars, 25k, 25 grand, 25,000 USD
            (r'(?:[$€¥£])\s*(\d{1,3}(?:,\d{3})*(?:\.\d+)?|\d+(?:\.\d+)?)|(\d{1,3}(?:,\d{3})*(?:\.\d+)?|\d+(?:\.\d+)?)\s*(?:[$€¥£]|\bdollars?\b|\beuro\b|\byuan\b|\bpounds?\b|\busd\b|\beur\b|\bcny\b|\bjpy\b|\bgbp\b|\bk\b|\bgrand\b|\bthousand\b)', "prize"),
            
            # Passenger space volume or trunk volume
            # 3.5m³, 3.5 cubic meters, 350L, 350 liters
            (r'(\d+(?:\.\d+)?)\s*(?:m[³3]|cubic\s*m(?:eters?|etres?)?|cu\.?\s*m)', "volume_cubic_meters"),
            (r'(\d+(?:\.\d+)?)\s*(?:l\b|liters?\b|litres?\b)', "volume_liters"),
            
            # Wheelbase and chassis height - length measurements
            # 2800mm, 2.8m, 280cm, 2800 millimeters
            (r'(\d+(?:\.\d+)?)\s*(?:mm\b|millimeters?\b|millimetres?\b)', "length_mm"),
            (r'(\d+(?:\.\d+)?)\s*(?:cm\b|centimeters?\b|centimetres?\b)', "length_cm"),
            (r'(\d+(?:\.\d+)?)\s*(?:m\b|meters?\b|metres?\b)(?!\s*[³3])', "length_m"),
            
            # Engine displacement
            # 2.0L, 2000cc, 2.0 liters, 2000 cubic centimeters
            (r'(\d+(?:\.\d+)?)\s*(?:l\b|liters?\b|litres?\b|ltr\b)', "engine_displacement"),
            (r'(\d+(?:\.\d+)?)\s*(?:cc\b|cm[³3]\b|cubic\s*centimeters?\b|cubic\s*centimetres?\b)', "engine_displacement_cc"),
            
            # Motor power
            # 150kW, 150 kilowatts, 150 kW
            (r'(\d+(?:\.\d+)?)\s*(?:kw\b|kilowatts?\b|kilo\s*watts?\b)', "motor_power"),
            
            # Battery capacity
            # 60kWh, 60 kilowatt hours, 60 kWh
            (r'(\d+(?:\.\d+)?)\s*(?:kwh\b|kilowatt[\s-]*hours?\b|kw[\s-]*h\b)', "battery_capacity"),
            
            # Fuel tank capacity
            # 60L, 60 liters, 60 liter tank
            (r'(\d+(?:\.\d+)?)\s*(?:l\b|liters?\b|litres?\b)(?:\s+tank)?\b', "fuel_tank_capacity"),
            
            # Horsepower
            # 200hp, 200 horsepower, 200bhp, 200 PS
            (r'(\d+(?:\.\d+)?)\s*(?:hp\b|horsepower\b|bhp\b|ps\b)', "horsepower"),
            
            # Torque
            # 400Nm, 400 newton meters, 400 N·m
            (r'(\d+(?:\.\d+)?)\s*(?:nm\b|n[\s·-]*m\b|newton[\s-]*meters?\b|newton[\s-]*metres?\b)', "torque"),
            
            # Acceleration time
            # 0-100 in 6s, accelerates to 100 km/h in 6 seconds, 0 to 60 mph in 6 seconds
            (r'(?:0[\s-]*to[\s-]*100|0[\s-]*100|zero[\s-]*to[\s-]*(?:100|hundred)|acceleration)(?:\s+(?:km/h|kph))?\s+(?:in\s+)?(\d+(?:\.\d+)?)\s*(?:s\b|sec(?:ond)?s?\b)|(\d+(?:\.\d+)?)\s*(?:s\b|sec(?:ond)?s?\b)(?:\s+(?:0[\s-]*to[\s-]*100|acceleration|zero[\s-]*to))', "acceleration_time"),
            
            # Top speed
            # 200km/h, 200 kilometers per hour, 200 kph, max speed 200
            (r'(\d+(?:\.\d+)?)\s*(?:km/h\b|kmph\b|kph\b|kilometers?\s+per\s+hour\b|kilometres?\s+per\s+hour\b)|(?:top|max(?:imum)?|highest)\s+speed\s+(?:of\s+)?(\d+(?:\.\d+)?)', "top_speed"),
            
            # Fuel consumption
            # 7L/100km, 7 liters per 100 kilometers, 7 liters/100km, fuel economy of 7
            (r'(\d+(?:\.\d+)?)\s*(?:l/100\s*km\b|liters?\s+per\s+100\s+kilometers?\b|litres?\s+per\s+100\s+kilometres?\b|liters?/100\s*km\b|litres?/100\s*km\b)|(?:fuel\s+consumption|fuel\s+economy|gas\s+mileage)\s+(?:of\s+)?(\d+(?:\.\d+)?)', "fuel_consumption"),
            
            # Electric consumption
            # 18kWh/100km, 18 kWh per 100 km
            (r'(\d+(?:\.\d+)?)\s*(?:kwh/100\s*km\b|kilowatt[\s-]*hours?\s+per\s+100\s+kilometers?\b|kilowatt[\s-]*hours?/100\s*km\b|kw[\s-]*h/100\s*km\b)', "electric_consumption"),
            
            # Driving range
            # 400km, 400 kilometer range, range of 400, 400 km on a single charge
            (r'(?:range\s+(?:of\s+)?)?(\d+(?:\.\d+)?)\s*(?:km\b|kilometers?\b|kilometres?\b)(?:\s+range)?|(?:range|distance)\s+(?:of\s+)?(\d+(?:\.\d+)?)|(\d+(?:\.\d+)?)\s*(?:km\b|kilometers?\b|kilometres?\b)\s+(?:on\s+a|per|with\s+one)\s+(?:single\s+)?(?:charge|tank)', "driving_range")
        ]
        
        extracted_values = []
        
        for pattern, unit_type in patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                # Get the capturing group that matched
                value = next((g for g in match.groups() if g is not None), None)
                if value:
                    # Remove commas from numbers like 25,000
                    value = value.replace(',', '')
                    
                    # Convert k/K (thousands) to actual number
                    if value.lower().endswith('k'):
                        value = value[:-1]
                        try:
                            value = str(float(value) * 1000)
                        except ValueError:
                            continue
                    
                    # Get some context for the value (text before and after)
                    start = max(0, match.start() - 25)
                    end = min(len(text), match.end() + 25)
                    context = text[start:end].lower()
                    
                    try:
                        extracted_values.append((float(value), context, unit_type))
                    except ValueError:
                        continue
        
        return extracted_values
    
    def _determine_likely_label_for_value(self, value, context, unit_type):
        """
        Determine the most likely label for a numeric value based on its context and unit type.
        
        Args:
            value (float): The numeric value
            context (str): The context string surrounding the value
            unit_type (str): The type of unit detected
            
        Returns:
            str: The most likely label, or None if undetermined
        """
        # Direct mapping from unit_type to label when unambiguous
        unit_to_label = {
            "prize": "prize",
            "volume_cubic_meters": "passenger_space_volume",  # Could be passenger_space_volume or trunk_volume
            "volume_liters": "trunk_volume",  # Could be trunk_volume or fuel_tank_capacity
            "length_mm": None,  # Could be wheelbase or chassis_height
            "length_cm": None,  # Could be wheelbase or chassis_height
            "length_m": None,  # Could be wheelbase
            "engine_displacement": "engine_displacement",
            "engine_displacement_cc": "engine_displacement",
            "motor_power": "motor_power",
            "battery_capacity": "battery_capacity",
            "fuel_tank_capacity": "fuel_tank_capacity",
            "horsepower": "horsepower",
            "torque": "torque",
            "acceleration_time": "zero_to_one_hundred_km_h_acceleration_time",
            "top_speed": "top_speed",
            "fuel_consumption": "fuel_consumption",
            "electric_consumption": "electric_consumption",
            "driving_range": "driving_range"
        }
        
        # Look for contextual clues to resolve ambiguous unit types
        context_clues = {
                        "prize": ["price", "cost", "dollar", "euro", "money", "budget", "afford", "expensive", "cheap", "worth", "pay"],
            "passenger_space_volume": ["passenger space", "cabin space", "interior space", "interior volume", "cabin volume", "passenger volume", "cabin size", "interior size"],
            "trunk_volume": ["trunk", "boot", "cargo", "luggage", "storage space", "storage capacity", "cargo capacity", "trunk size", "boot size"],
            "wheelbase": ["wheelbase", "wheel base", "between wheels", "wheel to wheel"],
            "chassis_height": ["chassis height", "ground clearance", "ride height", "under clearance", "off-road height", "clearance height"],
            "engine_displacement": ["engine displacement", "engine size", "engine volume", "engine capacity", "displacement", "cc", "cubic centimeter", "liter engine"],
            "motor_power": ["motor power", "engine power", "power output", "motor output", "kw", "kilowatt"],
            "battery_capacity": ["battery capacity", "battery size", "battery power", "kwh", "kilowatt hour", "kilowatt-hour", "battery energy"],
            "fuel_tank_capacity": ["fuel tank", "gas tank", "tank capacity", "fuel capacity", "gas capacity", "tank size"],
            "horsepower": ["horsepower", "hp", "bhp", "power", "engine power"],
            "torque": ["torque", "nm", "newton meter", "turning force", "twist", "newton-meter"],
            "zero_to_one_hundred_km_h_acceleration_time": ["0-100", "0-60", "acceleration", "zero to", "seconds to", "sprint time", "accelerate to"],
            "top_speed": ["top speed", "maximum speed", "max speed", "fastest", "km/h", "kph", "kilometers per hour", "speed limit"],
            "fuel_consumption": ["fuel consumption", "gas mileage", "fuel economy", "miles per gallon", "mpg", "l/100km", "liters per 100"],
            "electric_consumption": ["electric consumption", "electricity usage", "kwh/100km", "power consumption", "energy usage", "energy consumption"],
            "driving_range": ["driving range", "range", "distance on", "travel on", "km range", "mile range", "single charge", "tank of fuel"]
        }
        
        # Get initial label from unit type
        label = unit_to_label.get(unit_type)
        
        # If label is None or potentially ambiguous, use context to disambiguate
        if unit_type in ["volume_cubic_meters", "volume_liters", "length_mm", "length_cm", "length_m"]:
            best_match = None
            max_matches = 0
            
            # Determine which labels to check based on unit_type
            labels_to_check = []
            if unit_type == "volume_cubic_meters":
                labels_to_check = ["passenger_space_volume", "trunk_volume"]
            elif unit_type == "volume_liters":
                labels_to_check = ["trunk_volume", "fuel_tank_capacity"]
            elif unit_type in ["length_mm", "length_cm", "length_m"]:
                labels_to_check = ["wheelbase", "chassis_height"]
                
            for potential_label in labels_to_check:
                clues = context_clues.get(potential_label, [])
                matches = sum(1 for clue in clues if clue in context)
                if matches > max_matches:
                    max_matches = matches
                    best_match = potential_label
            
            if best_match:
                label = best_match
            else:
                # Default mappings for ambiguous units with no clear context
                if unit_type == "volume_cubic_meters":
                    label = "passenger_space_volume"  # Default to passenger space for cubic meters
                elif unit_type == "volume_liters":
                    label = "trunk_volume"  # Default to trunk volume for liters
                elif unit_type == "length_mm" or unit_type == "length_cm":
                    # Convert to approximate range for wheelbase vs chassis height
                    if unit_type == "length_mm":
                        if value >= 2000:  # Likely wheelbase
                            label = "wheelbase"
                        else:  # Likely chassis height
                            label = "chassis_height"
                    elif unit_type == "length_cm":
                        if value >= 200:  # Likely wheelbase
                            label = "wheelbase"
                        else:  # Likely chassis height
                            label = "chassis_height"
                elif unit_type == "length_m":
                    label = "wheelbase"  # Default to wheelbase for meters
        
        return label
        
    def _convert_to_standard_unit(self, value, unit_type):
        """
        Convert a value to the standard unit expected by _map_value_to_range.
        
        Args:
            value (float): The numeric value
            unit_type (str): The type of unit detected
            
        Returns:
            float: The value converted to the standard unit
        """
        # For each label, we need to convert to the expected unit
        if unit_type == "length_cm":
            # Convert cm to mm for wheelbase or chassis_height
            return value * 10
        elif unit_type == "length_m":
            # Convert m to mm for wheelbase or chassis_height
            return value * 1000
        elif unit_type == "engine_displacement_cc":
            # Convert cc to liters for engine_displacement
            return value / 1000
        
        # For other unit types, no conversion needed
        return value
    
    # @timer_decorator
    def extract_explicit_needs(self, user_input):
        """
        Extract explicit needs (label and value pairs) from user input.
        Only values that are defined in the labels' candidates are extracted.
        
        Only specific labels can be indirectly mentioned through their candidates:
        - interior_material_texture
        - design_style
        - brand
        - brand_country
        - brand_area
        - vehicle_category_bottom
        - vehicle_category_middle
        - vehicle_category_top
        - seat_layout
        - powertrain_type
        
        Other labels must be directly mentioned by name.
        
        For range-based labels, if a specific numeric value is mentioned, it will
        be mapped to the appropriate range:
        - prize
        - passenger_space_volume
        - trunk_volume
        - wheelbase
        - chassis_height
        - engine_displacement
        - motor_power
        - battery_capacity
        - fuel_tank_capacity
        - horsepower
        - torque
        - zero_to_one_hundred_km_h_acceleration_time
        - top_speed
        - fuel_consumption
        - electric_consumption
        - driving_range
        
        Args:
            user_input (str): User's conversation text
            
        Returns:
            dict: Dictionary mapping label names to their extracted values
        """
        explicit_needs = {}
        
        # Normalize the input
        normalized_input = user_input.lower()
        
        # Define which labels can be indirectly mentioned through candidates
        indirect_mention_labels = {
            "interior_material_texture",
            "design_style",
            "brand",
            "brand_country", 
            "brand_area",
            "vehicle_category_bottom",
            "vehicle_category_middle",
            "vehicle_category_top",
            "seat_layout",
            "powertrain_type",
        }
        
        # Define range-based labels
        range_based_labels = {
            "prize",
            "passenger_space_volume",
            "trunk_volume",
            "wheelbase",
            "chassis_height",
            "engine_displacement",
            "motor_power",
            "battery_capacity",
            "fuel_tank_capacity",
            "horsepower",
            "torque",
            "zero_to_one_hundred_km_h_acceleration_time",
            "top_speed",
            "fuel_consumption",
            "electric_consumption",
            "driving_range",
        }
        
        # Get all mentioned labels (direct mentions)
        directly_mentioned_labels = []
        
        # Check if any label or its synonym is directly mentioned
        for label, synonyms in self.label_synonyms.items():
            for synonym in synonyms:
                if re.search(r'\b' + re.escape(synonym) + r'\b', normalized_input):
                    directly_mentioned_labels.append(label)
                    break
        
        # Get indirect mentions only for allowed labels
        indirectly_mentioned_labels = []
        
        # Check if any candidate of allowed labels is mentioned
        for candidate, labels in self.candidate_to_label.items():
            # Filter to only include indirect_mention_labels
            relevant_labels = [label for label in labels if label in indirect_mention_labels]
            if not relevant_labels:
                continue
                
            # Check for exact match of candidate
            if re.search(r'\b' + re.escape(candidate) + r'\b', normalized_input):
                indirectly_mentioned_labels.extend(relevant_labels)
                continue
            
            # Check for synonyms of the candidate
            for orig_candidate, synonyms in self.candidate_synonyms.items():
                if candidate == orig_candidate.lower():
                    for synonym in synonyms:
                        if re.search(r'\b' + re.escape(synonym) + r'\b', normalized_input):
                            indirectly_mentioned_labels.extend(relevant_labels)
                            break
        
        # Combine both direct and indirect mentions
        mentioned_labels = list(set(directly_mentioned_labels + indirectly_mentioned_labels))
        
        # For each mentioned label, try to find a corresponding candidate value
        for label in mentioned_labels:
            if label not in self.query_labels:
                continue
                
            candidates = self.query_labels[label].get("candidates", [])
            
            # Check each candidate for this label
            for candidate in candidates:
                normalized_candidate = candidate.lower()
                
                # Check for exact match of candidate
                if re.search(r'\b' + re.escape(normalized_candidate) + r'\b', normalized_input):
                    explicit_needs[label] = candidate
                    break
                
                # Check for synonyms of the candidate
                if candidate in self.candidate_synonyms:
                    for synonym in self.candidate_synonyms[candidate]:
                        if re.search(r'\b' + re.escape(synonym) + r'\b', normalized_input):
                            explicit_needs[label] = candidate
                            break
                    
                    # If we found a match through a synonym, break the candidate loop
                    if label in explicit_needs:
                        break
        
        # Extract numeric values and map them to range-based labels
        extracted_values = self._extract_numeric_values(user_input)
        
        # For directly mentioned range labels that don't yet have a value
        for label in directly_mentioned_labels:
            if label in range_based_labels and label not in explicit_needs:
                # Find the most relevant numeric value for this label
                for value, context, unit_type in extracted_values:
                    # If the unit_type directly corresponds to this label, use it
                    likely_label = self._determine_likely_label_for_value(value, context, unit_type)
                    
                    if likely_label == label:
                        # Convert to standard unit if needed
                        converted_value = self._convert_to_standard_unit(value, unit_type)
                        range_value = self._map_value_to_range(converted_value, label)
                        if range_value:
                            explicit_needs[label] = range_value
                            break
                            
                    # Check if context contains the label or its synonyms
                    if not likely_label:
                        label_found = False
                        for synonym in self.label_synonyms.get(label, []):
                            if synonym in context:
                                label_found = True
                                break
                                
                        if label_found:
                            # Convert to standard unit if needed
                            converted_value = self._convert_to_standard_unit(value, unit_type)
                            range_value = self._map_value_to_range(converted_value, label)
                            if range_value:
                                explicit_needs[label] = range_value
                                break
        
        # For numeric values that haven't been assigned to a label yet
        for value, context, unit_type in extracted_values:
            # Try to determine the likely label for this value
            likely_label = self._determine_likely_label_for_value(value, context, unit_type)
            
            # If the label is in our range labels and not already assigned
            if likely_label in range_based_labels and likely_label not in explicit_needs:
                # Convert to standard unit if needed
                converted_value = self._convert_to_standard_unit(value, unit_type)
                range_value = self._map_value_to_range(converted_value, likely_label)
                if range_value:
                    explicit_needs[likely_label] = range_value
        
        return explicit_needs


# Example usage
if __name__ == "__main__":
    extractor = ExplicitNeedsExtractor()
    
    # Test with various user inputs
    test_inputs = [
        # Price and vehicle category combinations
        "I want a car for low energy consumption and around 25,000 dollars",
        "I'm looking for a mid-range sedan between 30,000 to 40,000 dollars with leather seats",
        "Can you recommend a luxury SUV above 100,000 with a panoramic sunroof?",
        "I need an economy car, preferably a small sedan below 10,000",
        "I'm interested in a mid-range high-end crossover SUV with at least 6 airbags",
        
        # Powertrain and technical specifications
        "I want a hybrid electric vehicle with good fuel efficiency and spacious trunk",
        "Looking for a battery electric vehicle with at least 250kw motor power and fast charging",
        "I prefer a gasoline engine with 2.0-2.5L displacement and automatic transmission",
        "Need a plug-in hybrid with at least moderate acceleration and low fuel consumption",
        
        # Comfort and space features
        "I want a car with large passenger space volume and a luxurious trunk",
        "Looking for a vehicle with luxury spacious wheelbase and off-road chassis height",
        "Need a car with high noise insulation and comfortable leather seats",
        "I prefer cars with wood trim interior and neutral colors",
        
        # Brand preferences
        "I'm looking for a German luxury brand like Mercedes-Benz or Audi",
        "I prefer Japanese brands like Toyota or Honda for reliability",
        "Can you recommend a good American electric car? I'm thinking of Tesla",
        "I'm interested in Chinese brands like BYD or NIO for their tech features",
        
        # Safety features
        "Safety is my priority - I need a car with ABS, ESP, and at least 8 airbags",
        "I want a vehicle with automatic emergency braking and lane keep assist",
        "Looking for a car with blind spot detection and fatigue driving detection",
        "Need a vehicle with high crash test ratings and comprehensive safety features",
        
        # Tech and assistance features
        "I want a car with L3 autonomous driving and adaptive cruise control",
        "Looking for a vehicle with traffic jam assist and remote parking capabilities",
        "I need a car with voice interaction and OTA updates for future-proofing",
        "Can you suggest a car with auto parking and 360-degree cameras?",
        
        # Design and style
        "I prefer a sporty design with low ride height and bright colors",
        "Looking for a business style sedan with high body line smoothness",
        "I want an SUV with off-road capabilities and rugged design",
        "Need a family-friendly vehicle with practical design and neutral colors",
        
        # Specific vehicle categories
        "I'm interested in a compact SUV or maybe a B-segment sedan",
        "Looking for a micro sedan for city driving with good parking abilities",
        "I need a large MPV for my large family, at least 7 seats",
        "Can you recommend a good four-door hardtop sports car?",
        
        # Combination of multiple needs
        "I need a mid-size business MPV with leather seats, voice interaction, and remote parking",
        "Looking for a compact sedan with hybrid powertrain, moderate acceleration, and L2 autonomous driving",
        "I want an all-terrain SUV with diesel engine, high chassis, and comprehensive safety features",
        "Need a convertible sports car with automatic transmission, high-end sound system, and sporty design",
        
        # Complex combinations
        "I'm looking for a German luxury sedan with leather seats, L3 autonomous driving, hybrid powertrain, and a price range between 60,000 and 100,000",
        "Need a Japanese or Korean compact SUV with good fuel efficiency, at least 6 airbags, lane keep assist, and a price below 30,000",
        "I want a Chinese electric vehicle with fast charging, at least 400 km range, voice interaction, OTA updates, and automatic parking",
        "Looking for an American muscle car with large engine displacement, sporty design, luxury interior, and comprehensive safety features"
    ]
    
    for input_text in test_inputs:
        print(f"Input: {input_text}")
        
        # Get mentioned labels
        mentioned = extractor.get_mentioned_needs(input_text)
        print(f"Mentioned labels: {mentioned}")
        
        # Extract explicit needs
        needs = extractor.extract_explicit_needs(input_text)
        print(f"Explicit needs: {needs}")
        print() 