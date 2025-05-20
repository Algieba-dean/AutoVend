from flask import Blueprint, request, jsonify
from app.models.test_drive import TestDrive
from app.config import Config
from datetime import datetime

test_drive_bp = Blueprint("test_drive", __name__)

@test_drive_bp.route("/api/test-drive", methods=["POST"])
def create_test_drive():
    """Creates a new test drive reservation"""
    data=request.get_json()
    test_drive_info = data.get("test_drive_info","")
    
    if not test_drive_info:
        return jsonify({"error": "Test drive information is required"}), 400
    
    # Validate required fields
    required_fields = [
        "test_driver",
        "reservation_date",
        "selected_car_model", 
        "reservation_time",
        "reservation_location",
        "reservation_phone_number", 
        "salesman"
    ]
    
    missing_fields = [field for field in required_fields if field not in test_drive_info or not test_drive_info[field]]
    if missing_fields:
        return jsonify({
            "error": "Validation error", 
            "details": [f"Missing required field: {field}" for field in missing_fields]
        }), 400
    
    # Check if reservation already exists with this phone number
    existing = Config.storage.get_test_drive_by_phone_number(test_drive_info["reservation_phone_number"])
    if existing:
        return jsonify({
            "error": "A test drive reservation already exists for this phone number"
        }), 409
    
    # Create test drive reservation
    test_drive = TestDrive(
        test_driver=test_drive_info["test_driver"],
        reservation_date=test_drive_info["reservation_date"],
        selected_car_model=test_drive_info["selected_car_model"],
        reservation_time=test_drive_info["reservation_time"],
        reservation_location=test_drive_info("reservation_location"),
        reservation_phone_number=test_drive_info["reservation_phone_number"],
        salesman=test_drive_info["salesman"],
        status=test_drive_info.get("status", "Pending")
    )
    
    # Save test drive
    Config.storage.save_test_drive(test_drive.convert_to_dict())
    
    return jsonify({
        "test_drive_info": test_drive.test_drive_info,
        "created_at": test_drive.created_at,
        "update_at" : test_drive.updated_at
    }), 201

@test_drive_bp.route("/api/test-drive/<reservation_phone_number>", methods=["GET"])
def get_test_drive(reservation_phone_number):
    """Retrieves details of a specific test drive reservation"""
    # Get test drive reservation
    test_drive_data = Config.storage.get_test_drive_by_phone_number(reservation_phone_number)
    if not test_drive_data:
        return jsonify({"error": "Test drive reservation not found"}), 404
    
    return jsonify(test_drive_data), 200

@test_drive_bp.route("/api/test-drive/<reservation_phone_number>", methods=["PUT"])
def update_test_drive(reservation_phone_number):
    """Updates an existing test drive reservation"""
    data = request.get_json()
    updata_drive_data = data["test_drive_info"]

    if not updata_drive_data:
        return jsonify({"error": "Update test drive information is required"}), 400
    
    # Get test drive reservation
    test_drive_data = Config.storage.get_test_drive_by_phone(reservation_phone_number)
    if not test_drive_data:
        return jsonify({"error": "Test drive reservation not found"}), 404
    
    # Create model instance from data
    test_drive = TestDrive.created_from_dict(test_drive_data)
    
    # Update with new information
    test_drive.update(updata_drive_data)
    
    # Save updated test drive
    Config.storage.update_test_drive(test_drive.convert_to_dict())
    
    return jsonify({
        "created_at": test_drive.created_at,
        "updated_at": test_drive.updated_at,
        "test_drive_info": test_drive.test_drive_info
    }), 200

@test_drive_bp.route("/api/test-drive/<reservation_phone_number>", methods=["DELETE"])
def delete_test_drive(reservation_phone_number):
    """Deletes a test drive reservation by phone number"""
    # Delete test drive
    Config.storage.delete_test_drive_by_phone_number(reservation_phone_number)
    
    return jsonify({
        "message": "Test drive reservation deleted successfully",
        "reservation_phone_number": reservation_phone_number
    }), 200

@test_drive_bp.route("/api/test-drive", methods=["GET"])
def list_test_drives():
    """Retrieves a list of test drive reservations with optional filtering"""
    # Get query parameters
    status = request.args.get("status")
    from_date = request.args.get("from_date")
    to_date = request.args.get("to_date")
    limit = int(request.args.get("limit", 20))
    offset = int(request.args.get("offset", 0))
    
    # Get all test drives
    test_drives = Config.storage.get_all_test_drives()
    
    # Apply filters
    filtered_drives = []
    for drive in test_drives:
        if status and drive["test_drive_info"]["status"] != status:
            continue
        if from_date < drive["test_drive_info"]["reservation_date"] < to_date:
            continue
        filtered_drives.append(drive)
    
    # Apply pagination
    total_count = len(filtered_drives)
    paginated_drives = filtered_drives[offset:offset + limit]
    
    return jsonify({
        "total_count": total_count,
        "limit": limit,
        "offset": offset,
        "test_drives": paginated_drives
    }), 200 