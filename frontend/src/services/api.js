import axios from 'axios';

const getApiBaseUrl = () => {
  if (typeof window !== 'undefined' && window.location.port && window.location.port !== '8000') {
    return `${window.location.protocol}//${window.location.hostname}:8000/api`;
  }
  return '/api';
};

const API_BASE_URL = getApiBaseUrl();

// User Profile API
export const profileService = {
  getDefaultProfile: async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/profile/default`);
      return response.data;
    } catch (error) {
      console.error('Failed to get default profile:', error);
      throw error;
    }
  },

  getUserProfile: async (phoneNumber) => {
    try {
      const response = await axios.get(`${API_BASE_URL}/profile/${phoneNumber}`);
      return response.data;
    } catch (error) {
      if (error.response && error.response.status === 404) {
        return null; // Return null when user doesn't exist
      }
      console.error('Failed to get user profile:', error);
      throw error;
    }
  },

  createProfile: async (profileData) => {
    try {
      const response = await axios.post(`${API_BASE_URL}/profile`, profileData);
      return response.data;
    } catch (error) {
      console.error('Failed to create profile:', error);
      throw error;
    }
  },

  updateProfile: async (phoneNumber, profileData) => {
    try {
      const response = await axios.put(`${API_BASE_URL}/profile/${phoneNumber}`, profileData);
      return response.data;
    } catch (error) {
      console.error('Failed to update profile:', error);
      throw error;
    }
  },

  // 添加删除用户资料的方法
  deleteProfile: async (phoneNumber) => {
    try {
      const response = await axios.delete(`${API_BASE_URL}/profile/${phoneNumber}`);
      return response.data;
    } catch (error) {
      console.error('Failed to delete profile:', error);
      throw error;
    }
  },

  // 添加获取所有用户资料的方法
  getAllProfiles: async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/profile`);
      return response.data;
    } catch (error) {
      console.error('Failed to get all profiles:', error);
      throw error;
    }
  }
};

// Chat API
export const chatService = {
  startSession: async (phoneNumber) => {
    try {
      const response = await axios.post(`${API_BASE_URL}/chat/session`, { phone_number: phoneNumber });
      return response.data;
    } catch (error) {
      console.error('Failed to start chat session:', error);
      throw error;
    }
  },

  sendMessage: async (sessionId, message) => {
    try {
      const response = await axios.post(`${API_BASE_URL}/chat/message`, {
        session_id: sessionId,
        message
      });
      return response.data;
    } catch (error) {
      console.error('Failed to send message:', error);
      throw error;
    }
  },

  getMessages: async (sessionId, limit = 50) => {
    try {
      const params = new URLSearchParams();
      if (limit) params.append('limit', limit);

      const response = await axios.get(
        `${API_BASE_URL}/chat/session/${sessionId}/messages?${params.toString()}`
      );
      return response.data;
    } catch (error) {
      console.error('Failed to get messages:', error);
      throw error;
    }
  },

  endSession: async (sessionId) => {
    try {
      const response = await axios.put(`${API_BASE_URL}/chat/session/${sessionId}/end`);
      return response.data;
    } catch (error) {
      console.error('Failed to end session:', error);
      throw error;
    }
  },

  // 添加获取所有会话的方法
  getAllSessions: async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/chat/sessions`);
      return response.data;
    } catch (error) {
      console.error('Failed to get all sessions:', error);
      throw error;
    }
  },

  // 添加获取单个会话详情的方法
  getSessionDetails: async (sessionId) => {
    try {
      const response = await axios.get(`${API_BASE_URL}/chat/session/${sessionId}`);
      return response.data;
    } catch (error) {
      console.error('Failed to get session details:', error);
      throw error;
    }
  },

  // 流式 SSE 发送消息
  sendMessageStream: async (sessionId, message, { onMetadata, onToken, onDone, onError }) => {
    try {
      const response = await fetch(`${API_BASE_URL}/chat/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId, message })
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder('utf-8');
      let buffer = '';

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const events = buffer.split('\n\n');
        buffer = events.pop();

        for (const rawEvent of events) {
          if (!rawEvent.trim()) continue;

          let eventType = 'message';
          let dataStr = '';

          const lines = rawEvent.split('\n');
          for (const line of lines) {
            if (line.startsWith('event: ')) {
              eventType = line.slice(7).trim();
            } else if (line.startsWith('data: ')) {
              dataStr = line.slice(6).trim();
            }
          }

          if (!dataStr) continue;

          try {
            const parsedData = JSON.parse(dataStr);
            if (eventType === 'metadata' && onMetadata) {
              onMetadata(parsedData);
            } else if (eventType === 'token' && onToken) {
              onToken(parsedData.delta);
            } else if (eventType === 'done' && onDone) {
              onDone(parsedData.response_text);
            }
          } catch (e) {
            console.error('Failed to parse SSE data:', e, dataStr);
          }
        }
      }
    } catch (err) {
      console.error('SSE Stream Error:', err);
      if (onError) onError(err);
    }
  }
};

