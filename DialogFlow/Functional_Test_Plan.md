# AutoVend Functional Test Plan

## 1. Test Scope

This test plan covers the functional testing of the AutoVend intelligent automotive sales AI agent system, mainly including the following modules:

- User profile extraction
- Car purchase requirement analysis
- Dialogue flow management
- Vehicle recommendation functionality
- API interfaces

## 2. Test Environment

- **Development Environment**: Python 3.10, FastAPI 0.104.1
- **Testing Tools**: pytest, requests, pytest-cov
- **Test Data**: Simulated dialogue dataset
- **Deployment Environment**: Docker container

## 3. Test Strategy

### 3.1 Unit Testing

Test individual modules and functions independently to ensure the functional correctness of each component.

### 3.2 Integration Testing

Test interactions between modules to ensure the system works correctly as a whole.

### 3.3 End-to-End Testing

Simulate complete user dialogue flows to verify the system can correctly process user requests and provide appropriate responses.

### 3.4 Performance Testing

Test system performance under high load to ensure it meets actual usage requirements.

## 4. Test Cases

### 4.1 User Profile Module Testing

#### TC-UP-001: BasicInformation Extraction Test

- **Description**: Test whether the system can correctly extract user BasicInformation from dialogues
- **Preconditions**: Test dialogue texts containing various user information have been prepared
- **Test Steps**:
  1. Call the information extraction function to process test texts
  2. Verify if the returned user information meets expectations
- **Expected Results**: The system should correctly extract age, gender, occupation, and other BasicInformation

#### TC-UP-002: User Tag Generation Test

- **Description**: Test whether the system can generate corresponding tags based on user profiles
- **Preconditions**: Complete user profile data has been prepared
- **Test Steps**:
  1. Call the tag generation function to process user profiles
  2. Verify if the generated tags are reasonable
- **Expected Results**: The generated tags should match user characteristics

#### TC-UP-003: User Association Recognition Test

- **Description**: Test whether the system can identify scenarios where users are buying cars for others
- **Preconditions**: Test dialogue texts containing purchase association information have been prepared
- **Test Steps**:
  1. Call the association recognition function to process test texts
  2. Verify if the system can correctly identify buying cars for others
- **Expected Results**: The system should be able to identify when users are buying cars for family/friends and record association information

### 4.2 Requirement Analysis Module Testing

#### TC-NA-001: Explicit Requirement Extraction Test

- **Description**: Test whether the system can extract explicit requirements from dialogues
- **Preconditions**: Test dialogue texts containing various explicit requirements have been prepared
- **Test Steps**:
  1. Call the requirement extraction function to process test texts
  2. Verify if the returned requirement information meets expectations
- **Expected Results**: The system should correctly extract budget, brand preferences, and other explicit requirements

#### TC-NA-002: Implicit Requirement Inference Test

- **Description**: Test whether the system can infer implicit requirements based on user profiles and dialogue content
- **Preconditions**: User profile and explicit requirement data have been prepared
- **Test Steps**:
  1. Call the implicit requirement inference function
  2. Verify if the inferred implicit requirements are reasonable
- **Expected Results**: The inferred implicit requirements should match user characteristics and explicit requirements

#### TC-NA-003: Requirement Conflict Resolution Test

- **Description**: Test whether the system can handle conflicts between requirements
- **Preconditions**: Test data containing conflicting requirements have been prepared
- **Test Steps**:
  1. Call the requirement addition function to add conflicting requirements
  2. Verify if the system handles conflicts as expected
- **Expected Results**: The system should follow the principle of later statements overriding earlier ones to handle conflicts

### 4.3 Dialogue Management Module Testing

#### TC-DM-001: Session Creation Test

- **Description**: Test whether the system can correctly create new chat sessions
- **Test Steps**:
  1. Call the session creation API
  2. Verify if the returned session information is complete
- **Expected Results**: The system should return a response containing the session ID and welcome message

#### TC-DM-002: Message Processing Test

