import os
from flask import Flask
from flask_cors import CORS
from app.config import config

def create_app(config_name='default'):
    """Create and configure the Flask application"""
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    
    # Enable CORS
    CORS(app)
    
    # Register blueprints
    from app.routes.profile import profile_bp
    from app.routes.chat import chat_bp
    
    app.register_blueprint(profile_bp)
    app.register_blueprint(chat_bp)
    
    # Simple index route
    @app.route('/')
    def index():
        return {"message": "Welcome to AutoVend API", "status": "running"}
    
    return app 