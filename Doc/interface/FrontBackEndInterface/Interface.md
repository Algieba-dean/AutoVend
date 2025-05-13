# Car Sales Website API Interface

## Overview

This document defines the API interface between the frontend and backend of AutoVend. The API simulates a voice call conversation through text exchange and supports user profile configuration management and chat functionalities.

## API Endpoints

### User Profile Configuration

#### 1. Load Default User Configuration

- **Endpoint**: `GET /api/profile/default`
- **Description**: Fetches the default user configuration for new visitors
- **Authentication**: Not required
- **Response**:
  - Status: 200 OK
  - Body:
    ```json
    {
      "phone_number": "",
      "age": "",
      "user_title": "",
      "name": "",
      "target_driver": "",
      "expertise": "",
      "additional_information": {
        "family_size": "",
        "price_sensitivity": "",
        "residence": "",
        "parking_conditions": ""
      },
      "connection_information": {
        "connection_phone_number": "",
        "connection_id_relationship": ""
      }
    }
    ```

#### 2. Load User Configuration

- **Endpoint**: `GET /api/profile/{phone_number}`
- **Description**: Loads an existing user configuration by phone number
- **Parameters**:
  - `phone_number`: Phone number of the user profile (unique identifier)
- **Response**:
  - Status: 200 OK
  - Body: User profile object (same structure as default profile)
  - Status: 404 Not Found
  - Body: `{ "error": "Profile not found" }`

#### 3. Create New User Profile

- **Endpoint**: `POST /api/profile`
- **Description**: Creates a new user profile configuration
- **Request Body**:
  ```json
  {
    "phone_number": "123456789",
    "age": "20-35",
    "user_title": "Mr. Zhang",
    "name": "John",
    "target_driver": "Self",
    "expertise": "5",
    "additional_information": {
      "family_size": "3",
      "price_sensitivity": "Medium",
      "residence": "China+Beijing+Haidian",
      "parking_conditions": "Allocated Parking Space"
    },
    "connection_information": {
      "connection_phone_number": "",
      "connection_id_relationship": ""
    }
  }
  ```
- **Required Fields**: `phone_number`, `age`, `user_title`, `target_driver`, `expertise`
- **Response**:
  - Status: 201 Created
  - Body: Created user profile
  - Status: 400 Bad Request
  - Body: `{ "error": "Validation error", "details": [...] }`
  - Status: 409 Conflict
  - Body: `{ "error": "Phone number already exists" }`

#### 4. Update User Profile

- **Endpoint**: `PUT /api/profile/{phone_number}`
- **Description**: Updates an existing user profile configuration
- **Parameters**:
  - `phone_number`: Phone number of the user profile (unique identifier)
- **Request Body**: Same structure as Create New User Profile
- **Response**:
  - Status: 200 OK
  - Body: Updated user profile
  - Status: 404 Not Found
  - Body: `{ "error": "Profile not found" }`
  - Status: 400 Bad Request
  - Body: `{ "error": "Validation error", "details": [...] }`

### Chat Functionality

#### 1. Start Chat Session

- **Endpoint**: `POST /api/chat/session`
- **Description**: Initiates a new chat session for the user and returns the initial welcome message
- **Request Body**:
  ```json
  {
    "phone_number": "123456789"
  }
  ```
