"""
Natural language processing utilities for AutoVend.
"""
import logging
import re
from typing import Dict, Any, List

# Configure logging
logger = logging.getLogger(__name__)

def extract_profile_info(text: str) -> Dict[str, Any]:
    """
    Extract user profile information from text.
    
    Args:
        text: Text to extract information from
        
    Returns:
        Dictionary of extracted profile information
    """
    # This is a simple placeholder implementation
    # In a real system, this would use more sophisticated NLP techniques
    
    profile_info = {}
    
    # Extract name
    name_patterns = [
        r"my name is (\w+)",
        r"I am (\w+)",
        r"call me (\w+)"
    ]
    
    for pattern in name_patterns:
        matches = re.findall(pattern, text.lower())
        if matches:
            profile_info["name"] = matches[0].capitalize()
            break
    
    # Extract title
    title_patterns = {
        r"\b(mr\.?)\b": "Mr.",
        r"\b(mrs\.?)\b": "Mrs.",
        r"\b(ms\.?)\b": "Ms.",
        r"\b(miss)\b": "Miss"
    }
    
    for pattern, title in title_patterns.items():
        if re.search(pattern, text.lower()):
            profile_info["user_title"] = title
            break
    
    # Extract age
    age_patterns = [
        r"(\d+)\s*years?\s*old",
        r"I am (\d+)",
        r"age.*?(\d+)"
    ]
    
    for pattern in age_patterns:
        matches = re.findall(pattern, text.lower())
        if matches:
            try:
                age = int(matches[0])
                profile_info["age"] = str(age)
            except ValueError:
                pass
            break
    
    # Extract target driver
    driver_patterns = {
        r"for myself": "Self",
        r"I will (?:be|do) the driving": "Self",
        r"for my wife": "Wife",
        r"for my husband": "Husband",
        r"for my family": "Family",
        r"for my parents": "Parents",
        r"for my children": "Children"
    }
    
    for pattern, driver in driver_patterns.items():
        if re.search(pattern, text.lower()):
            profile_info["target_driver"] = driver
            break
    
    # Extract family size
    family_patterns = [
        r"family of (\d+)",
        r"(\d+) (?:people|person) in (?:my|the) family",
        r"family (?:with|has) (\d+) (?:people|person|members)"
    ]
    
    for pattern in family_patterns:
        matches = re.findall(pattern, text.lower())
        if matches:
            try:
                family_size = int(matches[0])
                profile_info["family_size"] = family_size
            except ValueError:
                pass
            break
    
    # Extract residence
    residence_patterns = [
        r"live in ([\w\s]+)",
        r"from ([\w\s]+)",
        r"(?:live|stay) (?:at|in) ([\w\s]+)"
    ]
    
    for pattern in residence_patterns:
        matches = re.findall(pattern, text.lower())
        if matches:
            profile_info["residence"] = matches[0].capitalize()
            break
    
    # Extract expertise level (rough estimate)
    expertise_keywords = {
        "beginner": ["beginner", "know nothing", "first time", "no experience"],
        "intermediate": ["some knowledge", "basic understanding", "some experience"],
        "expert": ["expert", "enthusiast", "knowledgeable", "car guy", "car person"]
    }
    
    text_lower = text.lower()
    for level, keywords in expertise_keywords.items():
        for keyword in keywords:
            if keyword in text_lower:
                if level == "beginner":
                    profile_info["expertise"] = 2
                elif level == "intermediate":
                    profile_info["expertise"] = 5
                elif level == "expert":
                    profile_info["expertise"] = 8
                break
    
    logger.debug(f"Extracted profile info: {profile_info}")
    return profile_info

