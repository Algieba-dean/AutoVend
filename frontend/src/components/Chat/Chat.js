import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import './Chat.css';

const Chat = () => {
  const navigate = useNavigate();
  const [userProfile, setUserProfile] = useState(null);
  
  const handleBack = () => {
    if (window.confirm('Are you sure you want to exit the current conversation? This call will not be recorded after exiting.')) {
      navigate(-1);
    }
  };

  useEffect(() => {
    // 从后端获取默认用户信息
    const fetchUserProfile = async () => {
      try {
        const response = await axios.get('/api/users/default');
        setUserProfile(response.data);
      } catch (error) {
        console.error('Error fetching user profile:', error);
      }
    };

    fetchUserProfile();
  }, []);
   
  const [messages, setMessages] = useState([
    {
      type: 'assistant',
      content: "Hello! I'm your AutoVend smart assistant. To ensure quality service, your call will be recorded. I will match the right car model based on your need. I need some basic information. Is the car for you or your family?"
    }
   ]);
  
  const [inputMessage, setInputMessage] = useState('');

  const handleSendMessage = () => {
    if (!inputMessage.trim()) return;

    // 添加用户消息到消息列表
    setMessages(prev => [...prev, {
      type: 'user',
      content: inputMessage
    }]);

    // 清空输入框
    setInputMessage('');

    // TODO: 这里可以添加发送消息到后端的逻辑
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  return (
    <div className="chat-container">
      <div className="back-button-chat" onClick={handleBack}>
        ← Back
      </div>
      <div className="chat-content">
        <div className="chat-messages">
          {messages.map((message, index) => (
            <div key={index} className={`message ${message.type}`}>
              {message.type === 'assistant' && (
                <div className="wave-animation">
                  <svg width="200" height="100">
                    <path d="M0,50 C30,40 70,60 100,50 C130,40 170,60 200,50" 
                          stroke="#23A6F0" 
                          fill="none" 
                          strokeWidth="2" />
                  </svg>
                </div>
              )}
              <div className="message-content">{message.content}</div>
            </div>
          ))}
        </div>
        <div className="chat-input-container">
          <textarea
            className="chat-input"
            placeholder="Please enter your messages..."
            value={inputMessage}
            onChange={(e) => setInputMessage(e.target.value)}
            onKeyPress={handleKeyPress}
          />
          <button 
            className="send-button"
            onClick={handleSendMessage}
          >
            Send
          </button>
        </div>
      </div>
      <div className="info-panels">
        <div className="info-panel chat-user-profile">
          <h3>User Profile</h3>
          <div className="panel-content">
            <div className="profile-item">Phone number: {userProfile?.phoneNumber || 'Loading...'}</div>
            <div className="profile-item">Name: {userProfile?.name || 'Loading...'}</div>
            <div className="profile-item">Job: {userProfile?.job || 'Loading...'}</div>
            <div className="profile-item">Age: 30-35</div>
            <div className="profile-item">Car User Age: 50+</div>
            <div className="profile-item">Resident: Norway</div>
          </div>
        </div>
        <div className="info-panel need-analysis">
          <h3>Need Analysis</h3>
          <div className="panel-content">
            <div className="analysis-item">Electric vehicle possibility: low/implicit</div>
            <div className="analysis-item">Budget: $50,000</div>
          </div>
        </div>
        <div className="info-panel matched-car">
          <h3>Matched Car</h3>
          {/* 匹配的车辆信息将在这里显示 */}
        </div>
      </div>
    </div>
  );
};

export default Chat;