from flask import Blueprint, request, jsonify
from app.managers.profile_manager import ProfileManager

profile_bp = Blueprint("profile", __name__)

@profile_bp.route("/api/profile/default", methods=["GET"])
def get_default_profile():
    """Get default user profile configuration"""
    profile_data = ProfileManager.get_default_profile()
    return jsonify(profile_data), 200

@profile_bp.route("/api/profile/<phone_number>", methods=["GET"])
def get_profile(phone_number):
    """Get user profile by phone number"""
    profile_data, error = ProfileManager.get_profile(phone_number)
    if error:
        return jsonify({"error": error}), 404
    return jsonify(profile_data), 200

@profile_bp.route("/api/profile", methods=["POST"])
def create_profile():
    """Create a new user profile"""
    data = request.get_json()
    
    if not data:
        return jsonify({"error": "No data provided"}), 400
        
    profile_data, error, validation_errors = ProfileManager.create_profile(data)
    if error:
        if error == "From connection":
            return jsonify(profile_data), 200
        if error == "Phone number already exists":
            return jsonify({"error": error}), 409
        if validation_errors:
            return jsonify({
                "error": error,
                "details": validation_errors
            }), 400
        return jsonify({"error": error}), 400
        
    return jsonify(profile_data), 201

@profile_bp.route("/api/profile/<phone_number>", methods=["PUT"])
def update_profile(phone_number):
    """Update an existing user profile"""
    data = request.get_json()
    
    if not data:
        return jsonify({"error": "No data provided"}), 400
        
    profile_data, error, validation_errors = ProfileManager.update_profile(phone_number, data)
    if error:
        if error == "Profile not found":
            return jsonify({"error": error}), 404
        if validation_errors:
            return jsonify({
                "error": error,
                "details": validation_errors
            }), 400
        return jsonify({"error": error}), 400
        
    return jsonify(profile_data), 200

@profile_bp.route("/api/profile/<phone_number>", methods=["DELETE"])
def delete_profile(phone_number):
    """Delete a user profile"""
    success, error = ProfileManager.delete_profile(phone_number)
    if not success:
        if error == "Profile not found":
            return jsonify({"error": error}), 404
        return jsonify({"error": error}), 400
    return jsonify({"message": "Profile deleted successfully"}), 200 