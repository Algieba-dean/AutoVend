import json
import os
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from pathlib import Path
import shutil

class FileStorage:
    """File-based storage manager for AutoVend"""
    
    def __init__(self, storage_dir: str = "storage"):
        """Initialize file storage with storage directory"""
        self.storage_dir = storage_dir
        self.profiles_dir = os.path.join(storage_dir, "profiles")
        self.sessions_dir = os.path.join(storage_dir, "sessions")
        self.messages_dir = os.path.join(storage_dir, "messages")
        self.test_drives_dir = os.path.join(storage_dir, "test_drives")
        self.connection_data_dict = self._get_all_connection_number_with_user_name()
        
        # Create necessary directories
        for directory in [self.profiles_dir, self.sessions_dir, self.messages_dir, self.test_drives_dir]:
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

    def get_profiles_from_connection(self,phone_number:str)->Optional[Dict[str, Any]]:
        """Get profiles from connection, will only be called when directly,get profile can't find the profile, try to find it from connection"""
        try:
            if not phone_number:
                return None

            if phone_number in self.connection_data_dict:
                return self.connection_data_dict[phone_number]
            else:
                # print(f"Not found matched connection user name for {phone_number}")
                return None
        except Exception as e:
            print(f"Error getting profiles from connection: {e}")
            return None

    def _get_all_connection_number_with_user_name(self):
        """
        get all connection numbers with their user names
        
        Returns:
            dict, key is connection number, value is user name
        """
        connection_data_list = dict()
        if not Path(self.profiles_dir).exists():
            return connection_data_list
        for file in Path(self.profiles_dir).rglob("*.json"):
            try:
                with open(file, "r", encoding="utf-8") as f:
                    profile_data = json.load(f)
                    connection_phone_number = profile_data["connection_information"]["connection_phone_number"]
                    connection_user_name = profile_data["connection_information"]["connection_user_name"]
                    raw_phone_number = profile_data["phone_number"]
                    raw_name = profile_data["name"]
                    return_dict = {
                        "connection_phone_number":connection_phone_number,
                        "connection_user_name":connection_user_name,
                        "raw_phone_number":raw_phone_number,
                        "raw_name":raw_name
                    }
                    connection_data_list[raw_phone_number]=return_dict
            except Exception as e:
                # print(f"Error loading connection data from {file}: {e}")
                return dict()
        return connection_data_list
                
    
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

    def _get_test_drive_path(self, reservation_id: str) -> str:
        """Get test drive file path by reservation ID"""
        return os.path.join(self.test_drives_dir, f"{reservation_id}.json")
    
    def _get_test_drive_phone_index_path(self) -> str:
        """Get test drive phone number index file path"""
        return os.path.join(self.test_drives_dir, "phone_index.json")
    
    def save_test_drive(self, test_drive_data: Dict[str, Any]) -> bool:
        """Save test drive reservation"""
        try:
            reservation_id = test_drive_data.get("reservation_id")
            reservation_phone = test_drive_data.get("test_drive_info", {}).get("reservation_phone_number")
            
            if not reservation_id or not reservation_phone:
                return False
                
            # Save test drive data
            file_path = self._get_test_drive_path(reservation_id)
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(test_drive_data, f, ensure_ascii=False, indent=2)
                
            # Update phone index
            phone_index = {}
            index_path = self._get_test_drive_phone_index_path()
            if os.path.exists(index_path):
                with open(index_path, "r", encoding="utf-8") as f:
                    phone_index = json.load(f)
                    
            phone_index[reservation_phone] = reservation_id
            with open(index_path, "w", encoding="utf-8") as f:
                json.dump(phone_index, f, ensure_ascii=False, indent=2)
                
            return True
        except Exception as e:
            print(f"Error saving test drive: {e}")
            return False
    
    def update_test_drive(self, test_drive_data: Dict[str, Any]) -> bool:
        """Update test drive reservation"""
        try:
            reservation_id = test_drive_data.get("reservation_id")
            if not reservation_id:
                return False
                
            # Just save the updated data
            file_path = self._get_test_drive_path(reservation_id)
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(test_drive_data, f, ensure_ascii=False, indent=2)
                
            return True
        except Exception as e:
            print(f"Error updating test drive: {e}")
            return False
    
    def get_test_drive(self, reservation_id: str) -> Optional[Dict[str, Any]]:
        """Get test drive reservation by ID"""
        try:
            file_path = self._get_test_drive_path(reservation_id)
            if not os.path.exists(file_path):
                return None
                
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error getting test drive: {e}")
            return None
    
    def get_test_drive_by_phone(self, reservation_phone_number: str) -> Optional[Dict[str, Any]]:
        """Get test drive reservation by phone number"""
        try:
            # Get reservation ID from phone index
            index_path = self._get_test_drive_phone_index_path()
            if not os.path.exists(index_path):
                return None
                
            with open(index_path, "r", encoding="utf-8") as f:
                phone_index = json.load(f)
                
            reservation_id = phone_index.get(reservation_phone_number)
            if not reservation_id:
                return None
                
            # Get test drive data by ID
            return self.get_test_drive(reservation_id)
        except Exception as e:
            print(f"Error getting test drive by phone: {e}")
            return None
    
    def delete_test_drive(self, reservation_phone_number: str) -> bool:
        """Delete test drive reservation by phone number"""
        try:
            # Get reservation ID from phone index
            index_path = self._get_test_drive_phone_index_path()
            if not os.path.exists(index_path):
                return False
                
            with open(index_path, "r", encoding="utf-8") as f:
                phone_index = json.load(f)
                
            reservation_id = phone_index.get(reservation_phone_number)
            if not reservation_id:
                return False
                
            # Delete test drive file
            file_path = self._get_test_drive_path(reservation_id)
            if os.path.exists(file_path):
                os.remove(file_path)
                
            # Update phone index
            del phone_index[reservation_phone_number]
            with open(index_path, "w", encoding="utf-8") as f:
                json.dump(phone_index, f, ensure_ascii=False, indent=2)
                
            return True
        except Exception as e:
            print(f"Error deleting test drive: {e}")
            return False
    
    def get_all_test_drives(self) -> List[Dict[str, Any]]:
        """Get all test drive reservations"""
        try:
            test_drives = []
            # Only process JSON files that aren't the phone index
            for filename in os.listdir(self.test_drives_dir):
                if filename.endswith('.json') and filename != "phone_index.json":
                    with open(os.path.join(self.test_drives_dir, filename), "r", encoding="utf-8") as f:
                        test_drive = json.load(f)
                        test_drives.append(test_drive)
            return test_drives
        except Exception as e:
            print(f"Error getting all test drives: {e}")
            return [] 