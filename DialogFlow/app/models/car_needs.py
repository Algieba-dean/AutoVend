"""
Car needs and requirements data models.
"""
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
import toml
import os
import json
from datetime import datetime
from app.config import CAR_LABELS_FILE
from uuid import uuid4

class CarNeed(BaseModel):
    """
    Represents a single car requirement or need.
    """
    value: str
    is_implicit: bool = False  # Whether it's an implicit requirement
    confidence: float = 1.0  # Confidence level (0.0-1.0)
    source: str = "direct"  # Source: "direct" (user statement), "inference" (system inference), etc.
    
    class Config:
        json_schema_extra = {
            "example": {
                "value": "SUV",
                "is_implicit": False,
                "confidence": 1.0,
                "source": "direct"
            }
        }

class CarNeeds(BaseModel):
    """
    Represents a collection of car requirements for a user.
    """
    profile_id: str
    
    # Explicit requirements
    budget: Optional[CarNeed] = None
    brand: List[CarNeed] = []
    vehicle_category: List[CarNeed] = []
    color: List[CarNeed] = []
    
    # Performance requirements
    engine_type: List[CarNeed] = []
    transmission: List[CarNeed] = []
    fuel_efficiency: Optional[CarNeed] = None
    
    # Function and comfort
    seats: Optional[CarNeed] = None
    sunroof: Optional[CarNeed] = None
    entertainment: List[CarNeed] = []
    safety_features: List[CarNeed] = []
    
    # Implicit requirements
    size: Optional[CarNeed] = None
    usage: List[CarNeed] = []  # Urban driving, off-road, family, etc.
    style: List[CarNeed] = []  # Luxury, sports, practical, etc.
    
    # Custom requirements
    custom_needs: Dict[str, CarNeed] = {}
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    
    class Config:
        json_schema_extra = {
            "example": {
                "profile_id": "e9f8d7c6-5b4a-3c2a-1f9e-7a6b4c5d2e3f",
                "budget": {
                    "value": "300000",
                    "is_implicit": False,
                    "confidence": 1.0,
                    "source": "direct"
                },
                "vehicle_category": [
                    {
                        "value": "SUV",
                        "is_implicit": False,
                        "confidence": 1.0,
                        "source": "direct"
                    }
                ],
                "size": {
                    "value": "Medium",
                    "is_implicit": True,
                    "confidence": 0.8,
                    "source": "inference"
                }
            }
        }
    
    def add_need(self, category: str, value: str, is_implicit: bool = False, 
                 confidence: float = 1.0, source: str = "direct") -> None:
        """
        Add a new need to the appropriate category.
        
        Args:
            category: The category of the need
            value: The value of the need
            is_implicit: Whether the need is implicit
            confidence: Confidence level of the need
            source: Source of the need (direct, inference, etc.)
        
        Raises:
            ValueError: If the category is not valid
        """
        need = CarNeed(
            value=value,
            is_implicit=is_implicit,
            confidence=confidence,
            source=source
        )
        
        # Handle single-value categories
        if category in ["budget", "size", "seats", "fuel_efficiency", "sunroof"]:
            setattr(self, category, need)
        # Handle list categories
        elif category in ["brand", "vehicle_category", "color", "engine_type", 
                         "transmission", "entertainment", "safety_features", 
                         "usage", "style"]:
            category_list = getattr(self, category)
            
            # Check if the value already exists in the list
            for i, existing_need in enumerate(category_list):
                if existing_need.value.lower() == value.lower():
                    # Replace the existing need
                    category_list[i] = need
                    break
            else:
                # Value doesn't exist, append it
                category_list.append(need)
        else:
            # Handle custom needs
            self.custom_needs[category] = need
        
        self.updated_at = datetime.now()
    
    def remove_need(self, category: str, value: Optional[str] = None) -> None:
        """
        Remove a need from the appropriate category.
        
        Args:
            category: The category of the need
            value: The value to remove (only needed for list categories)
            
        Raises:
            ValueError: If the category is not valid or the value is not found
        """
        # Handle single-value categories
        if category in ["budget", "size", "seats", "fuel_efficiency", "sunroof"]:
            setattr(self, category, None)
        # Handle list categories
        elif category in ["brand", "vehicle_category", "color", "engine_type", 
                         "transmission", "entertainment", "safety_features", 
                         "usage", "style"]:
            if value is None:
                raise ValueError(f"Value must be provided to remove from list category {category}")
            
            category_list = getattr(self, category)
            # Find and remove the matching need
            for i, need in enumerate(category_list):
                if need.value.lower() == value.lower():
                    category_list.pop(i)
                    break
            else:
                raise ValueError(f"Value '{value}' not found in category {category}")
        else:
            # Handle custom needs
            if value is None:
                # Remove the entire custom category
                if category in self.custom_needs:
                    del self.custom_needs[category]
            else:
                # This branch would be used if we supported multiple values in custom categories
                raise ValueError(f"Cannot remove specific value from custom category {category}")
        
        self.updated_at = datetime.now()
    
    def get_all_needs(self) -> Dict[str, Any]:
        """
        Get all needs as a dictionary.
        
        Returns:
            Dictionary of all needs organized by category
        """
        needs_dict = {}
        
        # Process single-value categories
        for category in ["budget", "size", "seats", "fuel_efficiency", "sunroof"]:
            need = getattr(self, category)
            if need:
                if need.is_implicit:
                    needs_dict[category] = f"{need.value}, Implicit"
                else:
                    needs_dict[category] = need.value
        
        # Process list categories
        for category in ["brand", "vehicle_category", "color", "engine_type", 
                        "transmission", "entertainment", "safety_features", 
                        "usage", "style"]:
            needs_list = getattr(self, category)
            if needs_list:
                values = []
                for need in needs_list:
                    if need.is_implicit:
                        values.append(f"{need.value}, Implicit")
                    else:
                        values.append(need.value)
                needs_dict[category] = values
        
        # Process custom needs
        for category, need in self.custom_needs.items():
            if need.is_implicit:
                needs_dict[category] = f"{need.value}, Implicit"
            else:
                needs_dict[category] = need.value
        
        return needs_dict
    
    def get_tags(self):
        """Convert needs to tags format for compatibility with user profile tags"""
        tags = {}
        
        if self.budget:
            tags["Budget"] = self.budget.value
            
        if self.brand:
            brands = ", ".join([b.value for b in self.brand])
            tags["Brand"] = brands
            
        if self.vehicle_category:
            categories = ", ".join([c.value for c in self.vehicle_category])
            tags["Vehicle Category"] = categories
            
        if self.size:
            tags["Size"] = str(self.size)
            
        for category, need in self.custom_needs.items():
            tags[category.replace("_", " ").title()] = str(need)
            
        return tags
    
    def save(self, directory_path: str):
        """Save car needs to file"""
        self.updated_at = datetime.now()
        
        if not os.path.exists(directory_path):
            os.makedirs(directory_path)
            
        filepath = os.path.join(directory_path, f"needs_{self.profile_id}.json")
        
        with open(filepath, 'w') as f:
            f.write(self.model_dump_json(indent=4))
    
    @classmethod
    def load(cls, directory_path: str, profile_id: str):
        """Load car needs from file"""
        filepath = os.path.join(directory_path, f"needs_{profile_id}.json")
        
        if not os.path.exists(filepath):
            return cls(profile_id=profile_id)
            
        with open(filepath, 'r') as f:
            data = json.load(f)
            
        return cls(**data) 