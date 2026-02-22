'use client';

import React, { createContext, useContext, useEffect, useState, useCallback, useMemo } from 'react';
import api from '@/lib/api';
import { useRouter } from 'next/navigation';

interface User {
  id: string;
  email: string;
  nickname: string;
  baekjoon_id: string;
  is_pro: boolean;
  streak_freeze_count: number;
  equipped_title?: any;
}

interface AuthContextType {
  user: User | null;
  accessToken: string | null;
  loading: boolean;
  login: (access_token: string, refresh_token: string) => Promise<void>;
  logout: () => void;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [accessToken, setAccessToken] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const router = useRouter();

  const refreshUser = useCallback(async () => {
    try {
      const response = await api.get('/users/me/');
      setUser(response.data);
      if (typeof window !== 'undefined') {
        setAccessToken(localStorage.getItem('access_token'));
      }
    } catch (error: any) {
      // If unauthorized, try to manually refresh once
      if (error.response?.status === 401) {
        const rt = localStorage.getItem('refresh_token');
        if (rt) {
          try {
            console.log("[Auth] Attempting token rotation via refreshUser...");
            const res = await api.post(`/users/refresh?refresh_token=${rt}`);
            const { access_token, refresh_token: new_rt } = res.data;
            localStorage.setItem('access_token', access_token);
            localStorage.setItem('refresh_token', new_rt);
            setAccessToken(access_token);
            // Retry user fetch
            const retryResponse = await api.get('/users/me/');
            setUser(retryResponse.data);
            return;
          } catch (refreshErr) {
            console.error("[Auth] Forced logout due to expired refresh token");
          }
        }
      }
      setUser(null);
      setAccessToken(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (typeof window !== 'undefined') {
      const token = localStorage.getItem('access_token');
      setAccessToken(token);
      if (token) {
        refreshUser();
      } else {
        setLoading(false);
      }
    }
  }, [refreshUser]);

  const login = useCallback(async (access_token: string, refresh_token: string) => {
    localStorage.setItem('access_token', access_token);
    localStorage.setItem('refresh_token', refresh_token);
    setAccessToken(access_token);
    await refreshUser();
    router.push('/dashboard');
  }, [refreshUser, router]);

  const logout = useCallback(() => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    setUser(null);
    setAccessToken(null);
    router.push('/login');
  }, [router]);

  const contextValue = useMemo(() => ({
    user,
    accessToken,
    loading,
    login,
    logout,
    refreshUser
  }), [user, accessToken, loading, login, logout, refreshUser]);

  return (
    <AuthContext.Provider value={contextValue}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
