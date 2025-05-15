#!/usr/bin/env python
"""
AutoVend API main entry point
Run this script to start the AutoVend backend server
"""

import os
from app import create_app

# Get environment configuration
config_name = os.getenv('FLASK_CONFIG', 'default')
port = int(os.getenv('PORT', 5000))

# Create the application
app = create_app(config_name)

if __name__ == '__main__':
    # Start the Flask development server
    print(f"Starting AutoVend API server on port {port}...")
    print(f"Configuration: {config_name}")
    app.run(host='0.0.0.0', port=port, debug=True) 