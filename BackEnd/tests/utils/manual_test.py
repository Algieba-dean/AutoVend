#!/usr/bin/env python
"""
Manual test script for AutoVend API
This script performs basic API operations to test the AutoVend backend
"""

import requests
import json
import time
import sys
import os

# Constants
API_URL = "http://localhost:5000"
PROFILE_API = f"{API_URL}/api/profile"
CHAT_API = f"{API_URL}/api/chat"

# Test data
TEST_PROFILE = {
    "phone_number": "123456789",
    "age": "30-45",
    "user_title": "Mr. Zhang",
    "name": "Alex Zhang",
    "target_driver": "Self",
    "expertise": "6",
    "additional_information": {
        "family_size": "4",
        "price_sensitivity": "Medium",
        "residence": "China+Beijing+Haidian",
        "parking_conditions": "Allocated Parking Space"
    },
    "connection_information": {
        "connection_phone_number": "",
        "connection_id_relationship": ""
    }
}

TEST_MESSAGES = [
    "Hello, I'm looking for a new car.",
    "I want an electric SUV with good range.",
    "I'm interested in Tesla Model Y. What's its range?",
    "What about safety features?",
    "Can I schedule a test drive?",
    "I'd like to confirm that reservation."
]

def print_separator(title=""):
    """Print a separator line with an optional title"""
    print("\n" + "="*60)
    if title:
        print(f"  {title}")
        print("="*60)
    print()

def print_json(json_data):
    """Print JSON data in a readable format"""
    print(json.dumps(json_data, indent=2))

def make_request(method, url, data=None, params=None):
    """Make a request and handle errors"""
    headers = {"Content-Type": "application/json"}
    try:
        if method.lower() == "get":
            response = requests.get(url, headers=headers, params=params)
        elif method.lower() == "post":
            response = requests.post(url, headers=headers, json=data)
        elif method.lower() == "put":
            response = requests.put(url, headers=headers, json=data)
        else:
            print(f"Unsupported method: {method}")
            return None
            
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error making request: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response status code: {e.response.status_code}")
            try:
                print(f"Response body: {e.response.json()}")
            except:
                print(f"Response body: {e.response.text}")
        return None

def test_profile_api():
    """Test the profile API endpoints"""
    print_separator("TESTING PROFILE API")
    
    # Get default profile
    print("1. Getting default profile...")
    default_profile = make_request("get", f"{PROFILE_API}/default")
    if default_profile:
        print_json(default_profile)
    
    # Create a profile
    print("\n2. Creating a new profile...")
    created_profile = make_request("post", PROFILE_API, data=TEST_PROFILE)
    if created_profile:
        print_json(created_profile)
    
    # Get the profile
    print("\n3. Getting the created profile...")
    retrieved_profile = make_request("get", f"{PROFILE_API}/{TEST_PROFILE['phone_number']}")
    if retrieved_profile:
        print_json(retrieved_profile)
    
    # Update the profile
    print("\n4. Updating the profile...")
    update_data = TEST_PROFILE.copy()
    update_data["expertise"] = "8"
    updated_profile = make_request("put", f"{PROFILE_API}/{TEST_PROFILE['phone_number']}", data=update_data)
    if updated_profile:
        print_json(updated_profile)
    
    return TEST_PROFILE['phone_number'] if created_profile else None

def test_chat_api(phone_number):
    """Test the chat API endpoints"""
    print_separator("TESTING CHAT API")
    
    if not phone_number:
        print("Cannot test chat API without a valid profile")
        return
    
    # Start a chat session
    print("1. Starting a chat session...")
    session_data = make_request("post", f"{CHAT_API}/session", data={"phone_number": phone_number})
    if not session_data:
        print("Failed to start chat session")
        return
    
    print_json(session_data)
    session_id = session_data["session_id"]
    
    # Send messages
    print("\n2. Sending messages...")
    last_response = None
    for i, message in enumerate(TEST_MESSAGES):
        print(f"\nMessage {i+1}: {message}")
        message_data = make_request("post", f"{CHAT_API}/message", data={
            "session_id": session_id,
            "message": message
        })
        if message_data:
            print("User message sent.")
            print(f"System response: {message_data['response']['content']}")
            last_response = message_data
    
    if last_response:
        print("\n3. Current session state:")
        print(f"Stage: {last_response['stage']['current_stage']}")
        
        print("\nNeeds extracted:")
        print("Explicit:")
        for key, value in last_response['needs']['explicit'].items():
            print(f"  - {key}: {value}")
        print("Implicit:")
        for key, value in last_response['needs']['implicit'].items():
            print(f"  - {key}: {value}")
        
        # If we've reached reservation stage
        if last_response['stage']['current_stage'] == 'reservation_confirmation':
            print("\nReservation details:")
            for key, value in last_response['reservation_info'].items():
                if value:
                    print(f"  - {key}: {value}")
    
    # Get messages
    print("\n4. Getting chat messages...")
    messages_data = make_request("get", f"{CHAT_API}/session/{session_id}/messages")
    if messages_data:
        print(f"Retrieved {len(messages_data['messages'])} messages")
        for msg in messages_data['messages'][-2:]:  # Show last 2 messages
            sender = "User" if msg['sender_type'] == 'user' else "System"
            print(f"{sender}: {msg['content']}")
    
    # End session
    print("\n5. Ending chat session...")
    end_data = make_request("put", f"{CHAT_API}/session/{session_id}/end")
    if end_data:
        print(f"Session ended with status: {end_data['status']}")
    
    return session_id

def main():
    """Run the manual test"""
    try:
        print_separator("AUTOVEND API MANUAL TEST")
        print("Testing connection to server...")
        
        # Test server connection
        try:
            response = requests.get(API_URL)
            if response.status_code == 200:
                print(f"Server is running at {API_URL}")
            else:
                print(f"Server returned status code {response.status_code}")
                return
        except requests.exceptions.ConnectionError:
            print(f"Could not connect to server at {API_URL}")
            print("Make sure the AutoVend server is running")
            return
        
        # Test Profile API
        phone_number = test_profile_api()
        
        # Test Chat API
        session_id = test_chat_api(phone_number)
        
        print_separator("TEST COMPLETED")
        
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
    except Exception as e:
        print(f"\nError during test: {e}")

if __name__ == "__main__":
    main() 