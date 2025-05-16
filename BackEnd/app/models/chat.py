import uuid
from datetime import datetime, UTC

class ChatSession:
    """Chat session model for AutoVend application"""
    
    def __init__(self, phone_number, profile=None):
        """Initialize a new chat session"""
        self.session_id = str(uuid.uuid4())
        self.phone_number = phone_number
        self.created_at = datetime.now(UTC).isoformat()
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
        self.matched_car_models = []
        self.reservation_info = {
            "test_driver": "",
            "reservation_date": "",
            "reservation_time": "",
            "reservation_location": "",
            "reservation_phone_number": "",
            "salesman": ""
        }
    
    @classmethod
    def from_dict(cls, data):
        """Create a ChatSession instance from a dictionary"""
        session = cls(data.get('phone_number', ''), data.get('profile', {}))
        session.session_id = data.get('session_id', session.session_id)
        session.created_at = data.get('created_at', session.created_at)
        session.ended_at = data.get('ended_at', session.ended_at)
        session.status = data.get('status', session.status)
        session.stage = data.get('stage', session.stage)
        session.needs = data.get('needs', session.needs)
        session.matched_car_models = data.get('matched_car_models', session.matched_car_models)
        session.reservation_info = data.get('reservation_info', session.reservation_info)
        return session
    
    def to_dict(self):
        """Convert the session to a dictionary"""
        return {
            "session_id": self.session_id,
            "phone_number": self.phone_number,
            "created_at": self.created_at,
            "ended_at": self.ended_at,
            "status": self.status,
            "profile": self.profile,
            "stage": self.stage,
            "needs": self.needs,
            "matched_car_models": self.matched_car_models,
            "reservation_info": self.reservation_info
        }
        
    def end_session(self):
        """End the chat session"""
        if self.status == "closed":
            return False
            
        self.status = "closed"
        self.ended_at = datetime.now(UTC).isoformat()
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
        self.sender_id = sender_id or (str(uuid.uuid4()) if sender_type == "user" else "AutoVend")
        self.content = content
        self.timestamp = datetime.now(UTC).isoformat()
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
            sender_id="AutoVend"
        ) 