def extract_car_needs(text: str) -> Dict[str, Any]:
    """
    Extract car needs information from text.
    
    Args:
        text: Text to extract information from
        
    Returns:
        Dictionary of extracted car needs information
    """
    # This is a simple placeholder implementation
    # In a real system, this would use more sophisticated NLP techniques
    
    car_needs = {}
    
    # Extract budget
    if "budget" in text.lower():
        parts = text.lower().split("budget")
        if len(parts) > 1:
            budget_part = parts[1].strip()
            # Try to find a number
            for word in budget_part.split():
                if word.isdigit():
                    car_needs["budget"] = word
                    break
    
    # Extract vehicle category
    categories = ["sedan", "suv", "truck", "van", "hatchback", "coupe", "convertible"]
    for category in categories:
        if category in text.lower():
            if "vehicle_category_bottom" not in car_needs:
                car_needs["vehicle_category_bottom"] = []
            car_needs["vehicle_category_bottom"].append(category.capitalize())
    
    # Extract brands
    brands = ["toyota", "honda", "ford", "chevrolet", "bmw", "audi", "mercedes", "tesla", "hyundai", "kia"]
    for brand in brands:
        if brand in text.lower():
            if "brand" not in car_needs:
                car_needs["brand"] = []
            car_needs["brand"].append(brand.capitalize())
    
    # Extract colors
    colors = ["black", "white", "red", "blue", "green", "silver", "gray", "yellow", "orange"]
    for color in colors:
        if color in text.lower():
            if "color" not in car_needs:
                car_needs["color"] = []
            car_needs["color"].append(color.capitalize())
    
    # Extract engine types
    engine_types = ["gasoline", "diesel", "hybrid", "electric", "petrol"]
    for engine_type in engine_types:
        if engine_type in text.lower():
            if "engine_type" not in car_needs:
                car_needs["engine_type"] = []
            car_needs["engine_type"].append(engine_type.capitalize())
    
    # Extract transmission
    transmissions = ["automatic", "manual", "cvt"]
    for transmission in transmissions:
        if transmission in text.lower():
            if "transmission" not in car_needs:
                car_needs["transmission"] = []
            car_needs["transmission"].append(transmission.capitalize())
    
    # Extract seats
    if "seats" in text.lower():
        parts = text.lower().split("seats")
        if len(parts) > 0:
            seats_words = parts[0].strip().split()
            if seats_words:
                try:
                    seats = int(seats_words[-1])
                    car_needs["seats"] = str(seats)
                except ValueError:
                    pass
    
    # Extract sunroof
    if "sunroof" in text.lower():
        car_needs["sunroof"] = "Yes"
    
    # Extract usage
    usage_keywords = {
        "commuting": ["commute", "work", "daily", "city driving"],
        "family": ["family", "kids", "children", "school"],
        "adventure": ["adventure", "outdoor", "camping", "off-road", "off road"],
        "luxury": ["luxury", "comfort", "premium"]
    }
    
    for usage, keywords in usage_keywords.items():
        for keyword in keywords:
            if keyword in text.lower():
                if "usage" not in car_needs:
                    car_needs["usage"] = []
                car_needs["usage"].append(usage.capitalize())
                break
    
    logger.debug(f"Extracted car needs: {car_needs}")
    return car_needs

def extract_implicit_needs(profile_data: Dict[str, Any], explicit_needs: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract implicit needs based on user profile and explicit needs.
    
    Args:
        profile_data: User profile data
        explicit_needs: Explicitly stated needs
        
    Returns:
        Dictionary of implicit needs
    """
    # This is a simple placeholder implementation
    # In a real system, this would use more sophisticated inference techniques
    
    implicit_needs = {}
    
    # Infer size based on family size
    if "family_size" in profile_data and profile_data["family_size"]:
        family_size = profile_data["family_size"]
        if family_size >= 4 and "size" not in explicit_needs:
            implicit_needs["size"] = "Large, Implicit"
    
    # Infer safety features for families
    if "target_driver" in profile_data and profile_data["target_driver"] in ["Family", "Children"]:
        if "safety_features" not in explicit_needs:
            implicit_needs["safety_features"] = ["Advanced Safety Package, Implicit"]
    
    # Infer fuel efficiency for commuters
    if "usage" in explicit_needs:
        if isinstance(explicit_needs["usage"], list):
            usages = explicit_needs["usage"]
        else:
            usages = [explicit_needs["usage"]]
            
        for usage in usages:
            if usage.lower() == "commuting" and "fuel_efficiency" not in explicit_needs:
                implicit_needs["fuel_efficiency"] = "High, Implicit"
    
    # Infer luxury features based on price
    if "budget" in explicit_needs:
        try:
            budget = float(explicit_needs["budget"])
            if budget > 50000 and "style" not in explicit_needs:
                implicit_needs["style"] = ["Luxury, Implicit"]
        except (ValueError, TypeError):
            pass
    
    logger.debug(f"Extracted implicit needs: {implicit_needs}")
    return implicit_needs 