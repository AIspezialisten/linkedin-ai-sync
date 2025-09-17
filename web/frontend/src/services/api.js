import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || '/api';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// API functions
export const duplicateAPI = {
  // Get paginated duplicates
  getDuplicates: async (page = 1, perPage = 20, confidence = null, status = 'pending') => {
    const params = new URLSearchParams({ page, per_page: perPage });
    if (confidence) params.append('confidence', confidence);
    if (status) params.append('status', status);

    const response = await api.get(`/duplicates?${params}`);
    return response.data;
  },

  // Get specific duplicate
  getDuplicate: async (duplicateId) => {
    const response = await api.get(`/duplicates/${duplicateId}`);
    return response.data;
  },

  // Approve duplicate and update CRM
  approveDuplicate: async (duplicateId, updateData, userDecision = null) => {
    const response = await api.post(`/duplicates/${duplicateId}/approve`, {
      update_data: updateData,
      user_decision: userDecision
    });
    return response.data;
  },

  // Reject duplicate
  rejectDuplicate: async (duplicateId, reason = null) => {
    const response = await api.post(`/duplicates/${duplicateId}/reject`, {
      reason
    });
    return response.data;
  },

  // Flag for later review
  flagDuplicate: async (duplicateId, reason = null) => {
    const response = await api.post(`/duplicates/${duplicateId}/flag`, {
      reason
    });
    return response.data;
  },

  // Get statistics
  getStats: async () => {
    const response = await api.get('/stats');
    return response.data;
  },

  // Get recent sessions
  getRecentSessions: async (limit = 10) => {
    const response = await api.get(`/sessions?limit=${limit}`);
    return response.data;
  }
};

export default api;