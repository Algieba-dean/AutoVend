# AutoVend API Tests

This directory contains tests for the AutoVend API. The tests are designed to verify that the API implements the specifications defined in the Interface.md document.

## Overview

The tests are organized into two main categories:

1. **User Profile API Tests** - Tests for the user profile configuration endpoints
2. **Chat API Tests** - Tests for the chat functionality endpoints

## Test Coverage

The tests cover all the API endpoints defined in the Interface.md document:

### User Profile API:
- `GET /api/profile/default` - Get default user configuration
- `GET /api/profile/{phone_number}` - Get user profile by phone number
- `POST /api/profile` - Create a new user profile
- `PUT /api/profile/{phone_number}` - Update an existing user profile

### Chat API:
- `POST /api/chat/session` - Start a new chat session
- `POST /api/chat/message` - Send a message in an active chat session
- `GET /api/chat/session/{session_id}/messages` - Get messages from a chat session
- `PUT /api/chat/session/{session_id}/end` - End an active chat session

Additionally, the tests verify key functionality:
- User profile validation
- Chat session management
- Message sending and retrieval
- User needs tracking
- Test drive reservation flow

## Running the Tests

### Automated Tests

To run the automated tests and generate a comprehensive report:

```bash
# From the project root directory
python run_tests.py

# Or from the tests directory
python run_tests.py
```

This will run all tests and generate a report in `tests/report/test_report.json`, which contains details about:
- The number of tests run
- The number of tests passed/failed
- The coverage of API endpoints
- The coverage of key features

### Manual Tests

For interactive testing with a running server:

```bash
# From the project root directory
python run_manual_test.py

# Or from the tests/utils directory
python manual_test.py
```

## Directory Structure

```
tests/
  ├── __init__.py         # Package initialization
  ├── README.md           # This documentation
  ├── conftest.py         # Pytest configuration and fixtures
  ├── run_tests.py        # Test runner script
  ├── test_profile_api.py # Profile API tests
  ├── test_chat_api.py    # Chat API tests
  ├── data.py             # Test data definitions
  ├── report/             # Contains test reports
  │   └── test_report.json # Generated test report
  └── utils/              # Test utilities
      └── manual_test.py  # Manual test script
```

## Test Cases

### Profile API Test Cases:
1. Get default profile
2. Create valid profile
3. Create profile with missing required fields
4. Get existing profile by phone number
5. Get non-existent profile
6. Update existing profile
7. Validate duplicate phone numbers are rejected
8. Validate user title format
9. Validate expertise range (0-10)

### Chat API Test Cases:
1. Start chat session with valid phone number
2. Start chat session with invalid phone number
3. Send chat message in active session
4. Track user needs from chat messages
5. Send message to non-existent session
6. Retrieve messages from session
7. Test message limit parameter
8. End chat session
9. Test reservation flow from needs to confirmation
10. Send message to ended session

## Testing Notes

- The tests use in-memory storage instead of a database, as specified in the application design.
- Tests reset the application state before each test to ensure test isolation.
- Failure and error details are logged in the test report for easier debugging. 