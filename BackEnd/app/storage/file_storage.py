import json
import os
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import shutil

class FileStorage:
    """File-based storage manager for AutoVend"""
    
    def __init__(self, storage_dir: str = "storage"):
        """Initialize file storage with storage directory"""
        self.storage_dir = storage_dir
        self.profiles_dir = os.path.join(storage_dir, "profiles")
        self.sessions_dir = os.path.join(storage_dir, "sessions")
        self.messages_dir = os.path.join(storage_dir, "messages")
        
        # Create necessary directories
        for directory in [self.profiles_dir, self.sessions_dir, self.messages_dir]:
            os.makedirs(directory, exist_ok=True)
    
    def _get_profile_path(self, phone_number: str) -> str:
        """Get profile file path"""
        return os.path.join(self.profiles_dir, f"{phone_number}.json")
    
    def _get_session_path(self, session_id: str) -> str:
        """Get session file path"""
        return os.path.join(self.sessions_dir, f"{session_id}.json")
    
    def _get_messages_path(self, session_id: str) -> str:
        """Get messages file path"""
        return os.path.join(self.messages_dir, f"{session_id}.json")
    
    def save_profile(self, phone_number: str, profile: Dict[str, Any]) -> bool:
        """Save user profile"""
        try:
            file_path = self._get_profile_path(phone_number)
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(profile, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"Error saving profile: {e}")
            return False
    
    def get_profile(self, phone_number: str) -> Optional[Dict[str, Any]]:
        """Get user profile"""
        try:
            file_path = self._get_profile_path(phone_number)
            if not os.path.exists(file_path):
                return None
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error getting profile: {e}")
            return None
    
    def save_session(self, session_id: str, session_data: Dict[str, Any]) -> bool:
        """Save chat session"""
        try:
            file_path = self._get_session_path(session_id)
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(session_data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"Error saving session: {e}")
            return False
    
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get chat session"""
        try:
            file_path = self._get_session_path(session_id)
            if not os.path.exists(file_path):
                return None
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error getting session: {e}")
            return None
    
    def save_message(self, session_id: str, message: Dict[str, Any]) -> bool:
        """Save chat message"""
        try:
            file_path = self._get_messages_path(session_id)
            messages = []
            if os.path.exists(file_path):
                with open(file_path, "r", encoding="utf-8") as f:
                    messages = json.load(f)
            
            messages.append(message)
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(messages, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"Error saving message: {e}")
            return False
    
    def get_messages(self, session_id: str, limit: int = 50) -> list:
        """Get chat messages"""
        try:
            file_path = self._get_messages_path(session_id)
            if not os.path.exists(file_path):
                return []
            with open(file_path, "r", encoding="utf-8") as f:
                messages = json.load(f)
            return messages[-limit:]
        except Exception as e:
            print(f"Error getting messages: {e}")
            return []
    
    def delete_session(self, session_id: str) -> bool:
        """Delete chat session and its messages"""
        try:
            session_path = self._get_session_path(session_id)
            messages_path = self._get_messages_path(session_id)
            
            if os.path.exists(session_path):
                os.remove(session_path)
            if os.path.exists(messages_path):
                os.remove(messages_path)
            return True
        except Exception as e:
            print(f"Error deleting session: {e}")
            return False
    
    def cleanup_old_sessions(self, max_age_days: int = 7) -> bool:
        """Clean up old sessions and messages"""
        try:
            current_time = datetime.now()
            for directory in [self.sessions_dir, self.messages_dir]:
                for filename in os.listdir(directory):
                    file_path = os.path.join(directory, filename)
                    file_time = datetime.fromtimestamp(os.path.getmtime(file_path))
                    if (current_time - file_time) > timedelta(days=max_age_days):
                        os.remove(file_path)
            return True
        except Exception as e:
            print(f"Error cleaning up old sessions: {e}")
            return False 