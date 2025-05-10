import os
import json
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import uuid
import logging

from app.models import UserProfile, ChatSession, ChatMessage, CarNeeds, CarNeed
from app.utils.nlp_utils import extract_profile_info, extract_car_needs, extract_implicit_needs
from app.config import USER_PROFILES_DIR, SESSIONS_DIR, SYSTEM_PROMPTS
from app.services.openai_service import openai_service
from app.services.profile_service import profile_service
from app.services.needs_service import needs_service

# Configure logging
logger = logging.getLogger(__name__)

class ChatService:
    """
    Service for managing chat sessions and messages.
    """
    
    async def create_session(self, phone_number: Optional[str] = None) -> ChatSession:
        """
        Create a new chat session.
        
        Args:
            phone_number: Optional phone number for the user
            
        Returns:
            The created ChatSession object
        """
        # Create new session
        session = ChatSession(
            session_id=str(uuid.uuid4()),
            phone_number=phone_number
        )
        session.update_stage("welcome")
        
        # Try to associate with an existing profile
        if phone_number:
            profile = profile_service.get_profile_by_phone(phone_number)
            if profile:
                session.profile_id = profile.profile_id
        
        # Save the session
        self._save_session(session)
        
        # Add initial system message
        welcome_prompt = SYSTEM_PROMPTS["welcome"]
        
        # If we have a profile, personalize the welcome message
        if session.profile_id:
            profile = profile_service.get_profile_by_id(session.profile_id)
            if profile and profile.name:
                greeting = f"Hello {profile.user_title} {profile.name}, welcome back to AutoVend! How can I assist you with your car purchase today?"
                session.add_message("assistant", greeting)
            else:
                greeting = "Hello! Welcome to AutoVend. How can I assist you with your car purchase today?"
                session.add_message("assistant", greeting)
        else:
            greeting = "Hello! Welcome to AutoVend. How can I assist you with your car purchase today?"
            session.add_message("assistant", greeting)
        
        # Save session again with welcome message
        self._save_session(session)
        
        return session
    
    def get_session(self, session_id: str) -> Optional[ChatSession]:
        """
        Get a chat session by ID.
        
        Args:
            session_id: The ID of the session to retrieve
            
        Returns:
            The ChatSession object if found, None otherwise
        """
        try:
            filepath = os.path.join(SESSIONS_DIR, f"{session_id}.json")
            
            if not os.path.exists(filepath):
                return None
                
            with open(filepath, 'r') as f:
                data = json.load(f)
            
            # Create ChatSession instance
            session = ChatSession(
                session_id=data.get('session_id'),
                profile_id=data.get('profile_id'),
                phone_number=data.get('phone_number')
            )
            
            # Load messages
            for msg_data in data.get('messages', []):
                message = ChatMessage(
                    message_id=msg_data.get('message_id'),
                    role=msg_data.get('role'),
                    content=msg_data.get('content')
                )
                if 'timestamp' in msg_data:
                    message.timestamp = datetime.fromisoformat(msg_data.get('timestamp'))
                session.messages.append(message)
            
            # Set other fields
            if 'created_at' in data:
                session.created_at = datetime.fromisoformat(data.get('created_at'))
            if 'updated_at' in data:
                session.updated_at = datetime.fromisoformat(data.get('updated_at'))
            if 'stage' in data:
                session.stage = data.get('stage')
            if 'context' in data:
                session.context = data.get('context', {})
            
            return session
            
        except Exception as e:
            logger.error(f"Error retrieving chat session {session_id}: {str(e)}")
            return None
    
    async def add_message(self, session_id: str, content: str, role: str = "user") -> Optional[ChatMessage]:
        """
        Add a message to a chat session.
        
        Args:
            session_id: The ID of the session
            content: The content of the message
            role: The role of the message sender (usually 'user')
            
        Returns:
            The created ChatMessage object if successful, None otherwise
        """
        # Get the session
        session = self.get_session(session_id)
        if not session:
            logger.error(f"Session {session_id} not found")
            return None
        
        # Add the message
        message = session.add_message(role, content)
        
        # Process user message
        if role == "user":
            await self._process_user_message(session, content)
        
        # Save the session
        self._save_session(session)
        
        return message
    
    async def _process_user_message(self, session: ChatSession, content: str):
        """
        Process user message to extract information.
        
        Args:
            session: The chat session
            content: The message content
        """
        # Extract profile information
        profile_info = extract_profile_info(content)
        
        # Initialize or update user profile
        if session.profile_id:
            profile = profile_service.get_profile_by_id(session.profile_id)
            if profile:
                # Update existing profile with new information
                profile_service.update_profile(profile.profile_id, profile_info)
            else:
                # Create new profile
                profile = profile_service.create_profile(session.phone_number)
                profile_service.update_profile(profile.profile_id, profile_info)
                session.profile_id = profile.profile_id
        else:
            # Create new profile
            profile = profile_service.create_profile(session.phone_number)
            profile_service.update_profile(profile.profile_id, profile_info)
            session.profile_id = profile.profile_id
        
        # Extract car needs information
        car_needs_info = extract_car_needs(content)
        
        # Update car needs
        if session.profile_id and car_needs_info:
            # Add each need
            for category, value in car_needs_info.items():
                if isinstance(value, list):
                    for item in value:
                        needs_service.add_need(
                            session.profile_id,
                            category,
                            item,
                            is_implicit=False,
                            source="user"
                        )
                else:
                    needs_service.add_need(
                        session.profile_id,
                        category,
                        value,
                        is_implicit=False,
                        source="user"
                    )
            
            # Extract and update implicit needs
            profile = profile_service.get_profile_by_id(session.profile_id)
            if profile:
                profile_data = {k: v for k, v in vars(profile).items() if not k.startswith('_')}
                implicit_needs = extract_implicit_needs(profile_data, car_needs_info)
                
                # Add implicit needs
                for category, value in implicit_needs.items():
                    if isinstance(value, list):
                        for item in value:
                            if "Implicit" in item:
                                value_only = item.replace(", Implicit", "")
                                needs_service.add_need(
                                    session.profile_id,
                                    category,
                                    value_only,
                                    is_implicit=True,
                                    confidence=0.8,
                                    source="inference"
                                )
                            else:
                                needs_service.add_need(
                                    session.profile_id,
                                    category,
                                    item,
                                    is_implicit=False,
                                    confidence=0.9,
                                    source="inference"
                                )
                    else:
                        if "Implicit" in str(value):
                            value_only = value.replace(", Implicit", "")
                            needs_service.add_need(
                                session.profile_id,
                                category,
                                value_only,
                                is_implicit=True,
                                confidence=0.8,
                                source="inference"
                            )
                        else:
                            needs_service.add_need(
                                session.profile_id,
                                category,
                                value,
                                is_implicit=False,
                                confidence=0.9,
                                source="inference"
                            )
    
    async def generate_response(self, session_id: str) -> Optional[ChatMessage]:
        """
        Generate a response for a chat session.
        
        Args:
            session_id: The ID of the session
            
        Returns:
            The generated ChatMessage object if successful, None otherwise
        """
        # Get the session
        session = self.get_session(session_id)
        if not session:
            logger.error(f"Session {session_id} not found")
            return None
        
        # Get the appropriate system prompt based on stage
        system_prompt = SYSTEM_PROMPTS.get(session.stage, SYSTEM_PROMPTS["welcome"])
        
        try:
            # Get messages in API format
            messages = session.get_messages_for_api()
            
            # Generate response from OpenAI
            response_content = await openai_service.create_chat_completion(
                messages, 
                system_prompt=system_prompt
            )
            
            # Add the response to the session
            response_message = session.add_message("assistant", response_content)
            
            # Extract information from the conversation
            await self._extract_information(session)
            
            # Update the stage if needed
            self._update_stage(session)
            
            # Save the session
            self._save_session(session)
            
            return response_message
        except Exception as e:
            logger.error(f"Error generating response for session {session_id}: {str(e)}")
            
            # Add a fallback message
            fallback_message = "I apologize, but I'm having trouble processing your request at the moment. Could you please try again?"
            response_message = session.add_message("assistant", fallback_message)
            
            # Save the session
            self._save_session(session)
            
            return response_message
    
    async def _extract_information(self, session: ChatSession) -> None:
        """
        Extract user information and needs from the conversation.
        
        Args:
            session: The ChatSession object
        """
        # Define schemas for extraction
        profile_schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "user_title": {"type": "string"},
                "age": {"type": "string"},
                "target_driver": {"type": "string"},
                "family_size": {"type": "integer"},
                "price_sensitivity": {"type": "string"},
                "residence": {"type": "string"},
                "parking_conditions": {"type": "string"},
                "expertise": {"type": "integer"}
            }
        }
        
        needs_schema = {
            "type": "object",
            "properties": {
                "budget": {"type": "string"},
                "vehicle_category": {"type": "array", "items": {"type": "string"}},
                "brand": {"type": "array", "items": {"type": "string"}},
                "color": {"type": "array", "items": {"type": "string"}},
                "engine_type": {"type": "array", "items": {"type": "string"}},
                "transmission": {"type": "array", "items": {"type": "string"}},
                "seats": {"type": "string"},
                "sunroof": {"type": "string"},
                "size": {"type": "string"}
            }
        }
        
        # Get the last few messages for extraction
        messages_text = "\n".join([f"{msg.role}: {msg.content}" for msg in session.messages[-5:]])
        
        # Extract profile information
        profile_data = await openai_service.extract_structured_data(messages_text, profile_schema)
        if profile_data:
            # Clean up the data (remove None values)
            profile_data = {k: v for k, v in profile_data.items() if v is not None}
            
            # Update user profile if we have information to update
            if profile_data:
                # Get or create profile
                if session.profile_id:
                    profile = profile_service.get_profile_by_id(session.profile_id)
                    profile_service.update_profile(profile.profile_id, profile_data)
                else:
                    # Create new profile
                    profile = profile_service.create_profile(session.phone_number)
                    profile_service.update_profile(profile.profile_id, profile_data)
                    session.profile_id = profile.profile_id
        
        # Extract needs information
        needs_data = await openai_service.extract_structured_data(messages_text, needs_schema)
        if needs_data and session.profile_id:
            # Update needs if we have a profile ID
            needs = needs_service.get_needs(session.profile_id)
            
            # Update single-value fields
            for single_field in ["budget", "seats", "sunroof", "size"]:
                if needs_data.get(single_field):
                    needs_service.add_need(
                        session.profile_id, 
                        single_field, 
                        needs_data[single_field],
                        is_implicit=False
                    )
            
            # Update list fields
            for list_field in ["vehicle_category", "brand", "color", "engine_type", "transmission"]:
                if needs_data.get(list_field):
                    for value in needs_data[list_field]:
                        needs_service.add_need(
                            session.profile_id,
                            list_field,
                            value,
                            is_implicit=False
                        )
    
    def _update_stage(self, session: ChatSession) -> None:
        """
        Update the stage of the session based on the conversation.
        
        Args:
            session: The ChatSession object
        """
        # Simple rule-based stage transition
        # In a real implementation, this would be more sophisticated
        
        # Just logging for now
        logger.info(f"Session {session.session_id} is in stage {session.stage}")
    
    def _save_session(self, session: ChatSession) -> None:
        """
        Save a chat session to disk.
        
        Args:
            session: The ChatSession object to save
        """
        try:
            if not os.path.exists(SESSIONS_DIR):
                os.makedirs(SESSIONS_DIR)
                
            filepath = os.path.join(SESSIONS_DIR, f"{session.session_id}.json")
            
            # Convert to serializable dict
            session_data = {
                'session_id': session.session_id,
                'profile_id': session.profile_id,
                'phone_number': session.phone_number,
                'created_at': session.created_at.isoformat(),
                'updated_at': session.updated_at.isoformat(),
                'stage': session.stage,
                'context': session.context,
                'messages': [
                    {
                        'message_id': msg.message_id,
                        'role': msg.role,
                        'content': msg.content,
                        'timestamp': msg.timestamp.isoformat()
                    }
                    for msg in session.messages
                ]
            }
            
            with open(filepath, 'w') as f:
                json.dump(session_data, f, indent=4)
                
        except Exception as e:
            logger.error(f"Error saving chat session {session.session_id}: {str(e)}")


# Create a singleton instance
chat_service = ChatService() 