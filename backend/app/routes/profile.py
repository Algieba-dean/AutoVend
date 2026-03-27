"""
User profile API routes.
"""

import logging

from fastapi import APIRouter, HTTPException

from app.models.schemas import UserProfile
from app.models.storage import FileStorage

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/profile", tags=["profile"])


@router.get("/default", response_model=UserProfile)
async def get_default_profile():
    """Get default empty profile template."""
    return UserProfile()


@router.get("/{phone_number}", response_model=UserProfile)
async def get_profile(phone_number: str):
    """Get a user profile by phone number."""
    profile = FileStorage.load_profile(phone_number)
    if profile is None:
        raise HTTPException(status_code=404, detail="Profile not found.")
    return profile


@router.post("", response_model=UserProfile, status_code=201)
async def create_profile(profile: UserProfile):
    """Create a new user profile."""
    if not profile.phone_number:
        raise HTTPException(status_code=400, detail="Phone number is required.")

    existing = FileStorage.load_profile(profile.phone_number)
    if existing is not None:
        raise HTTPException(status_code=409, detail="Profile already exists.")

    FileStorage.save_profile(profile.phone_number, profile)
    return profile


@router.put("/{phone_number}", response_model=UserProfile)
async def update_profile(phone_number: str, profile: UserProfile):
    """Update an existing user profile."""
    existing = FileStorage.load_profile(phone_number)
    if existing is None:
        raise HTTPException(status_code=404, detail="Profile not found.")

    # Merge: new non-empty values overwrite
    merged = existing.model_dump()
    for key, value in profile.model_dump().items():
        if value:
            merged[key] = value
    merged["phone_number"] = phone_number

    updated = UserProfile(**merged)
    FileStorage.save_profile(phone_number, updated)
    return updated


@router.delete("/{phone_number}")
async def delete_profile(phone_number: str):
    """Delete a user profile."""
    if not FileStorage.delete_profile(phone_number):
        raise HTTPException(status_code=404, detail="Profile not found.")
    return {"message": "Profile deleted.", "phone_number": phone_number}


@router.get("", response_model=list[str])
async def list_profiles():
    """List all profile phone numbers."""
    return FileStorage.list_profiles()
