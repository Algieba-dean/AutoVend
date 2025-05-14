import uuid
from datetime import datetime

class ChatSession:
    """Chat session model for AutoVend application"""
    
    def __init__(self, phone_number, profile=None):
        """Initialize a new chat session"""
        self.session_id = str(uuid.uuid4())
        self.phone_number = phone_number
        self.created_at = datetime.utcnow().isoformat()
        self.ended_at = None
        self.status = "active"
        self.profile = profile or {}
        self.stage = {
            "previous_stage": "",
            "current_stage": "welcome"
        }
        self.needs = {
            "explicit": {},
            "implicit": {}
        }
        self.reservation_info = {
            "test_driver": "",
            "reservation_date": "",
            "reservation_time": "",
            "reservation_location": "",
            "reservation_phone_number": "",
            "salesman": ""
        }
    
    def to_dict(self):
        """Convert the session to a dictionary"""
        return {
            "session_id": self.session_id,
            "created_at": self.created_at,
            "ended_at": self.ended_at,
            "status": self.status,
            "profile": self.profile,
            "stage": self.stage,
            "needs": self.needs,
            "reservation_info": self.reservation_info
        }
        
    def end_session(self):
        """End the chat session"""
        if self.status == "closed":
            return False
            
        self.status = "closed"
        self.ended_at = datetime.utcnow().isoformat()
        self.stage["previous_stage"] = self.stage["current_stage"]
        self.stage["current_stage"] = "farewell"
        return True


class ChatMessage:
    """Chat message model for AutoVend application"""
    
    def __init__(self, session_id, content, sender_type="user", sender_id=None):
        """Initialize a new chat message"""
        self.message_id = str(uuid.uuid4())
        self.session_id = session_id
        self.sender_type = sender_type  # "user" or "system"
        self.sender_id = sender_id or (str(uuid.uuid4()) if sender_type == "user" else "agent_123")
        self.content = content
        self.timestamp = datetime.utcnow().isoformat()
        self.status = "delivered"
    
    def to_dict(self):
        """Convert the message to a dictionary"""
        return {
            "message_id": self.message_id,
            "sender_type": self.sender_type,
            "sender_id": self.sender_id,
            "content": self.content,
            "timestamp": self.timestamp,
            "status": self.status
        }
        
    @staticmethod
    def create_system_response(session_id, content):
        """Create a system response message"""
        return ChatMessage(
            session_id=session_id,
            content=content,
            sender_type="system",
            sender_id="agent_123"
        ) 