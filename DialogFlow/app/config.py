"""
Application configuration settings.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Base directory
BASE_DIR = Path(__file__).resolve().parent.parent

# API Configuration
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
OPENAI_MODEL = os.getenv('OPENAI_MODEL', 'gpt-3.5-turbo-1106')

# Application Settings
APP_ENVIRONMENT = os.getenv('APP_ENVIRONMENT', 'development')
DEBUG = os.getenv('DEBUG', 'True').lower() in ('true', '1', 't')
APP_SECRET_KEY = os.getenv('APP_SECRET_KEY', 'default_secret_key_for_development')

# Server Settings
HOST = os.getenv('HOST', '0.0.0.0')
PORT = int(os.getenv('PORT', '8000'))

# Data Directories
DATA_DIR = os.path.join(BASE_DIR, 'app', 'data')
SESSIONS_DIR = os.path.join(DATA_DIR, 'sessions')
USER_PROFILES_DIR = os.path.join(DATA_DIR, 'profiles')
NEEDS_DIR = os.path.join(DATA_DIR, 'needs')
VEHICLES_DIR = os.path.join(DATA_DIR, 'vehicles')

# Ensure data directories exist
for directory in [DATA_DIR, SESSIONS_DIR, USER_PROFILES_DIR, NEEDS_DIR, VEHICLES_DIR]:
    os.makedirs(directory, exist_ok=True)

# Car related settings
CAR_LABELS_FILE = os.path.join(DATA_DIR, 'car_labels.toml')

# User Profile Constants
USER_TITLE_OPTIONS = ["Mr.", "Mrs.", "Miss", "Ms."]
TARGET_DRIVER_OPTIONS = ["Self", "Spouse", "Child", "Parent", "Friend", "Other"]
EXPERTISE_RANGE = range(0, 11)  # 0-10
PRICE_SENSITIVITY_OPTIONS = ["High", "Medium", "Low"]

# System prompts for OpenAI
SYSTEM_PROMPTS = {
    "welcome": """You are AutoVend, an intelligent automotive sales assistant. 
Your goal is to help customers find the perfect vehicle for their needs. 
Be friendly, professional, and helpful. Ask for information that will help you understand the customer's requirements.
Extract information about the customer, such as their name, title (Mr./Mrs./Ms.), and basic demographic information if mentioned.
When greeting a returning customer, reference their previous interactions if they exist.
Always maintain a polite and respectful tone.""",
    
    "needs_analysis": """You are AutoVend, an intelligent automotive sales assistant currently in the needs analysis phase.
Your goal is to understand the customer's vehicle requirements in detail. 
Ask specific questions about their preferences regarding:
- Budget range
- Vehicle type (sedan, SUV, hatchback, etc.)
- Brand preferences
- Performance requirements
- Special features they need
- How the vehicle will be used (commuting, family, adventure, etc.)
Acknowledge information that has already been provided and focus on filling in the gaps.
Try to understand both explicit and implicit needs.""",
    
    "confirmation": """You are AutoVend, an intelligent automotive sales assistant in the confirmation phase.
Based on the information provided, you are presenting vehicle recommendations to the customer.
Explain why each recommendation matches their stated requirements.
Be open to refining the search if the customer provides additional requirements or feedback.
When the customer shows interest in a specific vehicle, offer more detailed information about that model.
Aim to help the customer reach a decision on which vehicle(s) they would like to test drive or learn more about.""",
    
    "dealership": """You are AutoVend, an intelligent automotive sales assistant in the dealership connection phase.
Your goal is to facilitate the customer's next steps with a dealership.
Offer to schedule a test drive or appointment at a nearby dealership.
Ask if they have any final questions before concluding the conversation.
Thank them for their time and express that you're looking forward to helping them with their vehicle purchase.
Provide contact information for follow-up questions."""
}

# API rate limiting
RATE_LIMIT_WINDOW = 60  # seconds
MAX_REQUESTS_PER_WINDOW = 100

# App configuration
APP_NAME = "AutoVend"

# Paths
USER_PROFILES_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "profiles")
CAR_LABELS_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "CarLabels.toml")

# Create directories if they don't exist
os.makedirs(USER_PROFILES_DIR, exist_ok=True)

# Profile settings
USER_TITLE_OPTIONS = ["Mr.", "Mrs.", "Miss.", "Ms."]
TARGET_DRIVER_OPTIONS = ["Self", "Wife", "Husband", "Partner", "Parents", "Children", "Friend", "Colleague", "Other"]
EXPERTISE_RANGE = range(0, 11)  # 0-10
PRICE_SENSITIVITY_OPTIONS = ["High", "Medium", "Low"]
PARKING_CONDITIONS_OPTIONS = [
    "Allocated Parking Space", 
    "Temporary Parking Allowed", 
    "Charging Pile Facilities Available", 
    "Street Parking Only",
    "Unknown"
]

# Car labels settings
VEHICLE_CATEGORY_OPTIONS = [
    "Micro Sedan", "Compact Sedan", "B-Segment Sedan", 
    "C-Segment Sedan", "D-Segment Sedan", 
    "Compact SUV", "Mid-Size SUV", "Full-Size SUV"
]
BRAND_OPTIONS = ["BMW", "Audi", "Mercedes-Benz", "Toyota", "Honda", "Ford", "Chevrolet", "Nissan", "Hyundai", "Kia"]
SIZE_OPTIONS = ["Small", "Medium", "Large"]
USABILITY_OPTIONS = ["Small", "Medium", "Large"]
AESTHETICS_OPTIONS = ["Low", "Medium", "High"]

# NLP settings
NLP_MODEL = "en_core_web_md"  # Spacy model to use
CONFIDENCE_THRESHOLD = 0.7  # Threshold for accepting entity extractions 