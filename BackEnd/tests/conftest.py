import pytest
import os
import sys
import json

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.config import Config
from app.models.profile import UserProfile

@pytest.fixture
def app():
    """Create and configure a Flask app for testing"""
    app = create_app('testing')
    
    # Establish application context
    with app.app_context():
        yield app
    
    # Reset all storage after test
    Config.USER_PROFILES = {}
    Config.CHAT_SESSIONS = {}
    Config.CHAT_MESSAGES = {}

@pytest.fixture
def client(app):
    """A test client for the app"""
    return app.test_client()

@pytest.fixture
def sample_profile():
    """Sample user profile for testing"""
    return {
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

@pytest.fixture
def registered_profile(client, sample_profile):
    """Create a profile and return the data"""
    response = client.post(
        '/api/profile',
        data=json.dumps(sample_profile),
        content_type='application/json'
    )
    return sample_profile

@pytest.fixture
def chat_session(client, registered_profile):
    """Create a chat session and return the session ID"""
    response = client.post(
        '/api/chat/session',
        data=json.dumps({"phone_number": registered_profile["phone_number"]}),
        content_type='application/json'
    )
    return json.loads(response.data)["session_id"] 