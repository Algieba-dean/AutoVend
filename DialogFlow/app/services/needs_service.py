"""
Needs service for managing car requirements.
"""
import json
import logging
import os
from typing import Dict, List, Optional, Any
from uuid import uuid4

from app.config import NEEDS_DIR
from app.models import CarNeeds, CarNeed

# Configure logging
logger = logging.getLogger(__name__)


class NeedsService:
    """
    Service for managing car needs and requirements.
    """
    
    def create_needs(self, profile_id: str) -> CarNeeds:
        """
        Create a new car needs object for a user.
        
        Args:
            profile_id: The ID of the user profile
            
        Returns:
            The created CarNeeds object
        """
        needs = CarNeeds(profile_id=profile_id)
        
        # Save the needs
        self._save_needs(needs)
        
        return needs
    
    def get_needs(self, profile_id: str) -> CarNeeds:
        """
        Get car needs for a user profile. Creates new needs if not found.
        
        Args:
            profile_id: The ID of the user profile
            
        Returns:
            The CarNeeds object for the user
        """
        try:
            filepath = os.path.join(NEEDS_DIR, f"needs_{profile_id}.json")
            
            if not os.path.exists(filepath):
                # Create new needs if not found
                return self.create_needs(profile_id)
                
            with open(filepath, 'r') as f:
                data = json.load(f)
                
            return CarNeeds(**data)
        except Exception as e:
            logger.error(f"Error retrieving car needs for profile {profile_id}: {str(e)}")
            # Create new needs if there was an error
            return self.create_needs(profile_id)
    
    def add_need(self, profile_id: str, category: str, value: str, 
                is_implicit: bool = False, confidence: float = 1.0, 
                source: str = "direct") -> CarNeeds:
        """
        Add a need to a user's car requirements.
        
        Args:
            profile_id: The ID of the user profile
            category: The category of the need
            value: The value of the need
            is_implicit: Whether the need is implicit
            confidence: Confidence level of the need
            source: Source of the need (direct, inference, etc.)
            
        Returns:
            The updated CarNeeds object
        """
        # Get the needs
        needs = self.get_needs(profile_id)
        
        # Add the need
        needs.add_need(
            category=category,
            value=value,
            is_implicit=is_implicit,
            confidence=confidence,
            source=source
        )
        
        # Save the needs
        self._save_needs(needs)
        
        return needs
    
    def remove_need(self, profile_id: str, category: str, value: Optional[str] = None) -> Optional[CarNeeds]:
        """
        Remove a need from a user's car requirements.
        
        Args:
            profile_id: The ID of the user profile
            category: The category of the need
            value: The value to remove (only needed for list categories)
            
        Returns:
            The updated CarNeeds object if successful, None otherwise
        """
        try:
            # Get the needs
            needs = self.get_needs(profile_id)
            
            # Remove the need
            needs.remove_need(category, value)
            
            # Save the needs
            self._save_needs(needs)
            
            return needs
        except ValueError as e:
            logger.error(f"Error removing need: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Error removing need: {str(e)}")
            return None
    
    def get_all_needs(self, profile_id: str) -> Dict[str, Any]:
        """
        Get all needs for a user profile as a dictionary.
        
        Args:
            profile_id: The ID of the user profile
            
        Returns:
            Dictionary of all needs organized by category
        """
        needs = self.get_needs(profile_id)
        return needs.get_all_needs()
    
    def infer_implicit_needs(self, profile_id: str) -> None:
        """
        Infer implicit needs based on user profile and explicit needs.
        
        Args:
            profile_id: The ID of the user profile
        """
        # This would be a more complex method in a full implementation
        # For now, we'll just add a simple example
        try:
            # Get the needs
            needs = self.get_needs(profile_id)
            
            # Example: If they have specified SUV, they might need more space
            for need in needs.vehicle_category_bottom:
                if need.value.lower() == "suv" and not need.is_implicit:
                    self.add_need(
                        profile_id=profile_id,
                        category="size",
                        value="Large",
                        is_implicit=True,
                        confidence=0.8,
                        source="inference"
                    )
                
            # Save the needs
            self._save_needs(needs)
        except Exception as e:
            logger.error(f"Error inferring implicit needs: {str(e)}")
    
    def _save_needs(self, needs: CarNeeds) -> None:
        """
        Save car needs to disk.
        
        Args:
            needs: The CarNeeds object to save
        """
        try:
            if not os.path.exists(NEEDS_DIR):
                os.makedirs(NEEDS_DIR)
                
            filepath = os.path.join(NEEDS_DIR, f"needs_{needs.profile_id}.json")
            
            with open(filepath, 'w') as f:
                f.write(needs.json(indent=4))
        except Exception as e:
            logger.error(f"Error saving car needs for profile {needs.profile_id}: {str(e)}")


# Create a singleton instance
needs_service = NeedsService() 