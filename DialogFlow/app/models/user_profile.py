"""
User profile data models.
"""
from typing import Optional, Dict, List, Any
from pydantic import BaseModel, Field, field_validator
import uuid
from datetime import datetime
import toml
import os
import json
from app.config import USER_PROFILES_DIR, USER_TITLE_OPTIONS, TARGET_DRIVER_OPTIONS, EXPERTISE_RANGE, PRICE_SENSITIVITY_OPTIONS

class ConnectionInfo(BaseModel):
    """
    Represents a connection between users (e.g., family relationships).
    """
    connection_id: str
    relationship: str
    phone_number: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "connection_id": "d4c3b2a1-f6e5-a7b8-9c0d-1e2f3a4b5c6d",
                "relationship": "Wife",
                "phone_number": "13900139000"
            }
        }

class UserProfile(BaseModel):
    """
    Represents a user profile with personal information and preferences.
    """
    # Basic information
    profile_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    phone_number: Optional[str] = None
    age: Optional[str] = None
    user_title: Optional[str] = None
    name: Optional[str] = None
    target_driver: Optional[str] = None  # Self, Family, Friend
    expertise: Optional[int] = None  # 0-10 level of automotive knowledge
    
    # Additional information
    family_size: Optional[int] = None
    price_sensitivity: Optional[str] = None  # High, Medium, Low
    residence: Optional[str] = None  # Format: Country+Province+City
    parking_conditions: Optional[str] = None
    
    # Dynamic tags
    tags: Dict[str, Any] = {}
    
    # Associated information
    connections: List[ConnectionInfo] = []
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    
    class Config:
        json_schema_extra = {
            "example": {
                "profile_id": "e9f8d7c6-5b4a-3c2a-1f9e-7a6b4c5d2e3f",
                "phone_number": "13800138000",
                "age": "30-40",
                "user_title": "Mr.",
                "name": "Zhang",
                "target_driver": "Self",
                "expertise": 3,
                "family_size": 3,
                "price_sensitivity": "Medium",
                "residence": "China+Beijing+Chaoyang",
                "parking_conditions": "Allocated Parking Space",
                "tags": {
                    "Age Group": "Middle-aged",
                    "Tech Comfort": "Medium",
                    "Urban Driving": "High",
                    "Parking Ease": "High, Implicit"
                },
                "connections": [],
                "created_at": "2023-11-20T15:31:15.654321",
                "updated_at": "2023-11-20T15:35:22.123456"
            }
        }
    
    def update_profile(self, update_data: Dict[str, Any]) -> None:
        """
        Update the user profile with new information.
        
        Args:
            update_data: Dictionary containing fields to update
        """
        for key, value in update_data.items():
            if hasattr(self, key):
                setattr(self, key, value)
        
        self.updated_at = datetime.now()
    
    def add_connection(self, connection_id: str, relationship: str, phone_number: Optional[str] = None) -> ConnectionInfo:
        """
        Add a new connection to the user profile.
        
        Args:
            connection_id: ID of the connected user profile
            relationship: Description of the relationship
            phone_number: Phone number of the connected user
            
        Returns:
            The created ConnectionInfo object
        """
        connection = ConnectionInfo(
            connection_id=connection_id,
            relationship=relationship,
            phone_number=phone_number
        )
        self.connections.append(connection)
        self.updated_at = datetime.now()
        return connection
    
    @field_validator('user_title')
    @classmethod
    def validate_user_title(cls, v):
        if v is not None and v not in USER_TITLE_OPTIONS:
            raise ValueError(f"user_title must be one of {USER_TITLE_OPTIONS}")
        return v
    
    @field_validator('target_driver')
    @classmethod
    def validate_target_driver(cls, v):
        if v is not None and v not in TARGET_DRIVER_OPTIONS:
            raise ValueError(f"target_driver must be one of {TARGET_DRIVER_OPTIONS}")
        return v
    
    @field_validator('expertise')
    @classmethod
    def validate_expertise(cls, v):
        if v is not None and v not in EXPERTISE_RANGE:
            raise ValueError(f"expertise must be between 0 and 10")
        return v
    
    @field_validator('price_sensitivity')
    @classmethod
    def validate_price_sensitivity(cls, v):
        if v is not None and v not in PRICE_SENSITIVITY_OPTIONS:
            raise ValueError(f"price_sensitivity must be one of {PRICE_SENSITIVITY_OPTIONS}")
        return v
    
    def save(self):
        """Save user profile to file"""
        self.updated_at = datetime.now()
        
        if not os.path.exists(USER_PROFILES_DIR):
            os.makedirs(USER_PROFILES_DIR)
            
        filepath = os.path.join(USER_PROFILES_DIR, f"{self.profile_id}.json")
        
        with open(filepath, 'w') as f:
            f.write(self.model_dump_json(indent=4))
    
    @classmethod
    def load_by_id(cls, profile_id: str):
        """Load user profile by ID"""
        filepath = os.path.join(USER_PROFILES_DIR, f"{profile_id}.json")
        
        if not os.path.exists(filepath):
            return None
            
        with open(filepath, 'r') as f:
            data = json.load(f)
            
        return cls(**data)
    
    @classmethod
    def load_by_phone(cls, phone_number: str):
        """Load user profile by phone number"""
        if not os.path.exists(USER_PROFILES_DIR):
            return None
            
        for filename in os.listdir(USER_PROFILES_DIR):
            if filename.endswith('.json'):
                filepath = os.path.join(USER_PROFILES_DIR, filename)
                
                with open(filepath, 'r') as f:
                    data = json.load(f)
                    
                if data.get('phone_number') == phone_number:
                    return cls(**data)
        
        return None
        
    @classmethod
    def load_by_connection_phone(cls, phone_number: str):
        """Check if any profile has this phone number as a connection"""
        if not os.path.exists(USER_PROFILES_DIR):
            return None
            
        for filename in os.listdir(USER_PROFILES_DIR):
            if filename.endswith('.json'):
                filepath = os.path.join(USER_PROFILES_DIR, filename)
                
                with open(filepath, 'r') as f:
                    data = json.load(f)
                
                connections = data.get('connections', [])
                for connection in connections:
                    if connection.get('connection_phone_number') == phone_number:
                        return cls(**data)
        
        return None
    
    def extract_tags(self):
        """Extract tags from profile information"""
        tags = {}
        
        # Age-based tags
        if self.age:
            if "-" in str(self.age):
                min_age, max_age = map(int, self.age.split("-"))
                avg_age = (min_age + max_age) / 2
                
                if avg_age < 30:
                    tags["Age Group"] = "Young"
                    tags["Tech Comfort"] = "High"
                elif avg_age < 50:
                    tags["Age Group"] = "Middle-aged"
                    tags["Tech Comfort"] = "Medium"
                else:
                    tags["Age Group"] = "Senior"
                    tags["Tech Comfort"] = "Low"
        
        # Residence-based tags
        if self.residence:
            parts = self.residence.split("+")
            if len(parts) >= 3:
                country, province, city = parts[0], parts[1], parts[2]
                
                # Northern cities may prefer models with better heating
                northern_provinces = ["Heilongjiang", "Jilin", "Liaoning", "Inner Mongolia", "Beijing", "Tianjin", "Hebei"]
                if province in northern_provinces:
                    tags["Climate Adaptation"] = "Cold Weather"
                    tags["Heating System"] = "High, Implicit"
                
                # Southern cities may prefer models with better cooling
                southern_provinces = ["Guangdong", "Guangxi", "Hainan", "Fujian", "Yunnan"]
                if province in southern_provinces:
                    tags["Climate Adaptation"] = "Hot Weather"
                    tags["Cooling System"] = "High, Implicit"
                
                # Big cities may prefer compact cars
                big_cities = ["Beijing", "Shanghai", "Guangzhou", "Shenzhen"]
                if city in big_cities:
                    tags["Urban Driving"] = "High"
                    tags["Parking Ease"] = "High, Implicit"
                    tags["Size"] = "Compact, Implicit"
        
        # Expertise-based tags
        if self.expertise is not None:
            if self.expertise <= 3:
                tags["Expertise"] = "Low"
                tags["Technical Detail Preference"] = "Low" 
                tags["Chat Style"] = "Simple, Implicit"
            elif self.expertise <= 7:
                tags["Expertise"] = "Medium"
                tags["Technical Detail Preference"] = "Medium"
                tags["Chat Style"] = "Balanced, Implicit"
            else:
                tags["Expertise"] = "High"
                tags["Technical Detail Preference"] = "High"
                tags["Chat Style"] = "Professional, Implicit"
        
        # Target driver based tags
        if self.target_driver:
            if self.target_driver == "Self":
                # No special tags
                pass
            elif self.target_driver in ["Parents", "Elderly"]:
                tags["Operability"] = "Simple, Implicit"
                tags["Entry Height"] = "High, Implicit"
                tags["Safety"] = "High, Implicit"
            elif self.target_driver in ["Wife", "Husband", "Partner"]:
                if not self.family_size or self.family_size <= 2:
                    tags["Size"] = "Medium, Implicit"
                else:
                    tags["Size"] = "Large, Implicit"
                    tags["Space"] = "Large, Implicit"
            elif self.target_driver == "Children":
                tags["Safety"] = "High, Implicit"
                tags["Technology"] = "High, Implicit"
        
        # Family size based tags
        if self.family_size:
            if self.family_size >= 4:
                tags["Space"] = "Large, Implicit"
                tags["Seats"] = f"{max(5, self.family_size)}, Implicit"
                tags["Child Seat"] = "Yes, Implicit"
            
        # Parking conditions based tags
        if self.parking_conditions:
            if self.parking_conditions and "Charging Pile" in str(self.parking_conditions):
                tags["Electric Vehicle"] = "High, Implicit"
            elif self.parking_conditions and "Temporary" in str(self.parking_conditions):
                tags["Size"] = "Compact, Implicit"
                tags["Parking Ease"] = "High, Implicit"
        
        self.tags = tags
        return tags 