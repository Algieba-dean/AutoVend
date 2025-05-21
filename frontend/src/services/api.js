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
  }
};