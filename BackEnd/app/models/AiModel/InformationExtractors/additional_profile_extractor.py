import json
import re
import os
from pathlib import Path

class AdditionalProfileExtractor:
    """
    A class for extracting additional user profile information from conversations,
    including family size, price sensitivity, residence, and parking conditions.
    """
    
    def __init__(self):
        """
        Initialize the AdditionalProfileExtractor with user profile configuration.
        """
        # Load user profile configuration from JSON file
        base_dir = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        user_profile_path = os.path.join(base_dir, "Config", "UserProfile.json")
        
        with open(user_profile_path, 'r', encoding='utf-8') as f:
            self.user_profile_config = json.load(f)["AdditionalInformation"]
        
        # Define mappings for price sensitivity variations
        self.price_sensitivity_mapping = {
            # High price sensitivity (very concerned about price)
            "high": "High",
            "very concerned": "High",
            "tight": "High",
            "limited": "High",
            "budget conscious": "High",
            "budget-conscious": "High",
            "affordable": "High",
            "economical": "High",
            "cheap": "High",
            "inexpensive": "High",
            "cost-effective": "High",
            "cost effective": "High",
            "low cost": "High",
            "low-cost": "High",
            "low price": "High",
            "low-price": "High",
            "low budget": "High",
            "low-budget": "High",
            "tight budget": "High",
            "save money": "High",
            "saving money": "High",
            "price is important": "High",
            "price is a concern": "High",
            "price is the main concern": "High",
            "price is a major factor": "High",
            "care about price": "High",
            "price matters": "High",
            "price sensitive": "High",
            "price-sensitive": "High",
            
            # Medium price sensitivity
            "medium": "Medium",
            "moderate": "Medium",
            "reasonable": "Medium",
            "balanced": "Medium",
            "fair": "Medium",
            "mid-range": "Medium",
            "mid range": "Medium",
            "middle": "Medium",
            "average": "Medium",
            "not too expensive": "Medium",
            "not too cheap": "Medium",
            "willing to pay for quality": "Medium",
            "quality and price": "Medium",
            "balance between price and quality": "Medium",
            "value for money": "Medium",
            "somewhat concerned about price": "Medium",
            "price is somewhat important": "Medium",
            "price is a factor": "Medium",
            
            # Low price sensitivity (not concerned about price)
            "low": "Low",
            "not concerned": "Low",
            "not worried": "Low",
            "flexible": "Low",
            "high-end": "Low",
            "high end": "Low",
            "premium": "Low",
            "luxury": "Low",
            "expensive": "Low",
            "top-tier": "Low",
            "top tier": "Low",
            "price is not an issue": "Low",
            "price doesn't matter": "Low",
            "price is not important": "Low",
            "price is not a concern": "Low",
            "budget is not a concern": "Low",
            "money is not an issue": "Low",
            "cost is not a problem": "Low",
            "willing to spend": "Low",
            "willing to pay more": "Low",
            "quality over price": "Low",
            "best regardless of price": "Low",
            "price insensitive": "Low"
        }
        
        # Define mappings for parking conditions
        self.parking_conditions_mapping = {
            "allocated": "Allocated Parking Space",
            "dedicated": "Allocated Parking Space",
            "assigned": "Allocated Parking Space",
            "reserved": "Allocated Parking Space",
            "private": "Allocated Parking Space",
            "own parking": "Allocated Parking Space",
            "garage": "Allocated Parking Space",
            "driveway": "Allocated Parking Space",
            "parking space": "Allocated Parking Space",
            "parking spot": "Allocated Parking Space",
            "carport": "Allocated Parking Space",
            
            "temporary": "Temporary Parking Alllowed",
            "street": "Temporary Parking Alllowed",
            "public": "Temporary Parking Alllowed",
            "shared": "Temporary Parking Alllowed",
            "limited time": "Temporary Parking Alllowed",
            "time-restricted": "Temporary Parking Alllowed",
            "metered": "Temporary Parking Alllowed",
            "paid parking": "Temporary Parking Alllowed",
            "parking lot": "Temporary Parking Alllowed",
            "parking garage": "Temporary Parking Alllowed",
            
            "charging": "Charging Pile Facilites Available",
            "charger": "Charging Pile Facilites Available",
            "charging station": "Charging Pile Facilites Available",
            "charging pile": "Charging Pile Facilites Available",
            "charging point": "Charging Pile Facilites Available",
            "charging port": "Charging Pile Facilites Available",
            "ev charging": "Charging Pile Facilites Available",
            "electric vehicle charging": "Charging Pile Facilites Available",
            "plug-in": "Charging Pile Facilites Available",
            "plug in": "Charging Pile Facilites Available"
        }
    
    def extract_additional_profile(self, user_input):
        """
        Extract additional profile information from user input.
        
        Args:
            user_input (str): The input text from the user
            
        Returns:
            dict: Dictionary containing extracted profile information
        """
        # Initialize profile with empty values
        profile = {
            "family_size": "",
            "price_sensitivy": "",
            "residence": "",
            "parking_conditions": ""
        }
        
        # Extract each profile element
        profile["family_size"] = self._extract_family_size(user_input)
        profile["price_sensitivy"] = self._extract_price_sensitivity(user_input)
        profile["residence"] = self._extract_residence(user_input)
        profile["parking_conditions"] = self._extract_parking_conditions(user_input)
        
        return profile
    
    def _extract_family_size(self, text):
        """
        Extract family size information from text.
        
        Args:
            text (str): The input text
            
        Returns:
            str: Extracted family size or empty string if not found
        """
        # Pattern for direct family size statements
        family_size_patterns = [
            r'family\s*(?:of|with)\s*(\d+)(?:\s*people)?',                  # family of 4, family with 5 people
            r'(\d+)(?:\s*person|\s*people|\s*member)?\s*(?:in\s*(?:my|the))?\s*family', # 4 people in my family, 5 member family
            r'family\s*size\s*(?:is|of)?\s*(\d+)',                          # family size is 3, family size of 4
            r'family\s*members?\s*(?:is|are)?\s*(\d+)',                     # family members are 5
            r'household\s*(?:of|with)\s*(\d+)',                             # household of 4
            r'(\d+)(?:\s*person|\s*people)?\s*household',                   # 4 person household
            r'living\s*with\s*(\d+)\s*(?:other)?\s*(?:people|family\s*members)', # living with 3 other people
            r'there\s*(?:are|is)\s*(\d+)\s*(?:of\s*us|people)\s*in\s*(?:my|the)\s*family', # there are 4 of us in my family
            r'i\s*have\s*(\d+)\s*(?:family\s*members|people\s*in\s*my\s*family)', # I have 3 family members
            r'we\s*are\s*a\s*family\s*of\s*(\d+)',                          # we are a family of 5
            r'i\s*live\s*with\s*my\s*(\d+)\s*(?:family\s*members)',         # I live with my 4 family members
            r'i\s*live\s*with\s*(\d+)\s*(?:other)?\s*(?:people|family\s*members)', # I live with 3 other people
        ]
        
        # Check for direct family size statements
        for pattern in family_size_patterns:
            matches = re.search(pattern, text, re.IGNORECASE)
            if matches:
                family_size = matches.group(1)
                return family_size
        
        # Pattern for family composition statements
        family_composition_patterns = {
            r'(?:i|me)(?:\s*and\s*my)?\s*(?:spouse|husband|wife)': 2,
            r'(?:i|me)(?:\s*and\s*my)?\s*(?:spouse|husband|wife)\s*and\s*(\d+)\s*(?:child|children|kid|kids)': lambda x: 2 + int(x),
            r'(?:i|me)\s*and\s*my\s*(\d+)\s*(?:child|children|kid|kids)': lambda x: 1 + int(x),
            r'(?:i|me)(?:\s*and\s*my)?\s*(?:spouse|husband|wife)\s*and\s*(?:a|one)\s*(?:child|kid)': 3,
            r'(?:i|me)\s*and\s*(?:a|one)\s*(?:child|kid)': 2,
            r'(?:i|me)(?:\s*and\s*my)?\s*(?:spouse|husband|wife)\s*and\s*two\s*(?:children|kids)': 4,
            r'(?:i|me)\s*and\s*two\s*(?:children|kids)': 3,
            r'(?:i|me)(?:\s*and\s*my)?\s*(?:spouse|husband|wife)\s*and\s*three\s*(?:children|kids)': 5,
            r'(?:i|me)\s*and\s*three\s*(?:children|kids)': 4,
            r'single': 1,
            r'(?:i|me)\s*(?:alone|only)': 1,
            r'just\s*(?:me|myself)': 1,
            r'(?:i|me)\s*and\s*my\s*(?:partner|significant\s*other)': 2,
            r'couple': 2,
            r'(?:i|me)\s*and\s*my\s*(?:roommate|housemate)': 2,
            r'(?:i|me)\s*and\s*my\s*(\d+)\s*(?:roommates|housemates)': lambda x: 1 + int(x),
        }
        
        # Check for family composition statements
        for pattern, size_or_func in family_composition_patterns.items():
            matches = re.search(pattern, text, re.IGNORECASE)
            if matches:
                if callable(size_or_func):
                    # If it's a function, call it with the captured group
                    family_size = size_or_func(matches.group(1))
                else:
                    # Otherwise, use the direct value
                    family_size = size_or_func
                return str(family_size)
        
        # Check for mentions of specific family members
        family_members = {
            r'\b(?:husband|wife|spouse|partner)\b': 1,
            r'\b(?:son|daughter|child|kid)\b': 1,
            r'\b(?:sons|daughters|children|kids)\b': 2,  # Assume at least 2 if plural
        }
        
        total_members = 1  # Start with the person themselves
        found_family = False
        
        for pattern, count in family_members.items():
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                found_family = True
                total_members += count * len(matches)
        
        if found_family:
            return str(total_members)
        
        return ""
    
    def _extract_price_sensitivity(self, text):
        """
        Extract price sensitivity information from text, ensuring it matches one of the allowed values.
        
        Args:
            text (str): The input text
            
        Returns:
            str: Extracted price sensitivity or empty string if not found
        """
        allowed_sensitivities = self.user_profile_config["price_sensitivy"]["candidates"]
        text = text.lower()
        
        # Check for direct mentions of price sensitivity terms
        for term, sensitivity in self.price_sensitivity_mapping.items():
            if term in text and sensitivity in allowed_sensitivities:
                return sensitivity
        
        # Check for price range mentions
        budget_patterns = [
            # High price sensitivity patterns (low budget)
            (r'budget\s*(?:is|of)?\s*(?:under|less\s*than|below|not\s*more\s*than)\s*\$?(\d{1,3}(?:,\d{3})*)', "High"),
            (r'(?:can|could)\s*(?:only)?\s*(?:afford|spend)\s*(?:up\s*to)?\s*\$?(\d{1,3}(?:,\d{3})*)', "High"),
            (r'looking\s*(?:to|for)\s*spend\s*(?:less\s*than|under|below|not\s*more\s*than)\s*\$?(\d{1,3}(?:,\d{3})*)', "High"),
            (r'(?:not|don\'t)\s*want\s*to\s*spend\s*(?:more\s*than|over)\s*\$?(\d{1,3}(?:,\d{3})*)', "High"),
            (r'(?:cheap|inexpensive|affordable|economical|budget|low[\s-]cost|low[\s-]price)', "High"),
            (r'tight\s*budget', "High"),
            (r'save\s*money', "High"),
            (r'cost[\s-]effective', "High"),
            
            # Medium price sensitivity patterns (moderate budget)
            (r'budget\s*(?:is|of)?\s*(?:around|about|approximately)\s*\$?(\d{1,3}(?:,\d{3})*)', "Medium"),
            (r'(?:willing|able|planning|looking)\s*to\s*spend\s*(?:around|about|approximately)\s*\$?(\d{1,3}(?:,\d{3})*)', "Medium"),
            (r'mid[\s-]range', "Medium"),
            (r'moderate\s*price', "Medium"),
            (r'reasonable\s*price', "Medium"),
            (r'value\s*for\s*money', "Medium"),
            (r'balance\s*(?:between|of)\s*price\s*and\s*quality', "Medium"),
            
            # Low price sensitivity patterns (high budget)
            (r'budget\s*(?:is|of)?\s*(?:over|more\s*than|above)\s*\$?(\d{1,3}(?:,\d{3})*)', "Low"),
            (r'(?:willing|able|planning|looking)\s*to\s*spend\s*(?:over|more\s*than|above)\s*\$?(\d{1,3}(?:,\d{3})*)', "Low"),
            (r'money\s*is\s*not\s*(?:an\s*issue|a\s*concern|a\s*problem)', "Low"),
            (r'price\s*is\s*not\s*(?:an\s*issue|a\s*concern|a\s*problem)', "Low"),
            (r'(?:high[\s-]end|luxury|premium|top[\s-]tier)', "Low"),
            (r'best\s*regardless\s*of\s*price', "Low"),
            (r'quality\s*over\s*price', "Low"),
        ]
        
        for pattern, sensitivity in budget_patterns:
            if re.search(pattern, text, re.IGNORECASE) and sensitivity in allowed_sensitivities:
                return sensitivity
        
        # Check for numeric budget values to determine sensitivity
        budget_value_patterns = [
            r'budget\s*(?:is|of)?\s*\$?(\d{1,3}(?:,\d{3})*)',
            r'(?:willing|able|planning|looking)\s*to\s*spend\s*\$?(\d{1,3}(?:,\d{3})*)',
            r'(?:spend|spending|cost|price)\s*(?:of)?\s*\$?(\d{1,3}(?:,\d{3})*)',
        ]
        
        for pattern in budget_value_patterns:
            matches = re.search(pattern, text, re.IGNORECASE)
            if matches:
                try:
                    # Remove commas and convert to integer
                    budget = int(matches.group(1).replace(',', ''))
                    
                    # Determine sensitivity based on budget amount
                    # These thresholds can be adjusted based on the market
                    if budget < 20000:
                        return "High" if "High" in allowed_sensitivities else ""
                    elif budget < 50000:
                        return "Medium" if "Medium" in allowed_sensitivities else ""
                    else:
                        return "Low" if "Low" in allowed_sensitivities else ""
                except ValueError:
                    continue
        
        return ""
    
    def _extract_residence(self, text):
        """
        Extract residence information from text.
        
        Args:
            text (str): The input text
            
        Returns:
            str: Extracted residence in "country+province+city" format or empty string if not found
        """
        # Format the text for easier processing
        text = text.replace(", ", ",")
        
        # Common country names to help with identification
        common_countries = [
            "china", "usa", "united states", "america", "canada", "japan", "germany", 
            "france", "uk", "united kingdom", "australia", "india", "russia", "brazil",
            "mexico", "italy", "spain", "south korea", "korea"
        ]
        
        # Major cities for direct identification
        major_cities = [
            "beijing", "shanghai", "guangzhou", "shenzhen", "chengdu", "hangzhou", 
            "tianjin", "wuhan", "chongqing", "tokyo", "osaka", "london", "paris", 
            "berlin", "rome", "madrid", "amsterdam", "new york", "los angeles", 
            "chicago", "toronto", "sydney", "melbourne", "dubai", "mumbai", "delhi",
            "boston", "miami", "seattle", "vancouver", "montreal", "hong kong"
        ]
        
        # Try exact patterns with boundary conditions for three-part addresses
        exact_address_patterns = [
            r'live\s+in\s+([A-Za-z\s]+),\s*([A-Za-z\s]+),\s*([A-Za-z\s]+)[.\s]',
            r'living\s+in\s+([A-Za-z\s]+),\s*([A-Za-z\s]+),\s*([A-Za-z\s]+)[.\s]',
            r'based\s+in\s+([A-Za-z\s]+),\s*([A-Za-z\s]+),\s*([A-Za-z\s]+)[.\s]',
            r'from\s+([A-Za-z\s]+),\s*([A-Za-z\s]+),\s*([A-Za-z\s]+)[.\s]',
            r'in\s+([A-Za-z\s]+),\s*([A-Za-z\s]+),\s*([A-Za-z\s]+)[.\s]',
            r'(?:home|residence|address)\s+(?:is|at|in)\s+([A-Za-z\s]+),\s*([A-Za-z\s]+),\s*([A-Za-z\s]+)[.\s]'
        ]
        
        for pattern in exact_address_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                city, province, country = match.groups()
                return f"{country.strip()}+{province.strip()}+{city.strip()}"
                
        # Try exact patterns with boundary conditions for two-part addresses
        two_part_patterns = [
            r'live\s+in\s+([A-Za-z\s]+),\s*([A-Za-z\s]+)[.\s]',
            r'living\s+in\s+([A-Za-z\s]+),\s*([A-Za-z\s]+)[.\s]',
            r'based\s+in\s+([A-Za-z\s]+),\s*([A-Za-z\s]+)[.\s]',
            r'from\s+([A-Za-z\s]+),\s*([A-Za-z\s]+)[.\s]',
            r'in\s+([A-Za-z\s]+),\s*([A-Za-z\s]+)[.\s]',
            r'(?:home|residence|address)\s+(?:is|at|in)\s+([A-Za-z\s]+),\s*([A-Za-z\s]+)[.\s]',
            r'moved\s+to\s+([A-Za-z\s]+),\s*([A-Za-z\s]+)[.\s]'
        ]
        
        for pattern in two_part_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                part1, part2 = match.groups()
                part1 = part1.strip()
                part2 = part2.strip()
                
                # Check if part2 is a country
                if part2.lower() in common_countries:
                    return f"{part2}++{part1}"  # country++city
                # Check if part1 is a country
                elif part1.lower() in common_countries:
                    return f"{part1}++{part2}"  # country++city
                else:
                    # Assume part2 is a state/province and part1 is a city
                    return f"+{part2}+{part1}"  # +province+city
                    
        # Try patterns for single location with strong location indicators
        single_location_patterns = [
            r'live\s+in\s+([A-Za-z]+)(?:[.\s]|$)',
            r'living\s+in\s+([A-Za-z]+)(?:[.\s]|$)',
            r'based\s+in\s+([A-Za-z]+)(?:[.\s]|$)',
            r'from\s+([A-Za-z]+)(?:[.\s]|$)',
            r'in\s+([A-Za-z]+)(?:\s+and|[.\s]|$)',
            r'(?:home|residence|address)\s+(?:is|at|in)\s+([A-Za-z]+)(?:[.\s]|$)',
            r'moved\s+to\s+([A-Za-z]+)(?:[.\s]|$)'
        ]
        
        for pattern in single_location_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                location = match.group(1).strip()
                
                # Check if it's a country or city
                if location.lower() in common_countries:
                    return f"{location.title()}++"
                elif location.lower() in major_cities:
                    return f"++{location.title()}"
                
        # Last resort: Check for any major cities mentioned in the text
        for city in major_cities:
            if re.search(r'\b' + city + r'\b', text.lower()):
                return f"++{city.title()}"
                
        # And finally check for any countries mentioned
        for country in common_countries:
            if re.search(r'\b' + country + r'\b', text.lower()):
                return f"{country.title()}++"
                
        return ""
    
    def _extract_parking_conditions(self, text):
        """
        Extract parking conditions from text, ensuring it matches one of the allowed values.
        
        Args:
            text (str): The input text
            
        Returns:
            str: Extracted parking condition or empty string if not found
        """
        allowed_conditions = self.user_profile_config["parking_conditions"]["candidates"]
        text = text.lower()
        
        # First check for "no parking" patterns to avoid false matches
        no_parking_patterns = [
            r'no\s*parking\s*space',
            r'don\'t\s*have\s*(?:a|any)\s*parking',
            r'without\s*(?:a|any)\s*parking',
            r'lack\s*of\s*parking',
        ]
        
        for pattern in no_parking_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return ""  # No parking condition matches
        
        # Check for direct mentions of parking condition terms
        for term, condition in self.parking_conditions_mapping.items():
            if term in text and condition in allowed_conditions:
                return condition
        
        # Check for parking-related phrases
        parking_patterns = [
            # Allocated Parking Space patterns
            (r'(?:i|we)\s*have\s*(?:my|our)\s*own\s*parking', "Allocated Parking Space"),
            (r'(?:i|we)\s*have\s*(?:a|an)\s*(?:allocated|assigned|dedicated|reserved|private)\s*parking', "Allocated Parking Space"),
            (r'(?:i|we)\s*have\s*(?:a|an)\s*garage', "Allocated Parking Space"),
            (r'(?:i|we)\s*have\s*(?:a|an)\s*driveway', "Allocated Parking Space"),
            (r'(?:i|we)\s*have\s*(?:a|an)\s*carport', "Allocated Parking Space"),
            (r'(?:i|we)\s*have\s*(?:a|an)\s*parking\s*(?:space|spot)', "Allocated Parking Space"),
            (r'(?:i|we)\s*own\s*(?:a|an)\s*parking\s*(?:space|spot)', "Allocated Parking Space"),
            (r'(?:i|we)\s*rent\s*(?:a|an)\s*parking\s*(?:space|spot)', "Allocated Parking Space"),
            
            # Temporary Parking Allowed patterns
            (r'(?:i|we)\s*(?:can|could)\s*park\s*(?:on|in)\s*the\s*street', "Temporary Parking Alllowed"),
            (r'(?:i|we)\s*(?:can|could)\s*use\s*(?:public|street|temporary|shared)\s*parking', "Temporary Parking Alllowed"),
            (r'(?:i|we)\s*have\s*(?:access\s*to)?\s*(?:a|an)\s*(?:public|shared)\s*parking\s*(?:lot|area|garage)', "Temporary Parking Alllowed"),
            (r'(?:i|we)\s*(?:can|could)\s*use\s*(?:a|an)\s*(?:parking\s*lot|parking\s*garage)', "Temporary Parking Alllowed"),
            (r'(?:i|we)\s*(?:can|could)\s*park\s*(?:for|with)\s*(?:a|an)\s*(?:limited|short)\s*time', "Temporary Parking Alllowed"),
            (r'(?:metered|paid)\s*parking\s*(?:is|are)\s*available', "Temporary Parking Alllowed"),
            (r'(?:only|just)\s*(?:street|public)\s*parking', "Temporary Parking Alllowed"),
            
            # Charging Pile Facilities Available patterns
            (r'(?:i|we)\s*have\s*(?:access\s*to)?\s*(?:a|an)\s*(?:charging\s*(?:station|pile|point|port|facility))', "Charging Pile Facilites Available"),
            (r'(?:i|we)\s*have\s*(?:a|an)\s*(?:ev|electric\s*vehicle)\s*charger', "Charging Pile Facilites Available"),
            (r'(?:i|we)\s*(?:can|could)\s*charge\s*(?:an|the|my|our)?\s*(?:ev|electric\s*vehicle|car)', "Charging Pile Facilites Available"),
            (r'(?:charging\s*(?:station|pile|point|port|facility))\s*(?:is|are)\s*available', "Charging Pile Facilites Available"),
            (r'(?:ev|electric\s*vehicle)\s*charging\s*(?:is|are)\s*available', "Charging Pile Facilites Available"),
            (r'charging\s*facilities', "Charging Pile Facilites Available"),
        ]
        
        for pattern, condition in parking_patterns:
            if re.search(pattern, text, re.IGNORECASE) and condition in allowed_conditions:
                return condition
        
        return ""
    
    def update_profile(self, current_profile, user_input):
        """
        Update an existing profile with new information extracted from user input.
        
        Args:
            current_profile (dict): The current user profile
            user_input (str): New user input to extract information from
            
        Returns:
            dict: Updated profile
        """
        new_info = self.extract_additional_profile(user_input)
        updated_profile = current_profile.copy()
        
        # Update each field if new information is available
        for key, value in new_info.items():
            if value:  # Only update if we found a value
                updated_profile[key] = value
        
        return updated_profile


