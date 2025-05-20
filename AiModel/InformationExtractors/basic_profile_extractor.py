import json
import re
import os
from pathlib import Path

class BasicProfileExtractor:
    """
    A class for extracting basic user profile information from conversations,
    including age, user title, name, and target driver.
    """
    
    def __init__(self):
        """
        Initialize the BasicProfileExtractor with user profile configuration.
        """
        # Load user profile configuration from JSON file
        base_dir = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        user_profile_path = os.path.join(base_dir, "Config", "UserProfile.json")
        
        with open(user_profile_path, 'r', encoding='utf-8') as f:
            self.user_profile_config = json.load(f)["BasicInformation"]
        
        # Define mappings for title variations
        self.title_variations = {
            "mr": "Mr.",
            "mr.": "Mr.",
            "mrs": "Mrs.",
            "mrs.": "Mrs.",
            "miss": "Miss.",
            "miss.": "Miss.",
            "ms": "Ms.",
            "ms.": "Ms."
        }
        
        # Define relationship mapping for target driver
        self.relationship_mapping = {
            # Direct matches
            "self": "Self",
            "wife": "Wife",
            "husband": "Husband", 
            "parents": "Parents",
            "father": "Father",
            "mother": "Mother",
            "son": "Son",
            "daughter": "Daughter",
            "grandparents": "Grandparents",
            "grandchildren": "Grandchildren",
            "brother": "Brother",
            "sister": "Sister",
            "uncle": "Uncle",
            "aunt": "Aunt",
            "cousin": "Cousin",
            "friend": "Friend",
            "other": "Other",
            
            # Common variations
            "myself": "Self",
            "me": "Self",
            "i": "Self",
            "spouse": "Husband",  # Will be refined in extraction logic
            "parent": "Parents",
            "mom": "Mother",
            "dad": "Father",
            "child": "Son",       # Will be refined in extraction logic
            "children": "Son",    # Will be refined in extraction logic
            "kid": "Son",         # Will be refined in extraction logic
            "kids": "Son",        # Will be refined in extraction logic
            "boy": "Son",
            "girl": "Daughter",
            "grandparent": "Grandparents",
            "grandmother": "Grandparents",
            "grandfather": "Grandparents",
            "grandchild": "Grandchildren",
            "grandson": "Grandchildren",
            "granddaughter": "Grandchildren",
            "sibling": "Brother", # Will be refined in extraction logic
            "relative": "Other",
            "buddy": "Friend",
            "pal": "Friend",
            "mate": "Friend"
        }
    
    def extract_basic_profile(self, user_input):
        """
        Extract basic profile information from user input.
        
        Args:
            user_input (str): The input text from the user
            
        Returns:
            dict: Dictionary containing extracted profile information
        """
        # Initialize profile with empty values
        profile = {
            "age": "",
            "user_title": "",
            "name": "",
            "target_driver": ""
        }
        
        # Extract each profile element
        profile["age"] = self._extract_age(user_input)
        profile["user_title"] = self._extract_title(user_input)
        profile["name"] = self._extract_name(user_input)
        profile["target_driver"] = self._extract_target_driver(user_input)
        
        return profile
    
    def _extract_age(self, text):
        """
        Extract age information from text.
        
        Args:
            text (str): The input text
            
        Returns:
            str: Extracted age range or empty string if not found
        """
        # Pattern for age ranges like "20-35", "20 to 35", "between 20 and 35"
        age_range_patterns = [
            r'\b(\d{1,2})\s*-\s*(\d{1,2})\b',                     # 20-35
            r'\b(\d{1,2})\s*to\s*(\d{1,2})\b',                    # 20 to 35
            r'between\s*(\d{1,2})\s*and\s*(\d{1,2})\b'            # between 20 and 35
        ]
        
        # Pattern for direct age statements
        direct_age_patterns = [
            r'\bi\'?m\s*(\d{1,2})\s*(?:years\s*old)?\b',          # I'm 25 (years old)
            r'\bmy\s*age\s*is\s*(\d{1,2})\b',                     # My age is 25
            r'\b(\d{1,2})\s*years?\s*old\b',                      # 25 years old
            r'\bage\D*(\d{1,2})\b'                                # age: 25, age - 25
        ]
        
        # Check for age ranges first
        for pattern in age_range_patterns:
            matches = re.search(pattern, text, re.IGNORECASE)
            if matches:
                low_age = int(matches.group(1))
                high_age = int(matches.group(2))
                # Ensure low_age <= high_age
                if low_age > high_age:
                    low_age, high_age = high_age, low_age
                return f"{low_age}-{high_age}"
        
        # Check for direct age statements
        for pattern in direct_age_patterns:
            matches = re.search(pattern, text, re.IGNORECASE)
            if matches:
                age = int(matches.group(1))
                # Return a small range around the exact age
                return f"{max(age-5, 18)}-{min(age+5, 100)}"
        
        return ""
    
    def _extract_title(self, text):
        """
        Extract user title from text, ensuring it matches one of the allowed values.
        
        Args:
            text (str): The input text
            
        Returns:
            str: Extracted title or empty string if not found
        """
        allowed_titles = self.user_profile_config["user_title"]["candidates"]
        
        # Create pattern matching variations of titles
        title_pattern = r'\b(mr\.?|mrs\.?|miss\.?|ms\.?)\b'
        
        matches = re.search(title_pattern, text, re.IGNORECASE)
        if matches:
            matched_title = matches.group(1).lower()
            if matched_title in self.title_variations:
                standardized_title = self.title_variations[matched_title]
                if standardized_title in allowed_titles:
                    return standardized_title
        
        # Check for gender indicators to infer title
        gender_patterns = {
            "Mr.": [r'\b(male|man|gentleman|guy|boy|husband|father)\b', r'\bhe\b'],
            "Mrs.": [r'\b(married\s*woman|wife|mother)\b'],
            "Ms.": [r'\b(female|woman|lady)\b', r'\bshe\b'],
        }
        
        for title, patterns in gender_patterns.items():
            for pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    return title
        
        return ""
    
    def _extract_name(self, text):
        """
        Extract user name from text.
        
        Args:
            text (str): The input text
            
        Returns:
            str: Extracted name or empty string if not found
        """
        # Common verbs with -ing form to avoid false positives
        ing_verbs = [
            'looking', 'searching', 'calling', 'checking', 'trying', 'going', 
            'wondering', 'thinking', 'considering', 'inquiring', 'asking',
            'interested', 'planning', 'hoping', 'needing', 'working', 'driving'
        ]
        
        # Avoid matching "I'm + verb-ing" patterns
        for verb in ing_verbs:
            text = re.sub(rf"i\'?m\s+{verb}\b", "i am " + verb, text, flags=re.IGNORECASE)
        
        # Look for name patterns with title + surname
        title_surname_pattern = r'(?:call\s+me|i\s+am|i\'m)\s+((?:mr|mrs|miss|ms|dr)\.?\s+(\w+))'
        title_match = re.search(title_surname_pattern, text, re.IGNORECASE)
        if title_match:
            surname = title_match.group(2).strip()
            if len(surname) > 1:  # Ensure it's not just a single letter
                return surname[0].upper() + surname[1:]
        
        # Look for name patterns
        name_patterns = [
            r'my\s*name\s*is\s+(\w+)',                             # My name is John
            r'i\'?m\s+([A-Z][a-z]+)(?!\s+\w+ing\b)',               # I'm John (avoiding I'm verb-ing)
            r'call\s*me\s+(\w+)',                                  # Call me John
            r'you\s+can\s+call\s+me\s+(?:mr\.?|mrs\.?|miss\.?|ms\.?)?\s*(\w+)',  # You can call me (Mr.) John
            r'this\s*is\s+(\w+)(?:\s*speaking)?',                  # This is John (speaking)
            r'name\'?s\s+(\w+)',                                   # Name's John
            r'\b([A-Z][a-z]+)\s+speaking',                         # John speaking
            r'\bhi,?\s+(?:this\s+is\s+)?([A-Z][a-z]+)',            # Hi, (this is) John
            r'\bhello,?\s+(?:this\s+is\s+)?([A-Z][a-z]+)',         # Hello, (this is) John
            r'(?:good|hello|hi)[\s,]+([A-Z][a-z]+)[\s,]+(?:here|speaking|calling)', # Hello, John here/speaking/calling
            r'(?:^|\.\s+|\n)([A-Z][a-z]+)[\s,]+(?:here|speaking|calling)', # John here/speaking/calling at start of sentence
            r'you(?:\s+can)?\s+address\s+me\s+as\s+(\w+)',         # You can address me as John
            r'(?:^|\.\s+|\n)(?:this\s+is\s+)?([A-Z][a-z]+)(?:\s+from)?' # This is John (from...)
        ]
        
        # Common words that should not be extracted as names
        common_words = [
            'mr', 'mrs', 'miss', 'ms', 'sir', 'madam', 'hello', 'hi', 'hey', 'good',
            'am', 'is', 'are', 'was', 'were', 'be', 'being', 'been', 
            'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
            'can', 'could', 'should', 'may', 'might', 'must', 'shall',
            'for', 'from', 'with', 'about', 'into', 'until', 'while',
            'a', 'an', 'the', 'this', 'that', 'these', 'those', 'in', 'on', 'at',
            'my', 'your', 'his', 'her', 'our', 'their', 'its', 'mine', 'yours',
            'to', 'of', 'by', 'as', 'if', 'so', 'or', 'and', 'but', 'not',
            'yes', 'no', 'please', 'thank', 'thanks', 'sorry', 'excuse'
        ]
        
        for pattern in name_patterns:
            matches = re.search(pattern, text, re.IGNORECASE)
            if matches:
                name = matches.group(1).strip()
                # Skip common words that might be matched
                if name.lower() in common_words:
                    continue
                # Ensure name starts with capital letter
                return name[0].upper() + name[1:] if name else ""
        
        return ""
    
    def _extract_target_driver(self, text):
        """
        Extract target driver from text, ensuring it matches one of the allowed values.
        
        Args:
            text (str): The input text
            
        Returns:
            str: Extracted target driver or empty string if not found
        """
        allowed_drivers = self.user_profile_config["target_driver"]["candidates"]
        text = text.lower()
        
        # Check for common phrases indicating the driver
        driver_indicators = {
            "Self": [r'\b(i|myself|me)\s*(?:will|am|going to)?\s*(?:be\s*)?(?:the\s*)?(?:one\s*)?(?:to\s*)?drive', 
                    r'(?:drive|driving)\s*(?:myself|me|by myself)'],
            "Wife": [r'(?:my\s*)?wife\s*(?:will|is)?\s*(?:be\s*)?(?:driving|drive)'],
            "Husband": [r'(?:my\s*)?husband\s*(?:will|is)?\s*(?:be\s*)?(?:driving|drive)'],
            "Parents": [r'(?:my\s*)?parents\s*(?:will|are)?\s*(?:be\s*)?(?:driving|drive)'],
            "Father": [r'(?:my\s*)?(?:father|dad)\s*(?:will|is)?\s*(?:be\s*)?(?:driving|drive)'],
            "Mother": [r'(?:my\s*)?(?:mother|mom)\s*(?:will|is)?\s*(?:be\s*)?(?:driving|drive)'],
            "Son": [r'(?:my\s*)?son\s*(?:will|is)?\s*(?:be\s*)?(?:driving|drive)'],
            "Daughter": [r'(?:my\s*)?daughter\s*(?:will|is)?\s*(?:be\s*)?(?:driving|drive)'],
            "Friend": [r'(?:my\s*)?friend\s*(?:will|is)?\s*(?:be\s*)?(?:driving|drive)']
        }
        
        # Check driver indicator patterns
        for driver, patterns in driver_indicators.items():
            for pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    return driver
        
        # Check for direct mentions of relationships
        words = text.lower().split()
        for word in words:
            word = word.strip(".,;:!?")
            if word in self.relationship_mapping:
                candidate = self.relationship_mapping[word]
                if candidate in allowed_drivers:
                    # Handle gender-specific refinements
                    if candidate == "Husband" and "wife" in text:
                        return "Wife"
                    if (candidate == "Son" or candidate == "Daughter") and "daughter" in text:
                        return "Daughter"
                    if (candidate == "Son" or candidate == "Daughter") and "son" in text:
                        return "Son"
                    if (candidate == "Brother" or candidate == "Sister") and "sister" in text:
                        return "Sister"
                    return candidate
        
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
        new_info = self.extract_basic_profile(user_input)
        updated_profile = current_profile.copy()
        
        # Update each field if new information is available
        for key, value in new_info.items():
            if value:  # Only update if we found a value
                updated_profile[key] = value
        
        return updated_profile 


