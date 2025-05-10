# AutoVend Requirements Analysis Document

## 1. Project Overview

AutoVend is an intelligent automotive sales AI agent system designed to automatically extract user information and analyze car purchase requirements from customer chat records, thereby providing personalized vehicle recommendations. The system is capable of intelligently distinguishing between explicit and implicit needs, and making car purchase suggestions based on user feature tags.

## 2. Core Functional Requirements

### 2.1 User Profile Extraction

#### 2.1.1 Dynamic User Profile Creation and Updates
- The system can extract basic user information from conversations, including gender, age, personality traits, automotive knowledge level, etc.
- It can dynamically update user profiles based on conversation content
- Supports continuous supplementation and refinement of user information in multi-round dialogues

#### 2.1.2 Intelligent User Association
- Supports relationship identification, recognizing whether users are buying cars for themselves or for family/friends
- When users are buying cars for others, the system records the individual's information and retains specific tags
- If this person contacts through a specific phone number next time, the system can automatically switch to the reserved profile

#### 2.1.3 Offline User Profile Supplementation
- Provides functionality for offline staff to supplement or modify user profiles after customers complete offline processes
- Information collected offline can be seamlessly integrated into system profiles

#### 2.1.4 Dynamic Tag Association and Extraction
- Automatically associates and converts user profile content into potential requirement tags
- Generates conversation strategy preference tags based on geographic location, professional level, etc.
- For example: <Lives in Harbin>-<Electric Vehicle=Low, Implicit>, <Expertise Level=3>-<Professional Conversation Style>

### 2.2 Car Purchase Requirement Analysis

#### 2.2.1 Explicit and Implicit Requirement Distinction
- Explicit requirements: Directly expressed by users, such as 300,000 yuan budget, preference for BMW or Mercedes
- Implicit requirements: Requirements inferred by the system from conversations, such as safety, ease of operation, etc.

#### 2.2.2 Requirement Tagging Processing
- Extract explicit requirement tags such as <Budget=300,000>, <Brand=BMW, Mercedes>
- Infer implicit requirement tags such as <Safety=High, Implicit>, <Operation=Simple, Implicit>

#### 2.2.3 Multi-granular Requirement Classification
- Requirements classified by different granularity, which can be dynamically associated according to user expertise
- For example: Appearance (including brand, size, model, color, wheels), Energy consumption (fuel/power consumption, fuel tank capacity, etc.)

#### 2.2.4 Dynamic Requirement Refinement Control
- Supports dynamic control and adjustment of requirement granularity
- For example: Implicitly inferred <Sunroof=Yes, Implicit> can be upgraded to <Panoramic Sunroof=Yes> based on user explicit statement

#### 2.2.5 Conflicting Requirement Processing
- Capable of handling requirement conflicts in user statements
- Adopts the principle of later statements overriding earlier ones to dynamically update

## 3. Technical Architecture

### 3.1 Backend Architecture
- Uses Python as the main development language
- Uses FastAPI to build Web API services
- Uses OpenAI SDK as the dialogue engine
- Adopts modular design, including dialogue management module, user profile module, requirement analysis module, and recommendation engine

### 3.2 Data Storage
- Initially uses JSON file storage (local deployment)
- User profile data storage
- Conversation history storage
- Car requirement data storage
- Vehicle tag database

### 3.3 Dialogue Processing
- Uses OpenAI API for natural language processing and dialogue generation
- Optimizes dialogue interaction through prompt engineering
- Implements dialogue flow management and state transitions

### 3.4 Dialogue Flow Management
- Implements state machine-based dialogue flow management
- Supports context maintenance in multi-round dialogues
- Dynamically adjusts dialogue strategies based on user profiles and requirements

## 4. Dialogue Process

### 4.1 Welcome Phase
- Query existing user profiles
- If matched with historical users, load user profiles and greet cordially
- If new user, self-introduce and create new user profile
- Inquire about target driver and budget range

### 4.2 Requirement Analysis Phase
- Infer initial requirements based on user profile
- Inquire about key requirements based on importance (brand, purpose, etc.)
- Conduct backend analysis and generate requirement suggestions
- Confirm user's requirement additions, updates, and removals

### 4.3 Confirmation Phase
- Recommend vehicle models based on analysis results
- Introduce selected models based on user requirement tags
- Allow users to update requirements
- Confirm final vehicle selection

### 4.4 Dealership Connection
- Match suitable sales personnel
- Handle special situations such as no inventory, scheduling, etc.

## 5. System Interfaces

### 5.1 API Interfaces
- Dialogue session management API
- User profile management API
- Requirement analysis and update API
- Vehicle recommendation API

### 5.2 OpenAI Integration Interfaces
- Dialogue generation interface
- Information extraction interface
- Requirement analysis interface

## 6. Implementation Strategy

### 6.1 Short-term Implementation Goals
- Complete basic OpenAI integration
- Implement basic dialogue flow management
- Develop simple user profile extraction functionality
- Implement simple explicit requirement recognition
- Create simple vehicle database and matching logic

### 6.2 Medium-term Implementation Goals
- Enhance the accuracy and richness of user profiles
- Improve implicit requirement inference capability
- Optimize dialogue experience and flow
- Expand vehicle database and tag system 