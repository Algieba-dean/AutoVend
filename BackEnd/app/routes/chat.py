from flask import Blueprint, request, jsonify
from app.models.chat import ChatSession, ChatMessage
from app.managers.dialog_manager import DialogManager
from app.config import Config
import uuid
from datetime import datetime

chat_bp = Blueprint("chat", __name__)
dialog_manager = DialogManager()

@chat_bp.route("/api/chat/session", methods=["POST"])
def start_chat_session():
    """Start a new chat session"""
    data = request.get_json()
    if not data or "phone_number" not in data:
        return jsonify({"error": "Phone number is required"}), 400
        
    phone_number = data["phone_number"]
    
    # Get user profile
    profile = Config.storage.get_profile(phone_number)
    if not profile:
        return jsonify({"error": "User profile not found"}), 404
        
    # Create new session
    session_id = str(uuid.uuid4())
    session = ChatSession(phone_number, profile)
    
    # Save session
    Config.storage.save_session(session_id, session.to_dict())
    
    # Generate welcome message
    welcome_message = dialog_manager.get_welcome_message(session_id, {
        "stage": "welcome",
        "profile": profile,
        "needs": {},
        "matched_car_models": [],
        "reservation_info": {}
    })
    welcome_message = ChatMessage(
        session_id=session_id,
        content=welcome_message["response"]["content"],
        sender_type="system",
        sender_id="AutoVend"
    )
    
    # Save welcome message
    Config.storage.save_message(session_id, welcome_message.to_dict())
    
    return jsonify({
        "session_id": session_id,
        "created_at": session.created_at,
        "status": session.status,
        "message": welcome_message.to_dict(),
        "profile": profile,
        "matched_car_models":session.matched_car_models,
        "needs": session.needs,
        "stage": {
            "previous_stage": session.stage,
            "current_stage": "welcome"
        },
        "reservation_info": session.reservation_info,
    }), 201

@chat_bp.route("/api/chat/message", methods=["POST"])
def send_chat_message():
    """Send a message in an active chat session"""
    data = request.get_json()
    if not data or "session_id" not in data or "message" not in data:
        return jsonify({"error": "Session ID and message are required"}), 400
        
    session_id = data["session_id"]
    message = data["message"]
    
    # Get session
    session_data = Config.storage.get_session(session_id)
    if not session_data:
        return jsonify({"error": "Chat session not found"}), 404
        
    session = ChatSession.from_dict(session_data)
    if session.status != "active":
        return jsonify({"error": "Chat session is not active"}), 400
        
    # Process message through dialog manager
    response = dialog_manager.process_message(session_id, message, {
        "stage": session.stage,
        "needs": session.needs,
        "profile": session.profile,
        "matched_car_models": session.matched_car_models,
        "reservation_info": session.reservation_info
    })
    
    # Update session with new information
    session.stage = response["stage"]["current_stage"]
    session.needs = response["needs"]
    session.matched_car_models = response["matched_car_models"]
    session.reservation_info = response["reservation_info"]
    
    # Save updated session
    Config.storage.save_session(session_id, session.to_dict())
    
    # Save user message
    user_message = ChatMessage(
        session_id=session_id,
        content=message,
        sender_type="user",
        sender_id=session.phone_number
    )
    Config.storage.save_message(session_id, user_message.to_dict())
    
    # Save system response
    system_message = ChatMessage(
        session_id=session_id,
        content=response["response"]["content"],
        sender_type="system",
        sender_id="AutoVend"
    )
    Config.storage.save_message(session_id, system_message.to_dict())
    
    return jsonify(response), 200

@chat_bp.route("/api/chat/session/<session_id>/messages", methods=["GET"])
def get_chat_messages(session_id):
    """Get messages from a chat session"""
    # Get session
    session_data = Config.storage.get_session(session_id)
    if not session_data:
        return jsonify({"error": "Chat session not found"}), 404
        
    session = ChatSession.from_dict(session_data)
    
    # Get messages
    messages = Config.storage.get_messages(session_id)
    
    return jsonify({
        "messages": messages,
        "stage": {
            "previous_stage": session.stage,
            "current_stage": session.stage
        },
        "needs": session.needs,
        "matched_car_models": session.matched_car_models,
        "reservation_info": session.reservation_info
    }), 200

@chat_bp.route("/api/chat/session/<session_id>/end", methods=["PUT"])
def end_chat_session(session_id):
    """End a chat session"""
    # Get session
    session_data = Config.storage.get_session(session_id)
    if not session_data:
        return jsonify({"error": "Chat session not found"}), 404
        
    session = ChatSession.from_dict(session_data)
    session.end_session()
    
    # Save updated session
    Config.storage.save_session(session_id, session.to_dict())
    
    # End session in dialog manager
    dialog_manager.end_session(session_id)
    
    return jsonify({
        "status": session.status,
        "ended_at": session.ended_at,
        "stage": {
            "previous_stage": session.stage,
            "current_stage": session.stage
        },
        "needs": session.needs,
        "matched_car_models": session.matched_car_models,
        "reservation_info": session.reservation_info
    }), 200 