# Example usage
if __name__ == "__main__":
    extractor = AdditionalProfileExtractor()
    
    # Test with various additional profile information expressions
    test_texts = [
        "I live with my wife and two children, so we're a family of 4.",
        "My budget is around $30,000 for a new car.",
        "I'm very price sensitive and looking for something under $20,000.",
        "Price is not an issue, I want the best quality car.",
        "I live in Shanghai, China and have my own garage for parking.",
        "We're based in New York City, NY, USA with street parking only.",
        "I have a charging station at home for electric vehicles.",
        "I'm a single person living in Beijing, China.",
        "We are a family of 5 with a moderate budget for a new car.",
        "I live in Toronto, Canada and have access to temporary parking only."
    ]
    
    # Additional car-related test cases with diverse conversational styles
    car_related_tests = [
        "I'm Mr. Zhang from Beijing, my family has three members, and I'm looking for an SUV suitable for family use with a budget of around $40,000.",
        "As a father of two children, I need a car that's both safe and fuel-efficient, but my budget is limited to at most $25,000. I have my own garage at home.",
        "I live in Guangzhou and want to buy a luxury car, price is not an issue, preferably imported. Our community has charging piles available.",
        "My wife and I just moved to Shanghai, we need a small city car for commuting. We can only park on the street.",
        "As a single person, I want to find a compact car suitable for city driving in Chengdu, with a medium budget of around $30,000.",
        "We are a family of six and need a large MPV. We live in the Nanshan district of Shenzhen and have our own parking space.",
        "I'm a young professional living in Hangzhou, looking for a stylish but not too expensive car. There's a public parking lot below my apartment building.",
        "Our family of four lives in Tianjin and wants to buy an economical family sedan with a budget not exceeding $20,000. We have our own garage.",
        "I'm a corporate executive who needs a luxury business car, price is not a major consideration. I have a designated parking space in central Wuhan.",
        "My husband and I live in Chongqing, and we want to buy a hybrid car with a moderate price. Our community has charging facilities for electric vehicles.",
        "I'm looking for an SUV for my family of 6 living in Chicago. We care a lot about getting good value for our money.",
        "I need a luxury car that reflects my status. Budget is not a concern, and I have a private garage in my Beverly Hills home.",
        "As a single mom with two kids, I need an affordable and reliable car. We live in an apartment in Boston with street parking only.",
        "I'm interested in an electric vehicle since we have charging facilities in our London flat. My partner and I are willing to pay more for environmental benefits.",
        "Our family of 3 is moving to Sydney and needs a mid-range car that's good for city driving. We'll have a dedicated parking spot.",
        "I'm a college student in Toronto looking for my first car. It must be very affordable, and I only have access to public parking lots.",
        "We're a retired couple living in Miami looking for a comfortable sedan. We're moderately price sensitive and have our own garage.",
        "I'm a businessman from Dubai and I'm looking for a premium vehicle. Cost is not an issue, and I have multiple parking spaces available.",
        "As a family of 4 with a moderate budget, we need a practical car for our life in Berlin. We only have street parking available.",
        "I live alone in a small apartment in Tokyo with no parking space. I need a very compact and affordable car that I can park in public lots."
    ]
    
    # Test the basic test cases
    print("TESTING BASIC CASES:")
    print("====================")
    for text in test_texts:
        profile = extractor.extract_additional_profile(text)
        print(f"Input: {text}")
        print(f"Extracted profile:")
        print(f"  Family size: {profile['family_size'] or 'Not found'}")
        print(f"  Price sensitivity: {profile['price_sensitivy'] or 'Not found'}")
        print(f"  Residence: {profile['residence'] or 'Not found'}")
        print(f"  Parking conditions: {profile['parking_conditions'] or 'Not found'}")
        print()
    
    # Test the car-related test cases
    print("\nTESTING CAR-RELATED CASES:")
    print("=========================")
    for text in car_related_tests:
        profile = extractor.extract_additional_profile(text)
        print(f"Input: {text}")
        print(f"Extracted profile:")
        print(f"  Family size: {profile['family_size'] or 'Not found'}")
        print(f"  Price sensitivity: {profile['price_sensitivy'] or 'Not found'}")
        print(f"  Residence: {profile['residence'] or 'Not found'}")
        print(f"  Parking conditions: {profile['parking_conditions'] or 'Not found'}")
        print()
    
    # Test profile updating
    print("\nTESTING PROFILE UPDATE FUNCTIONALITY:")
    print("===================================")
    current_profile = {
        "family_size": "2",
        "price_sensitivy": "High",
        "residence": "",
        "parking_conditions": ""
    }
    
    update_text = "I live in Los Angeles, California, USA. I have a dedicated parking space."
    updated_profile = extractor.update_profile(current_profile, update_text)
    
    print(f"Initial profile: {current_profile}")
    print(f"Update text: {update_text}")
    print(f"Updated profile: {updated_profile}") 