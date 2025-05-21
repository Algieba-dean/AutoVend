import axios from 'axios';

const API_BASE_URL = '/api';

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
      const response = await axios.get(`${API_BASE_URL}/profiles`);
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
  }
};

// Vehicle Needs API
export const needsService = {
  getUserNeeds: async (profileId) => {
    try {
      const response = await axios.get(`${API_BASE_URL}/needs/${profileId}`);
      return response.data;
    } catch (error) {
      console.error('Failed to get user needs:', error);
      throw error;
    }
  },
  
  addNeed: async (profileId, category, value, isImplicit = false) => {
    try {
      const response = await axios.post(`${API_BASE_URL}/needs/${profileId}`, {
        category,
        value,
        is_implicit: isImplicit
      });
      return response.data;
    } catch (error) {
      console.error('Failed to add need:', error);
      throw error;
    }
  },
  
  // 添加更新需求的方法
  updateNeed: async (profileId, needId, needData) => {
    try {
      const response = await axios.put(`${API_BASE_URL}/needs/${profileId}/${needId}`, needData);
      return response.data;
    } catch (error) {
      console.error('Failed to update need:', error);
      throw error;
    }
  },
  
  // 添加删除需求的方法
  deleteNeed: async (profileId, needId) => {
    try {
      const response = await axios.delete(`${API_BASE_URL}/needs/${profileId}/${needId}`);
      return response.data;
    } catch (error) {
      console.error('Failed to delete need:', error);
      throw error;
    }
  }
};

// Vehicle Recommendation API
export const recommendationService = {
  getRecommendations: async (profileId) => {
    try {
      const response = await axios.get(`${API_BASE_URL}/recommendations/${profileId}`);
      return response.data;
    } catch (error) {
      console.error('Failed to get vehicle recommendations:', error);
      throw error;
    }
  },
  
  // 添加获取特定车型详情的方法
  getCarDetails: async (carId) => {
    try {
      const response = await axios.get(`${API_BASE_URL}/car/${carId}`);
      return response.data;
    } catch (error) {
      console.error('Failed to get car details:', error);
      throw error;
    }
  },
  
  // 添加搜索车型的方法
  searchCars: async (searchParams) => {
    try {
      const response = await axios.post(`${API_BASE_URL}/cars/search`, searchParams);
      return response.data;
    } catch (error) {
      console.error('Failed to search cars:', error);
      throw error;
    }
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