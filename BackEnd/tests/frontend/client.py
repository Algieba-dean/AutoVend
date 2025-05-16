#!/usr/bin/env python
"""
Frontend HTTP client for testing AutoVend backend API
This client simulates frontend calls to the backend API
"""

import requests
import json
import os
import sys

class ApiClient:
    """API client for AutoVend backend"""
    
    def __init__(self, base_url="http://localhost:5000"):
        """Initialize the client with base URL"""
        self.base_url = base_url
        self.headers = {"Content-Type": "application/json"}
        self.session_id = None
        self.phone_number = None
    
    def get_default_profile(self):
        """Get default user profile configuration"""
        try:
            response = requests.get(
                f"{self.base_url}/api/profile/default",
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            self._handle_error(e)
            return None
    
    def create_profile(self, profile_data):
        """Create a new user profile"""
        try:
            response = requests.post(
                f"{self.base_url}/api/profile",
                headers=self.headers,
                json=profile_data
            )
            response.raise_for_status()
            self.phone_number = profile_data.get("phone_number")
            return response.json()
        except requests.exceptions.RequestException as e:
            self._handle_error(e)
            return None
    
    def get_profile(self, phone_number=None):
        """Get user profile by phone number"""
        if not phone_number and not self.phone_number:
            print("Error: No phone number provided or set")
            return None
            
        phone = phone_number or self.phone_number
        
        try:
            response = requests.get(
                f"{self.base_url}/api/profile/{phone}",
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            self._handle_error(e)
            return None
    
    def update_profile(self, profile_data, phone_number=None):
        """Update an existing user profile"""
        if not phone_number and not self.phone_number:
            print("Error: No phone number provided or set")
            return None
            
        phone = phone_number or self.phone_number
        
        try:
            response = requests.put(
                f"{self.base_url}/api/profile/{phone}",
                headers=self.headers,
                json=profile_data
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            self._handle_error(e)
            return None
    
    def start_chat_session(self, phone_number=None):
        """Start a new chat session"""
        if not phone_number and not self.phone_number:
            print("Error: No phone number provided or set")
            return None
            
        phone = phone_number or self.phone_number
        
        try:
            response = requests.post(
                f"{self.base_url}/api/chat/session",
                headers=self.headers,
                json={"phone_number": phone}
            )
            response.raise_for_status()
            result = response.json()
            self.session_id = result.get("session_id")
            return result
        except requests.exceptions.RequestException as e:
            self._handle_error(e)
            return None
    
    def send_message(self, message, session_id=None):
        """Send a message in an active chat session"""
        if not session_id and not self.session_id:
            print("Error: No session ID provided or set")
            return None
            
        session = session_id or self.session_id
        
        try:
            response = requests.post(
                f"{self.base_url}/api/chat/message",
                headers=self.headers,
                json={
                    "session_id": session,
                    "message": message
                }
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            self._handle_error(e)
            return None
    
    def get_messages(self, session_id=None, since_timestamp=None, limit=50):
        """Get messages from a chat session"""
        if not session_id and not self.session_id:
            print("Error: No session ID provided or set")
            return None
            
        session = session_id or self.session_id
        
        params = {}
        if since_timestamp:
            params["since_timestamp"] = since_timestamp
        if limit:
            params["limit"] = limit
        
        try:
            response = requests.get(
                f"{self.base_url}/api/chat/session/{session}/messages",
                headers=self.headers,
                params=params
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            self._handle_error(e)
            return None
    
    def end_chat_session(self, session_id=None):
        """End an active chat session"""
        if not session_id and not self.session_id:
            print("Error: No session ID provided or set")
            return None
            
        session = session_id or self.session_id
        
        try:
            response = requests.put(
                f"{self.base_url}/api/chat/session/{session}/end",
                headers=self.headers
            )
            response.raise_for_status()
            result = response.json()
            # Clear the session ID if we ended our current session
            if session == self.session_id:
                self.session_id = None
            return result
        except requests.exceptions.RequestException as e:
            self._handle_error(e)
            return None
    
    def _handle_error(self, exception):
        """Handle API request exceptions"""
        print(f"API Error: {exception}")
        if hasattr(exception, "response") and exception.response is not None:
            print(f"Status code: {exception.response.status_code}")
            try:
                error_data = exception.response.json()
                print(f"Error details: {json.dumps(error_data, indent=2)}")
            except:
                print(f"Response body: {exception.response.text}") 