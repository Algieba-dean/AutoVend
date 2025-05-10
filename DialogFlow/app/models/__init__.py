"""
Models module for AutoVend application.
Contains data models for different components of the system.
"""

# Import models to make them available at module level
from app.models.chat import ChatMessage, ChatSession
from app.models.user_profile import UserProfile, ConnectionInfo
from app.models.car_needs import CarNeed, CarNeeds
from app.models.vehicle import Vehicle, VehicleSpecs

# Models package initialization 