- **Response**:
  - Status: 201 Created
  - Body:
    ```json
    {
      "session_id": "<uuid>",
      "created_at": "2025-06-01T12:34:56Z",
      "status": "active",
      "welcome_message": {
        "message_id": "<uuid>",
        "sender_type": "system",
        "sender_id": "agent_123",
        "content": "Hi I'm AutoVend, your smart assistant! How can I assist you in finding your ideal vehicle today?",
        "timestamp": "2025-06-01T12:34:56Z",
        "status": "delivered"
      },
      "profile": {
        "phone_number": "123456789",
        "age": "20-35",
        "user_title": "Mr. Zhang",
        "name": "John",
        "target_driver": "Self",
        "expertise": "5",
        "additional_information": {
          "family_size": "3",
          "price_sensitivity": "Medium",
          "residence": "China+Beijing+Haidian",
          "parking_conditions": "Allocated Parking Space"
        },
        "connection_information": {
          "connection_phone_number": "",
          "connection_id_relationship": ""
        }
      },
      "stage": {
        "previous_stage": "",
        "current_stage": "welcome"
      },
      "reservation_info": {
        "test_driver": "",
        "reservation_date": "",
        "reservation_time": "",
        "reservation_location": "",
        "reservation_phone_number": "",
        "salesman": ""
      }
    }
    ```
  - Status: 400 Bad Request
  - Body: `{ "error": "Invalid phone_number" }`

#### 2. Send Chat Message

- **Endpoint**: `POST /api/chat/message`
- **Description**: Sends a message in an active chat session and returns the system's response
- **Request Body**:
  ```json
  {
    "session_id": "<uuid>",
    "message": "I'm looking for an electric SUV with good range"
  }
  ```
- **Response**:
  - Status: 200 OK
  - Body:
    ```json
    {
      "user_message": {
        "message_id": "<uuid>",
        "timestamp": "2025-06-01T12:35:00Z",
        "status": "delivered"
      },
      "system_response": {
        "message_id": "<uuid>",
        "sender_type": "system",
        "sender_id": "agent_123",
        "content": "I'd be happy to help you find an electric SUV with good range. Tesla Model Y offers around 330 miles of range, while Ford Mustang Mach-E offers up to 300 miles. Would you like more information about these models or would you prefer other options?",
        "timestamp": "2025-06-01T12:35:05Z",
        "status": "delivered"
      },
      "profile": {
        "phone_number": "123456789",
        "age": "20-35",
        "user_title": "Mr. Zhang",
        "name": "John",
        "target_driver": "Self",
        "expertise": "6",
        "additional_information": {
          "family_size": "3",
          "price_sensitivity": "Medium",
          "residence": "China+Beijing+Haidian",
          "parking_conditions": "Allocated Parking Space"
        },
        "connection_information": {
          "connection_phone_number": "",
          "connection_id_relationship": ""
        }
      },
      "needs": {
        "explicit": {
          "powertrain_type": "Battery Electric Vehicle",
          "vehicle_category_bottom": "Compact SUV",
          "driving_range": "Above 800km"
        },
        "implicit": {
          "energy_consumption_level": "Low"
        }
      },
      "stage": {
        "previous_stage": "welcome",
        "current_stage": "needs_analysis"
      },
      "reservation_info": {
        "test_driver": "",
        "reservation_date": "",
        "reservation_time": "",
        "reservation_location": "",
        "reservation_phone_number": "",
        "salesman": ""
      }
    }
    ```
  - Status: 404 Not Found
  - Body: `{ "error": "Chat session not found" }`
  - Status: 400 Bad Request
  - Body: `{ "error": "Message cannot be empty" }`

#### 3. Receive Chat Messages

- **Endpoint**: `GET /api/chat/session/{session_id}/messages`
- **Description**: Retrieves messages from a chat session
- **Parameters**:
  - `session_id`: UUID of the chat session
  - `since_timestamp` (query, optional): Retrieve messages after this timestamp
  - `limit` (query, optional): Maximum number of messages to retrieve, default 50
