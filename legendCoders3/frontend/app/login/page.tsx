'use client';

import React, { useState, useEffect } from 'react';
import { useAuth } from '@/components/auth-provider';
import { useRouter } from 'next/navigation';
import api from '@/lib/api';
import { User, Lock, Loader2, ArrowRight, AlertCircle } from 'lucide-react';
import Link from 'next/link';

export default function LoginPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const { user, loading, login } = useAuth();
  const router = useRouter();

  // Redirect if already logged in
  useEffect(() => {
    if (!loading && user) {
      router.push('/dashboard');
    }
  }, [user, loading, router]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError('');

    try {
      const formData = new FormData();
      formData.append('username', email);
      formData.append('password', password);

      const response = await api.post(`/users/token`, formData, {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
      });
      
      const { access_token, refresh_token } = response.data;
      await login(access_token, refresh_token);
      router.push('/dashboard');
    } catch (err: any) {
      setError(err.response?.data?.detail || '로그인에 실패했습니다. 이메일과 비밀번호를 확인해주세요.');
    } finally {
      setIsLoading(false);
    }
  };

  if (loading || user) {
    return (
      <div className="flex items-center justify-center min-h-[80vh]">
        <div className="animate-pulse text-blue-600 font-bold">인증 로딩 중...</div>
      </div>
    );
  }

  return (
    <div className="min-h-[80vh] flex items-center justify-center px-4">
      <div className="max-w-md w-full">
        <div className="text-center mb-10">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-blue-600 rounded-2xl mb-4 shadow-xl shadow-blue-200">
            <User className="text-white" size={32} />
          </div>
          <h1 className="text-3xl font-black text-gray-900 tracking-tight italic uppercase">Welcome Back</h1>
          <p className="text-gray-500 mt-2 font-medium">다시 전설을 써내려갈 시간입니다.</p>
        </div>

        <div className="bg-white p-10 rounded-[2.5rem] shadow-sm border border-gray-100">
          <form onSubmit={handleSubmit} className="space-y-6">
            {error && (
              <div className="p-4 bg-red-50 text-red-600 text-sm rounded-2xl flex items-center gap-2 border border-red-100">
                <AlertCircle size={18} />
                <span className="font-bold">{error}</span>
              </div>
            )}

            <div className="space-y-2">
              <label className="text-[10px] font-black text-gray-400 uppercase tracking-widest ml-1">Email Address</label>
              <div className="relative">
                <User className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400" size={18} />
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full pl-12 pr-4 py-4 rounded-2xl bg-gray-50 border border-transparent focus:bg-white focus:border-blue-500 focus:ring-4 focus:ring-blue-50 outline-none transition-all font-bold text-gray-900"
                  placeholder="name@example.com"
                  required
                />
              </div>
            </div>

            <div className="space-y-2">
              <label className="text-[10px] font-black text-gray-400 uppercase tracking-widest ml-1">Password</label>
              <div className="relative">
                <Lock className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400" size={18} />
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full pl-12 pr-4 py-4 rounded-2xl bg-gray-50 border border-transparent focus:bg-white focus:border-blue-500 focus:ring-4 focus:ring-blue-50 outline-none transition-all font-bold text-gray-900"
                  placeholder="••••••••"
                  required
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="w-full bg-blue-600 hover:bg-blue-700 text-white py-5 rounded-2xl font-black uppercase tracking-tighter shadow-xl shadow-blue-100 transition-all flex items-center justify-center gap-2 active:scale-95 disabled:opacity-70"
            >
              {isLoading ? (
                <Loader2 className="animate-spin" size={24} />
              ) : (
                <>
                  Sign In <ArrowRight size={20} />
                </>
              )}
            </button>
          </form>

          <div className="mt-8 text-center text-sm font-bold text-gray-400 uppercase tracking-widest">
            계정이 없으신가요? <Link href="/register" className="text-blue-600 hover:underline ml-2">회원가입</Link>
          </div>
        </div>
      </div>
    </div>
  );
}
