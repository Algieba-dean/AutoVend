# AutoVend User Manual

## 1. System Overview

AutoVend is an intelligent automotive sales AI agent system designed to automatically extract user information and analyze car purchase requirements through chat records, providing personalized vehicle recommendations for customers. The system can intelligently distinguish between explicit and implicit needs, and provide precise car purchase suggestions based on user feature tags.

## 2. System Access

### 2.1 API Access

The system provides RESTful API interfaces, accessible via:

- Base URL: `http://{server_host}:{port}/api`
- API Documentation: `http://{server_host}:{port}/docs`

### 2.2 Permission Requirements

- Basic Queries: No special permissions required
- User Profile Management: Administrator permissions required
- System Configuration: Administrator permissions required

## 3. Main Functions

### 3.1 Chat Dialogue

#### 3.1.1 Create New Session

**Request Method**: POST `/api/chat/new`

**Parameters**:
- `phone_number`: User phone number (optional)

**Example**:
```json
{
  "phone_number": "13800138000"
}
```

**Response**:
```json
{
  "session_id": "f8d7e9c3-5b2a-4c1a-8f9e-3a6b2c5d4e7f",
  "messages": [
    {
      "message_id": "a1b2c3d4-e5f6-7a8b-9c0d-1e2f3a4b5c6d",
      "content": "Hello! Welcome to AutoVend. How should I address you? Sir, Madam, or Miss?",
      "sender": "system",
      "timestamp": "2023-11-20T15:30:45.123456"
    }
  ],
  "profile_id": null,
  "stage": "welcome"
}
```

#### 3.1.2 Send Message

**Request Method**: POST `/api/chat/{session_id}/message`

**Parameters**:
- `session_id`: Session ID (path parameter)
- `content`: Message content
- `sender`: Sender (default is "user")

**Example**:
```json
{
  "content": "Hello, I am Mr. Zhang. I want to buy an SUV with a budget of around 300,000 yuan."
}
```

**Response**:
```json
{
  "session_id": "f8d7e9c3-5b2a-4c1a-8f9e-3a6b2c5d4e7f",
  "messages": [
    {
      "message_id": "a1b2c3d4-e5f6-7a8b-9c0d-1e2f3a4b5c6d",
      "content": "Hello! Welcome to AutoVend. How should I address you? Sir, Madam, or Miss?",
      "sender": "system",
      "timestamp": "2023-11-20T15:30:45.123456"
    },
    {
      "message_id": "b2c3d4e5-f6a7-8b9c-0d1e-2f3a4b5c6d7e",
      "content": "Hello, I am Mr. Zhang. I want to buy an SUV with a budget of around 300,000 yuan.",
      "sender": "user",
      "timestamp": "2023-11-20T15:31:15.654321"
    },
    {
      "message_id": "c3d4e5f6-a7b8-9c0d-1e2f-3a4b5c6d7e8f",
      "content": "Hello, Mr. Zhang! Thank you very much for your information. Is this SUV mainly for your own use, or are you purchasing it for a family member?",
      "sender": "system",
      "timestamp": "2023-11-20T15:31:16.123456"
    }
  ],
  "profile_id": "e9f8d7c6-5b4a-3c2a-1f9e-7a6b4c5d2e3f",
  "stage": "welcome"
}
```

#### 3.1.3 Get Session Information

**Request Method**: GET `/api/chat/{session_id}`

**Parameters**:
- `session_id`: Session ID (path parameter)

**Response**: Same format as the send message response

### 3.2 User Profile Management

#### 3.2.1 Get User Profile

**Request Method**: GET `/api/profile/{profile_id}`

**Parameters**:
- `profile_id`: User profile ID (path parameter)

**Response**:
```json
{
  "profile_id": "e9f8d7c6-5b4a-3c2a-1f9e-7a6b4c5d2e3f",
  "phone_number": "13800138000",
  "age": "30-40",
  "user_title": "Mr.",
  "name": "Zhang",
  "target_driver": "Self",
  "expertise": 3,
  "family_size": 3,
  "price_sensitivity": "Medium",
  "residence": "China+Beijing+Chaoyang",
  "parking_conditions": "Allocated Parking Space",
  "tags": {
    "Age Group": "Middle-aged",
    "Tech Comfort": "Medium",
    "Urban Driving": "High",
    "Parking Ease": "High, Implicit"
  },
  "connections": [],
  "created_at": "2023-11-20T15:31:15.654321",
  "updated_at": "2023-11-20T15:35:22.123456"
}
```

