#!/usr/bin/env python
"""
AutoVend API main entry point
Run this script to start the AutoVend backend server
"""

import os
import sys

# Add the AiModel directory to sys.path to resolve its internal modules
# This assumes run.py is in the BackEnd directory
project_root = os.path.dirname(os.path.abspath(__file__))
ai_model_dir = os.path.join(project_root, 'app', 'models', 'AiModel')
if ai_model_dir not in sys.path:
    sys.path.insert(0, ai_model_dir)

from app import create_app

# Get environment configuration
config_name = os.getenv("FLASK_CONFIG", "default")
port = int(os.getenv("PORT", 5000))

# Create the application
app = create_app(config_name)

if __name__ == "__main__":
    # Start the Flask development server
    print(f"Starting AutoVend API server on port {port}...")
    print(f"Configuration: {config_name}")
    app.run(host="0.0.0.0", port=port, debug=True) 