- **Response**:
  - Status: 200 OK
  - Body:
    ```json
    {
      "messages": [
        {
          "message_id": "<uuid>",
          "sender_type": "user",
          "sender_id": "<uuid>",
          "content": "I'm looking for an electric SUV with good range",
          "timestamp": "2025-06-01T12:35:00Z"
        },
        {
          "message_id": "<uuid>",
          "sender_type": "system",
          "sender_id": "agent_123",
          "content": "I'd be happy to help you find an electric SUV. Could you tell me your typical daily commute distance?",
          "timestamp": "2025-06-01T12:35:10Z"
        }
      ],
      "has_more": false,
      "profile": {
        "phone_number": "123456789",
        "age": "20-35",
        "user_title": "Mr. Zhang",
        "name": "John",
        "target_driver": "Self",
        "expertise": "6",
        "additional_information": {
          "family_size": "3",
          "price_sensitivity": "Medium",
          "residence": "China+Beijing+Haidian",
          "parking_conditions": "Allocated Parking Space"
        },
        "connection_information": {
          "connection_phone_number": "",
          "connection_id_relationship": ""
        }
      },
      "needs": {
        "explicit": {
          "powertrain_type": "Battery Electric Vehicle",
          "vehicle_category_bottom": "Compact SUV",
          "driving_range": "Above 800km"
        },
        "implicit": {
          "energy_consumption_level": "Low"
        }
      },
      "stage": {
        "previous_stage": "needs_analysis",
        "current_stage": "car_selection_confirmation"
      },
      "reservation_info": {
        "test_driver": "",
        "reservation_date": "",
        "reservation_time": "",
        "reservation_location": "",
        "reservation_phone_number": "",
        "salesman": ""
      }
    }
    ```
  - Status: 404 Not Found
  - Body: `{ "error": "Chat session not found" }`

#### 4. End Chat Session

- **Endpoint**: `PUT /api/chat/session/{session_id}/end`
- **Description**: Ends an active chat session
- **Parameters**:
  - `session_id`: UUID of the chat session
- **Response**:
  - Status: 200 OK
  - Body:
    ```json
    {
      "session_id": "<uuid>",
      "ended_at": "2025-06-01T13:00:00Z",
      "status": "closed",
      "profile": {
        "phone_number": "123456789",
        "age": "20-35",
        "user_title": "Mr. Zhang",
        "name": "John",
        "target_driver": "Self",
        "expertise": "6",
        "additional_information": {
          "family_size": "3",
          "price_sensitivity": "Medium",
          "residence": "China+Beijing+Haidian",
          "parking_conditions": "Allocated Parking Space"
        },
        "connection_information": {
          "connection_phone_number": "",
          "connection_id_relationship": ""
        }
      },
      "needs": {
        "explicit": {
          "powertrain_type": "Battery Electric Vehicle",
          "vehicle_category_bottom": "Compact SUV",
          "driving_range": "Above 800km",
          "brand": "Tesla",
          "prize": "40,000~60,000"
        },
        "implicit": {
          "energy_consumption_level": "Low",
          "size": "Medium",
          "family_friendliness": "High"
        }
      },
      "stage": {
        "previous_stage": "reservation_confirmation",
        "current_stage": "farewell"
      },
      "reservation_info": {
        "test_driver": "Mr. Zhang",
        "reservation_date": "2025-06-05",
        "reservation_time": "14:00",
        "reservation_location": "Tesla Beijing Haidian Store",
        "reservation_phone_number": "123456789",
        "salesman": "David Chen"
      }
    }
    ```
  - Status: 404 Not Found
  - Body: `{ "error": "Chat session not found" }`
  - Status: 400 Bad Request
  - Body: `{ "error": "Session already ended" }`

## Data Structures

### User Profile

```
BasicInformation:
  phone_number: Required, string format (unique identifier for the user)
  age: Required, string format (e.g., "20-35")
  user_title: Required, enum: "Mr.", "Mrs.", "Miss.", "Ms.", should be formatted like "Mr. Zhang"
  name: Optional, string format
  target_driver: Required, enum: "Self", "Wife", "Parents", etc.
  expertise: Required, number from 0 to 10 (string format) to indicate knowledge level about cars

AdditionalInformation:
  family_size: Optional, number (string format)
  price_sensitivity: Optional, enum: "High", "Medium", "Low"
  residence: Optional, string format "country+province+city"
  parking_conditions: Optional, enum: "Allocated Parking Space", "Temporary Parking Allowed", "Charging Pile Facilities Available"

ConnectionInformation:
  connection_phone_number: Optional, string format
  connection_id_relationship: Optional, string format describing relationship
```

