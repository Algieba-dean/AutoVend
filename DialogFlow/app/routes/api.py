from fastapi import APIRouter, HTTPException, Body, Query, Path, Depends, status
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime

from app.services.chat_service import chat_service
from app.services.profile_service import profile_service
from app.services.needs_service import needs_service
from app.services.vehicle_service import vehicle_service

router = APIRouter(prefix="/api")

# --- Chat API Models ---

class MessageRequest(BaseModel):
    content: str
    sender: str = "user"
    
class MessageResponse(BaseModel):
    message_id: str
    content: str
    role: str
    timestamp: str
    
class SessionResponse(BaseModel):
    session_id: str
    profile_id: Optional[str] = None
    phone_number: Optional[str] = None
    messages: List[MessageResponse]
    stage: str
    
class NewSessionRequest(BaseModel):
    phone_number: Optional[str] = None

# --- User Profile API Models ---

class ProfileResponse(BaseModel):
    profile_id: str
    phone_number: Optional[str]
    age: Optional[str] = None
    user_title: Optional[str] = None
    name: Optional[str] = None
    target_driver: Optional[str] = None
    expertise: Optional[int] = None
    family_size: Optional[int] = None
    price_sensitivity: Optional[str] = None
    residence: Optional[str] = None
    parking_conditions: Optional[str] = None
    tags: Dict[str, Any] = {}
    connections: List[Dict[str, Any]] = []
    created_at: datetime
    updated_at: datetime

class ProfileUpdateRequest(BaseModel):
    age: Optional[str] = None
    user_title: Optional[str] = None
    name: Optional[str] = None
    target_driver: Optional[str] = None
    expertise: Optional[int] = None
    family_size: Optional[int] = None
    price_sensitivity: Optional[str] = None
    residence: Optional[str] = None
    parking_conditions: Optional[str] = None

class ConnectionRequest(BaseModel):
    connection_phone_number: str
    connection_id_relationship: str

# --- Car Needs API Models ---

class NeedRequest(BaseModel):
    category: str
    value: str
    is_implicit: bool = False

# --- Vehicle API Models ---

class VehicleSpecsResponse(BaseModel):
    engine: str
    transmission: str
    fuel_economy: Optional[str] = None
    range: Optional[str] = None
    horsepower: int
    seats: int
    towing_capacity: Optional[str] = None

class VehicleResponse(BaseModel):
    vehicle_id: str
    brand: str
    model: str
    category: str
    price: float
    year: int
    specs: VehicleSpecsResponse
    features: List[str] = []
    tags: List[str] = []

# --- Chat API Routes ---

