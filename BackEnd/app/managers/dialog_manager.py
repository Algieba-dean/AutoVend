from typing import Dict, List, Optional, Any
from datetime import datetime, UTC
import json
from functools import lru_cache
from app.models.chat import ChatSession
from app.models.mock_message import MockMessage
from app.config import Config

class DialogManager:
    """Manager class for handling dialog interactions"""
    
    def __init__(self):
        """Initialize the dialog manager"""
        self.active_sessions = {}
        self.response_cache = {}
    
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
        # if not session_data:
        #     return jsonify({"error": "Chat session not found"}), 404
            
        session = ChatSession.from_dict(session_data)
        # Update session stage based on message content
        current_stage = context["stage"]
        previous_stage = current_stage
        
        # Simple stage transition logic
        if current_stage == "welcome":
            context["stage"] = "profile_analysis"
        elif current_stage == "profile_analysis" and "car" in message.lower():
            context["stage"] = "needs_analysis"
        elif current_stage == "needs_analysis" and "model" in message.lower():
            context["stage"] = "car_selection_confirmation"
            # Mock car model matching
            context["matched_car_models"] = ["Tesla Model Y", "Ford Mustang Mach-E"]
        elif current_stage == "car_selection_confirmation" and "test" in message.lower():
            context["stage"] = "reservation4s"
        elif current_stage == "reservation4s" and any(word in message.lower() for word in ["yes", "sure", "ok"]):
            context["stage"] = "reservation_confirmation"
            # Mock reservation info
            context["reservation_info"].update({
                "reservation_date": "2024-03-20",
                "reservation_time": "14:00",
                "reservation_location": "Main Showroom"
            })
        
        context["previous_stage"] = previous_stage
        
        # Generate response using MockMessage
        return MockMessage.generate_response(context["stage"], context)
    
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