### User Profile Field Details

#### Basic Information
| Field | Type | Required | Description | Candidate Values |
|-------|------|----------|-------------|-----------------|
| phone_number | String | Yes | Unique identifier for user profile | Any valid phone number |
| age | String | Yes | Age range of the user | Example: "20-35" |
| user_title | String | Yes | Title with honorific | "Mr.", "Mrs.", "Miss.", "Ms." (format: "Mr. Zhang") |
| name | String | No | Full name of the user | Any name string |
| target_driver | String | Yes | Person who will drive the car | "Self", "Wife", "Parents", etc. |
| expertise | String (Number) | Yes | Car knowledge level | Number from 0 to 10 |

#### Additional Information
| Field | Type | Required | Description | Candidate Values |
|-------|------|----------|-------------|-----------------|
| family_size | String (Number) | No | Number of family members | Any numeric value |
| price_sensitivity | String | No | User's price sensitivity | "High", "Medium", "Low" |
| residence | String | No | User's location | Format: "country+province+city" |
| parking_conditions | String | No | Available parking facilities | "Allocated Parking Space", "Temporary Parking Allowed", "Charging Pile Facilities Available" |

#### Connection Information
| Field | Type | Required | Description | Candidate Values |
|-------|------|----------|-------------|-----------------|
| connection_phone_number | String | No | Phone number of connection | Any valid phone number |
| connection_id_relationship | String | No | Relationship to connection | Any relationship description |

### Car Needs/Requirements

The needs structure represents the car requirements and preferences derived from the conversation.

```
needs:
  explicit: Object containing requirements explicitly mentioned by the user
  implicit: Object containing requirements implicitly derived from the conversation
  key_details: Optional, string with additional details
```

### Car Needs Fields

All car need fields can appear in either explicit or implicit categories depending on how they were determined during the conversation. Explicit needs are directly mentioned by the user, while implicit needs are inferred by the system.

