import unittest
import json
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.config import Config

class ProfileAPITestCase(unittest.TestCase):
    """Test case for the user profile API"""
    
    def setUp(self):
        """Set up the test client and other test variables"""
        self.app = create_app("testing")
        self.client = self.app.test_client()
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
    
    def test_get_default_profile(self):
        """Test API can get default user profile (GET /api/profile/default)"""
        res = self.client.get("/api/profile/default")
        self.assertEqual(res.status_code, 200)
        result = json.loads(res.data)
        self.assertIn("phone_number", result)
        self.assertIn("age", result)
        self.assertIn("user_title", result)
        self.assertIn("target_driver", result)
        self.assertIn("expertise", result)
        self.assertIn("additional_information", result)
        self.assertIn("connection_information", result)
    
    def test_create_profile(self):
        """Test API can create a user profile (POST /api/profile)"""
        res = self.client.post(
            "/api/profile",
            data=json.dumps(self.profile),
            content_type="application/json"
        )
        self.assertEqual(res.status_code, 201)
        result = json.loads(res.data)
        self.assertEqual(result["phone_number"], self.profile["phone_number"])
    
    def test_create_profile_validation(self):
        """Test API validates required fields when creating a profile"""
        # Missing required fields
        invalid_profile = {
            "phone_number": "987654321",
            "name": "Alice"
        }
        res = self.client.post(
            "/api/profile",
            data=json.dumps(invalid_profile),
            content_type="application/json"
        )
        self.assertEqual(res.status_code, 400)
        result = json.loads(res.data)
        self.assertIn("error", result)
        self.assertIn("details", result)
        self.assertGreater(len(result["details"]), 0)
    
    def test_get_profile(self):
        """Test API can get a single user profile by phone number (GET /api/profile/<phone_number>)"""
        # First create a profile
        self.client.post(
            "/api/profile",
            data=json.dumps(self.profile),
            content_type="application/json"
        )
        
        # Then get the profile
        res = self.client.get(f"/api/profile/{self.profile["phone_number"]}")
        self.assertEqual(res.status_code, 200)
        result = json.loads(res.data)
        self.assertEqual(result["phone_number"], self.profile["phone_number"])
    
    def test_get_nonexistent_profile(self):
        """Test API returns 404 for nonexistent profile"""
        res = self.client.get("/api/profile/nonexistent")
        self.assertEqual(res.status_code, 404)
    
    def test_update_profile(self):
        """Test API can update an existing profile (PUT /api/profile/<phone_number>)"""
        # First create a profile
        self.client.post(
            "/api/profile",
            data=json.dumps(self.profile),
            content_type="application/json"
        )
        
        # Update the profile
        updated_profile = self.profile.copy()
        updated_profile["age"] = "35-50"
        updated_profile["expertise"] = "8"
        
        res = self.client.put(
            f"/api/profile/{self.profile["phone_number"]}",
            data=json.dumps(updated_profile),
            content_type="application/json"
        )
        self.assertEqual(res.status_code, 200)
        result = json.loads(res.data)
        self.assertEqual(result["age"], updated_profile["age"])
        self.assertEqual(result["expertise"], updated_profile["expertise"])
    
    def test_duplicate_profile(self):
        """Test API prevents creating duplicate profiles with same phone number"""
        # Create the first profile
        self.client.post(
            "/api/profile",
            data=json.dumps(self.profile),
            content_type="application/json"
        )
        
        # Try to create a duplicate
        res = self.client.post(
            "/api/profile",
            data=json.dumps(self.profile),
            content_type="application/json"
        )
        self.assertEqual(res.status_code, 409)  # Conflict
        result = json.loads(res.data)
        self.assertIn("error", result)
        self.assertIn("already exists", result["error"])
    
    def test_validate_title_format(self):
        """Test API validates user_title format"""
        # Invalid title format
        invalid_profile = self.profile.copy()
        invalid_profile["user_title"] = "Master Zhang"  # Should be Mr., Mrs., Miss., or Ms.
        
        res = self.client.post(
            "/api/profile",
            data=json.dumps(invalid_profile),
            content_type="application/json"
        )
        self.assertEqual(res.status_code, 400)
        result = json.loads(res.data)
        self.assertIn("error", result)
        self.assertIn("details", result)
        title_error = any("title" in error.lower() for error in result["details"])
        self.assertTrue(title_error)
    
    def test_validate_expertise_range(self):
        """Test API validates expertise is between 0 and 10"""
        # Invalid expertise range
        invalid_profile = self.profile.copy()
        invalid_profile["expertise"] = "15"  # Should be 0-10
        
        res = self.client.post(
            "/api/profile",
            data=json.dumps(invalid_profile),
            content_type="application/json"
        )
        self.assertEqual(res.status_code, 400)
        result = json.loads(res.data)
        self.assertIn("error", result)
        self.assertIn("details", result)
        expertise_error = any("expertise" in error.lower() for error in result["details"])
        self.assertTrue(expertise_error)


if __name__ == "__main__":
    unittest.main() 