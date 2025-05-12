#!/usr/bin/env python3
"""
Test script for AutoVend dialogue flow.
"""
import json
import requests
import time
import sys

# API base URL
BASE_URL = "http://localhost:8000/api"

def print_formatted_message(role, content):
    """Print a formatted message."""
    if role == "user":
        print(f"\n👤 User: {content}")
    else:
        print(f"\n🤖 AutoVend: {content}")
    time.sleep(1)  # Pause for readability

def test_dialogue_flow():
    """Test the complete dialogue flow."""
    print("\n--- Starting AutoVend Dialogue Test ---\n")
    
    # Check if server is running
    try:
        requests.get("http://localhost:8000/health", timeout=2)
    except requests.exceptions.ConnectionError:
        print("Error: Cannot connect to the server. Make sure the application is running.")
        print("Run 'python run.py' in a separate terminal to start the server.")
        return
    
    # Step 1: Create a new chat session
    print("Creating new session...")
    try:
        response = requests.post(f"{BASE_URL}/chat/new", json={})
        response.raise_for_status()  # Raise exception for 4XX/5XX responses
    except requests.exceptions.RequestException as e:
        print(f"Failed to create session: {str(e)}")
        return
    
    session_data = response.json()
    session_id = session_data["session_id"]
    print(f"Session ID: {session_id}")
    
    # Print initial greeting
    for message in session_data["messages"]:
        print_formatted_message(message["role"], message["content"])
    
    # Step 2: User introduces themselves
    user_messages = [
        "Hello, I am Mr. Zhang and I want to buy a car.",
        "I am 35 years old, with a family of four, and we live in Beijing.",
        "My budget is 300,000 yuan and I want an SUV.",
        "I like Toyota and Honda cars, and need one with more space.",
        "I will mainly use it for commuting and weekend family trips.",
        "I don't know much about cars, this is my first time buying one."
    ]
    
    for message in user_messages:
        print_formatted_message("user", message)
        
        # Send message to API
        try:
            response = requests.post(
                f"{BASE_URL}/chat/{session_id}/message",
                json={"content": message, "sender": "user"}
            )
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            print(f"Failed to send message: {str(e)}")
            continue
        
        # Print latest response
        latest_message = response.json()["messages"][-1]
        print_formatted_message(latest_message["role"], latest_message["content"])
    
    # Step 3: Get recommendations
    print("\n--- Getting User Profile ---")
    profile_id = response.json().get("profile_id")
    
    if profile_id:
        try:
            profile_response = requests.get(f"{BASE_URL}/profile/{profile_id}")
            profile_response.raise_for_status()
            profile_data = profile_response.json()
            print(json.dumps(profile_data, indent=2, ensure_ascii=False))
        except requests.exceptions.RequestException as e:
            print(f"Failed to get profile: {str(e)}")
        
        print("\n--- Getting Needs Analysis ---")
        try:
            needs_response = requests.get(f"{BASE_URL}/needs/{profile_id}")
            needs_response.raise_for_status()
            needs_data = needs_response.json()
            print(json.dumps(needs_data, indent=2, ensure_ascii=False))
        except requests.exceptions.RequestException as e:
            print(f"Failed to get needs: {str(e)}")
        
        print("\n--- Getting Vehicle Recommendations ---")
        try:
            recommendations_response = requests.get(f"{BASE_URL}/recommendations/{profile_id}")
            recommendations_response.raise_for_status()
            recommendations = recommendations_response.json()
            print("\nRecommended Vehicles:")
            for i, vehicle in enumerate(recommendations, 1):
                print(f"{i}. {vehicle['brand']} {vehicle['model']} - ¥{vehicle['price']}")
        except requests.exceptions.RequestException as e:
            print(f"Failed to get recommendations: {str(e)}")
    else:
        print("Could not get user ID, skipping recommendation steps")
    
    print("\n--- Test Completed ---")

if __name__ == "__main__":
    try:
        test_dialogue_flow()
    except KeyboardInterrupt:
        print("\nTest interrupted by user.")
        sys.exit(0) 