- **Description**: Test whether the system can correctly process user messages
- **Preconditions**: Test sessions have been created
- **Test Steps**:
  1. Send test messages to the session
  2. Verify if the system can extract information and generate appropriate responses
- **Expected Results**: The system should be able to extract information from messages and generate meaningful responses

#### TC-DM-003: State Transition Test

- **Description**: Test whether dialogue states can correctly transition
- **Preconditions**: Test sessions at specific stages have been created
- **Test Steps**:
  1. Send messages triggering state transitions
  2. Verify if the session state transitions to the expected stage
- **Expected Results**: The session state should correctly transition based on dialogue content

### 4.4 Vehicle Recommendation Module Testing

#### TC-CR-001: Basic Recommendation Test

- **Description**: Test whether the system can recommend suitable vehicles based on requirements
- **Preconditions**: User requirement data has been prepared
- **Test Steps**:
  1. Call the recommendation function to process requirement data
  2. Verify if the recommended vehicles meet the requirements
- **Expected Results**: The recommended vehicles should meet the user's main requirements

#### TC-CR-002: Personalized Ranking Test

- **Description**: Test whether the system can rank recommendation results based on user preferences
- **Preconditions**: User profile and requirement data have been prepared
- **Test Steps**:
  1. Call the recommendation function with personalized ranking enabled
  2. Verify if the ranking results match user preferences
- **Expected Results**: Vehicles ranked higher should better match the user's core requirements and preferences

### 4.5 API Interface Testing

#### TC-API-001: Create Chat Session

- **Description**: Test the API for creating new chat sessions
- **Test Steps**:
  1. Send a POST request to `/api/chat/new`
  2. Verify the returned response code and session information
- **Expected Results**: Should return a 200 status code and valid session information

#### TC-API-002: Send Chat Message

- **Description**: Test the API for sending chat messages
- **Preconditions**: Test sessions have been created
- **Test Steps**:
  1. Send a POST request to `/api/chat/{session_id}/message`
  2. Verify the returned response code and system reply
- **Expected Results**: Should return a 200 status code and the system's reply message

#### TC-API-003: Get User Profile

- **Description**: Test the API for getting user profiles
- **Preconditions**: Test user profiles have been created
- **Test Steps**:
  1. Send a GET request to `/api/profile/{profile_id}`
  2. Verify the returned response code and user profile information
- **Expected Results**: Should return a 200 status code and complete user profile information

## 5. Test Data Preparation

### 5.1 Simulated Dialogue Dataset

Create a series of simulated dialogues, including but not limited to the following scenarios:

- Users directly expressing personal information and requirements
- Users buying cars for family/friends
- Users with clear brand and budget preferences
- Users with only vague requirement descriptions
- Users changing requirements during the dialogue process

### 5.2 User Profile Data

Prepare test data for various types of user profiles, covering different age groups, occupations, family situations, and other characteristics.

### 5.3 Vehicle Data

Prepare various types of vehicle data, including different brands, types, and price ranges, for testing the recommendation functionality.

## 6. Test Execution Plan

### 6.1 Test Preparation

- Set up the test environment
- Prepare test data
- Configure testing tools

### 6.2 Test Execution

- Execute unit tests to ensure each module functions correctly
- Execute integration tests to verify module interactions
- Execute end-to-end tests to verify complete flows
- Execute performance tests to ensure system stability

### 6.3 Defect Management

- Record issues found during testing
- Track issue resolution progress
- Execute regression testing to ensure fixes are effective

## 7. Test Report

After testing is complete, a detailed test report will be generated, including:

- Test coverage statistics
- Passed/failed test case statistics
- Summary of issues found
- System performance metrics
- Improvement suggestions

## 8. Test Automation

To improve testing efficiency and repeatability, we plan to implement the following automated tests:

- Unit test automation: Using the pytest framework
- API test automation: Using the requests library and pytest
- Coverage statistics: Using the pytest-cov plugin
- Integration into CI/CD processes: Automatically executing tests when code is committed 