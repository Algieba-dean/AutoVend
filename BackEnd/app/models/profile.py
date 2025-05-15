import json
from datetime import datetime
from typing import List, Dict, Any, Optional

class UserProfile:
    """User profile model for AutoVend application"""
    
    def __init__(self, phone_number: str, age: str = "", user_title: str = "", name: str = "", 
                 target_driver: str = "", expertise: str = "", additional_information: Optional[Dict[str, str]] = None,
                 connection_information: Optional[Dict[str, str]] = None):
        """Initialize a new user profile"""
        self.phone_number = phone_number
        self.age = age
        self.user_title = user_title
        self.name = name
        self.target_driver = target_driver
        self.expertise = expertise
        self.additional_information = additional_information or {
            "family_size": "",
            "price_sensitivity": "",
            "residence": "",
            "parking_conditions": ""
        }
        self.connection_information = connection_information or {
            "connection_phone_number": "",
            "connection_id_relationship": ""
        }
        self.updated_at = datetime.utcnow().isoformat()
        
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UserProfile':
        """Create a UserProfile from a dictionary"""
        return cls(
            phone_number=data.get('phone_number', ''),
            age=data.get('age', ''),
            user_title=data.get('user_title', ''),
            name=data.get('name', ''),
            target_driver=data.get('target_driver', ''),
            expertise=data.get('expertise', ''),
            additional_information=data.get('additional_information', {}),
            connection_information=data.get('connection_information', {})
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the profile to a dictionary"""
        return {
            'phone_number': self.phone_number,
            'age': self.age,
            'user_title': self.user_title,
            'name': self.name,
            'target_driver': self.target_driver,
            'expertise': self.expertise,
            'additional_information': self.additional_information,
            'connection_information': self.connection_information,
            'updated_at': self.updated_at
        }
    
    def validate(self) -> List[str]:
        """Validate the profile data
        
        Returns:
            List[str]: List of validation error messages
        """
        errors = []
        
        # Required fields
        if not self.phone_number:
            errors.append("Phone number is required")
        elif not self._validate_phone_number(self.phone_number):
            errors.append("Phone number must contain only digits, spaces, '+' or '-' characters")
            
        if not self.age:
            errors.append("Age is required")
        elif not self._validate_age(self.age):
            errors.append("Age must be a number between 18 and 120, or a range in format 'min-max' (e.g., '20-35')")
            
        if not self.user_title:
            errors.append("User title is required")
        elif not self._validate_user_title(self.user_title):
            errors.append("User title must start with one of: Mr., Mrs., Miss., Ms.")
            
        if not self.name:
            errors.append("Name is required")
        elif not self._validate_name(self.name):
            errors.append("Name must be between 2 and 50 characters")
            
        if not self.target_driver:
            errors.append("Target driver is required")
        elif not self._validate_target_driver(self.target_driver):
            errors.append("Target driver must be one of: self, spouse, child, parent, other")
            
        if not self.expertise:
            errors.append("Expertise is required")
        elif not self._validate_expertise(self.expertise):
            errors.append("Expertise must be a number from 0 to 10")
            
        # Validate additional information
        if not self._validate_additional_information():
            errors.append("Additional information must include: family_size, price_sensitivity, residence, parking_conditions")
            
        # Validate connection information
        if not self._validate_connection_information():
            errors.append("Connection information must include: connection_phone_number, connection_id_relationship")
            
        return errors
    
    def _validate_phone_number(self, phone: str) -> bool:
        """Validate phone number format"""
        # Basic phone number validation (can be enhanced based on specific requirements)
        return bool(phone and phone.replace('+', '').replace('-', '').replace(' ', '').isdigit())
    
    def _validate_age(self, age: str) -> bool:
        """Validate age format and range
        
        Accepts formats:
        - Single number: "25"
        - Age range: "20-35"
        """
        try:
            if '-' in age:
                min_age, max_age = map(int, age.split('-'))
                return 18 <= min_age <= max_age <= 120
            else:
                age_val = int(age)
                return 18 <= age_val <= 120
        except (ValueError, TypeError):
            return False
    
    def _validate_user_title(self, title: str) -> bool:
        """Validate user title format"""
        valid_titles = ["Mr.", "Mrs.", "Miss.", "Ms."]
        title_part = title.split(' ')[0] if ' ' in title else title
        return title_part in valid_titles
    
    def _validate_name(self, name: str) -> bool:
        """Validate name format"""
        return 2 <= len(name) <= 50
    
    def _validate_target_driver(self, driver: str) -> bool:
        """Validate target driver value"""
        valid_drivers = ["self", "spouse", "child", "parent", "other"]
        return driver.lower() in valid_drivers
    
    def _validate_expertise(self, expertise: str) -> bool:
        """Validate expertise value"""
        try:
            expertise_val = int(expertise)
            return 0 <= expertise_val <= 10
        except ValueError:
            return False
    
    def _validate_additional_information(self) -> bool:
        """Validate additional information fields"""
        required_fields = ["family_size", "price_sensitivity", "residence", "parking_conditions"]
        return all(field in self.additional_information for field in required_fields)
    
    def _validate_connection_information(self) -> bool:
        """Validate connection information fields"""
        required_fields = ["connection_phone_number", "connection_id_relationship"]
        return all(field in self.connection_information for field in required_fields)
    
    @staticmethod
    def get_default_profile() -> Dict[str, Any]:
        """Return a default user profile"""
        return {
            "phone_number": "",
            "age": "",
            "user_title": "",
            "name": "",
            "target_driver": "",
            "expertise": "",
            "additional_information": {
                "family_size": "",
                "price_sensitivity": "",
                "residence": "",
                "parking_conditions": ""
            },
            "connection_information": {
                "connection_phone_number": "",
                "connection_id_relationship": ""
            }
        } 