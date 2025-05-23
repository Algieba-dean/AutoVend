import React, { useState, useEffect, useRef } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { chatService, profileService } from '../../services/api';
import './Chat.css';

const Chat = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const messagesEndRef = useRef(null);
  const isInitialized = useRef(false);

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

  // 添加语音相关状态
  const [isSpeaking, setIsSpeaking] = useState(false);
  const speechSynthesisRef = useRef(null);
  // 添加已朗读消息ID集合
  const [spokenMessageIds, setSpokenMessageIds] = useState(new Set());

  // 添加语音识别相关状态
  const [isListening, setIsListening] = useState(false);
  const recognitionRef = useRef(null);

  // Get sessionData and profile from location.state
  useEffect(() => {
    if (isInitialized.current) return;
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

      const assistantMessage = {
        type: 'assistant',
        content: sessionData.message.content,
        id: sessionData.session_id
      };
      setMessages([assistantMessage]);

      // 朗读初始消息
      setTimeout(() => {
        speakText(assistantMessage.content, assistantMessage.id);
        console.log('开始朗读1：', assistantMessage.id);
      }, 1000);

      // If there is session stage information, set it
      if (sessionData.stage) {
        setCurrentStage(sessionData.stage);
      }
    } else {
      // If there is no sessionData, display default welcome message
      const welcomeMessage = {
        type: 'assistant',
        content: "Hello! I'm your AutoVend smart assistant. To ensure quality service, your call will be recorded. I will match the right car model based on your need. I need some basic information. Is the car for you or your family?",
        id: Date.now()
      };
      setMessages([welcomeMessage]);

      // 朗读欢迎消息
      setTimeout(() => {
        speakText(welcomeMessage.content, welcomeMessage.id);
      }, 1000);
    }
    isInitialized.current = true;
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
              // 检查是否有新的助手消息
              const lastMessage = formattedMessages[formattedMessages.length - 1];

              setMessages(formattedMessages);

              // 如果最新消息是助手消息，停止轮询并朗读
              if (lastMessage && lastMessage.type === 'assistant') {
                setShouldPoll(false);
                setIsTyping(false);

                // 检查是否已经朗读过这条消息
                if (!spokenMessageIds.has(lastMessage.id) && !isSpeaking) {
                  speakText(lastMessage.content, lastMessage.id);
                }
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

  // 文字转语音功能
  const speakText = (text, messageId) => {
    // 如果该消息已经朗读过，则不再朗读
    if ((messageId && spokenMessageIds.has(messageId)) || isSpeaking) {
      console.log('消息已朗读过或正在朗读中，跳过朗读:', messageId);
      return;
    }

    // 如果浏览器不支持语音合成API，直接返回
    if (!window.speechSynthesis) {
      console.error('您的浏览器不支持语音合成功能');
      return;
    }

    // 如果正在说话，先停止
    if (isSpeaking) {
      window.speechSynthesis.cancel();
    }

    // 创建语音合成实例
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = 'en-US'; // 设置语言为英文
    utterance.rate = 1.0; // 语速
    utterance.pitch = 1.0; // 音调

    // 获取可用的语音
    const voices = window.speechSynthesis.getVoices();
    // 尝试找到英文语音
    const englishVoice = voices.find(voice => voice.lang.includes('en'));
    if (englishVoice) {
      utterance.voice = englishVoice;
    }

    // 开始说话事件
    utterance.onstart = () => {
      setIsSpeaking(true);
    };

    // 结束说话事件
    utterance.onend = () => {
      setIsSpeaking(false);
      // 将消息ID添加到已朗读集合中
      if (messageId) {
        setSpokenMessageIds(prev => new Set([...prev, messageId]));
      }

      // 语音结束后自动开始语音识别
      if (!isListening) {
        startSpeechRecognition();
      }
    };

    // 错误事件
    utterance.onerror = (event) => {
      console.error('语音合成错误:', event);
      setIsSpeaking(false);
    };

    // 保存引用以便可以取消
    speechSynthesisRef.current = utterance;

    // 播放语音
    window.speechSynthesis.speak(utterance);
  };


  // 添加新函数专门处理语音识别结果的发送
  const sendRecognizedMessage = async (recognizedText) => {
    if (!recognizedText.trim()) return;

    // 停止语音识别
    stopSpeechRecognition();

    // 发送消息时启用轮询
    setShouldPoll(true);

    const newMessage = {
      type: 'user',
      content: recognizedText,
      id: Date.now()
    };

    // 先将用户消息添加到UI
    setMessages(prev => [...prev, newMessage]);
    setInputMessage(''); // 清空输入框
    setIsTyping(true);

    try {
      // 调用api.js中的sendMessage函数将消息发送到后端
      const response = await chatService.sendMessage(Date.now(), recognizedText);

      // 处理响应...与handleSendMessage中的代码相同
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

        // 自动朗读助手回复
        setTimeout(() => {
          speakText(assistantMessage.content, assistantMessage.id);
          console.log('开始朗读2：', assistantMessage.id);
        }, 1000);
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
      // 错误处理...与handleSendMessage中的代码相同
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


  // 语音识别功能
  const startSpeechRecognition = () => {
    // 如果浏览器不支持语音识别API，直接返回
    if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
      console.error('您的浏览器不支持语音识别功能');
      return;
    }

    // 如果已经在监听，则不重复启动
    if (isListening) return;

    // 创建语音识别实例
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    const recognition = new SpeechRecognition();

    // 配置语音识别
    recognition.lang = 'en-US'; // 设置语言为英文
    recognition.continuous = false; // 不持续识别
    recognition.interimResults = false; // 不返回中间结果

    // 开始识别事件
    recognition.onstart = () => {
      setIsListening(true);
      console.log('语音识别已启动，请说话...');
    };

    // 识别结果事件
    recognition.onresult = (event) => {
      const transcript = event.results[0][0].transcript;
      console.log('识别结果:', transcript);

      // 将识别结果填入输入框
      setInputMessage(transcript);

      // 修改：直接使用识别到的文本发送消息，而不是依赖状态
      setTimeout(() => {
        // 直接使用transcript变量，而不是inputMessage状态
        sendRecognizedMessage(transcript);
      }, 500);
      console.log('发送成功！');
    };

    // 结束识别事件
    recognition.onend = () => {
      setIsListening(false);
      console.log('语音识别已结束');
    };

    // 错误事件
    recognition.onerror = (event) => {
      console.error('语音识别错误:', event.error);
      setIsListening(false);
    };

    // 保存引用以便可以取消
    recognitionRef.current = recognition;

    // 开始识别
    recognition.start();
  };

  // 停止语音识别
  const stopSpeechRecognition = () => {
    if (recognitionRef.current) {
      recognitionRef.current.stop();
      setIsListening(false);
    }
  };

  // 在组件卸载时取消所有语音操作
  useEffect(() => {
    return () => {
      if (speechSynthesisRef.current) {
        window.speechSynthesis.cancel();
      }
      if (recognitionRef.current) {
        recognitionRef.current.stop();
      }
    };
  }, []);

  // 修改handleSendMessage函数，在收到助手回复时自动朗读
  const handleSendMessage = async () => {
    if (!inputMessage.trim() || !sessionId) return;

    // 停止语音识别
    stopSpeechRecognition();

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

        // 自动朗读助手回复
        setTimeout(() => {
          speakText(assistantMessage.content, assistantMessage.id);
          console.log('开始朗读2：', assistantMessage.id);
        }, 1000);
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

  // 修改轮询获取消息的useEffect，在收到新的助手消息时自动朗读
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
              // 检查是否有新的助手消息
              const lastMessage = formattedMessages[formattedMessages.length - 1];

              setMessages(formattedMessages);

              // 如果最新消息是助手消息，停止轮询并朗读
              if (lastMessage && lastMessage.type === 'assistant') {
                setShouldPoll(false);
                setIsTyping(false);

                // 检查是否已经朗读过这条消息
                if (!spokenMessageIds.has(lastMessage.id) && !isSpeaking) {
                  speakText(lastMessage.content, lastMessage.id);
                  console.log('开始朗读3：', lastMessage.id);
                }
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
  }, [sessionId, messages.length, shouldPoll, spokenMessageIds, isSpeaking]);

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
            {userProfile?.connection_information?.connection_phone_number && (
              <div className="profile-item">Connection Phone: {userProfile.connection_information.connection_phone_number}</div>
            )}
            {userProfile?.connection_information?.connection_id_relationship && (
              <div className="profile-item">Relationship: {userProfile.connection_information.connection_id_relationship}</div>
            )}
            {userProfile?.connection_information?.connection_user_name && (
              <div className="profile-item">Connection Name: {userProfile.connection_information.connection_user_name}</div>
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
          <button
            className={`voice-input-button ${isListening ? 'listening' : ''}`}
            onClick={isListening ? stopSpeechRecognition : startSpeechRecognition}
            title={isListening ? "停止语音输入" : "开始语音输入"}
          >
            <i className={`fa ${isListening ? 'fa-microphone-slash' : 'fa-microphone'}`}></i>
          </button>
          <textarea
            className="chat-input"
            value={inputMessage}
            onChange={(e) => setInputMessage(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="Type your message here..."
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