@router.post("/chat/new", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
async def create_chat_session(request: NewSessionRequest):
    """
    Create a new chat session.
    """
    session = await chat_service.create_session(request.phone_number)
    
    # Convert session to response model
    message_responses = [
        MessageResponse(
            message_id=msg.message_id,
            role=msg.role,
            content=msg.content,
            timestamp=msg.timestamp.isoformat()
        )
        for msg in session.messages
    ]
    
    return SessionResponse(
        session_id=session.session_id,
        profile_id=session.profile_id,
        phone_number=session.phone_number,
        messages=message_responses,
        stage=session.stage
    )


@router.get("/chat/{session_id}", response_model=SessionResponse)
async def get_chat_session(session_id: str = Path(..., description="The ID of the chat session")):
    """
    Get a chat session by ID.
    """
    session = chat_service.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Chat session {session_id} not found")
    
    # Convert session to response model
    message_responses = [
        MessageResponse(
            message_id=msg.message_id,
            role=msg.role,
            content=msg.content,
            timestamp=msg.timestamp.isoformat()
        )
        for msg in session.messages
    ]
    
    return SessionResponse(
        session_id=session.session_id,
        profile_id=session.profile_id,
        phone_number=session.phone_number,
        messages=message_responses,
        stage=session.stage
    )


@router.post("/chat/{session_id}/message", response_model=SessionResponse)
async def send_message(
    message: MessageRequest,
    session_id: str = Path(..., description="The ID of the chat session")
):
    """
    Send a message to a chat session and get a response.
    """
    # Check if session exists
    session = chat_service.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Chat session {session_id} not found")
    
    # Add the user message
    await chat_service.add_message(session_id, message.content, message.sender)
    
    # Generate a response
    await chat_service.generate_response(session_id)
    
    # Get the updated session
    session = chat_service.get_session(session_id)
    
    # Convert session to response model
    message_responses = [
        MessageResponse(
            message_id=msg.message_id,
            role=msg.role,
            content=msg.content,
            timestamp=msg.timestamp.isoformat()
        )
        for msg in session.messages
    ]
    
    return SessionResponse(
        session_id=session.session_id,
        profile_id=session.profile_id,
        phone_number=session.phone_number,
        messages=message_responses,
        stage=session.stage
    )


# --- User Profile API Routes ---

@router.get("/profile/{profile_id}")
async def get_profile(profile_id: str = Path(..., description="The ID of the user profile")):
    """
    Get a user profile by ID.
    """
    profile = profile_service.get_profile_by_id(profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail=f"Profile {profile_id} not found")
    
    return {
        "profile_id": profile.profile_id,
        "phone_number": profile.phone_number,
        "age": profile.age,
        "user_title": profile.user_title,
        "name": profile.name,
        "target_driver": profile.target_driver,
        "expertise": profile.expertise,
        "family_size": profile.family_size,
        "price_sensitivity": profile.price_sensitivity,
        "residence": profile.residence,
        "parking_conditions": profile.parking_conditions,
        "tags": profile.tags,
        "connections": [conn.dict() for conn in profile.connections],
        "created_at": profile.created_at,
        "updated_at": profile.updated_at
    }


@router.patch("/profile/{profile_id}")
async def update_profile(
    update_data: ProfileUpdateRequest,
    profile_id: str = Path(..., description="The ID of the user profile")
):
    """
    Update a user profile.
    """
    profile = profile_service.update_profile(profile_id, update_data.dict(exclude_unset=True))
    if not profile:
        raise HTTPException(status_code=404, detail=f"Profile {profile_id} not found")
    
    return {
        "profile_id": profile.profile_id,
        "phone_number": profile.phone_number,
        "age": profile.age,
        "user_title": profile.user_title,
        "name": profile.name,
        "target_driver": profile.target_driver,
        "expertise": profile.expertise,
        "family_size": profile.family_size,
        "price_sensitivity": profile.price_sensitivity,
        "residence": profile.residence,
        "parking_conditions": profile.parking_conditions,
        "tags": profile.tags,
        "connections": [conn.dict() for conn in profile.connections],
        "created_at": profile.created_at,
        "updated_at": profile.updated_at
    }


@router.post("/profile/{profile_id}/connection")
async def add_connection(
    connection: ConnectionRequest,
    profile_id: str = Path(..., description="The ID of the user profile")
):
    """
    Add a connection to a user profile.
    """
    # First, check if there's a profile with this phone number
    connection_profile = profile_service.get_profile_by_phone(connection.connection_phone_number)
    
    if not connection_profile:
        # Create a new profile for the connection
        connection_profile = profile_service.create_profile(connection.connection_phone_number)
    
    # Add the connection to the user profile
    profile = profile_service.add_connection(
        profile_id,
        connection_profile.profile_id,
        connection.connection_id_relationship,
        connection.connection_phone_number
    )
    
    if not profile:
        raise HTTPException(status_code=404, detail=f"Profile {profile_id} not found")
    
    return {
        "profile_id": profile.profile_id,
        "phone_number": profile.phone_number,
        "age": profile.age,
        "user_title": profile.user_title,
        "name": profile.name,
        "target_driver": profile.target_driver,
        "expertise": profile.expertise,
        "family_size": profile.family_size,
        "price_sensitivity": profile.price_sensitivity,
        "residence": profile.residence,
        "parking_conditions": profile.parking_conditions,
        "tags": profile.tags,
        "connections": [conn.dict() for conn in profile.connections],
        "created_at": profile.created_at,
        "updated_at": profile.updated_at
    }


# --- Car Needs API Routes ---

@router.get("/needs/{profile_id}")
async def get_needs(profile_id: str = Path(..., description="The ID of the user profile")):
    """
    Get car needs for a user profile.
    """
    needs = needs_service.get_all_needs(profile_id)
    return {"profile_id": profile_id, "needs": needs}


@router.post("/needs/{profile_id}")
async def add_need(
    need: NeedRequest,
    profile_id: str = Path(..., description="The ID of the user profile")
):
    """
    Add a need to a user's car requirements.
    """
    needs = needs_service.add_need(
        profile_id,
        need.category,
        need.value,
        need.is_implicit
    )
    
    return {"profile_id": profile_id, "needs": needs.get_all_needs()}


@router.delete("/needs/{profile_id}/{category}")
async def remove_need(
    profile_id: str = Path(..., description="The ID of the user profile"),
    category: str = Path(..., description="The category of the need"),
    value: Optional[str] = Query(None, description="The value to remove (only needed for list categories)")
):
    """
    Remove a need from a user's car requirements.
    """
    needs = needs_service.remove_need(profile_id, category, value)
    if not needs:
        raise HTTPException(status_code=400, detail=f"Failed to remove need {category}")
    
    return {"profile_id": profile_id, "needs": needs.get_all_needs()}


# --- Vehicle API Routes ---

@router.get("/vehicles", response_model=List[VehicleResponse])
async def get_vehicles():
    """
    Get all vehicles.
    """
    vehicles = vehicle_service.get_all_vehicles()
    return vehicles


@router.get("/vehicles/{vehicle_id}", response_model=VehicleResponse)
async def get_vehicle(vehicle_id: str = Path(..., description="The ID of the vehicle")):
    """
    Get a vehicle by ID.
    """
    vehicle = vehicle_service.get_vehicle_by_id(vehicle_id)
    if not vehicle:
        raise HTTPException(status_code=404, detail=f"Vehicle {vehicle_id} not found")
    
    return vehicle


@router.get("/recommendations/{profile_id}", response_model=List[VehicleResponse])
async def get_recommendations(
    profile_id: str = Path(..., description="The ID of the user profile"),
    limit: int = Query(5, description="Maximum number of recommendations")
):
    """
    Get vehicle recommendations based on user needs.
    """
    needs = needs_service.get_all_needs(profile_id)
    recommendations = vehicle_service.recommend_vehicles(needs, limit)
    
    return recommendations 