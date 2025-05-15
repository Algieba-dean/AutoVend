#!/usr/bin/env python
"""
Frontend simulator for AutoVend backend API
This script simulates a frontend application interacting with the backend
"""

import os
import sys
import json
import time
import random
from datetime import datetime

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from tests.frontend.client import ApiClient
from tests.data import VALID_PROFILES, CHAT_MESSAGES

class FrontendSimulator:
    """Frontend simulator class to test backend API"""
    
    def __init__(self, base_url="http://localhost:5000"):
        """Initialize the simulator with API client"""
        self.client = ApiClient(base_url)
        self.current_profile = None
        self.conversation_log = []
        self.current_session_status = {
            "stage": None,
            "needs": None,
            "matched_car_models": None,
            "reservation_info": None
        }
        
    def log(self, message, data=None):
        """Log a message with optional data"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = {
            "timestamp": timestamp,
            "message": message
        }
        
        if data:
            log_entry["data"] = data
            
        self.conversation_log.append(log_entry)
        print(f"[{timestamp}] {message}")
        
        # Update session status if data contains relevant information
        if data and isinstance(data, dict):
            if "stage" in data:
                self.current_session_status["stage"] = data["stage"]
            if "needs" in data:
                self.current_session_status["needs"] = data["needs"]
            if "matched_car_models" in data:
                self.current_session_status["matched_car_models"] = data["matched_car_models"]
            if "reservation_info" in data:
                self.current_session_status["reservation_info"] = data["reservation_info"]
            
            # Print current session status
            self.print_session_status()
    
    def print_session_status(self):
        """Print the current session status"""
        print("\n=== Session Status ===")
        if self.current_session_status["stage"]:
            print(f"Current Stage: {self.current_session_status['stage'].get('current_stage', 'N/A')}")
            print(f"Previous Stage: {self.current_session_status['stage'].get('previous_stage', 'N/A')}")
        
        if self.current_session_status["needs"]:
            print("\nNeeds:")
            print(f"Explicit: {json.dumps(self.current_session_status['needs'].get('explicit', {}), indent=2)}")
            print(f"Implicit: {json.dumps(self.current_session_status['needs'].get('implicit', {}), indent=2)}")
        
        if self.current_session_status["matched_car_models"]:
            print("\nMatched Car Models:")
            for car in self.current_session_status["matched_car_models"]:
                print(f"- {car}")
        
        if self.current_session_status["reservation_info"]:
            print("\nReservation Info:")
            print(json.dumps(self.current_session_status["reservation_info"], indent=2))
        
        print("=====================\n")
    
    def save_log(self, filename="conversation_log.json"):
        """Save the conversation log to a file"""
        with open(filename, 'w') as f:
            json.dump(self.conversation_log, f, indent=2)
        print(f"Log saved to {filename}")
    
    def run_user_profile_scenario(self):
        """Run user profile management scenario"""
        self.log("Starting user profile management scenario")
        
        # Get default profile
        self.log("Getting default profile")
        default_profile = self.client.get_default_profile()
        if default_profile:
            self.log("Default profile retrieved", default_profile)
        else:
            self.log("Failed to retrieve default profile")
            return False
        
        # Create a new profile
        profile_index = random.randint(0, len(VALID_PROFILES) - 1)
        test_profile = VALID_PROFILES[profile_index]
        
        self.log(f"Creating new profile with phone number {test_profile['phone_number']}")
        created_profile = self.client.create_profile(test_profile)
        if created_profile:
            self.log("Profile created successfully", created_profile)
            self.current_profile = created_profile
        else:
            self.log("Failed to create profile")
            return False
        
        # Get the profile
        self.log(f"Retrieving profile with phone number {test_profile['phone_number']}")
        retrieved_profile = self.client.get_profile()
        if retrieved_profile:
            self.log("Profile retrieved successfully", retrieved_profile)
        else:
            self.log("Failed to retrieve profile")
            return False
        
        # Update the profile
        update_data = test_profile.copy()
        update_data["expertise"] = str(min(int(update_data["expertise"]) + 2, 10))
        self.log(f"Updating profile expertise to {update_data['expertise']}")
        
        updated_profile = self.client.update_profile(update_data)
        if updated_profile:
            self.log("Profile updated successfully", updated_profile)
            self.current_profile = updated_profile
        else:
            self.log("Failed to update profile")
            return False
        
        self.log("User profile management scenario completed successfully")
        return True
    
    def run_chat_scenario(self):
        """Run chat functionality scenario"""
        if not self.current_profile:
            self.log("No profile available, running profile scenario first")
            if not self.run_user_profile_scenario():
                return False
        
        self.log("Starting chat scenario")
        
        # Start a chat session
        self.log("Starting chat session")
        session = self.client.start_chat_session()
        if session:
            self.log("Chat session started", {
                "session_id": session.get("session_id"),
                "welcome_message": session.get("message", {}).get("content", ""),
                "stage": session.get("stage"),
                "needs": session.get("needs"),
                "matched_car_models": session.get("matched_car_models", []),
                "reservation_info": session.get("reservation_info", {})
            })
        else:
            self.log("Failed to start chat session")
            return False
        
        # Send a series of messages
        self.log("Sending chat messages")
        last_response = None
        
        for i, message in enumerate(CHAT_MESSAGES):
            self.log(f"Sending message: {message}")
            response = self.client.send_message(message)
            
            if response:
                system_reply = response.get("response", {}).get("content", "")
                self.log(f"Received response: {system_reply}")
                
                # Log the current session status
                self.log("Session status updated", {
                    "stage": response.get("stage"),
                    "needs": response.get("needs"),
                    "matched_car_models": response.get("matched_car_models", []),
                    "reservation_info": response.get("reservation_info", {})
                })
                
                last_response = response
            else:
                self.log("Failed to send message")
                return False
            
            # Add a delay to simulate real user interaction
            time.sleep(0.5)
        
        # Get chat messages
        self.log("Retrieving chat messages")
        messages = self.client.get_messages()
        if messages:
            message_count = len(messages.get("messages", []))
            self.log(f"Retrieved {message_count} messages")
            
            # Update session status with the latest information
            self.log("Final session status", {
                "stage": messages.get("stage"),
                "needs": messages.get("needs"),
                "matched_car_models": messages.get("matched_car_models", []),
                "reservation_info": messages.get("reservation_info", {})
            })
        else:
            self.log("Failed to retrieve messages")
            return False
        
        # End chat session
        self.log("Ending chat session")
        end_result = self.client.end_chat_session()
        if end_result:
            self.log("Chat session ended", {
                "status": end_result.get("status"),
                "ended_at": end_result.get("ended_at"),
                "stage": end_result.get("stage"),
                "needs": end_result.get("needs"),
                "matched_car_models": end_result.get("matched_car_models", []),
                "reservation_info": end_result.get("reservation_info", {})
            })
        else:
            self.log("Failed to end chat session")
            return False
        
        self.log("Chat scenario completed successfully")
        return True
    
    def run_full_user_journey(self):
        """Run a complete user journey simulation"""
        self.log("Starting full user journey simulation")
        
        # Run profile management
        if not self.run_user_profile_scenario():
            self.log("User journey failed at profile management stage")
            return False
        
        # Run chat functionality
        if not self.run_chat_scenario():
            self.log("User journey failed at chat stage")
            return False
        
        self.log("Full user journey completed successfully")
        return True

def main():
    """Run the frontend simulator"""
    # Get base URL from command line if provided
    base_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:5000"
    
    print(f"Starting frontend simulator for AutoVend backend at {base_url}")
    print("This will simulate a frontend application interacting with the backend API")
    
    # Create simulator
    simulator = FrontendSimulator(base_url)
    
    try:
        # Run full user journey
        simulator.run_full_user_journey()
        
        # Save the log
        log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'report')
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, f"frontend_simulation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        simulator.save_log(log_file)
        
        print("\nSimulation completed.")
        print(f"Log saved to {log_file}")
        
    except KeyboardInterrupt:
        print("\nSimulation interrupted by user")
    except Exception as e:
        print(f"\nError during simulation: {e}")

if __name__ == "__main__":
    main() 