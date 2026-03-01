'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import api from '@/lib/api';
import { UserPlus, Loader2, CheckCircle2, AlertCircle } from 'lucide-react';

export default function RegisterPage() {
  const [email, setEmail] = useState('');
  const [nickname, setNickname] = useState('');
  const [baekjoonId, setBaekjoonId] = useState('');
  const [password, setPassword] = useState('');
  const [passwordConfirm, setPasswordConfirm] = useState(''); 
  const [invitationCode, setInvitationCode] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isSuccess, setIsSuccess] = useState(false);
  const router = useRouter();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (password !== passwordConfirm) {
      setError('비밀번호가 일치하지 않습니다.');
      return;
    }

    if (!invitationCode.trim()) {
      setError('초대 코드를 입력해주세요.');
      return;
    }

    setIsLoading(true);

    try {
      await api.post('/users/', {
        email,
        nickname,
        baekjoon_id: baekjoonId,
        password,
        invitation_code: invitationCode.trim().toUpperCase(),
      });

      setIsSuccess(true);
      setTimeout(() => {
        router.push('/login');
      }, 2000);
    } catch (err: any) {
      setError(err.response?.data?.detail || '회원가입에 실패했습니다. 초대 코드를 다시 확인해주세요.');
    } finally {
      setIsLoading(false);
    }
  };

  if (isSuccess) {
    return (
      <div className="min-h-screen flex items-center justify-center p-4">
        <div className="max-w-md w-full bg-white rounded-2xl shadow-xl p-10 border border-gray-100 text-center">
          <div className="inline-flex items-center justify-center w-20 h-20 bg-green-100 text-green-600 rounded-full mb-6">
            <CheckCircle2 size={48} />
          </div>
          <h1 className="text-2xl font-bold text-gray-900">환영합니다!</h1>
          <p className="text-gray-500 mt-2">회원가입이 완료되었습니다.<br />잠시 후 로그인 페이지로 이동합니다.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex flex-col items-center justify-start px-4 pt-20 pb-10">
      <div className="max-w-md w-full">
        <div className="text-center mb-10">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-blue-600 rounded-2xl mb-4 text-white shadow-xl shadow-blue-200">
            <UserPlus size={32} />
          </div>
          <h1 className="text-3xl font-black text-gray-900 tracking-tight italic uppercase">Join the Legend</h1>
          <p className="text-gray-500 mt-2 font-medium">새로운 전설의 시작을 함께하세요.</p>
        </div>

        {error && (
          <div className="mb-6 p-4 bg-red-50 text-red-600 text-sm rounded-2xl flex items-center gap-2 border border-red-100">
            <AlertCircle size={18} className="shrink-0" />
            <span className="font-bold">{error}</span>
          </div>
        )}

        <div className="bg-white p-10 rounded-[2.5rem] shadow-sm border border-gray-100">
          <form onSubmit={handleSubmit} className="space-y-5">
            <div className="p-5 bg-amber-50 rounded-2xl border border-amber-100 mb-2">
              <div className="flex justify-between items-center mb-2">
                <label className="text-[10px] font-black text-amber-700 uppercase tracking-widest ml-1">Invitation Code</label>
                <span className="text-[9px] font-black bg-amber-200 text-amber-800 px-2 py-0.5 rounded-full uppercase">Beta Access</span>
              </div>
              <input
                type="text"
                value={invitationCode}
                onChange={(e) => setInvitationCode(e.target.value)}
                className="w-full px-4 py-3 rounded-xl border border-amber-200 focus:outline-none focus:ring-4 focus:ring-amber-500/20 focus:border-amber-500 transition-all font-black text-center tracking-widest placeholder:font-medium placeholder:tracking-normal placeholder:text-amber-300 text-amber-900"
                placeholder="코드 입력"
                required
              />
            </div>

            <div className="space-y-1.5">
              <label className="text-[10px] font-black text-gray-400 uppercase tracking-widest ml-1">Email Address</label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full px-5 py-3.5 rounded-2xl bg-gray-50 border border-transparent focus:bg-white focus:border-blue-500 focus:ring-4 focus:ring-blue-50 transition-all font-bold text-gray-900 outline-none"
                placeholder="name@example.com"
                required
              />
            </div>

            <div className="space-y-1.5">
              <label className="text-[10px] font-black text-gray-400 uppercase tracking-widest ml-1">Nickname</label>
              <input
                type="text"
                value={nickname}
                onChange={(e) => setNickname(e.target.value)}
                className="w-full px-5 py-3.5 rounded-2xl bg-gray-50 border border-transparent focus:bg-white focus:border-blue-500 focus:ring-4 focus:ring-blue-50 transition-all font-bold text-gray-900 outline-none"
                placeholder="멋진 닉네임"
                required
              />
            </div>

            <div className="space-y-1.5">
              <label className="text-[10px] font-black text-gray-400 uppercase tracking-widest ml-1">Baekjoon ID</label>
              <input
                type="text"
                value={baekjoonId}
                onChange={(e) => setBaekjoonId(e.target.value)}
                className="w-full px-5 py-3.5 rounded-2xl bg-gray-50 border border-transparent focus:bg-white focus:border-blue-500 focus:ring-4 focus:ring-blue-50 transition-all font-bold text-gray-900 outline-none"
                placeholder="baekjoon_id"
                required
              />
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <label className="text-[10px] font-black text-gray-400 uppercase tracking-widest ml-1">Password</label>
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full px-5 py-3.5 rounded-2xl bg-gray-50 border border-transparent focus:bg-white focus:border-blue-500 focus:ring-4 focus:ring-blue-50 transition-all font-bold text-gray-900 outline-none"
                  placeholder="••••••••"
                  required
                />
              </div>
              <div className="space-y-1.5">
                <label className="text-[10px] font-black text-gray-400 uppercase tracking-widest ml-1">Confirm</label>
                <input
                  type="password"
                  value={passwordConfirm}
                  onChange={(e) => setPasswordConfirm(e.target.value)}
                  className="w-full px-5 py-3.5 rounded-2xl bg-gray-50 border border-transparent focus:bg-white focus:border-blue-500 focus:ring-4 focus:ring-blue-50 transition-all font-bold text-gray-900 outline-none"
                  placeholder="••••••••"
                  required
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="w-full bg-blue-600 hover:bg-blue-700 text-white font-black uppercase tracking-tighter py-5 rounded-2xl transition-all shadow-xl shadow-blue-100 flex items-center justify-center gap-2 mt-4 active:scale-95 disabled:opacity-70"
            >
              {isLoading ? (
                <Loader2 className="animate-spin" size={24} />
              ) : (
                'Create Account'
              )}
            </button>
          </form>

          <div className="mt-8 text-center text-sm font-bold text-gray-400 uppercase tracking-widest">
            이미 계정이 있으신가요? <Link href="/login" className="text-blue-600 hover:underline ml-2">로그인</Link>
          </div>
        </div>
      </div>
    </div>
  );
}
