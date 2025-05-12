# AutoVend

AutoVend is an intelligent automotive sales AI agent system designed to automatically extract user information and analyze car purchase requirements from chat conversations, providing personalized vehicle recommendations.

## Features

- **Intelligent User Profiling**: Extracts and manages user information from conversations
- **Advanced Needs Analysis**: Identifies both explicit and implicit car purchase requirements
- **Dynamic Dialogue Management**: Supports multi-stage conversations with context awareness
- **Recommendation Engine**: Suggests suitable vehicles based on user profiles and requirements
- **RESTful API**: Provides a comprehensive API for integration with frontend applications

## Getting Started

### Prerequisites

- Python 3.8+
- pip (Python package manager)

### Installation

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/autovend.git
   cd autovend
   ```

2. Create a virtual environment (optional but recommended):
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows, use: venv\Scripts\activate
   ```

3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

4. Create an environment file:
   ```
   cp env.example .env
   ```

5. Edit the `.env` file to add your OpenAI API key and other configuration settings:
   ```
   OPENAI_API_KEY=your_api_key_here
   ```

### Running the Application

1. Start the server:
   ```
   python run.py
   ```

2. The API will be available at `http://localhost:8000`
3. API documentation is available at `http://localhost:8000/docs`

## API Endpoints

### Chat API

- `POST /api/chat/new` - Create a new chat session
- `GET /api/chat/{session_id}` - Get a chat session by ID
- `POST /api/chat/{session_id}/message` - Send a message to a chat session

### User Profile API

- `GET /api/profile/{profile_id}` - Get a user profile by ID
- `PATCH /api/profile/{profile_id}` - Update a user profile
- `POST /api/profile/{profile_id}/connection` - Add a connection to a user profile

### Car Needs API

- `GET /api/needs/{profile_id}` - Get car needs for a user profile
- `POST /api/needs/{profile_id}` - Add a need to a user's car requirements
- `DELETE /api/needs/{profile_id}/{category}` - Remove a need from a user's car requirements

## Project Structure

```
autovend/
├── app/                    # Application code
│   ├── data/               # Data storage
│   │   ├── sessions/       # Chat session data
│   │   ├── profiles/       # User profile data
│   │   ├── needs/          # Car needs data
│   │   └── vehicles/       # Vehicle data
│   ├── models/             # Data models
│   ├── services/           # Business logic
│   ├── routes/             # API routes
│   ├── utils/              # Utility functions
│   ├── config.py           # Configuration
│   └── main.py             # Application entry point
├── env.example             # Environment variables template
├── requirements.txt        # Dependencies
├── run.py                  # Script to run the application
└── README.md               # This file
```

## Development

### Adding New Features

1. Create appropriate models in `app/models/`
2. Implement business logic in `app/services/`
3. Add API endpoints in `app/routes/`
4. Update documentation

## License

This project is licensed under the MIT License - see the LICENSE file for details. 