| Field | Type | Required | Description | Candidate Values |
|-------|------|----------|-------------|-----------------|
| prize | String | No | Price range | "Below 10,000", "10,000~20,000", "20,000~30,000", "30,000~40,000", "40,000~60,000", "60,000~100,000", "Above 100,000" |
| vehicle_category_bottom | String | No | Vehicle type/category | "Micro Sedan", "Compact Sedan", "B-Segment Sedan", "C-Segment Sedan", "D-Segment Sedan", "Compact SUV", "Mid-Size SUV", "Mid-to-Large SUV", "Off-road SUV", "All-terrain SUV", "Compact MPV", "Mid-Size MPV", "Large MPV", "Mid-Size Business MPV", "Large-Size Busness MPV", "Two-door Convertible Sprots Car", "Four-door Convertible Sprots Car", "Two-door Hardtop Sports Car", "Four-door Hardtop Sports Car" |
| brand | String | No | Car manufacturer | "Volkswagen", "Audi", "Porsche", "Bentley", "Bugatti", "Lamborghini", "BMW", "Mercedes-Benz", "Peugeot", "Renault", "Jaguar", "Land Rover", "Rolls-Royce", "Volvo", "Chevrolet", "Buick", "Cadillac", "Ford", "Tesla", "Toyota", "Honda", "Nissan", "Suzuki", "Mazda", "Hyundai", "BYD", "Geely", "Changan", "Great Wall Motor", "Nio", "XiaoMi", "XPeng" |
| powertrain_type | String | No | Engine/motor type | "Gasoline Engine", "Diesel Engine", "Hybrid Electric Vehicle", "Plug-in Hybird Electric Vehicle", "Range-Extended Electric Vehicle", "Battery Electric Vehicle" |
| passenger_sapce_volume | String | No | Interior space | "2.5~3.5 cubic meter", "3.5~4.5 cubic meter", "4.5~5.5 cubic meter", "Above 5.5 cubic meter" |
| trunk_volume | String | No | Cargo space | "200~300L", "300~400L", "400~500L", "Above 500L" |
| wheelbase | String | No | Distance between wheel centers | "2300~2650mm", "2650~2800mm", "2800~2950mm", "2950~3100mm", "Above 3100mm" |
| chassis_height | String | No | Ground clearance | "100~130mm", "130~150mm", "150~200mm", "Above 200mm" |
| design_style | String | No | Vehicle style | "Sporty", "Business" |
| body_line_smoothness | String | No | Exterior styling characteristic | "High", "Medium", "Low" |
| color | String | No | Exterior color preference | "Bright Colors", "Neutral Colors", "Dark Colors" |
| interior_material_texture | String | No | Interior finish | "Wood Trim", "Metal Trim" |
| ABS | String | No | Anti-lock Braking System | "Yes", "No" |
| ESP | String | No | Electronic Stability Program | "Yes", "No" |
| airbag_count | String | No | Number of airbags | "2", "4", "6", "8", "10", "Above 10" |
| seat_material | String | No | Seat upholstery | "Leather", "Fabric" |
| noise_insulation | String | No | Sound dampening quality | "High", "Medium", "Low" |
| voice_interaction | String | No | Voice command support | "Yes", "No" |
| ota_updates | String | No | Over-the-air software updates | "Yes", "No" |
| autonomous_driving_level | String | No | Self-driving capability | "L2", "L3" |
| adaptive_cruise_control | String | No | Smart cruise control | "Yes", "No" |
| traffic_jam_assist | String | No | Low-speed autonomous driving | "Yes", "No" |
| automatic_emergency_braking | String | No | Emergency brake feature | "Yes", "No" |
| lane_keep_assist | String | No | Lane departure prevention | "Yes", "No" |
| remote_parking | String | No | Park vehicle from outside | "Yes", "No" |
| auto_parking | String | No | Automatic parking feature | "Yes", "No" |
| blind_spot_detection | String | No | Blind spot monitoring | "Yes", "No" |
| fatigue_driving_detection | String | No | Driver alertness monitoring | "Yes", "No" |
| engine_displacement | String | No | Engine size | "Below 1.0L", "1.0~1.6L", "1.6~2.0L", "2.0~2.5L", "2.5~3.5L", "3.5~6.0L", "Above 6.0L", "None" |
| motor_power | String | No | Electric motor output | "Below 70kW", "70~120kW", "120~180kW", "180~250kW", "250~400kW", "Above 400kW" |
| battery_capacity | String | No | Electric range capacity | "30~50kWh", "50~80kWh", "80~100kWh", "Above 100kWh", "None" |
| fuel_tank_capacity | String | No | Fuel storage capacity | "30~50L", "50~70L", "Above 70L", "None" |
| horsepower | String | No | Engine power rating | "Below 100hp", "100~200hp", "200~300hp", "300~400hp", "Above 400hp" |
| torque | String | No | Engine torque rating | "Below 200N·m", "200~300N·m", "300~400N·m", "400~500N·m", "Above 500N·m" |
| zero_to_one_hundred_km_h_acceleration_time | String | No | Acceleration performance | "Above 10s", "8~10s", "6~8s", "4~6s", "Below 4s" |
| top_speed | String | No | Maximum velocity | "Below 150km/h", "160~200km/h", "200~240km/h", "240~300km/h", "Above 300km/h" |
| fuel_consumption | String | No | Fuel efficiency | "4~6L/100km", "6~8L/100km", "Above 8L/100km", "None" |
| electric_consumption | String | No | Energy efficiency | "10~12kWh/100km", "12~14kWh/100km", "Above 14kWh/100km", "None" |
| driving_range | String | No | Distance per charge/tank | "300~400km", "400~800km", "Above 800km" |
| drive_type | String | No | Wheel drive configuration | "Front-Wheel Drive", "Rear-Wheel Drive", "All-Wheel Drive" |
| suspension | String | No | Suspension system type | "Independent Suspension", "Non-independent Suspension" |
| passibility | String | No | Rough terrain capability | "Low", "Medium", "High" |
| seat_layout | String | No | Seating configuration | "5-seat", "7-seat" |
| city_commuting | String | No | Urban driving suitability | "Yes", "No" |
| highway_long_distance | String | No | Highway driving suitability | "Yes", "No" |
| off_road_capability | String | No | Off-road performance | "Low", "Medium", "High" |
| cargo_capability | String | No | Cargo hauling suitability | "Yes", "No" |
| cold_resistance | String | No | Cold weather performance | "High", "Medium", "Low" |
| heat_resistance | String | No | Hot weather performance | "High", "Medium", "Low" |
| size | String | No | Vehicle size perception | "Small", "Medium", "Large" |
| vehicle_usability | String | No | General utility | "Small", "Medium", "Large" |
| aesthetics | String | No | Visual appeal | "Low", "Medium", "High" |
| energy_consumption_level | String | No | Efficiency perception | "Low", "Medium", "High" |
| comfort_level | String | No | Ride comfort | "Low", "Medium", "High" |
| smartness | String | No | Technology level | "Low", "Medium", "High" |
| family_friendliness | String | No | Family suitability | "Low", "Medium", "High" |