#### 3.2.2 Update User Profile

**Request Method**: PATCH `/api/profile/{profile_id}`

**Parameters**:
- `profile_id`: User profile ID (path parameter)
- Fields to be updated and their values

**Example**:
```json
{
  "family_size": 4,
  "residence": "China+Shanghai+Pudong"
}
```

**Response**: Complete updated user profile

#### 3.2.3 Add User Association

**Request Method**: POST `/api/profile/{profile_id}/connection`

**Parameters**:
- `profile_id`: User profile ID (path parameter)
- `connection_phone_number`: Associated user's phone number
- `connection_id_relationship`: Description of the association relationship

**Example**:
```json
{
  "connection_phone_number": "13900139000",
  "connection_id_relationship": "Wife"
}
```

**Response**: Complete updated user profile

### 3.3 Requirement Management

#### 3.3.1 Get Requirement Information

**Request Method**: GET `/api/needs/{profile_id}`

**Parameters**:
- `profile_id`: User profile ID (path parameter)

**Response**:
```json
{
  "profile_id": "e9f8d7c6-5b4a-3c2a-1f9e-7a6b4c5d2e3f",
  "needs": {
    "budget": "300000",
    "vehicle_category_bottom": ["SUV"],
    "brand": ["Toyota", "Honda"],
    "size": "Medium, Implicit",
    "safety_features": ["Advanced Safety Package, Implicit"]
  }
}
```

#### 3.3.2 Add Requirement

**Request Method**: POST `/api/needs/{profile_id}`

**Parameters**:
- `profile_id`: User profile ID (path parameter)
- `category`: Requirement category
- `value`: Requirement value
- `is_implicit`: Whether it's an implicit requirement (default is false)

**Example**:
```json
{
  "category": "color",
  "value": "Black",
  "is_implicit": false
}
```

**Response**: Complete updated requirement information

#### 3.3.3 Delete Requirement

**Request Method**: DELETE `/api/needs/{profile_id}/{category}`

**Parameters**:
- `profile_id`: User profile ID (path parameter)
- `category`: Requirement category (path parameter)
- `value`: Requirement value (query parameter, for list-type requirements)

**Example**:
```
DELETE /api/needs/e9f8d7c6-5b4a-3c2a-1f9e-7a6b4c5d2e3f/brand?value=Honda
```

**Response**: Complete updated requirement information

## 4. Administrator Functions

### 4.1 Offline User Profile Supplementation

Administrators can supplement or modify information for customers who have completed offline processes through the user profile API:

1. Use GET request to retrieve existing user profile
2. Use PATCH request to update fields in the user profile
3. The system will automatically regenerate tags based on the updated information

### 4.2 View System Statistics

Administrators can view system operating statistics, including:

- Number of active sessions
- Total number of user profiles
- Requirement tag distribution
- Recommended vehicle statistics

## 5. Best Practices

### 5.1 Dialogue Techniques

- **Provide Clear Information**: Clearly express budget, preferred brands, models, and other requirements
- **Answer System Questions**: The system will ask targeted questions; answering these questions helps the system better understand your needs
- **Update Requirements Anytime**: You can update or modify your requirements at any time during the conversation

### 5.2 System Features

- **Dynamic User Profiles**: The system dynamically updates your user profile based on conversation content
- **Implicit Requirement Inference**: The system can infer requirements you haven't explicitly stated but may exist
- **Personalized Recommendations**: Provides personalized vehicle recommendations based on your explicit and implicit requirements

## 6. Troubleshooting

### 6.1 Common Issues

1. **System Not Responding**: Check network connection, refresh the page, or restart the application
2. **Session ID Invalid**: Create a new session
3. **Recommendations Not Meeting Expectations**: Provide more specific requirements, or explicitly reject certain recommendation types

### 6.2 Contact Support

For technical issues, please contact the system administrator or technical support team:

- Email: support@autovend.com
- Phone: 400-123-4567

## 7. Privacy Policy

AutoVend values user privacy protection:

- All user data is stored encrypted
- User information is only used to provide vehicle recommendation services
- Without user authorization, user information will not be used for other purposes or shared with third parties

## 8. Update Log

### Version 0.1.0 (2023-11-20)

- Initial version release
- Implemented basic dialogue functionality
- Supports user profile extraction and requirement analysis
- Provides simple vehicle recommendation functionality 