# Example usage
if __name__ == "__main__":
    extractor = BasicProfileExtractor()
    
    # Test with various profile information expressions
    test_texts = [
        "Hi, my name is John and I'm 28 years old. I'll be driving the car myself.",
        "Mrs. Smith here. I'm looking for a car for my husband to drive.",
        "I'm in the 30-45 age range, and my son will be driving this car.",
        "Hello, I'm looking for a car. My daughter will be the one driving it.",
        "My age is 50 and you can call me Mr. Johnson.",
        "I want to buy a car for my wife who is between 25 and 35 years old.",
        "Hi, this is Sarah speaking. I'm looking for a family car that my parents will drive.",
        "My dad is looking for a new vehicle. He's 65 years old.",
        "I'm a 42 year old woman looking for my first car.",
        "Hello Ms. Davis here, I'll be driving myself to work."
    ]
    
    for text in test_texts:
        profile = extractor.extract_basic_profile(text)
        print(f"Input: {text}")
        print(f"Extracted profile:")
        print(f"  Age: {profile['age'] or 'Not found'}")
        print(f"  Title: {profile['user_title'] or 'Not found'}")
        print(f"  Name: {profile['name'] or 'Not found'}")
        print(f"  Target driver: {profile['target_driver'] or 'Not found'}")
        print()
    
    # Test profile updating
    print("Testing profile update functionality:")
    current_profile = {
        "age": "30-40",
        "user_title": "Mr.",
        "name": "",
        "target_driver": ""
    }
    
    update_text = "My name is David and my wife will be driving this car."
    updated_profile = extractor.update_profile(current_profile, update_text)
    
    print(f"Initial profile: {current_profile}")
    print(f"Update text: {update_text}")
    print(f"Updated profile: {updated_profile}") 