### Conversation Stage

The stage structure represents the current state of the conversation flow.

```
stage:
  previous_stage: String indicating the previous stage of the conversation
  current_stage: String indicating the current stage of the conversation
```

### Conversation Stage Field Details

| Field | Type | Required | Description | Candidate Values |
|-------|------|----------|-------------|-----------------|
| previous_stage | String | Yes | Previous state of conversation | See stage values below |
| current_stage | String | Yes | Current state of conversation | See stage values below |

#### Stage Values
| Value | Description |
|-------|-------------|
| welcome | Initial greeting stage |
| profile_analysis | Collecting or analyzing user profile information |
| needs_analysis | Collecting or analyzing car requirements |
| car_selection_confirmation | Confirming selected car models |
| reservation4s | Setting up 4S store test drive |
| reservation_confirmation | Confirming test drive reservation details |
| farewell | Conversation closing stage |

### Reservation Information

The reservation_info structure contains information about a test drive appointment.

```
reservation_info:
  test_driver: String identifying the person who will test drive the vehicle
  reservation_date: String in YYYY-MM-DD format for the reservation date
  reservation_time: String in HH:MM format for the reservation time
  reservation_location: String describing the dealership or store location
  reservation_phone_number: String with contact phone number
  salesman: String with the name of the assigned salesperson
```

### Reservation Information Field Details

| Field | Type | Required | Description | Example Values |
|-------|------|----------|-------------|----------------|
| test_driver | String | No | Name of test driver | "Mr. Zhang" |
| reservation_date | String | No | Date of test drive | "2025-06-05" (YYYY-MM-DD format) |
| reservation_time | String | No | Time of test drive | "14:00" (HH:MM format) |
| reservation_location | String | No | Dealership location | "Tesla Beijing Haidian Store" |
| reservation_phone_number | String | No | Contact phone | "123456789" |
| salesman | String | No | Assigned sales person | "David Chen" |

### Chat Session

```
session_id: UUID
phone_number: String (reference to user profile)
created_at: ISO 8601 datetime
ended_at: ISO 8601 datetime or null
status: enum: "active", "closed"
```

### Chat Message

```
message_id: UUID
session_id: UUID (reference to chat session)
sender_type: enum: "user", "system"
sender_id: UUID or identifier string
content: string
timestamp: ISO 8601 datetime
status: enum: "delivered", "read"
```

## Error Handling

All API responses use standard HTTP status codes. For errors, a JSON response with an `error` field is returned with an optional `details` field providing more information about the error.

Common error codes:
- 400: Bad Request - Invalid input
- 401: Unauthorized - Authentication required
- 403: Forbidden - Insufficient permissions
- 404: Not Found - Resource not found
- 500: Internal Server Error - Server-side error

## Versioning

The API version is specified in the URL path: `/api/v1/...`. This document describes v1 of the API.