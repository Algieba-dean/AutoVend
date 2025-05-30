import os
from app.storage.file_storage import FileStorage

# Try to import dotenv, but don't fail if it's not available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # If dotenv is not available, just continue without it
    pass

class Config:
    """Base configuration class for AutoVend API"""
    SECRET_KEY = os.getenv("SECRET_KEY", "default-dev-key")
    DEBUG = False
    TESTING = False
    
    # Initialize storage
    storage = FileStorage(os.getenv("STORAGE_DIR", "storage"))


class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True


class TestingConfig(Config):
    """Testing configuration"""
    DEBUG = True
    TESTING = True


class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False


# Configuration dictionary
config = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig
} 