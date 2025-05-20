# Initialize the routes package
from app.routes.chat import chat_bp
from app.routes.profile import profile_bp
from app.routes.test_drive import test_drive_bp

def register_blueprints(app):
    """Register all blueprints with the Flask app"""
    app.register_blueprint(chat_bp)
    app.register_blueprint(profile_bp)
    app.register_blueprint(test_drive_bp) 