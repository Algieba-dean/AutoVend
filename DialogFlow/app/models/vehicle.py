"""
Vehicle data models.
"""
from typing import Dict, List, Optional, Any
from uuid import uuid4
from datetime import datetime
from pydantic import BaseModel, Field


class VehicleSpecs(BaseModel):
    """
    Represents vehicle specifications.
    """
    engine: str
    transmission: str
    fuel_economy: Optional[str] = None
    range: Optional[str] = None  # For electric vehicles
    horsepower: int
    seats: int
    towing_capacity: Optional[str] = None


class Vehicle(BaseModel):
    """
    Represents a vehicle.
    """
    vehicle_id: str = Field(default_factory=lambda: str(uuid4()))
    brand: str
    model: str
    category: str
    price: float
    year: int
    specs: VehicleSpecs
    features: List[str] = []
    tags: List[str] = []
    
    class Config:
        json_schema_extra = {
            "example": {
                "vehicle_id": "f8d7e9c3-5b2a-4c1a-8f9e-3a6b2c5d4e7f",
                "brand": "Toyota",
                "model": "Camry",
                "category": "Sedan",
                "price": 25000.00,
                "year": 2023,
                "specs": {
                    "engine": "2.5L 4-Cylinder",
                    "transmission": "8-Speed Automatic",
                    "fuel_economy": "28 city / 39 highway",
                    "horsepower": 203,
                    "seats": 5
                },
                "features": [
                    "Android Auto",
                    "Apple CarPlay",
                    "Bluetooth",
                    "Backup Camera",
                    "Lane Departure Warning"
                ],
                "tags": ["Reliable", "Fuel-efficient", "Family", "Commuter"]
            }
        } 