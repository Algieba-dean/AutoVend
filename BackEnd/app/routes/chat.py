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
    if phone_number not in Config.USER_PROFILES:
        return jsonify({"error": "Invalid phone_number"}), 400
        
    # Create chat session
    profile = Config.USER_PROFILES[phone_number].to_dict()
    session = ChatSession(phone_number, profile)
    
    # Store session
    Config.CHAT_SESSIONS[session.session_id] = session
    
    # Create welcome message
    welcome_message = ChatMessage.create_system_response(
        session_id=session.session_id,
        content="Hi I'm AutoVend, your smart assistant! How can I assist you in finding your ideal vehicle today?"
    )
    
    # Store message
    if session.session_id not in Config.CHAT_MESSAGES:
        Config.CHAT_MESSAGES[session.session_id] = []
    Config.CHAT_MESSAGES[session.session_id].append(welcome_message)
    
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
    if session_id not in Config.CHAT_SESSIONS:
        return jsonify({"error": "Chat session not found"}), 404
        
    session = Config.CHAT_SESSIONS[session_id]
    
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
    if session_id not in Config.CHAT_MESSAGES:
        Config.CHAT_MESSAGES[session_id] = []
    Config.CHAT_MESSAGES[session_id].append(user_message)
    
    # Generate system response (this would be more complex in a real implementation)
    # Here we're just simulating a response based on the user's message
    response_content = generate_response(message_content, session)
    
    # Update session state based on message (simplified)
    # In a real implementation, this would involve NLP and state tracking
    update_session_state(session, message_content)
    
    # Create system response
    system_response = ChatMessage.create_system_response(
        session_id=session_id,
        content=response_content
    )
    
    # Store system response
    Config.CHAT_MESSAGES[session_id].append(system_response)
    
    # Prepare response
    response = {
        "message": user_message.to_dict(),
        "response": system_response.to_dict(),
        "profile": session.profile,
        "needs": session.needs,
        "stage": session.stage,
        "reservation_info": session.reservation_info
    }
    
    return jsonify(response), 200

@chat_bp.route('/api/chat/session/<session_id>/messages', methods=['GET'])
def get_chat_messages(session_id):
    """Get messages from a chat session"""
    # Check if session exists
    if session_id not in Config.CHAT_SESSIONS:
        return jsonify({"error": "Chat session not found"}), 404
        
    session = Config.CHAT_SESSIONS[session_id]
    
    # Get query parameters
    since_timestamp = request.args.get('since_timestamp', None)
    limit = int(request.args.get('limit', 50))
    
    # Get messages
    messages = Config.CHAT_MESSAGES.get(session_id, [])
    
    # Filter messages by timestamp if provided
    if since_timestamp:
        messages = [msg for msg in messages if msg.timestamp > since_timestamp]
    
    # Limit number of messages
    messages = messages[-limit:] if limit > 0 else messages
    
    # Prepare response
    response = {
        "messages": [msg.to_dict() for msg in messages],
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
    if session_id not in Config.CHAT_SESSIONS:
        return jsonify({"error": "Chat session not found"}), 404
        
    session = Config.CHAT_SESSIONS[session_id]
    
    # Check if session is already ended
    if session.status == "closed":
        return jsonify({"error": "Session already ended"}), 400
        
    # End session
    session.end_session()
    
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
            return "I'd be happy to help you find an electric SUV with good range. Tesla Model Y offers around 330 miles of range, while Ford Mustang Mach-E offers up to 300 miles. Would you like more information about these models or would you prefer other options?"
    
    if "range" in message.lower():
        session.needs["explicit"]["driving_range"] = "Above 800km"
        session.needs["implicit"]["energy_consumption_level"] = "Low"
    
    if "test drive" in message.lower() or "reservation" in message.lower():
        session.stage["previous_stage"] = session.stage["current_stage"] 
        session.stage["current_stage"] = "reservation4s"
        return "I'd be happy to help you schedule a test drive. Could you tell me which day works best for you?"
        
    if "confirm" in message.lower() and session.stage["current_stage"] == "reservation4s":
        session.stage["previous_stage"] = "reservation4s"
        session.stage["current_stage"] = "reservation_confirmation"
        # Set some dummy reservation info
        session.reservation_info["test_driver"] = session.profile.get("user_title", "")
        future_date = datetime.now().date() + timedelta(days=3)
        session.reservation_info["reservation_date"] = future_date.strftime("%Y-%m-%d")
        session.reservation_info["reservation_time"] = "14:00"
        session.reservation_info["reservation_location"] = "Tesla Beijing Haidian Store"
        session.reservation_info["reservation_phone_number"] = session.profile.get("phone_number", "")
        session.reservation_info["salesman"] = "David Chen"
        
        return f"Great! I've confirmed your test drive for {session.reservation_info['reservation_date']} at {session.reservation_info['reservation_time']} at {session.reservation_info['reservation_location']}. Your assigned salesperson will be {session.reservation_info['salesman']}. Is there anything else I can help you with?"
    
    # Default response if no specific triggers are matched
    return "Thank you for sharing that information. Could you tell me more about your specific requirements or preferences for your ideal vehicle?"

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