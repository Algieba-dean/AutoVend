from flask import Blueprint, request, jsonify
from app.models.profile import UserProfile
from app.config import Config

profile_bp = Blueprint('profile', __name__)

@profile_bp.route('/api/profile/default', methods=['GET'])
def get_default_profile():
    """Get default user profile configuration"""
    return jsonify(UserProfile.get_default_profile()), 200

@profile_bp.route('/api/profile/<phone_number>', methods=['GET'])
def get_profile(phone_number):
    """Get user profile by phone number"""
    if phone_number not in Config.USER_PROFILES:
        return jsonify({"error": "Profile not found"}), 404
        
    return jsonify(Config.USER_PROFILES[phone_number].to_dict()), 200

@profile_bp.route('/api/profile', methods=['POST'])
def create_profile():
    """Create a new user profile"""
    data = request.get_json()
    
    if not data:
        return jsonify({"error": "No data provided"}), 400
        
    # Check if phone number already exists
    phone_number = data.get('phone_number', '')
    if phone_number in Config.USER_PROFILES:
        return jsonify({"error": "Phone number already exists"}), 409
        
    # Create and validate profile
    profile = UserProfile.from_dict(data)
    validation_errors = profile.validate()
    
    if validation_errors:
        return jsonify({
            "error": "Validation error",
            "details": validation_errors
        }), 400
        
    # Store profile
    Config.USER_PROFILES[phone_number] = profile
    
    return jsonify(profile.to_dict()), 201

@profile_bp.route('/api/profile/<phone_number>', methods=['PUT'])
def update_profile(phone_number):
    """Update an existing user profile"""
    if phone_number not in Config.USER_PROFILES:
        return jsonify({"error": "Profile not found"}), 404
        
    data = request.get_json()
    
    if not data:
        return jsonify({"error": "No data provided"}), 400
        
    # Ensure phone number in URL matches payload
    if 'phone_number' in data and data['phone_number'] != phone_number:
        return jsonify({"error": "Phone number in URL must match payload"}), 400
        
    # Update and validate profile
    profile = UserProfile.from_dict(data)
    validation_errors = profile.validate()
    
    if validation_errors:
        return jsonify({
            "error": "Validation error",
            "details": validation_errors
        }), 400
        
    # Update profile
    Config.USER_PROFILES[phone_number] = profile
    
    return jsonify(profile.to_dict()), 200 