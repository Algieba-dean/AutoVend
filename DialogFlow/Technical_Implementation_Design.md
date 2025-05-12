# AutoVend Technical Implementation Design Document

## 1. System Architecture

### 1.1 Overall Architecture

The AutoVend system adopts a modular architecture design, primarily divided into the following core modules:

- **Dialogue Management Module**: Manages dialogue interactions with OpenAI, processes dialogue flow
- **User Profile Module**: Responsible for extracting, storing, and managing user information
- **Requirement Analysis Module**: Processes the identification and management of explicit and implicit car purchase requirements
- **Recommendation Engine**: Provides vehicle recommendations based on user profiles and requirement analysis
- **API Service**: Provides RESTful API interfaces, supporting frontend and third-party system integration

### 1.2 Technology Selection

- **Backend Framework**: FastAPI (Python)
- **Dialogue Engine**: OpenAI API (GPT-4/GPT-3.5)
- **Natural Language Processing**: Primarily relies on OpenAI, supplemented by simple rule extraction
- **Data Storage**: SQLite (local development) / JSON file storage
- **API Documentation**: Swagger UI (built into FastAPI)
- **Frontend Interface**: Streamlit (optional, for rapid development of demonstration interface)

## 2. Core Module Design

### 2.1 Dialogue Management Module

#### 2.1.1 Data Model

```python
class ChatMessage:
    message_id: str
    role: str  # 'user', 'system', 'assistant'
    content: str
    timestamp: datetime
    
class ChatSession:
    session_id: str
    profile_id: Optional[str]
    phone_number: Optional[str]
    messages: List[ChatMessage]
    created_at: datetime
    updated_at: datetime
    stage: str  # welcome, needs_analysis, confirmation, dealership
    
    context: dict  # Stores dialogue context and state
```

#### 2.1.2 Key Functions

- **Session Initialization**: Creates new sessions, sets initial system prompts
- **Message Processing**: Processes user messages and calls OpenAI API to generate responses
- **Context Management**: Maintains dialogue history and context information
- **State Transition**: Manages dialogue state transitions
- **Extraction Processing**: Extracts user information and requirements from dialogues

#### 2.1.3 Interface Definition

```python
def create_session(phone_number: Optional[str] = None) -> ChatSession:
    """Creates a new chat session"""

def add_message(session_id: str, content: str, role: str = "user") -> ChatMessage:
    """Adds a new message to the session"""
    
def generate_response(session_id: str) -> ChatMessage:
    """Generates system response based on current session"""
    
def extract_information(session_id: str) -> dict:
    """Extracts user information and requirements from the session"""
```

### 2.2 User Profile Module

#### 2.2.1 Data Model

```python
class UserProfile:
    # BasicInformation
    profile_id: str
    phone_number: str
    age: Optional[str]
    user_title: Optional[str]
    name: Optional[str]
    target_driver: Optional[str]
    expertise: Optional[int]  # 0-10 level of automotive knowledge
    
    # AdditionalInformation
    family_size: Optional[int]
    price_sensitivity: Optional[str]  # High, Medium, Low
    residence: Optional[str]  # Residence, format: Country+Province+City
    parking_conditions: Optional[str]
    
    # Dynamic tags
    tags: Dict[str, Any]
    
    # Associated information
    connections: List[ConnectionInfo]
```

#### 2.2.2 Key Functions

- **Information Extraction**: Extracts user information from dialogues
- **Profile Creation**: Creates user profiles based on extracted information
- **Profile Updates**: Dynamically updates user information
- **Tag Generation**: Generates tags based on user information
- **Association Management**: Manages associations between users

#### 2.2.3 Interface Definition

```python
def create_profile(session_id: str, initial_info: dict = None) -> UserProfile:
    """Creates a new user profile"""
    
def update_profile(profile_id: str, update_info: dict) -> UserProfile:
    """Updates user profile information"""
    
def generate_tags(profile_id: str) -> Dict[str, str]:
    """Generates tags based on user profile"""
    
def get_profile(profile_id: str) -> UserProfile:
    """Gets user profile"""
```

### 2.3 Requirement Analysis Module

#### 2.3.1 Data Model

```python
class CarNeed:
    value: str
    is_implicit: bool  # Whether it's an implicit requirement
    confidence: float  # Confidence level
    source: str  # Source: direct user statement, system inference, etc.
    
class CarNeeds:
    profile_id: str
    
    # Explicit requirements
    budget: Optional[CarNeed]
    brand: List[CarNeed]
    vehicle_category_bottom: List[CarNeed]
    color: List[CarNeed]
    
    # Performance requirements
    engine_type: List[CarNeed]
    transmission: List[CarNeed]
    fuel_efficiency: Optional[CarNeed]
    
    # Function and comfort
    seats: Optional[CarNeed]
    sunroof: Optional[CarNeed]
    entertainment: List[CarNeed]
    safety_features: List[CarNeed]
    
    # Implicit requirements
    size: Optional[CarNeed]
    usage: List[CarNeed]  # Urban driving, off-road, family, etc.
    style: List[CarNeed]  # Luxury, sports, practical, etc.
    
    # Custom requirements
    custom_needs: Dict[str, CarNeed]
```

