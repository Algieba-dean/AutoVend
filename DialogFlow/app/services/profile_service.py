"""
Profile service for managing user profiles.
"""
import json
import logging
import os
from typing import Dict, Optional, Any
from uuid import uuid4

from app.config import USER_PROFILES_DIR
from app.models import UserProfile

# Configure logging
logger = logging.getLogger(__name__)


class ProfileService:
    """
    Service for managing user profiles.
    """
    
    def create_profile(self, phone_number: Optional[str] = None) -> UserProfile:
        """
        Create a new user profile.
        
        Args:
            phone_number: Optional phone number for the user
            
        Returns:
            The created UserProfile object
        """
        profile = UserProfile(
            profile_id=str(uuid4()),
            phone_number=phone_number
        )
        
        # Save the profile
        self._save_profile(profile)
        
        return profile
    
    def get_profile_by_id(self, profile_id: str) -> Optional[UserProfile]:
        """
        Get a user profile by ID.
        
        Args:
            profile_id: The ID of the profile to retrieve
            
        Returns:
            The UserProfile object if found, None otherwise
        """
        try:
            filepath = os.path.join(USER_PROFILES_DIR, f"{profile_id}.json")
            
            if not os.path.exists(filepath):
                return None
                
            with open(filepath, 'r') as f:
                data = json.load(f)
                
            return UserProfile(**data)
        except Exception as e:
            logger.error(f"Error retrieving user profile {profile_id}: {str(e)}")
            return None
    
    def get_profile_by_phone(self, phone_number: str) -> Optional[UserProfile]:
        """
        Get a user profile by phone number.
        
        Args:
            phone_number: The phone number to search for
            
        Returns:
            The UserProfile object if found, None otherwise
        """
        try:
            if not os.path.exists(USER_PROFILES_DIR):
                return None
                
            for filename in os.listdir(USER_PROFILES_DIR):
                if filename.endswith('.json'):
                    filepath = os.path.join(USER_PROFILES_DIR, filename)
                    
                    with open(filepath, 'r') as f:
                        data = json.load(f)
                        
                    if data.get('phone_number') == phone_number:
                        return UserProfile(**data)
            
            return None
        except Exception as e:
            logger.error(f"Error searching for user profile by phone {phone_number}: {str(e)}")
            return None
    
    def update_profile(self, profile_id: str, update_data: Dict[str, Any]) -> Optional[UserProfile]:
        """
        Update a user profile.
        
        Args:
            profile_id: The ID of the profile to update
            update_data: Dictionary of fields to update
            
        Returns:
            The updated UserProfile object if successful, None otherwise
        """
        # Get the profile
        profile = self.get_profile_by_id(profile_id)
        if not profile:
            logger.error(f"Profile {profile_id} not found")
            return None
        
        # Update profile fields
        for key, value in update_data.items():
            if hasattr(profile, key):
                setattr(profile, key, value)
        
        # Generate tags based on profile information
        self._generate_tags(profile)
        
        # Save the profile
        self._save_profile(profile)
        
        return profile
    
    def add_connection(self, profile_id: str, connection_id: str, 
                       relationship: str, phone_number: Optional[str] = None) -> Optional[UserProfile]:
        """
        Add a connection to a user profile.
        
        Args:
            profile_id: The ID of the profile to update
            connection_id: The ID of the connected profile
            relationship: Description of the relationship
            phone_number: Optional phone number of the connection
            
        Returns:
            The updated UserProfile object if successful, None otherwise
        """
        # Get the profile
        profile = self.get_profile_by_id(profile_id)
        if not profile:
            logger.error(f"Profile {profile_id} not found")
            return None
        
        # Add the connection
        profile.add_connection(connection_id, relationship, phone_number)
        
        # Save the profile
        self._save_profile(profile)
        
        return profile
    
    def _generate_tags(self, profile: UserProfile) -> None:
        """
        Generate tags based on profile information.
        
        Args:
            profile: The UserProfile object
        """
        tags = {}
        
        # Age group
        if profile.age:
            age_str = profile.age.lower()
            if "20" in age_str or "young" in age_str:
                tags["Age Group"] = "Young Adult"
            elif "30" in age_str or "40" in age_str or "middle" in age_str:
                tags["Age Group"] = "Middle-aged"
            elif "50" in age_str or "60" in age_str or "senior" in age_str or "elder" in age_str:
                tags["Age Group"] = "Senior"
        
        # Tech comfort based on expertise
        if profile.expertise is not None:
            if profile.expertise <= 3:
                tags["Tech Comfort"] = "Low"
            elif profile.expertise <= 7:
                tags["Tech Comfort"] = "Medium"
            else:
                tags["Tech Comfort"] = "High"
        
        # Urban vs. rural based on residence
        if profile.residence:
            residence = profile.residence.lower()
            urban_keywords = ["beijing", "shanghai", "guangzhou", "shenzhen", "tianjin", "city", "urban"]
            rural_keywords = ["rural", "village", "town", "county"]
            
            if any(keyword in residence for keyword in urban_keywords):
                tags["Urban Driving"] = "High"
            elif any(keyword in residence for keyword in rural_keywords):
                tags["Rural Driving"] = "High"
        
        # Parking preferences based on parking conditions
        if profile.parking_conditions:
            parking = profile.parking_conditions.lower()
            if "garage" in parking or "private" in parking:
                tags["Parking Preference"] = "Private"
            elif "street" in parking or "public" in parking:
                tags["Parking Preference"] = "Public"
            elif "limited" in parking or "difficult" in parking:
                tags["Parking Ease"] = "Low, Implicit"
            elif "ample" in parking or "easy" in parking:
                tags["Parking Ease"] = "High, Implicit"
        
        # Family size implications
        if profile.family_size:
            if profile.family_size >= 4:
                tags["Family Size"] = "Large"
                tags["Space Needs"] = "High, Implicit"
            elif profile.family_size >= 2:
                tags["Family Size"] = "Medium"
            else:
                tags["Family Size"] = "Small"
        
        # Price sensitivity
        if profile.price_sensitivity:
            tags["Price Sensitivity"] = profile.price_sensitivity
        
        # Update the profile tags
        profile.tags.update(tags)
    
    def _save_profile(self, profile: UserProfile) -> None:
        """
        Save a user profile to disk.
        
        Args:
            profile: The UserProfile object to save
        """
        try:
            if not os.path.exists(USER_PROFILES_DIR):
                os.makedirs(USER_PROFILES_DIR)
                
            filepath = os.path.join(USER_PROFILES_DIR, f"{profile.profile_id}.json")
            
            with open(filepath, 'w') as f:
                f.write(profile.json(indent=4))
        except Exception as e:
            logger.error(f"Error saving user profile {profile.profile_id}: {str(e)}")


# Create a singleton instance
profile_service = ProfileService() 