import json
from datetime import datetime

class UserProfile:
    """User profile model for AutoVend application"""
    
    def __init__(self, phone_number, age="", user_title="", name="", target_driver="", expertise="",
                 additional_information=None, connection_information=None):
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
    def from_dict(cls, data):
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
    
    def to_dict(self):
        """Convert the profile to a dictionary"""
        return {
            'phone_number': self.phone_number,
            'age': self.age,
            'user_title': self.user_title,
            'name': self.name,
            'target_driver': self.target_driver,
            'expertise': self.expertise,
            'additional_information': self.additional_information,
            'connection_information': self.connection_information
        }
    
    def validate(self):
        """Validate the profile data"""
        errors = []
        
        # Required fields
        if not self.phone_number:
            errors.append("Phone number is required")
        if not self.age:
            errors.append("Age is required")
        if not self.user_title:
            errors.append("User title is required")
        if not self.target_driver:
            errors.append("Target driver is required")
        if not self.expertise:
            errors.append("Expertise is required")
            
        # Validate expertise is a number from 0 to 10
        if self.expertise:
            try:
                expertise_val = int(self.expertise)
                if expertise_val < 0 or expertise_val > 10:
                    errors.append("Expertise must be a number from 0 to 10")
            except ValueError:
                errors.append("Expertise must be a number from 0 to 10")
                
        # Validate user_title format
        valid_titles = ["Mr.", "Mrs.", "Miss.", "Ms."]
        if self.user_title:
            title_part = self.user_title.split(' ')[0] if ' ' in self.user_title else self.user_title
            if title_part not in valid_titles:
                errors.append(f"User title must start with one of: {', '.join(valid_titles)}")
        
        return errors
    
    @staticmethod
    def get_default_profile():
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