#### 2.3.2 Key Functions

- **Explicit Requirement Extraction**: Identifies requirements directly expressed by users
- **Implicit Requirement Inference**: Infers implicit requirements based on user profiles and dialogue content
- **Requirement Conflict Resolution**: Handles conflicts between requirements
- **Requirement Granularity Control**: Adjusts requirement display granularity based on user expertise level

#### 2.3.3 Interface Definition

```python
def extract_explicit_needs(text: str) -> Dict[str, Any]:
    """Extracts explicit requirements from text"""
    
def infer_implicit_needs(profile_id: str, explicit_needs: Dict[str, Any]) -> Dict[str, Any]:
    """Infers implicit requirements based on user profile and explicit requirements"""
    
def add_need(profile_id: str, category: str, value: str, is_implicit: bool = False) -> None:
    """Adds a requirement item"""
    
def remove_need(profile_id: str, category: str, value: Optional[str] = None) -> None:
    """Removes a requirement item"""
    
def get_needs(profile_id: str) -> Dict[str, Any]:
    """Gets all user requirements"""
```

### 2.4 Recommendation Engine

#### 2.4.1 Data Model

```python
class Vehicle:
    vehicle_id: str
    brand: str
    model: str
    category: str
    price: float
    specs: Dict[str, Any]
    features: List[str]
    
class Recommendation:
    profile_id: str
    recommendations: List[Tuple[Vehicle, float]]  # Vehicle and match degree
    created_at: datetime
    reasoning: Dict[str, str]  # Recommendation reasons
```

#### 2.4.2 Key Functions

- **Vehicle Matching**: Matches suitable vehicles based on user requirements
- **Feature Explanation**: Explains vehicle features based on user focus points
- **Match Degree Calculation**: Calculates the match degree between each vehicle and user requirements

#### 2.4.3 Interface Definition

```python
def generate_recommendations(profile_id: str, limit: int = 5) -> List[Recommendation]:
    """Generates recommended vehicles based on user profile and requirements"""
    
def explain_recommendation(profile_id: str, vehicle_id: str) -> Dict[str, str]:
    """Explains why a specific vehicle is recommended to a specific user"""
    
def get_vehicle_details(vehicle_id: str) -> Vehicle:
    """Gets detailed vehicle information"""
```

### 2.5 OpenAI Integration Module

#### 2.5.1 Key Functions

- **API Call Management**: Handles communication with the OpenAI API
- **Prompt Engineering**: Designs and optimizes prompts for interaction with OpenAI
- **Response Parsing**: Parses response content returned by OpenAI

#### 2.5.2 Interface Definition

```python
def create_completion(messages: List[dict], system_prompt: Optional[str] = None) -> str:
    """Calls OpenAI API to generate responses"""
    
def extract_structured_data(text: str, schema: Dict[str, Any]) -> Dict[str, Any]:
    """Uses OpenAI to extract structured data from text"""
    
def analyze_sentiment(text: str) -> Dict[str, float]:
    """Analyzes sentiment tendencies in text"""
```

## 3. API Interface Design

### 3.1 Dialogue API

```
POST /api/chat/new
GET /api/chat/{session_id}
POST /api/chat/{session_id}/message
```

### 3.2 User Profile API

```
GET /api/profile/{profile_id}
PATCH /api/profile/{profile_id}
```

### 3.3 Requirement Analysis API

```
GET /api/needs/{profile_id}
POST /api/needs/{profile_id}
DELETE /api/needs/{profile_id}/{category}
```

### 3.4 Recommendation API

```
GET /api/recommendations/{profile_id}
GET /api/vehicles/{vehicle_id}
```

## 4. Data Storage Design

### 4.1 Local Storage Solution

Initial phase uses a simple file storage system:

```
/data
  /sessions  # Session data
    {session_id}.json
  /profiles  # User profile data
    {profile_id}.json
  /needs     # Requirement data
    needs_{profile_id}.json
  /vehicles  # Vehicle data
    vehicles.json
```

Later consideration for migration to SQLite:

```python
# Example database table structure
chat_sessions (session_id, profile_id, phone_number, created_at, updated_at, stage)
chat_messages (message_id, session_id, role, content, timestamp)
user_profiles (profile_id, phone_number, name, ..., created_at, updated_at)
user_needs (need_id, profile_id, category, value, is_implicit, confidence)
vehicles (vehicle_id, brand, model, category, price, ...)
```

## 5. Implementation Strategy

### 5.1 Short-term Implementation Goals

- Implement basic dialogue management and OpenAI integration
- Develop simple user profile extraction functionality
- Implement basic explicit requirement recognition
- Create simple vehicle database and matching logic
- Build basic API service

### 5.2 Medium-term Implementation Goals

- Enhance the accuracy and richness of user profiles
- Improve implicit requirement inference capability
- Optimize dialogue experience and flow
- Expand vehicle database

## 6. Security Measures

- API authentication and authorization
- Data encryption
- Input validation and cleaning
- Logging and auditing
