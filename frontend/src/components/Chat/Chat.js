import React, { useState, useEffect, useRef } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { chatService, profileService } from '../../services/api';
import './Chat.css';

const Chat = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const messagesEndRef = useRef(null);

  const [userProfile, setUserProfile] = useState(null);
  const [currentStage, setCurrentStage] = useState('welcome');
  const [messages, setMessages] = useState([]);
  const [inputMessage, setInputMessage] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [sessionId, setSessionId] = useState(null);
  const [appointment, setAppointment] = useState({
    phoneNumber: '',
    name: '',
    location: '',
    time: ''
  });

  // Get sessionData and profile from location.state
  useEffect(() => {
    if (location.state && location.state.sessionData) {
      const { sessionData, profile } = location.state;

      // Set session ID
      if (sessionData.session_id) {
        setSessionId(sessionData.session_id);
      }

      // Set user profile
      if (profile) {
        setUserProfile(profile);
      }

      // If sessionData has messages, display them
      if (sessionData.messages && sessionData.messages.length > 0) {
        const formattedMessages = sessionData.messages.map(msg => ({
          type: msg.role === 'user' ? 'user' : 'assistant',
          content: msg.content,
          id: msg.message_id || Date.now()
        }));
        setMessages(formattedMessages);
      } else if (sessionData.message && sessionData.message.content) {
        setMessages([{
          type: 'assistant',
          content: sessionData.message.content,
          id: Date.now()
        }]);
      }

      // If there is session stage information, set it
      if (sessionData.stage) {
        setCurrentStage(sessionData.stage);
      }
    } else {
      // If there is no sessionData, display default welcome message
      setMessages([
        {
          type: 'assistant',
          content: "Hello! I'm your AutoVend smart assistant. To ensure quality service, your call will be recorded. I will match the right car model based on your need. I need some basic information. Is the car for you or your family?",
          id: Date.now()
        }
      ]);
    }
  }, [location.state]);

  // Define a state to track whether polling should continue
  const [shouldPoll, setShouldPoll] = useState(false);

  // Add needs state
  const [needs, setNeeds] = useState([]);

  // Add matchedCars state
  const [matchedCars, setMatchedCars] = useState([]);

  // Periodically fetch new messages
  useEffect(() => {
    let intervalId;

    if (sessionId && shouldPoll) {
      const fetchMessages = async () => {
        try {
          const response = await chatService.getMessages(sessionId);
          if (response && response.messages) {
            const formattedMessages = response.messages.map(msg => ({
              type: msg.sender_type === 'user' ? 'user' : 'assistant',
              content: msg.content,
              id: msg.message_id || Date.now()
            }));

            // Only update when the number of messages changes
            if (formattedMessages.length !== messages.length) {
              setMessages(formattedMessages);

              // Check if the latest message is from the assistant, if so, stop polling
              const lastMessage = formattedMessages[formattedMessages.length - 1];
              if (lastMessage && lastMessage.type === 'assistant') {
                setShouldPoll(false);
                setIsTyping(false);
              }
            }

            // Update stage information
            if (response.stage && response.stage.current_stage) {
              setCurrentStage(response.stage.current_stage);
            }

            // Update user profile
            if (response.profile) {
              setUserProfile(response.profile);
            }

            // Update needs analysis data
            if (response.needs) {
              setNeeds(response.needs);
            }

            // Update matched car data
            if (response.matched_car_models) {
              // Display up to 5 records
              setMatchedCars(response.matched_car_models.slice(0, 5));
            }

            // Update appointment information
            if (response.reservation_info) {
              setAppointment(response.reservation_info);
            }
          }
        } catch (error) {
          console.error('Failed to get messages:', error);
        }
      };

      // Fetch new messages every 5 seconds
      intervalId = setInterval(fetchMessages, 5000);
    }

    return () => {
      if (intervalId) {
        clearInterval(intervalId);
      }
    };
  }, [sessionId, messages.length, shouldPoll]);

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const handleSendMessage = async () => {
    if (!inputMessage.trim() || !sessionId) return;

    // 发送消息时启用轮询
    setShouldPoll(true);

    const newMessage = {
      type: 'user',
      content: inputMessage,
      id: Date.now()
    };

    // First add user message to UI
    setMessages(prev => [...prev, newMessage]);
    setInputMessage('');
    setIsTyping(true);

    try {
      // Call the sendMessage function in api.js to send message to backend
      const response = await chatService.sendMessage(sessionId, inputMessage);

      // If the backend directly returns a reply, add it to the message list
      if (response && response.response) {
        const assistantMessage = {
          type: 'assistant',
          content: response.response.content,
          id: response.response.message_id || Date.now()
        };
        setMessages(prev => [...prev, assistantMessage]);

        // 收到助手回复后立即停止轮询
        setShouldPoll(false);
        setIsTyping(false);
      } else {
        // 如果后端没有直接返回回复，启动轮询等待回复
        setShouldPoll(true);
      }

      // Update current stage
      if (response && response.stage) {
        setCurrentStage(response.stage);
      }

      // If it's reservation stage, update appointment information
      if (response && response.stage === 'reservation4s' && response.reservation_info) {
        setAppointment(response.reservation_info);
      }

      // Update user profile
      if (response && response.profile) {
        setUserProfile(response.profile);
      }

      // Update needs analysis data
      if (response && response.needs) {
        setNeeds(response.needs);
      }

      // Update matched car data
      if (response && response.matched_car_models) {
        // Display up to 5 records
        setMatchedCars(response.matched_car_models.slice(0, 5));
      }

      // Update appointment information
      if (response.reservation_info) {
        setAppointment(response.reservation_info);
      }
    } catch (error) {
      console.error('Failed to send message:', error);
      setMessages(prev => [...prev, {
        type: 'assistant',
        content: 'Sorry, an error occurred. Please try again later.',
        id: Date.now()
      }]);

      // Error message also counts as assistant message, stop polling
      setShouldPoll(false);
      setIsTyping(false);
    }
  };

  // Modify the Need Analysis part in renderInfoPanels function
  const renderInfoPanels = () => {
    if (currentStage === 'reservation4s') {
      // Check if there is any appointment information
      const hasAppointmentInfo = appointment && (
        appointment.test_driver || 
        appointment.reservation_date || 
        appointment.reservation_time || 
        appointment.reservation_location || 
        appointment.reservation_phone_number || 
        appointment.salesman
      );
      
      return (
        <>
          <div className="info-panel test-drive-appointment">
            <h3>Test Drive Appointment</h3>
            <div className="panel-content">
              {hasAppointmentInfo ? (
                <>
                  {appointment.test_driver && (
                    <div className="appointment-item">
                      <span className="item-label">Test Driver:</span>
                      <span className="item-value">{appointment.test_driver}</span>
                    </div>
                  )}
                  {appointment.reservation_date && (
                    <div className="appointment-item">
                      <span className="item-label">Date:</span>
                      <span className="item-value">{appointment.reservation_date}</span>
                    </div>
                  )}
                  {appointment.reservation_time && (
                    <div className="appointment-item">
                      <span className="item-label">Time:</span>
                      <span className="item-value">{appointment.reservation_time}</span>
                    </div>
                  )}
                  {appointment.reservation_location && (
                    <div className="appointment-item">
                      <span className="item-label">Location:</span>
                      <span className="item-value">{appointment.reservation_location}</span>
                    </div>
                  )}
                  {appointment.reservation_phone_number && (
                    <div className="appointment-item">
                      <span className="item-label">Contact:</span>
                      <span className="item-value">{appointment.reservation_phone_number}</span>
                    </div>
                  )}
                </>
              ) : (
                <div className="empty-appointment"></div>
              )}
            </div>
          </div>
        </>
      );
    }

    return (
      <>
        <div className="info-panel chat-user-profile">
          <h3>User Profile</h3>
          <div className="panel-content">
            {userProfile?.phone_number && (
              <div className="profile-item">Phone number: {userProfile.phone_number}</div>
            )}
            {userProfile?.name && (
              <div className="profile-item">Name: {userProfile.name}</div>
            )}
            {userProfile?.job && (
              <div className="profile-item">Job: {userProfile.job}</div>
            )}
            {userProfile?.age && (
              <div className="profile-item">Age: {userProfile.age}</div>
            )}
            {userProfile?.target_driver && (
              <div className="profile-item">Target Driver: {userProfile.target_driver}</div>
            )}
            {userProfile?.residence && (
              <div className="profile-item">Resident: {userProfile.residence}</div>
            )}
            {userProfile?.user_title && (
              <div className="profile-item">Title: {userProfile.user_title}</div>
            )}
            {userProfile?.expertise && (
              <div className="profile-item">Car Knowledge: {userProfile.expertise}/10</div>
            )}
            {userProfile?.family_size && (
              <div className="profile-item">Family Size: {userProfile.family_size}</div>
            )}
            {userProfile?.price_sensitivity && (
              <div className="profile-item">Price Sensitivity: {userProfile.price_sensitivity}</div>
            )}
            {userProfile?.parking_conditions && (
              <div className="profile-item">Parking Conditions: {userProfile.parking_conditions}</div>
            )}
          </div>
        </div>
        <div className="info-panel need-analysis">
          <h3>Need Analysis</h3>
          <div className="panel-content">
            {needs && needs.length > 0 ? (
              needs.map((need, index) => (
                <div key={index} className="analysis-item">
                  {need.category}: {need.value}
                  {need.is_implicit && <span className="implicit-tag">, implicit</span>}
                </div>
              ))
            ) : (
              <div className="empty-analysis"></div>
            )}
          </div>
        </div>
        <div className="info-panel matched-car">
          <h3>Matched Car</h3>
          <div className="panel-content">
            {matchedCars && matchedCars.length > 0 ? (
              matchedCars.map((car, index) => (
                <div key={index} className="car-item">
                  {car.brand} {car.model} {car.year}
                </div>
              ))
            ) : (
              <div className="empty-cars"></div>
            )}
          </div>
        </div>
      </>
    );
  };

  // Function to scroll to the bottom
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  // Automatically scroll when the message list updates
  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleBack = async () => {
    if (window.confirm('Are you sure you want to exit the current conversation? This call will not be recorded after exiting.')) {
      try {
        // If session ID exists, terminate the session
        if (sessionId) {
          await chatService.endSession(sessionId);
          console.log('Session terminated');
        }
        
        // If user profile exists, delete the user profile, default user cannot be deleted
        if (userProfile && userProfile.phone_number && userProfile.phone_number !== '13888888888') {
          await profileService.deleteProfile(userProfile.phone_number);
          console.log('User profile deleted');
        }
      } catch (error) {
        console.error('Error terminating session or deleting user profile:', error);
      } finally {
        // Return to previous page regardless of success or failure
        navigate(-1);
      }
    }
  };

  // Modify rendering part
  return (
    <div className="chat-container">
      <div className="back-button-chat" onClick={handleBack}>
        ← Back
      </div>
      <div className="chat-content">
        <div className="chat-messages">
          {messages.map((message) => (
            <div
              key={message.id}
              className={`message ${message.type} animate-in`}
            >
              <div className="message-content">{message.content}</div>
            </div>
          ))}
          {isTyping && (
            <div className="typing-indicator">
              AI is typing
              <div className="dots">
                <span>.</span>
                <span>.</span>
                <span>.</span>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>
        <div className="chat-input-container">
          <textarea
            className="chat-input"
            placeholder="Please enter your messages..."
            value={inputMessage}
            onChange={(e) => setInputMessage(e.target.value)}
            onKeyPress={handleKeyPress}
          />
          <div className="button-group">
            <button
              className="send-button"
              onClick={handleSendMessage}
              disabled={!inputMessage.trim()}
            >
              Send
            </button>
            <button
              className="hang-up-button"
              onClick={async () => {
                if (window.confirm('Are you sure you want to end the current conversation? This conversation will be recorded')) {
                  try {
                    if (sessionId) {
                      await chatService.endSession(sessionId);
                      console.log('Session terminated');
                    }
                  } catch (error) {
                    console.error('Error terminating session:', error);
                  } finally {
                    navigate(-1);
                  }
                }
              }}
            >
              Hang Up
            </button>
          </div>
        </div>
      </div>
      <div className="info-panels">
        {renderInfoPanels()}
      </div>
    </div>
  );
};

export default Chat;