// Vehicle Needs API (backed by session/profile details)
export const needsService = {
  getUserNeeds: async (sessionOrProfileId) => {
    try {
      const response = await axios.get(`${API_BASE_URL}/chat/session/${sessionOrProfileId}`);
      return {
        explicit: response.data.explicit_needs || {},
        implicit: response.data.implicit_needs || {}
      };
    } catch (error) {
      console.error('Failed to get user needs:', error);
      throw error;
    }
  }
};

// Vehicle Recommendation & Truth Catalog API
export const recommendationService = {
  getRecommendations: async (sessionId) => {
    try {
      const response = await axios.get(`${API_BASE_URL}/chat/session/${sessionId}`);
      return response.data.matched_cars || [];
    } catch (error) {
      console.error('Failed to get vehicle recommendations:', error);
      throw error;
    }
  },

  getCarDetails: async (carModel) => {
    try {
      const response = await axios.get(`${API_BASE_URL}/truth/report/${encodeURIComponent(carModel)}`);
      return response.data;
    } catch (error) {
      console.error('Failed to get car details:', error);
      throw error;
    }
  },

  listKnownModels: async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/truth/models`);
      return response.data;
    } catch (error) {
      console.error('Failed to list known models:', error);
      throw error;
    }
  }
};

// Consumer Truth Engine API (/api/truth/*)
export const truthService = {
  deconstructSpecs: async (carModel) => {
    const response = await axios.get(`${API_BASE_URL}/truth/deconstruct`, {
      params: { car_model: carModel }
    });
    return response.data;
  },

  debiasMarketing: async (claim, carModel = null) => {
    const response = await axios.post(`${API_BASE_URL}/truth/debias`, {
      claim,
      car_model: carModel
    });
    return response.data;
  },

  getReliability: async (carModel, queryFilter = '') => {
    const response = await axios.get(`${API_BASE_URL}/truth/reliability`, {
      params: { car_model: carModel, query_filter: queryFilter }
    });
    return response.data;
  },

  calculatePricing: async ({ carModel, msrpWan = null, cashDiscount = 0, perksDiscount = 0, tradeInSubsidy = 0 }) => {
    const response = await axios.post(`${API_BASE_URL}/truth/pricing`, {
      car_model: carModel,
      msrp_wan: msrpWan,
      cash_discount: cashDiscount,
      perks_discount: perksDiscount,
      trade_in_subsidy: tradeInSubsidy
    });
    return response.data;
  },

  getNationalStandards: async () => {
    const response = await axios.get(`${API_BASE_URL}/truth/standards`);
    return response.data;
  },

  getFullTruthReport: async (carModel) => {
    const response = await axios.get(`${API_BASE_URL}/truth/report/${encodeURIComponent(carModel)}`);
    return response.data;
  }
};

// Automotive Terminology Knowledge Graph API (/api/terminology/*)
export const terminologyService = {
  resolveTerm: async (term, context = '') => {
    const response = await axios.get(`${API_BASE_URL}/terminology/resolve`, {
      params: { term, context }
    });
    return response.data;
  },

  extractTerms: async (text) => {
    const response = await axios.post(`${API_BASE_URL}/terminology/extract`, { text });
    return response.data;
  },

  compareTechnologies: async (terms) => {
    const response = await axios.post(`${API_BASE_URL}/terminology/compare`, { terms });
    return response.data;
  },

  getEquivalents: async (term) => {
    const response = await axios.get(`${API_BASE_URL}/terminology/equivalents/${encodeURIComponent(term)}`);
    return response.data;
  },

  getBrandTechStack: async (brandKey) => {
    const response = await axios.get(`${API_BASE_URL}/terminology/brand/${encodeURIComponent(brandKey)}`);
    return response.data;
  },

  listCategories: async () => {
    const response = await axios.get(`${API_BASE_URL}/terminology/categories`);
    return response.data;
  }
};

// Enterprise MLOps & Observability API (/api/v1/mlops/*)
export const mlopsService = {
  listExperiments: async (experimentName = null) => {
    const response = await axios.get(`${API_BASE_URL}/v1/mlops/experiments`, {
      params: experimentName ? { experiment_name: experimentName } : {}
    });
    return response.data;
  },

  listPrompts: async (promptName = 'response_generation') => {
    const response = await axios.get(`${API_BASE_URL}/v1/mlops/prompts`, {
      params: { prompt_name: promptName }
    });
    return response.data;
  },

  getDriftReport: async (format = 'json') => {
    const response = await axios.get(`${API_BASE_URL}/v1/mlops/drift`, {
      params: { format }
    });
    return response.data;
  },

  getCanaryStatus: async () => {
    const response = await axios.get(`${API_BASE_URL}/v1/mlops/canary`);
    return response.data;
  },

  listDlqTasks: async (status = null) => {
    const response = await axios.get(`${API_BASE_URL}/v1/mlops/dlq`, {
      params: status ? { status } : {}
    });
    return response.data;
  },

  listAlerts: async () => {
    const response = await axios.get(`${API_BASE_URL}/v1/mlops/alerts`);
    return response.data;
  }
};

// 添加预约服务
export const reservationService = {
  createReservation: async (sessionId, reservationData) => {
    try {
      const response = await axios.post(`${API_BASE_URL}/test-drive`, {
        test_drive_info: {
          ...reservationData
        }
      });
      return response.data;
    } catch (error) {
      console.error('创建预约失败:', error);
      throw error;
    }
  },

  getReservation: async (phoneNumber) => {
    try {
      const response = await axios.get(`${API_BASE_URL}/test-drive/${phoneNumber}`);
      return response.data;
    } catch (error) {
      console.error('获取预约失败:', error);
      throw error;
    }
  },

  updateReservation: async (phoneNumber, reservationData) => {
    try {
      const response = await axios.put(`${API_BASE_URL}/test-drive/${phoneNumber}`, {
        test_drive_info: {
          ...reservationData
        }
      });
      return response.data;
    } catch (error) {
      console.error('更新预约失败:', error);
      throw error;
    }
  },

  cancelReservation: async (phoneNumber) => {
    try {
      const response = await axios.delete(`${API_BASE_URL}/test-drive/${phoneNumber}`);
      return response.data;
    } catch (error) {
      console.error('取消预约失败:', error);
      throw error;
    }
  },

  getAllReservations: async (filters = {}) => {
    try {
      // 支持可选的筛选参数
      const params = new URLSearchParams();
      if (filters.status) params.append('status', filters.status);
      if (filters.brand) params.append('brand', filters.brand);
      if (filters.from_date) params.append('from_date', filters.from_date);
      if (filters.to_date) params.append('to_date', filters.to_date);
      if (filters.limit) params.append('limit', filters.limit);
      if (filters.offset) params.append('offset', filters.offset);

      const url = `${API_BASE_URL}/test-drive${params.toString() ? '?' + params.toString() : ''}`;
      const response = await axios.get(url);
      return response.data.test_drives || [];
    } catch (error) {
      console.error('获取所有预约失败:', error);
      throw error;
    }
  }
};

// 语音服务 Voice API
export const voiceService = {
  // 一步到位语音交互 (上传语音 Blob -> ASR识别 -> SalesAgent思考 -> TTS合成 -> 返回识别文本与回复音频Base64)
  processVoiceTurn: async (sessionId, audioBlob) => {
    try {
      const formData = new FormData();
      formData.append('file', audioBlob, 'input_audio.webm');
      formData.append('session_id', sessionId);

      const response = await axios.post(`${API_BASE_URL}/voice/process`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      return response.data;
    } catch (error) {
      console.error('语音识别与合成处理失败:', error);
      throw error;
    }
  },

  // 语音识别 ASR (音频文件 -> 识别文本)
  transcribeAudio: async (audioBlob) => {
    try {
      const formData = new FormData();
      formData.append('file', audioBlob, 'input_audio.webm');
      const response = await axios.post(`${API_BASE_URL}/voice/transcribe`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      return response.data;
    } catch (error) {
      console.error('语音转写识别失败:', error);
      throw error;
    }
  },

  // 语音合成 TTS (文本 -> MP3 音频播放)
  synthesizeSpeech: async (text) => {
    try {
      const response = await axios.post(
        `${API_BASE_URL}/voice/synthesize?text=${encodeURIComponent(text)}`,
        {},
        { responseType: 'blob' }
      );
      const audioUrl = URL.createObjectURL(response.data);
      const audio = new Audio(audioUrl);
      await audio.play();
      return audioUrl;
    } catch (error) {
      console.error('语音合成播放失败:', error);
      throw error;
    }
  },

  // 创建语音会话
  createVoiceSession: async (phoneNumber = '') => {
    try {
      const response = await axios.post(`${API_BASE_URL}/voice/session?phone_number=${encodeURIComponent(phoneNumber)}`);
      return response.data;
    } catch (error) {
      console.error('创建语音会话失败:', error);
      throw error;
    }
  },

  // 实时低延迟全双工 WebSocket 通话连接
  createVoiceWebSocket: (sessionId, handlers = {}) => {
    if (!sessionId || sessionId === 'undefined') {
      console.error('[VoiceWS] 拒绝连接: sessionId 为空或 undefined');
      if (handlers.onError) handlers.onError(new Error('Invalid sessionId'));
      return { sendAudio: () => {}, endTurn: () => {}, ping: () => {}, close: () => {} };
    }

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsHost = (typeof window !== 'undefined' && window.location.port && window.location.port !== '8000')
      ? `${window.location.hostname}:8000`
      : window.location.host;
    const wsUrl = `${protocol}//${wsHost}/api/voice/ws/${sessionId}`;

    const ws = new WebSocket(wsUrl);
    ws.binaryType = 'arraybuffer';

    ws.onopen = () => {
      console.log(`[VoiceWS] 实时语音 WebSocket 已连接: ${wsUrl}`);
      if (handlers.onOpen) handlers.onOpen();
    };

    ws.onmessage = (event) => {
      if (typeof event.data === 'string') {
        try {
          const json = JSON.parse(event.data);
          if (handlers.onJson) handlers.onJson(json);
        } catch (err) {
          console.error('[VoiceWS] JSON 解析错误:', err);
        }
      } else if (event.data instanceof ArrayBuffer) {
        if (handlers.onAudio) handlers.onAudio(event.data);
      }
    };

    ws.onerror = (err) => {
      console.error('[VoiceWS] 错误:', err);
      if (handlers.onError) handlers.onError(err);
    };

    ws.onclose = () => {
      console.log('[VoiceWS] 实时语音 WebSocket 连接已关闭');
      if (handlers.onClose) handlers.onClose();
    };

    return {
      sendAudio: (arrayBuffer) => {
        if (ws.readyState === WebSocket.OPEN) {
          ws.send(arrayBuffer);
        }
      },
      startTurn: () => {
        if (ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({ type: 'start_turn' }));
        }
      },
      endTurn: () => {
        if (ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({ type: 'end_turn' }));
        }
      },
      ping: () => {
        if (ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({ type: 'ping' }));
        }
      },
      close: () => {
        if (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING) {
          try {
            ws.send(JSON.stringify({ type: 'end_session' }));
          } catch (e) {}
          ws.close();
        }
      }
    };
  }
};
