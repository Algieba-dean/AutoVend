"""
Chat session and message data models.
"""
from datetime import datetime
from typing import Dict, List, Optional, Any
from uuid import uuid4
from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    """
    Represents a single message in a chat session.
    """
    message_id: str = Field(default_factory=lambda: str(uuid4()))
    role: str  # 'user', 'system', 'assistant'
    content: str
    timestamp: datetime = Field(default_factory=datetime.now)

    class Config:
        json_schema_extra = {
            "example": {
                "message_id": "a1b2c3d4-e5f6-7a8b-9c0d-1e2f3a4b5c6d",
                "role": "assistant",
                "content": "Hello! How can I assist you with your car purchase today?",
                "timestamp": "2023-11-20T15:30:45.123456"
            }
        }


class ChatSession(BaseModel):
    """
    Represents a chat session with a user.
    """
    session_id: str = Field(default_factory=lambda: str(uuid4()))
    profile_id: Optional[str] = None
    phone_number: Optional[str] = None
    messages: List[ChatMessage] = []
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    stage: str = "welcome"  # welcome, needs_analysis, confirmation, dealership
    context: Dict[str, Any] = {}
    
    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "f8d7e9c3-5b2a-4c1a-8f9e-3a6b2c5d4e7f",
                "profile_id": "e9f8d7c6-5b4a-3c2a-1f9e-7a6b4c5d2e3f",
                "phone_number": "13800138000",
                "messages": [],
                "created_at": "2023-11-20T15:30:45.123456",
                "updated_at": "2023-11-20T15:30:45.123456",
                "stage": "welcome",
                "context": {}
            }
        }
    
    def add_message(self, role: str, content: str) -> ChatMessage:
        """
        Add a new message to the chat session.
        
        Args:
            role: The role of the message sender ('user', 'system', 'assistant')
            content: The content of the message
            
        Returns:
            The created ChatMessage object
        """
        message = ChatMessage(role=role, content=content)
        self.messages.append(message)
        self.updated_at = datetime.now()
        return message
    
    def update_stage(self, new_stage: str) -> None:
        """
        Update the stage of the chat session.
        
        Args:
            new_stage: The new stage to set
        """
        self.stage = new_stage
        self.updated_at = datetime.now()
    
    def get_messages_for_api(self) -> List[Dict[str, Any]]:
        """
        Get messages in the format expected by the OpenAI API.
        
        Returns:
            List of message dictionaries in the format expected by OpenAI API
        """
        return [{"role": msg.role, "content": msg.content} for msg in self.messages] 