from typing import Dict, Any, Optional, List, Tuple
from app.models.profile import UserProfile
from app.config import Config
import os

class ProfileManager:
    """Manager class for handling user profile operations"""
    
    @staticmethod
    def get_default_profile() -> Dict[str, Any]:
        """Get the default user profile configuration"""
        defalt_user_phone_number = "13888888888"
        return ProfileManager.get_profile(defalt_user_phone_number)
    
    @staticmethod
    def get_profile(phone_number: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """Get user profile by phone number
        
        Returns:
            Tuple[Optional[Dict[str, Any]], Optional[str]]: (profile_data, error_message)
        """
        if not phone_number:
            return None, "Phone number is required"
            
        profile_data = Config.storage.get_profile(phone_number)
        if profile_data:
            return profile_data, None
        connection_data = Config.storage.get_profiles_from_connection(phone_number)
        from_user_name = connection_data.get("raw_name","")
        from_phone_number = connection_data.get("raw_phone_number","")
        connection_name = connection_data.get("connection_user_name","")
        connection_profile = UserProfile(phone_number)
        connection_profile.name = connection_name
        connection_profile.connection_information["connection_phone_number"] = from_phone_number
        connection_profile.connection_information["connection_user_name"] = from_user_name
        if not connection_data:
            return None, "Profile not found"
        Config.storage.save_profile(phone_number, connection_profile.to_dict())
        return connection_profile.to_dict(), None
    
    @staticmethod
    def create_profile(profile_data: Dict[str, Any]) -> Tuple[Optional[Dict[str, Any]], Optional[str], Optional[List[str]]]:
        """Create a new user profile
        
        Returns:
            Tuple[Optional[Dict[str, Any]], Optional[str], Optional[List[str]]]: 
            (profile_data, error_message, validation_errors)
        """
        if not profile_data:
            return None, "No data provided", None
            
        # Check if phone number already exists
        phone_number = profile_data.get("phone_number", "")
        if not phone_number:
            return None, "Phone number is required", None
            
        existing_profile = Config.storage.get_profile(phone_number)
        if existing_profile:
            return None, "Phone number already exists", None
            
        # load from connection if exists
        connection_data = Config.storage.get_profiles_from_connection(phone_number)
        profile = UserProfile.from_dict(profile_data)
        # connection_phone_number = phone_number
        if connection_data:
            from_user_name = connection_data.get("raw_name","")
            from_phone_number = connection_data.get("raw_phone_number","")
            connection_name = connection_data.get("connection_user_name","")
            connected_profile = UserProfile(phone_number)
            connected_profile.name = connection_name
            connected_profile.phone_number = phone_number
            connected_profile.connection_information["connection_phone_number"] = from_phone_number
            connected_profile.connection_information["connection_user_name"] = from_user_name
            Config.storage.save_profile(phone_number, connected_profile.to_dict())
            return connected_profile.to_dict(), "From connection", None
        # Create and validate profile
        validation_errors = profile.validate()
        
        if validation_errors:
            return None, "Validation error", validation_errors
            
        # Store profile
        if Config.storage.save_profile(phone_number, profile.to_dict()):
            return profile.to_dict(), None, None
        return None, "Failed to save profile", None
    
    @staticmethod
    def update_profile(phone_number: str, profile_data: Dict[str, Any]) -> Tuple[Optional[Dict[str, Any]], Optional[str], Optional[List[str]]]:
        """Update an existing user profile
        
        Returns:
            Tuple[Optional[Dict[str, Any]], Optional[str], Optional[List[str]]]: 
            (profile_data, error_message, validation_errors)
        """
        if not profile_data:
            return None, "No data provided", None
            
        # Check if profile exists
        existing_profile = Config.storage.get_profile(phone_number)
        if not existing_profile:
            return None, "Profile not found", None
            
        # Ensure phone number in data matches the one in URL
        if "phone_number" in profile_data and profile_data["phone_number"] != phone_number:
            return None, "Phone number in URL must match payload", None
            
        # Update and validate profile
        profile = UserProfile.from_dict(profile_data)
        validation_errors = profile.validate()
        
        if validation_errors:
            return None, "Validation error", validation_errors
            
        # Update profile
        if Config.storage.save_profile(phone_number, profile.to_dict()):
            return profile.to_dict(), None, None
        return None, "Failed to update profile", None
    
    @staticmethod
    def delete_profile(phone_number: str) -> Tuple[bool, Optional[str]]:
        """Delete a user profile
        
        Returns:
            Tuple[bool, Optional[str]]: (success, error_message)
        """
        if not phone_number:
            return False, "Phone number is required"
            
        try:
            profile_path = Config.storage._get_profile_path(phone_number)
            if not os.path.exists(profile_path):
                return False, "Profile not found"
                
            os.remove(profile_path)
            return True, None
        except Exception as e:
            return False, f"Error deleting profile: {str(e)}" 