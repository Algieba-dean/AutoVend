import os
from flask import Flask
from flask_cors import CORS
from app.config import Config

def create_app(config_name="default"):
    """Create and configure the Flask application"""
    app = Flask(__name__)
    
    # Load configuration
    app.config.update(Config.get_api_config())
    
    # Enable CORS
    CORS(app)
    
    # Register blueprints
    from app.routes.profile import profile_bp
    from app.routes.chat import chat_bp
    from app.routes.test_drive import test_drive_bp
    
    app.register_blueprint(profile_bp)
    app.register_blueprint(chat_bp)
    app.register_blueprint(test_drive_bp)
    
    # Simple index route
    @app.route("/")
    def index():
        return {"message": "Welcome to AutoVend API", "status": "running"}
    
    return app 