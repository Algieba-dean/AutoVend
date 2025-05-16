import unittest
import json
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.config import Config
from app.models.profile import UserProfile

class ChatAPITestCase(unittest.TestCase):
    """Test case for the chat API"""
    
    def setUp(self):
        """Set up the test client and other test variables"""
        self.app = create_app("testing")
        self.client = self.app.test_client()
        
        # Create a profile for testing
        self.profile = {
            "phone_number": "123456789",
            "age": "20-35",
            "user_title": "Mr. Zhang",
            "name": "John",
            "target_driver": "Self",
            "expertise": "5",
            "additional_information": {
                "family_size": "3",
                "price_sensitivity": "Medium",
                "residence": "China+Beijing+Haidian",
                "parking_conditions": "Allocated Parking Space"
            },
            "connection_information": {
                "connection_phone_number": "",
                "connection_id_relationship": ""
            }
        }
        
        # Reset the storage before each test
        Config.USER_PROFILES = {}
        Config.CHAT_SESSIONS = {}
        Config.CHAT_MESSAGES = {}
        
        # Create a user profile
        profile_obj = UserProfile.from_dict(self.profile)
        Config.USER_PROFILES[self.profile["phone_number"]] = profile_obj
    
    def test_start_chat_session(self):
        """Test API can start a new chat session (POST /api/chat/session)"""
        res = self.client.post(
            "/api/chat/session",
            data=json.dumps({"phone_number": self.profile["phone_number"]}),
            content_type="application/json"
        )
        self.assertEqual(res.status_code, 201)
        result = json.loads(res.data)
        
        self.assertIn("session_id", result)
        self.assertIn("created_at", result)
        self.assertEqual(result["status"], "active")
        self.assertIn("message", result)
        self.assertEqual(result["stage"]["current_stage"], "welcome")
        self.assertIn("matched_car_models", result)
        self.assertEqual(result["matched_car_models"], [])
        
        # Verify welcome message is returned
        self.assertEqual(result["message"]["sender_type"], "system")
        self.assertIn("AutoVend", result["message"]["content"])
    
    def test_start_chat_session_invalid_phone(self):
        """Test API handles start session with invalid phone number"""
        res = self.client.post(
            "/api/chat/session",
            data=json.dumps({"phone_number": "nonexistent"}),
            content_type="application/json"
        )
        self.assertEqual(res.status_code, 400)
        result = json.loads(res.data)
        self.assertIn("error", result)
    
    def test_send_chat_message(self):
        """Test API can send a message in an active chat session (POST /api/chat/message)"""
        # First start a session
        start_res = self.client.post(
            "/api/chat/session",
            data=json.dumps({"phone_number": self.profile["phone_number"]}),
            content_type="application/json"
        )
        start_result = json.loads(start_res.data)
        session_id = start_result["session_id"]
        
        # Send a message
        message = "I'm looking for an electric SUV with good range"
        res = self.client.post(
            "/api/chat/message",
            data=json.dumps({
                "session_id": session_id,
                "message": message
            }),
            content_type="application/json"
        )
        self.assertEqual(res.status_code, 200)
        result = json.loads(res.data)
        
        # Verify the user message was recorded correctly
        self.assertEqual(result["message"]["content"], message)
        self.assertEqual(result["message"]["sender_type"], "user")
        
        # Verify the system responded
        self.assertIn("response", result)
        self.assertEqual(result["response"]["sender_type"], "system")
        self.assertNotEqual(result["response"]["content"], "")
    
    def test_send_message_with_needs_tracking(self):
        """Test API tracks user needs when sending messages about car preferences"""
        # First start a session
        start_res = self.client.post(
            "/api/chat/session",
            data=json.dumps({"phone_number": self.profile["phone_number"]}),
            content_type="application/json"
        )
        start_result = json.loads(start_res.data)
        session_id = start_result["session_id"]
        
        # Send a message about car preferences
        message = "I'm looking for an electric SUV with good range"
        res = self.client.post(
            "/api/chat/message",
            data=json.dumps({
                "session_id": session_id,
                "message": message
            }),
            content_type="application/json"
        )
        result = json.loads(res.data)
        
        # Verify needs are being tracked
        self.assertIn("needs", result)
        # Since our message mentions "electric" and "SUV", these should be captured
        if "explicit" in result["needs"] and result["needs"]["explicit"]:
            powertrain = result["needs"]["explicit"].get("powertrain_type", "")
            vehicle_type = result["needs"]["explicit"].get("vehicle_category_bottom", "")
            self.assertTrue(
                "Electric" in powertrain or "SUV" in vehicle_type,
                "Message needs tracking should capture electric or SUV preference"
            )
        
        # Verify matched car models are being tracked
        self.assertIn("matched_car_models", result)
        self.assertIsInstance(result["matched_car_models"], list)
        # If we have matched cars, they should be strings
        for car_model in result["matched_car_models"]:
            self.assertIsInstance(car_model, str)
    
    def test_send_message_nonexistent_session(self):
        """Test API handles sending message to nonexistent session"""
        res = self.client.post(
            "/api/chat/message",
            data=json.dumps({
                "session_id": "nonexistent",
                "message": "Hello"
            }),
            content_type="application/json"
        )
        self.assertEqual(res.status_code, 404)
        result = json.loads(res.data)
        self.assertIn("error", result)
    
    def test_get_chat_messages(self):
        """Test API can retrieve messages from a chat session (GET /api/chat/session/<session_id>/messages)"""
        # First start a session
        start_res = self.client.post(
            "/api/chat/session",
            data=json.dumps({"phone_number": self.profile["phone_number"]}),
            content_type="application/json"
        )
        start_result = json.loads(start_res.data)
        session_id = start_result["session_id"]
        
        # Send a couple of messages
        messages = ["Hello", "I'm looking for a car", "Something electric"]
        for message in messages:
            self.client.post(
                "/api/chat/message",
                data=json.dumps({
                    "session_id": session_id,
                    "message": message
                }),
                content_type="application/json"
            )
        
        # Get the messages
        res = self.client.get(f"/api/chat/session/{session_id}/messages")
        self.assertEqual(res.status_code, 200)
        result = json.loads(res.data)
        
        # Verify the messages are returned
        self.assertIn("messages", result)
        # We should have at least the welcome message + our 3 messages + 3 system responses
        self.assertGreaterEqual(len(result["messages"]), 7)
        
        # Check if the limit parameter works
        limit_res = self.client.get(f"/api/chat/session/{session_id}/messages?limit=2")
        limit_result = json.loads(limit_res.data)
        self.assertEqual(len(limit_result["messages"]), 2)
        self.assertTrue(limit_result["has_more"])
    
    def test_end_chat_session(self):
        """Test API can end an active chat session (PUT /api/chat/session/<session_id>/end)"""
        # First start a session
        start_res = self.client.post(
            "/api/chat/session",
            data=json.dumps({"phone_number": self.profile["phone_number"]}),
            content_type="application/json"
        )
        start_result = json.loads(start_res.data)
        session_id = start_result["session_id"]
        
        # End the session
        res = self.client.put(f"/api/chat/session/{session_id}/end")
        self.assertEqual(res.status_code, 200)
        result = json.loads(res.data)
        
        # Verify the session is marked as closed
        self.assertEqual(result["status"], "closed")
        self.assertIsNotNone(result["ended_at"])
        self.assertEqual(result["stage"]["current_stage"], "farewell")
    
    def test_end_nonexistent_session(self):
        """Test API handles ending a nonexistent session"""
        res = self.client.put("/api/chat/session/nonexistent/end")
        self.assertEqual(res.status_code, 404)
        result = json.loads(res.data)
        self.assertIn("error", result)
    
    def test_reservation_flow(self):
        """Test the complete reservation flow including matched cars and reservation info"""
        # Start a session
        start_res = self.client.post(
            "/api/chat/session",
            data=json.dumps({"phone_number": self.profile["phone_number"]}),
            content_type="application/json"
        )
        start_result = json.loads(start_res.data)
        session_id = start_result["session_id"]
        
        # Send messages to simulate a reservation flow
        messages = [
            "I'm looking for an electric SUV",
            "Yes, I'd like to test drive the Tesla Model Y",
            "I can come tomorrow at 2 PM",
            "My name is John Zhang"
        ]
        
        for message in messages:
            res = self.client.post(
                "/api/chat/message",
                data=json.dumps({
                    "session_id": session_id,
                    "message": message
                }),
                content_type="application/json"
            )
            result = json.loads(res.data)
            
            # Verify matched cars are being tracked
            self.assertIn("matched_car_models", result)
            self.assertIsInstance(result["matched_car_models"], list)
            
            # Verify reservation info is being updated
            self.assertIn("reservation_info", result)
            reservation_info = result["reservation_info"]
            self.assertIsInstance(reservation_info, dict)
            
            # If we"re in the final stages, verify reservation details
            if result["stage"]["current_stage"] in ["reservation_confirmation", "farewell"]:
                self.assertNotEqual(reservation_info["test_driver"], "")
                self.assertNotEqual(reservation_info["reservation_date"], "")
                self.assertNotEqual(reservation_info["reservation_time"], "")
                self.assertNotEqual(reservation_info["reservation_location"], "")
                self.assertNotEqual(reservation_info["reservation_phone_number"], "")
                self.assertNotEqual(reservation_info["salesman"], "")
                
                # Verify Tesla Model Y is in matched cars
                self.assertIn("Tesla Model Y", result["matched_car_models"])
    
    def test_send_message_after_session_end(self):
        """Test API handles sending message to an ended session"""
        # First start a session
        start_res = self.client.post(
            "/api/chat/session",
            data=json.dumps({"phone_number": self.profile["phone_number"]}),
            content_type="application/json"
        )
        start_result = json.loads(start_res.data)
        session_id = start_result["session_id"]
        
        # End the session
        self.client.put(f"/api/chat/session/{session_id}/end")
        
        # Try to send a message
        res = self.client.post(
            "/api/chat/message",
            data=json.dumps({
                "session_id": session_id,
                "message": "Hello again"
            }),
            content_type="application/json"
        )
        self.assertEqual(res.status_code, 400)
        result = json.loads(res.data)
        self.assertIn("error", result)
        self.assertIn("not active", result["error"])


if __name__ == "__main__":
    unittest.main() 