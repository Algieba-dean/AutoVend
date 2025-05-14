import os
from app import create_app

# Create the Flask application instance
app = create_app(os.getenv('FLASK_CONFIG', 'default'))

if __name__ == '__main__':
    # Run the application
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port) 