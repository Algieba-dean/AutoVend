from typing import Dict, List, Optional, Any
from datetime import datetime, UTC
import json
from functools import lru_cache
from app.models.chat import ChatSession
from app.models.mock_message import MockMessage
from app.config import Config
from app.models.ai_model_message import AiModelMessage

class DialogManager:
    """Manager class for handling dialog interactions"""
    
    def __init__(self):
        """Initialize the dialog manager"""
        self.active_sessions = {}
        self.response_cache = {}
        self.ai_model_message = AiModelMessage()
        self.is_initalized = False
    
    def process_message(self, session_id: str, message: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Process incoming message and generate response"""
        # Get or create session context
        initial_context = {
            "stage": "welcome",
            "needs": {"explicit": {}, "implicit": {}},
            "matched_car_models": [],
            "profile": context["profile"],
            "reservation_info": {
                "test_driver": "",
                "reservation_date": "",
                "reservation_time": "",
                "reservation_location": "",
                "reservation_phone_number": "",
                "salesman": ""
            }
        }
        session_context = self.active_sessions.get(session_id, initial_context)
        
        # Update session context with new message
        session_context["last_message"] = message
        session_context["last_update"] = datetime.now(UTC).isoformat()
        
        # Generate response
        response = self._generate_response(session_id, message, session_context)
        
        # Update session context with response
        session_context["last_response"] = response
        self.active_sessions[session_id] = session_context
        
        # Return response with updated session context
        return {
            "message": {
                "message_id": f"msg_{datetime.now().timestamp()}",
                "sender_type": "user",
                "sender_id": session_id,
                "content": message,
                "timestamp": datetime.now(UTC).isoformat(),
                "status": "delivered"
            },
            "response": response,
            "stage": {
                "previous_stage": session_context.get("previous_stage", ""),
                "current_stage": session_context["stage"]
            },
            "needs": session_context["needs"],
            "matched_car_models": session_context["matched_car_models"],
            "reservation_info": session_context["reservation_info"]
        }
    
    def _generate_response(self, session_id: str, message: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate response for the message"""

        session_data = Config.storage.get_session(session_id)
        if not self.is_initalized:
            message = ""
            self.is_initalized = True
        response, current_stage_info, current_profile, current_needs, current_matched_car_models, current_reservation_info = self.ai_model_message.generate_response(message,context["stage"],context["profile"],context["needs"],context["matched_car_models"],context["reservation_info"])
        context["stage"] = current_stage_info["current_stage"]
        context["profile"] = current_profile
        context["needs"] = current_needs
        context["matched_car_models"] = current_matched_car_models
        context["reservation_info"] = current_reservation_info
        
        # Generate response using MockMessage
        return {
            "message_id": f"msg_{datetime.now().timestamp()}",
            "sender_type": "system",
            "sender_id": "AutoVend",
            "content": response,
            "timestamp": datetime.now().isoformat(),
            "status": "delivered"
        } 
    
    def get_session_context(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session context by ID"""
        return self.active_sessions.get(session_id)
    
    def end_session(self, session_id: str) -> bool:
        """End a chat session"""
        if session_id in self.active_sessions:
            del self.active_sessions[session_id]
            return True
        return False
    
    
    def get_welcome_message(self, session_id: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Get welcome message"""
        # Get welcome message from session context
        message = "welcome"
        
        return self.process_message(session_id, message, context)
    
    def clear_cache(self, session_id: Optional[str] = None):
        """Clear response cache for a session or all sessions"""
        if session_id:
            # Clear specific session cache
            keys_to_remove = [k for k in self.response_cache.keys() if k.startswith(f"{session_id}:")]
            for key in keys_to_remove:
                del self.response_cache[key]
        else:
            # Clear all cache
            self.response_cache.clear() 