import React, { useState, useEffect, useRef } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { chatService, profileService, voiceService } from '../../services/api';
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
  const [isRecording, setIsRecording] = useState(false);
  const [sessionId, setSessionId] = useState(null);
  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);
  const [appointment, setAppointment] = useState({
    phoneNumber: '',
    name: '',
    location: '',
    time: ''
  });

  // WebSocket 低延迟全双工实时语音通话状态
  const [isWsCallActive, setIsWsCallActive] = useState(false);
  const [wsCallState, setWsCallState] = useState('idle'); // 'idle' | 'connecting' | 'listening' | 'speaking' | 'thinking' | 'playing'
  const [wsAudioLevel, setWsAudioLevel] = useState(0);

  // ASR & TTS 实时诊断数据
  const [asrTelemetry, setAsrTelemetry] = useState(null); // { text, timeMs, language, status }
  const [ttsTelemetry, setTtsTelemetry] = useState(null); // { status, size, format }

  const wsClientRef = useRef(null);
  const wsRecorderRef = useRef(null);
  const wsStreamRef = useRef(null);
  const wsAudioContextRef = useRef(null);
  const wsAnalyserRef = useRef(null);
  const wsVadTimerRef = useRef(null);
  const isSpeakingRef = useRef(false);
  const playingAudioRef = useRef(null);
  const animFrameRef = useRef(null);
  const audioQueueRef = useRef([]);
  const isAudioPlayingRef = useRef(false);

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

      // If there is current session stage information, set it
      if (sessionData.stage && sessionData.stage.current_stage) {
        setCurrentStage(sessionData.stage.current_stage);
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

    const userMsgText = inputMessage;
    const newMessage = {
      type: 'user',
      content: userMsgText,
      id: Date.now()
    };

    setMessages(prev => [...prev, newMessage]);
    setInputMessage('');
    setIsTyping(true);

    const assistantMsgId = Date.now() + 1;
    let assistantMsgCreated = false;

    try {
      await chatService.sendMessageStream(sessionId, userMsgText, {
        onMetadata: (metadata) => {
          if (metadata.stage && metadata.stage.current_stage) {
            setCurrentStage(metadata.stage.current_stage);
          }
          if (metadata.profile) {
            setUserProfile(metadata.profile);
          }
          if (metadata.needs) {
            setNeeds(metadata.needs);
          }
          if (metadata.matched_car_models) {
            setMatchedCars(metadata.matched_car_models.slice(0, 5));
          }
          if (metadata.reservation_info) {
            setAppointment(metadata.reservation_info);
          }
        },
        onToken: (delta) => {
          setIsTyping(false);
          setMessages(prev => {
            if (!assistantMsgCreated) {
              assistantMsgCreated = true;
              return [...prev, { type: 'assistant', content: delta, id: assistantMsgId }];
            } else {
              return prev.map(msg =>
                msg.id === assistantMsgId
                  ? { ...msg, content: msg.content + delta }
                  : msg
              );
            }
          });
        },
        onDone: () => {
          setIsTyping(false);
          setShouldPoll(false);
        },
        onError: async (err) => {
          console.warn('Stream failed, falling back to standard API:', err);
          try {
            const response = await chatService.sendMessage(sessionId, userMsgText);
            if (response && response.response) {
              setMessages(prev => [...prev, {
                type: 'assistant',
                content: response.response.content,
                id: Date.now()
              }]);
            }
          } catch (e) {
            console.error('Fallback send message failed:', e);
          }
          setIsTyping(false);
        }
      });
    } catch (error) {
      console.error('Failed to send message stream:', error);
      setIsTyping(false);
    }
  };

  const handleStartRecording = async () => {
    if (!sessionId) return;
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaRecorderRef.current = new MediaRecorder(stream);
      audioChunksRef.current = [];

      mediaRecorderRef.current.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      mediaRecorderRef.current.onstop = async () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
        await handleSendVoiceBlob(audioBlob);
      };

      mediaRecorderRef.current.start();
      setIsRecording(true);
    } catch (err) {
      alert('无法开启麦克风权限: ' + err.message);
    }
  };

  const handleStopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      if (mediaRecorderRef.current.stream) {
        mediaRecorderRef.current.stream.getTracks().forEach((track) => track.stop());
      }
      setIsRecording(false);
    }
  };

  const handleSendVoiceBlob = async (audioBlob) => {
    if (!sessionId) return;
    setIsTyping(true);
    try {
      const data = await voiceService.processVoiceTurn(sessionId, audioBlob);

      if (data.user_text !== undefined) {
        const text = (data.user_text || '').trim();
        setAsrTelemetry({
          text: text || '(未检测到清晰语音)',
          timeMs: data.asr_time_ms || 0,
          status: text ? 'success' : 'empty'
        });

        if (text) {
          setMessages((prev) => [...prev, { type: 'user', content: text, isVoice: true, id: Date.now() }]);
        } else {
          setMessages((prev) => [...prev, { type: 'system-asr', content: '🎤 ASR 语音识别完成：未检测到清晰声音/背景静音', id: Date.now() }]);
        }
      }

      if (data.agent_response) {
        setMessages((prev) => [...prev, { type: 'assistant', content: data.agent_response, isVoice: true, id: Date.now() + 1 }]);
      }
      if (data.stage) {
        setCurrentStage(data.stage);
      }
      if (data.audio_base64) {
        const estBytes = Math.round(data.audio_base64.length * 0.75);
        setTtsTelemetry({
          status: '正在播报 TTS 语音回复',
          size: estBytes,
          format: data.audio_format || 'mp3'
        });
        const audioSrc = `data:${data.audio_format || 'audio/mp3'};base64,${data.audio_base64}`;
        const audio = new Audio(audioSrc);
        audio.play().catch(e => console.error('Audio playback error:', e));
      }
    } catch (error) {
      console.error('Voice turn failed:', error);
    } finally {
      setIsTyping(false);
    }
  };

  // ── 低延迟全双工 WebSocket 实时语音通话管理逻辑 ────────────────────
  const handleStartWsCall = async () => {
    let currentSessionId = sessionId;
    if (!currentSessionId) {
      try {
        const res = await voiceService.createVoiceSession(userProfile?.phone_number || '');
        currentSessionId = res.session_id;
        setSessionId(currentSessionId);
      } catch (err) {
        console.error('Failed to create voice session:', err);
        alert('创建语音会话失败，无法开启实时语音通话');
        return;
      }
    }

    setIsWsCallActive(true);
    setWsCallState('connecting');

    try {
      // 1. 获取麦克风权限
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      wsStreamRef.current = stream;

      // 2. 音频数据分析与 VAD (静音感应)
      const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
      wsAudioContextRef.current = audioCtx;
      const source = audioCtx.createMediaStreamSource(stream);
      const analyser = audioCtx.createAnalyser();
      analyser.fftSize = 256;
      source.connect(analyser);
      wsAnalyserRef.current = analyser;

      // 3. 建立 WebSocket 连接
      wsClientRef.current = voiceService.createVoiceWebSocket(currentSessionId, {
        onOpen: () => {
          setWsCallState('listening');
          console.log('[VoiceWS] 实时通话服务连接成功');
        },
        onJson: (json) => {
          if (json.type === 'transcription') {
            const hasText = json.text && json.text.trim();
            const recognizedText = hasText ? json.text.trim() : '';
            setAsrTelemetry({
              text: recognizedText || '(未检测到有效语音)',
              timeMs: json.processing_time_ms || 0,
              language: json.language || 'zh',
              status: hasText ? 'success' : 'empty'
            });

            if (hasText) {
              setMessages(prev => [...prev, { type: 'user', content: recognizedText, isVoice: true, id: Date.now() }]);
            } else {
              setWsCallState('listening');
              setIsTyping(false);
            }
          } else if (json.type === 'stage_update') {
            if (json.stage) setCurrentStage(json.stage);
          } else if (json.type === 'response_chunk') {
            setIsTyping(false);
            setMessages(prev => {
              const last = prev[prev.length - 1];
              if (last && last.type === 'assistant' && last.isStreaming) {
                return [...prev.slice(0, -1), { ...last, content: last.content + json.text }];
              } else {
                return [...prev, { type: 'assistant', content: json.text, isVoice: true, isStreaming: true, id: Date.now() }];
              }
            });
          } else if (json.type === 'response_done') {
            setIsTyping(false);
            setMessages(prev => {
              const last = prev[prev.length - 1];
              if (last && last.type === 'assistant') {
                return [...prev.slice(0, -1), { ...last, isStreaming: false }];
              }
              return prev;
            });
          } else if (json.type === 'tts_chunk') {
            setTtsTelemetry(prev => ({
              status: '正在流式播报',
              size: (prev?.size || 0) + (json.size || 0),
              format: json.format || 'mp3'
            }));
          } else if (json.type === 'error') {
            console.error('[VoiceWS Error]', json.message);
            setWsCallState('listening');
            setIsTyping(false);
          }
        },
        onAudio: (arrayBuffer) => {
          audioQueueRef.current.push(arrayBuffer);
          if (!isAudioPlayingRef.current) {
            const playNext = () => {
              if (audioQueueRef.current.length === 0) {
                isAudioPlayingRef.current = false;
                setWsCallState('listening');
                return;
              }
              isAudioPlayingRef.current = true;
              setWsCallState('playing');
              const buf = audioQueueRef.current.shift();
              const blob = new Blob([buf], { type: 'audio/mp3' });
              const url = URL.createObjectURL(blob);
              const audio = new Audio(url);
              playingAudioRef.current = audio;
              audio.onended = playNext;
              audio.onerror = playNext;
              audio.play().catch(playNext);
            };
            playNext();
          }
        },
        onError: () => {
          setWsCallState('idle');
          setIsWsCallActive(false);
        },
        onClose: () => {
          handleStopWsCall();
        }
      });

      // 4. 开启 MediaRecorder 收集音轨并定时送入 WS
      const recorder = new MediaRecorder(stream);
      wsRecorderRef.current = recorder;

      recorder.ondataavailable = (event) => {
        if (event.data && event.data.size > 0 && wsClientRef.current) {
          event.data.arrayBuffer().then(buffer => {
            wsClientRef.current.sendAudio(buffer);
          });
        }
      };

      recorder.start(250); // 每 250ms 发送一个音轨切片

      // 5. VAD 音量循环检测（基于频段 Peak 音量精准识别人声）
      const dataArray = new Uint8Array(analyser.frequencyBinCount);
      const callStartTime = Date.now();
      let speechConsecutiveFrames = 0;
      let speechStartTime = 0;

      const checkVolume = () => {
        if (!wsStreamRef.current) return;
        analyser.getByteFrequencyData(dataArray);

        // 聚焦人声主要频段 (0 - 5.5 kHz，即前 64 个频段)，取 Peak 峰值音量
        let maxVol = 0;
        const voiceBins = Math.min(64, dataArray.length);
        for (let i = 0; i < voiceBins; i++) {
          if (dataArray[i] > maxVol) maxVol = dataArray[i];
        }
        setWsAudioLevel(Math.min(100, Math.round(maxVol / 2.5)));

        // 当 AI 正在语音播报 (playing) 或思考中 (thinking) 时，禁用 VAD 人声检测，防止扬声器播报的声音倒灌回麦克风误识别！
        if (isAudioPlayingRef.current || wsCallState === 'playing' || wsCallState === 'thinking') {
          speechConsecutiveFrames = 0;
          animFrameRef.current = requestAnimationFrame(checkVolume);
          return;
        }

        // 开启通话前 800ms 为麦克风设备预热期，忽略声音检测，防止硬件爆音误触发
        if (Date.now() - callStartTime < 800) {
          animFrameRef.current = requestAnimationFrame(checkVolume);
          return;
        }

        const SPEECH_PEAK_THRESHOLD = 25;  // 说话峰值音量门槛 (大于 25 轻松命中说话)
        const SILENCE_PEAK_THRESHOLD = 12; // 静音峰值音量门槛

        if (maxVol >= SPEECH_PEAK_THRESHOLD) {
          speechConsecutiveFrames++;
          // 连续 2 帧（约 100ms）满足峰值门槛即确认为说话
          if (speechConsecutiveFrames >= 2) {
            if (!isSpeakingRef.current) {
              isSpeakingRef.current = true;
              speechStartTime = Date.now();
              setAsrTelemetry({ text: '🎙️ 正在实时接收您的语音...', status: 'recording' });
              if (wsClientRef.current) {
                wsClientRef.current.startTurn();
              }
              if (wsRecorderRef.current && wsRecorderRef.current.state === 'recording') {
                try {
                  wsRecorderRef.current.stop();
                  wsRecorderRef.current.start(250);
                } catch (e) {}
              }
            }
            setWsCallState(prev => prev === 'playing' ? 'playing' : 'speaking');
            if (wsVadTimerRef.current) {
              clearTimeout(wsVadTimerRef.current);
              wsVadTimerRef.current = null;
            }
          }
        } else if (maxVol <= SILENCE_PEAK_THRESHOLD) {
          speechConsecutiveFrames = 0;
          if (isSpeakingRef.current) {
            // 静音持续 1.2 秒自动结束本轮说话
            if (!wsVadTimerRef.current) {
              wsVadTimerRef.current = setTimeout(() => {
                const speechDuration = Date.now() - speechStartTime;
                isSpeakingRef.current = false;
                wsVadTimerRef.current = null;

                // 若有效说话时长小于 300ms（短暂咳嗽/气音），静默重置
                if (speechDuration < 300) {
                  setWsCallState('listening');
                  if (wsClientRef.current) {
                    wsClientRef.current.startTurn();
                  }
                  return;
                }

                if (wsRecorderRef.current && wsRecorderRef.current.state === 'recording') {
                  try { wsRecorderRef.current.requestData(); } catch (e) {}
                }
                if (wsClientRef.current) {
                  wsClientRef.current.endTurn();
                  setWsCallState('thinking');
                  setIsTyping(true);
                  setAsrTelemetry({ text: '⌛ 正在识别语音中...', status: 'processing' });
                }
              }, 1200);
            }
          }
        }

        animFrameRef.current = requestAnimationFrame(checkVolume);
      };
      checkVolume();

    } catch (err) {
      alert('无法开启麦克风或建立语音连接: ' + err.message);
      handleStopWsCall();
    }
  };

  const handleManualEndTurn = () => {
    if (wsClientRef.current) {
      if (wsVadTimerRef.current) {
        clearTimeout(wsVadTimerRef.current);
        wsVadTimerRef.current = null;
      }
      isSpeakingRef.current = false;
      setAsrTelemetry({ text: '⌛ 正在识别您的语音...', status: 'processing' });
      if (wsRecorderRef.current && wsRecorderRef.current.state === 'recording') {
        try { wsRecorderRef.current.requestData(); } catch (e) {}
      }
      wsClientRef.current.endTurn();
      setWsCallState('thinking');
      setIsTyping(true);
    }
  };

  const handleStopWsCall = () => {
    if (animFrameRef.current) {
      cancelAnimationFrame(animFrameRef.current);
      animFrameRef.current = null;
    }
    if (wsVadTimerRef.current) {
      clearTimeout(wsVadTimerRef.current);
      wsVadTimerRef.current = null;
    }
    if (wsRecorderRef.current && wsRecorderRef.current.state !== 'inactive') {
      try {
        wsRecorderRef.current.stop();
      } catch (e) {}
      wsRecorderRef.current = null;
    }
    if (wsStreamRef.current) {
      wsStreamRef.current.getTracks().forEach(track => track.stop());
      wsStreamRef.current = null;
    }
    if (wsAudioContextRef.current) {
      wsAudioContextRef.current.close().catch(() => {});
      wsAudioContextRef.current = null;
    }
    if (playingAudioRef.current) {
      playingAudioRef.current.pause();
      playingAudioRef.current = null;
    }
    if (wsClientRef.current) {
      wsClientRef.current.close();
      wsClientRef.current = null;
    }
    setIsWsCallActive(false);
    setWsCallState('idle');
    setWsAudioLevel(0);
    setIsTyping(false);
  };

  // 组件卸载时清理语音连接与媒体流
  useEffect(() => {
    return () => {
      handleStopWsCall();
    };
  }, []);

  const formatValue = (value) => {
    if (Array.isArray(value)) {
      return value.join(', ');
    }
    return value;
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
        appointment.salesman ||
        appointment.brand ||
        appointment.selected_car_model
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
                  {appointment.test_driver_name && (
                    <div className="appointment-item">
                      <span className="item-label">Driver Name:</span>
                      <span className="item-value">{appointment.test_driver_name}</span>
                    </div>
                  )}
                  {appointment.brand && (
                    <div className="appointment-item">
                      <span className="item-label">Brand:</span>
                      <span className="item-value">{appointment.brand}</span>
                    </div>
                  )}
                  {appointment.selected_car_model && (
                    <div className="appointment-item">
                      <span className="item-label">Car Model:</span>
                      <span className="item-value">{appointment.selected_car_model}</span>
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
                  {appointment.salesman && (
                    <div className="appointment-item">
                      <span className="item-label">Salesman:</span>
                      <span className="item-value">{appointment.salesman}</span>
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
            {needs && (needs.explicit || needs.implicit) ? (
              <>
                {/* 处理显式需求 - 仅显示非空字段 */}
                {needs.explicit && Object.entries(needs.explicit)
                  .filter(([, value]) => value && String(value).trim())
                  .map(([category, value], index) => (
                    <div key={`explicit-${index}`} className="analysis-item">
                      {category}: {formatValue(value)}
                    </div>
                  ))}

                {/* 处理隐式需求 - 仅显示非空字段 */}
                {needs.implicit && Object.entries(needs.implicit)
                  .filter(([, value]) => value && String(value).trim())
                  .map(([category, value], index) => (
                    <div key={`implicit-${index}`} className="analysis-item">
                      {category}: {formatValue(value)}
                      <span className="implicit-tag">, implicit</span>
                    </div>
                  ))}
              </>
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
                  {typeof car === 'string' ? car : (car.car_model || JSON.stringify(car))}
                  {car.score != null && <span className="car-score"> (score: {car.score})</span>}
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
        {/* ASR & TTS 实时语音诊断与监控面板 */}
        <div className="voice-diagnostics-bar">
          <div className="diag-header">
            <span className="diag-title"><i className="fa-solid fa-wave-square"></i> ASR / TTS 语音引擎监控</span>
            {asrTelemetry?.timeMs > 0 && <span className="diag-badge">{asrTelemetry.timeMs}ms</span>}
          </div>
          <div className="diag-body">
            <div className={`diag-box asr ${asrTelemetry?.status === 'empty' ? 'warning' : ''}`}>
              <span className="diag-label">🎤 ASR 识别</span>
              <span className="diag-text">
                {asrTelemetry ? `"${asrTelemetry.text}"` : '未开始或尚无识别数据'}
              </span>
            </div>
            <div className="diag-box tts">
              <span className="diag-label">🔊 TTS 播报</span>
              <span className="diag-text">
                {ttsTelemetry ? `${ttsTelemetry.status} (${Math.round((ttsTelemetry.size || 0) / 1024)} KB)` : '就绪'}
              </span>
            </div>
          </div>
        </div>

        {/* 低延迟全双工 WebSocket 实时通话状态条 */}
        {isWsCallActive && (
          <div className="ws-call-bar">
            <div className="ws-call-info">
              <span className="ws-call-dot pulse"></span>
              <span className="ws-call-status-text">
                {wsCallState === 'connecting' && '⚡ 正在建立 WebSocket 语音连接...'}
                {wsCallState === 'listening' && '🎙️ 随时说话中 (静音自动感应)'}
                {wsCallState === 'speaking' && '🗣️ 正在检测您的语音...'}
                {wsCallState === 'thinking' && '🤖 AI 智能思考与检索中...'}
                {wsCallState === 'playing' && '🔊 AI 正在语音播报...'}
              </span>
            </div>

            {/* 动态音量波形条 */}
            <div className="ws-audio-meter">
              <div className="ws-audio-bar" style={{ height: `${Math.max(4, wsAudioLevel)}px` }}></div>
              <div className="ws-audio-bar" style={{ height: `${Math.max(6, wsAudioLevel * 0.8)}px` }}></div>
              <div className="ws-audio-bar" style={{ height: `${Math.max(8, wsAudioLevel * 1.2)}px` }}></div>
              <div className="ws-audio-bar" style={{ height: `${Math.max(5, wsAudioLevel * 0.7)}px` }}></div>
            </div>

            <div className="ws-call-actions">
              <button 
                className="ws-action-btn send-turn"
                onClick={handleManualEndTurn}
                disabled={wsCallState === 'thinking' || wsCallState === 'playing'}
                title="说完后可手动提前触发AI回答"
              >
                ⚡ 立即发送
              </button>
              <button className="ws-action-btn hangup" onClick={handleStopWsCall}>
                🔴 结束通话
              </button>
            </div>
          </div>
        )}

        <div className="chat-messages">
          {messages.map((message) => {
            if (message.type === 'system-asr') {
              return (
                <div key={message.id} className="message system-asr animate-in">
                  <div className="system-asr-bubble">
                    <i className="fa-solid fa-microphone-slash"></i>
                    <span>{message.content}</span>
                  </div>
                </div>
              );
            }

            return (
              <div
                key={message.id}
                className={`message ${message.type} animate-in`}
              >
                {message.isVoice && (
                  <div className="voice-tag">
                    {message.type === 'user' ? '🎤 语音识别 (ASR)' : '🔊 语音合成 (TTS)'}
                  </div>
                )}
                <div className="message-content">{message.content}</div>
              </div>
            );
          })}
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
              className={`ws-call-start-btn ${isWsCallActive ? 'active' : ''}`}
              onClick={isWsCallActive ? handleStopWsCall : handleStartWsCall}
              title="低延迟全双工 WebSocket 实时语音通话"
            >
              {isWsCallActive ? '🔴 结束实时通话' : '📞 开启 WS 实时通话'}
            </button>
            <button
              className={`voice-button ${isRecording ? 'recording' : ''}`}
              onMouseDown={handleStartRecording}
              onMouseUp={handleStopRecording}
              onTouchStart={handleStartRecording}
              onTouchEnd={handleStopRecording}
              title="按住说话，松开自动发送语音"
            >
              {isRecording ? '🎙️ 正在录音(松开发送)' : '🎤 按住说话'}
            </button>
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
                    if (isWsCallActive) {
                      handleStopWsCall();
                    }
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
