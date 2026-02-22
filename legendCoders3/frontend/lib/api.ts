// frontend/lib/api.ts
import axios from 'axios';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: true,
});

// Request interceptor: attach access_token from localStorage
api.interceptors.request.use((config) => {
  if (typeof window !== 'undefined') {
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
  }
  return config;
});

// Response interceptor: handle 401 and token rotation
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    
    // If 401 and not already retried
    if (error.response?.status === 401 && !originalRequest._retry && !originalRequest.url.includes('/users/token')) {
      originalRequest._retry = true;
      
      try {
        const refreshToken = localStorage.getItem('refresh_token');
        if (!refreshToken) throw new Error('No refresh token');

        // Note: Backend endpoint for refresh expects a query param or body?
        // backend/app/routers/users.py: refresh_access_token(refresh_token: str, ...) 
        // In FastAPI, if it's a simple string parameter, it's usually a query param.
        const res = await axios.post(`${API_URL}/users/refresh?refresh_token=${refreshToken}`);
        
        if (res.status === 200) {
          const { access_token, refresh_token: new_refresh_token } = res.data;
          localStorage.setItem('access_token', access_token);
          localStorage.setItem('refresh_token', new_refresh_token);
          api.defaults.headers.common['Authorization'] = `Bearer ${access_token}`;
          return api(originalRequest);
        }
      } catch (refreshError) {
        // Refresh failed: clear tokens and redirect to login
        if (typeof window !== 'undefined') {
          localStorage.removeItem('access_token');
          localStorage.removeItem('refresh_token');
          window.location.href = '/login';
        }
      }
    }
    return Promise.reject(error);
  }
);

export const arenaApi = {
  createArena: async (difficulty: string, mode: string = "OPEN") => {
    const response = await api.post('/api/arena/', { difficulty, mode });
    return response.data;
  },
  
  getOpenArenas: async () => {
    const response = await api.get('/api/arena/');
    return response.data;
  },
  
  getArena: async (id: string) => {
    const response = await api.get(`/api/arena/${id}`);
    return response.data;
  },
  
  joinArena: async (id: string) => {
    const response = await api.post(`/api/arena/${id}/join`);
    return response.data;
  },
  
  checkSubmission: async (id: string) => {
    const response = await api.post(`/api/arena/${id}/submit`);
    return response.data;
  },
  
  getActiveArena: async () => {
    const response = await api.get('/api/arena/active');
    return response.data;
  }
};

export default api;
