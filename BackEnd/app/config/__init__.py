from app.config.settings import Settings
from app.storage.file_storage import FileStorage

class Config:
    """Application configuration wrapper"""
    
    # Initialize storage
    storage = FileStorage()
    
    @classmethod
    def get_all(cls):
        """Get all settings"""
        return Settings.get_all()
    
    @classmethod
    def get_storage_config(cls):
        """Get storage configuration"""
        return Settings.get_storage_config()
    
    @classmethod
    def get_dialog_config(cls):
        """Get dialog configuration"""
        return Settings.get_dialog_config()
    
    @classmethod
    def get_stage_config(cls):
        """Get stage configuration"""
        return Settings.get_stage_config()
    
    @classmethod
    def get_api_config(cls):
        """Get API configuration"""
        return Settings.get_api_config()
    
    @classmethod
    def get_logging_config(cls):
        """Get logging configuration"""
        return Settings.get_logging_config() 