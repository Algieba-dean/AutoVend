# AutoVend Backend

A Flask-based backend for AutoVend, a voice-based car sales assistant that simulates a conversation via text exchange.

## Features

- User profile management
- Chat session management
- Voice call simulation through text exchange

## API Documentation

The API documentation is available in `Interface.md`.

## Project Structure

```
app/
  models/         # Data models
  routes/         # API routes
  utils/          # Utility functions
  __init__.py     # Application factory
  config.py       # Configuration settings
run.py            # Main entry point
```

## Setup

1. Clone the repository
2. Create a virtual environment and activate it:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install the required packages:
   ```
   pip install -r requirements.txt
   ```
4. Run the application:
   ```
   python run.py
   ```

## Environment Variables

You can configure the application using the following environment variables:

- `FLASK_CONFIG`: Configuration environment (default, development, testing, production)
- `SECRET_KEY`: Secret key for session management
- `PORT`: Port to run the application on (default: 5000)

## API Endpoints

### User Profile Configuration

- `GET /api/profile/default` - Get default user configuration
- `GET /api/profile/{phone_number}` - Get user profile by phone number
- `POST /api/profile` - Create a new user profile
- `PUT /api/profile/{phone_number}` - Update an existing user profile

### Chat Functionality

- `POST /api/chat/session` - Start a new chat session
- `POST /api/chat/message` - Send a message in an active chat session
- `GET /api/chat/session/{session_id}/messages` - Get messages from a chat session
- `PUT /api/chat/session/{session_id}/end` - End an active chat session 