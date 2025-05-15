from flask import Blueprint, request, jsonify
from datetime import datetime, timedelta
from app.models.chat import ChatSession, ChatMessage
from app.config import Config

chat_bp = Blueprint('chat', __name__)

@chat_bp.route('/api/chat/session', methods=['POST'])
def start_chat_session():
    """Start a new chat session"""
    data = request.get_json()
    
    if not data:
        return jsonify({"error": "No data provided"}), 400
        
    phone_number = data.get('phone_number', '')
    if not phone_number:
        return jsonify({"error": "Phone number is required"}), 400
        
    # Check if user profile exists
    profile_data = Config.storage.get_profile(phone_number)
    if not profile_data:
        return jsonify({"error": "Invalid phone_number"}), 400
        
    # Create chat session
    session = ChatSession(phone_number, profile_data)
    
    # Store session
    Config.storage.save_session(session.session_id, session.to_dict())
    
    # Create welcome message
    welcome_message = ChatMessage.create_system_response(
        session_id=session.session_id,
        content="Hi I'm AutoVend, your smart assistant! How can I assist you in finding your ideal vehicle today?"
    )
    
    # Store message
    Config.storage.save_message(session.session_id, welcome_message.to_dict())
    
    # Prepare response
    response = session.to_dict()
    response['message'] = welcome_message.to_dict()
    
    return jsonify(response), 201

@chat_bp.route('/api/chat/message', methods=['POST'])
def send_chat_message():
    """Send a message in an active chat session"""
    data = request.get_json()
    
    if not data:
        return jsonify({"error": "No data provided"}), 400
        
    session_id = data.get('session_id', '')
    message_content = data.get('message', '')
    
    if not session_id:
        return jsonify({"error": "Session ID is required"}), 400
        
    if not message_content:
        return jsonify({"error": "Message cannot be empty"}), 400
        
    # Check if session exists
    session_data = Config.storage.get_session(session_id)
    if not session_data:
        return jsonify({"error": "Chat session not found"}), 404
        
    session = ChatSession.from_dict(session_data)
    
    # Check if session is active
    if session.status != "active":
        return jsonify({"error": "Chat session is not active"}), 400
        
    # Create user message
    user_message = ChatMessage(
        session_id=session_id,
        content=message_content,
        sender_type="user"
    )
    
    # Store user message
    Config.storage.save_message(session_id, user_message.to_dict())
    
    # Generate system response
    response_content = generate_response(message_content, session)
    
    # Update session state based on message
    update_session_state(session, message_content)
    
    # Create system response
    system_response = ChatMessage.create_system_response(
        session_id=session_id,
        content=response_content
    )
    
    # Store system response
    Config.storage.save_message(session_id, system_response.to_dict())
    
    # Update session
    Config.storage.save_session(session_id, session.to_dict())
    
    # Prepare response
    response = {
        "message": user_message.to_dict(),
        "response": system_response.to_dict(),
        "profile": session.profile,
        "needs": session.needs,
        "stage": session.stage,
        "reservation_info": session.reservation_info,
        "matched_car_models": session.matched_car_models,
    }
    
    return jsonify(response), 200

@chat_bp.route('/api/chat/session/<session_id>/messages', methods=['GET'])
def get_chat_messages(session_id):
    """Get messages from a chat session"""
    # Check if session exists
    session_data = Config.storage.get_session(session_id)
    if not session_data:
        return jsonify({"error": "Chat session not found"}), 404
        
    session = ChatSession.from_dict(session_data)
    
    # Get query parameters
    since_timestamp = request.args.get('since_timestamp', None)
    limit = int(request.args.get('limit', 50))
    
    # Get messages
    messages = Config.storage.get_messages(session_id, limit)
    
    # Filter messages by timestamp if provided
    if since_timestamp:
        messages = [msg for msg in messages if msg['timestamp'] > since_timestamp]
    
    # Prepare response
    response = {
        "messages": messages,
        "has_more": len(messages) >= limit,
        "profile": session.profile,
        "needs": session.needs,
        "stage": session.stage,
        "reservation_info": session.reservation_info
    }
    
    return jsonify(response), 200

@chat_bp.route('/api/chat/session/<session_id>/end', methods=['PUT'])
def end_chat_session(session_id):
    """End a chat session"""
    # Check if session exists
    session_data = Config.storage.get_session(session_id)
    if not session_data:
        return jsonify({"error": "Chat session not found"}), 404
        
    session = ChatSession.from_dict(session_data)
    
    # Check if session is already ended
    if session.status == "closed":
        return jsonify({"error": "Session already ended"}), 400
        
    # End session
    session.end_session()
    
    # Update session
    Config.storage.save_session(session_id, session.to_dict())
    
    # Prepare response
    response = session.to_dict()
    
    return jsonify(response), 200

# Helper functions to simulate chat behavior

def generate_response(message, session):
    """Generate a response based on the user's message and session state"""
    # This is a simplified response generator
    # In a real implementation, this would use NLP, a dialogue manager, etc.
    
    stage = session.stage["current_stage"]
    
    if stage == "welcome":
        return "I'd be happy to help you find your ideal car. Could you tell me what type of vehicle you're interested in?"
    
    if "electric" in message.lower() or "ev" in message.lower():
        # Update session needs
        session.needs["explicit"]["powertrain_type"] = "Battery Electric Vehicle"
        
        if "suv" in message.lower():
            session.needs["explicit"]["vehicle_category_bottom"] = "Compact SUV"
            session.matched_car_models = ["Tesla Model Y", "Ford Mustang Mach-E"]
            return "I'd be happy to help you find an electric SUV with good range. Tesla Model Y offers around 330 miles of range, while Ford Mustang Mach-E offers up to 300 miles. Would you like more information about these models or would you prefer other options?"
    
    if "range" in message.lower():
        session.needs["explicit"]["driving_range"] = "Above 800km"
        session.needs["implicit"]["energy_consumption_level"] = "Low"
    
    if "test drive" in message.lower() or "reservation" in message.lower():
        session.stage["previous_stage"] = session.stage["current_stage"] 
        session.stage["current_stage"] = "reservation4s"
        return "I'd be happy to help you schedule a test drive. Could you tell me which day works best for you?"
    
    return "I understand you're interested in a car. Could you tell me more about your preferences and requirements?"

def update_session_state(session, message):
    """Update the session state based on the message content"""
    # This is a simplified state tracker
    # In a real implementation, this would use NLP to identify intents, entities, etc.
    
    current_stage = session.stage["current_stage"]
    
    # Simple stage transitions
    if current_stage == "welcome":
        session.stage["previous_stage"] = "welcome"
        session.stage["current_stage"] = "needs_analysis"
    elif current_stage == "needs_analysis" and "model" in message.lower():
        session.stage["previous_stage"] = "needs_analysis"
        session.stage["current_stage"] = "car_selection_confirmation"
    
    # Extract and update expertise level (simplified)
    if "experience" in message.lower() or "knowledge" in message.lower():
        # Update expertise in profile
        if "beginner" in message.lower() or "new" in message.lower():
            session.profile["expertise"] = "2"
        elif "expert" in message.lower() or "advanced" in message.lower():
            session.profile["expertise"] = "8" 