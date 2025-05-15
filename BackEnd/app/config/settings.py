import os
from typing import Dict, Any

class Settings:
    """Application settings"""
    
    # Storage settings
    STORAGE_CONFIG = {
        'storage_dir': os.getenv('STORAGE_DIR', 'storage'),
        'max_session_age_days': 7
    }
    
    # Dialog settings
    DIALOG_CONFIG = {
        'welcome_messages_path': 'config/welcome_messages.json',
        'max_message_length': 1000,
        'response_timeout': 30,  # seconds
        'cache_size': 1000,
        'cache_ttl': 3600  # 1 hour
    }
    
    # Stage settings
    STAGE_CONFIG = {
        'max_stage_duration': 1800,  # 30 minutes
        'stage_timeout': 300  # 5 minutes
    }
    
    # API settings
    API_CONFIG = {
        'host': os.getenv('API_HOST', '0.0.0.0'),
        'port': int(os.getenv('API_PORT', '5000')),
        'debug': os.getenv('API_DEBUG', 'False').lower() == 'true'
    }
    
    # Logging settings
    LOGGING_CONFIG = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'standard': {
                'format': '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
            },
        },
        'handlers': {
            'default': {
                'level': 'INFO',
                'formatter': 'standard',
                'class': 'logging.StreamHandler',
            },
            'file': {
                'level': 'INFO',
                'formatter': 'standard',
                'class': 'logging.FileHandler',
                'filename': 'logs/autovend.log',
                'mode': 'a',
            },
        },
        'loggers': {
            '': {
                'handlers': ['default', 'file'],
                'level': 'INFO',
                'propagate': True
            }
        }
    }
    
    @classmethod
    def get_all(cls) -> Dict[str, Any]:
        """Get all settings as a dictionary"""
        return {
            'storage': cls.STORAGE_CONFIG,
            'dialog': cls.DIALOG_CONFIG,
            'stage': cls.STAGE_CONFIG,
            'api': cls.API_CONFIG,
            'logging': cls.LOGGING_CONFIG
        }
    
    @classmethod
    def get_storage_config(cls) -> Dict[str, Any]:
        """Get storage configuration"""
        return cls.STORAGE_CONFIG
    
    @classmethod
    def get_dialog_config(cls) -> Dict[str, Any]:
        """Get dialog configuration"""
        return cls.DIALOG_CONFIG
    
    @classmethod
    def get_stage_config(cls) -> Dict[str, Any]:
        """Get stage configuration"""
        return cls.STAGE_CONFIG
    
    @classmethod
    def get_api_config(cls) -> Dict[str, Any]:
        """Get API configuration"""
        return cls.API_CONFIG
    
    @classmethod
    def get_logging_config(cls) -> Dict[str, Any]:
        """Get logging configuration"""
        return cls.LOGGING_CONFIG 