"""
Sample data utility for AutoVend application.
"""
import json
import os
import shutil
from datetime import datetime
from uuid import uuid4

from app.config import (
    USER_PROFILES_DIR,
    NEEDS_DIR,
    SESSIONS_DIR,
    VEHICLES_DIR
)


def init_sample_data():
    """
    Initialize sample data for the application.
    """
    # Create sample vehicle data
    create_sample_vehicles()
    
    # Clean out existing session data
    clean_sessions()


def clean_sessions():
    """
    Clean out existing session data.
    """
    if os.path.exists(SESSIONS_DIR):
        # Remove all files in the sessions directory
        for file in os.listdir(SESSIONS_DIR):
            file_path = os.path.join(SESSIONS_DIR, file)
            if os.path.isfile(file_path):
                os.remove(file_path)


def create_sample_vehicles():
    """
    Create sample vehicle data.
    """
    vehicles = [
        {
            "vehicle_id": str(uuid4()),
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
                "Lane Departure Warning",
                "Adaptive Cruise Control"
            ],
            "tags": ["Reliable", "Fuel-efficient", "Family", "Commuter"]
        },
        {
            "vehicle_id": str(uuid4()),
            "brand": "Honda",
            "model": "CR-V",
            "category": "SUV",
            "price": 28000.00,
            "year": 2023,
            "specs": {
                "engine": "1.5L Turbo 4-Cylinder",
                "transmission": "CVT",
                "fuel_economy": "28 city / 34 highway",
                "horsepower": 190,
                "seats": 5
            },
            "features": [
                "Android Auto",
                "Apple CarPlay",
                "Bluetooth",
                "Backup Camera",
                "Lane Keeping Assist",
                "Adaptive Cruise Control",
                "Collision Mitigation Braking"
            ],
            "tags": ["Versatile", "Spacious", "Family", "Reliable", "Safety"]
        },
        {
            "vehicle_id": str(uuid4()),
            "brand": "BMW",
            "model": "3 Series",
            "category": "Luxury Sedan",
            "price": 45000.00,
            "year": 2023,
            "specs": {
                "engine": "2.0L Turbo 4-Cylinder",
                "transmission": "8-Speed Automatic",
                "fuel_economy": "26 city / 36 highway",
                "horsepower": 255,
                "seats": 5
            },
            "features": [
                "Android Auto",
                "Apple CarPlay",
                "Bluetooth",
                "Navigation",
                "Heated Seats",
                "Premium Sound System",
                "Heads-up Display"
            ],
            "tags": ["Luxury", "Performance", "Status", "Technology"]
        },
        {
            "vehicle_id": str(uuid4()),
            "brand": "Tesla",
            "model": "Model 3",
            "category": "Electric Sedan",
            "price": 42000.00,
            "year": 2023,
            "specs": {
                "engine": "Electric",
                "transmission": "Single-Speed",
                "range": "358 miles",
                "horsepower": 283,
                "seats": 5
            },
            "features": [
                "Autopilot",
                "Navigation",
                "Panoramic Roof",
                "Over-the-air Updates",
                "Sentry Mode",
                "15-inch Touchscreen"
            ],
            "tags": ["Electric", "Tech-forward", "Eco-friendly", "Modern"]
        },
        {
            "vehicle_id": str(uuid4()),
            "brand": "Ford",
            "model": "F-150",
            "category": "Pickup Truck",
            "price": 35000.00,
            "year": 2023,
            "specs": {
                "engine": "3.5L V6",
                "transmission": "10-Speed Automatic",
                "fuel_economy": "20 city / 26 highway",
                "horsepower": 290,
                "seats": 6,
                "towing_capacity": "8,500 lbs"
            },
            "features": [
                "Android Auto",
                "Apple CarPlay",
                "Bluetooth",
                "Backup Camera",
                "Pro Trailer Backup Assist",
                "Tailgate Step"
            ],
            "tags": ["Rugged", "Utility", "Work", "Towing", "Off-road"]
        }
    ]
    
    # Create vehicles directory if it doesn't exist
    if not os.path.exists(VEHICLES_DIR):
        os.makedirs(VEHICLES_DIR)
    
    # Save each vehicle to a separate file
    for vehicle in vehicles:
        file_path = os.path.join(VEHICLES_DIR, f"{vehicle['vehicle_id']}.json")
        with open(file_path, 'w') as f:
            json.dump(vehicle, f, indent=4)
    
    # Also save a combined file for easier access
    with open(os.path.join(VEHICLES_DIR, "vehicles.json"), 'w') as f:
        json.dump(vehicles, f, indent=4) 