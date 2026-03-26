"""
Test drive reservation API routes.
"""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException

from app.models.schemas import TestDriveRequest, TestDriveResponse
from app.models.storage import FileStorage

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/test-drive", tags=["test-drive"])


@router.post("", response_model=TestDriveResponse, status_code=201)
async def create_test_drive(request: TestDriveRequest):
    """Create a test drive reservation."""
    if not request.phone_number:
        raise HTTPException(status_code=400, detail="Phone number is required.")

    data = {
        "phone_number": request.phone_number,
        "reservation": {
            "test_driver": request.test_driver,
            "reservation_date": request.reservation_date,
            "reservation_time": request.reservation_time,
            "reservation_location": request.reservation_location,
            "reservation_phone_number": request.phone_number,
            "salesman": request.salesman,
        },
        "car_model": request.car_model,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    FileStorage.save_test_drive(request.phone_number, data)

    return TestDriveResponse(**data)


@router.get("/{phone_number}", response_model=TestDriveResponse)
async def get_test_drive(phone_number: str):
    """Get a test drive reservation."""
    data = FileStorage.load_test_drive(phone_number)
    if data is None:
        raise HTTPException(status_code=404, detail="Test drive not found.")
    return TestDriveResponse(**data)


@router.put("/{phone_number}", response_model=TestDriveResponse)
async def update_test_drive(phone_number: str, request: TestDriveRequest):
    """Update a test drive reservation."""
    existing = FileStorage.load_test_drive(phone_number)
    if existing is None:
        raise HTTPException(status_code=404, detail="Test drive not found.")

    # Merge non-empty fields
    reservation = existing.get("reservation", {})
    for key in ["test_driver", "reservation_date", "reservation_time",
                "reservation_location", "salesman"]:
        new_val = getattr(request, key, "")
        if new_val:
            reservation[key] = new_val

    existing["reservation"] = reservation
    if request.car_model:
        existing["car_model"] = request.car_model

    FileStorage.save_test_drive(phone_number, existing)
    return TestDriveResponse(**existing)


@router.delete("/{phone_number}")
async def delete_test_drive(phone_number: str):
    """Delete a test drive reservation."""
    if not FileStorage.delete_test_drive(phone_number):
        raise HTTPException(status_code=404, detail="Test drive not found.")
    return {"message": "Test drive deleted.", "phone_number": phone_number}


@router.get("", response_model=list[str])
async def list_test_drives():
    """List all test drive phone numbers."""
    return FileStorage.list_test_drives()
