'use client';

import React, { useState, useEffect } from 'react';
import { useAuth } from '@/components/auth-provider';
import { useRouter } from 'next/navigation';
import api from '@/lib/api';
import { User, Save, Loader2, AlertCircle, CheckCircle2, ChevronLeft, Award } from 'lucide-react';
import Link from 'next/link';
import TitleBadge from '@/components/title-badge';

export default function ProfilePage() {
  const { user, loading, refreshUser } = useAuth();
  const router = useRouter();
  
  const [nickname, setNickname] = useState('');
  const [baekjoonId, setBaekjoonId] = useState('');
  const [password, setPassword] = useState('');
  const [passwordConfirm, setPasswordConfirm] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [message, setMessage] = useState({ type: '', text: '' });

  // Titles State
  const [myTitles, setMyTitles] = useState<any[]>([]);
  const [allTitles, setAllTitles] = useState<any[]>([]);
  const [isTitlesLoading, setIsTitlesLoading] = useState(true);

  useEffect(() => {
    if (!loading && !user) {
      router.push('/login');
    }
    if (user) {
      setNickname(user.nickname);
      setBaekjoonId(user.baekjoon_id);
      fetchTitles();
    }
  }, [user, loading, router]);

  const fetchTitles = async () => {
    try {
      const [myRes, allRes] = await Promise.all([
        api.get('/titles/me'),
        api.get('/titles/all')
      ]);
      setMyTitles(myRes.data);
      setAllTitles(allRes.data);
    } catch (error) {
      console.error('Failed to fetch titles:', error);
    } finally {
      setIsTitlesLoading(false);
    }
  };

  const handleEquip = async (titleId: string) => {
    try {
      await api.post(`/titles/equip/${titleId}`);
      await refreshUser();
      setMessage({ type: 'success', text: '칭호가 성공적으로 변경되었습니다.' });
    } catch (error: any) {
      alert(error.response?.data?.detail || '칭호 장착에 실패했습니다.');
    }
  };

  const handleUnequip = async () => {
    try {
      await api.post('/titles/unequip');
      await refreshUser();
      setMessage({ type: 'success', text: '칭호가 해제되었습니다.' });
    } catch (error) {
      alert('칭호 해제에 실패했습니다.');
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setMessage({ type: '', text: '' });

    if (password.trim() && password !== passwordConfirm) {
      setMessage({ type: 'error', text: '새 비밀번호가 일치하지 않습니다.' });
      return;
    }

    setIsSubmitting(true);
    try {
      const updateData: any = { nickname, baekjoon_id: baekjoonId };
      if (password.trim()) updateData.password = password;

      await api.put('/users/me/', updateData);
      await refreshUser();
      setMessage({ type: 'success', text: '개인정보가 성공적으로 수정되었습니다.' });
      setPassword('');
      setPasswordConfirm('');
    } catch (error: any) {
      setMessage({ type: 'error', text: error.response?.data?.detail || '정보 수정에 실패했습니다.' });
    } finally {
      setIsSubmitting(false);
    }
  };

  if (loading) return null;

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
      <Link 
        href="/dashboard" 
        className="inline-flex items-center text-sm font-bold text-gray-400 hover:text-blue-600 transition-colors mb-8 group"
      >
        <ChevronLeft size={16} className="group-hover:-translate-x-1 transition-transform" />
        대시보드로 돌아가기
      </Link>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Left: Profile Settings */}
        <div className="lg:col-span-2 space-y-8">
          <div className="bg-white rounded-[2.5rem] shadow-sm border border-gray-100 overflow-hidden">
            <div className="bg-gray-900 px-8 py-8 text-white relative overflow-hidden">
              <div className="relative z-10">
                <h1 className="text-2xl font-black tracking-tight uppercase italic">Settings</h1>
                <p className="text-gray-400 text-xs mt-1">개인정보 및 계정 설정</p>
              </div>
              <User size={100} className="absolute -right-6 -bottom-6 text-white/5 rotate-12" />
            </div>

            <form onSubmit={handleSubmit} className="p-8 space-y-6">
              {message.text && (
                <div className={`p-4 rounded-2xl flex items-center gap-3 border ${
                  message.type === 'success' ? 'bg-green-50 text-green-700 border-green-100' : 'bg-red-50 text-red-700 border-red-100'
                }`}>
                  {message.type === 'success' ? <CheckCircle2 size={20} /> : <AlertCircle size={20} />}
                  <span className="font-bold text-sm">{message.text}</span>
                </div>
              )}

              <div className="grid grid-cols-1 gap-6">
                <div className="space-y-2">
                  <label className="text-[10px] font-black text-gray-400 uppercase tracking-widest ml-1">Nickname</label>
                  <input
                    type="text"
                    value={nickname}
                    onChange={(e) => setNickname(e.target.value)}
                    className="w-full px-5 py-3 rounded-xl bg-gray-50 border border-transparent focus:bg-white focus:border-blue-500 transition-all font-bold text-gray-900"
                    required
                  />
                </div>

                <div className="space-y-2">
                  <label className="text-[10px] font-black text-gray-400 uppercase tracking-widest ml-1">Baekjoon ID</label>
                  <input
                    type="text"
                    value={baekjoonId}
                    onChange={(e) => setBaekjoonId(e.target.value)}
                    className="w-full px-5 py-3 rounded-xl bg-gray-50 border border-transparent focus:bg-white focus:border-blue-500 transition-all font-bold text-gray-900"
                    required
                  />
                </div>

                <div className="pt-4 border-t border-gray-50 grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <label className="text-[10px] font-black text-gray-400 uppercase tracking-widest ml-1">New Password</label>
                    <input
                      type="password"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      className="w-full px-5 py-3 rounded-xl bg-gray-50 border border-transparent focus:bg-white focus:border-blue-500 transition-all font-bold text-gray-900"
                      placeholder="••••••••"
                    />
                  </div>
                  <div className="space-y-2">
                    <label className="text-[10px] font-black text-gray-400 uppercase tracking-widest ml-1">Confirm Password</label>
                    <input
                      type="password"
                      value={passwordConfirm}
                      onChange={(e) => setPasswordConfirm(e.target.value)}
                      className="w-full px-5 py-3 rounded-xl bg-gray-50 border border-transparent focus:bg-white focus:border-blue-500 transition-all font-bold text-gray-900"
                      placeholder="••••••••"
                    />
                  </div>
                </div>
              </div>

              <button
                type="submit"
                disabled={isSubmitting}
                className="w-full bg-blue-600 hover:bg-blue-700 text-white py-4 rounded-xl font-black uppercase tracking-tighter transition-all flex items-center justify-center gap-2 active:scale-95 disabled:opacity-70"
              >
                {isSubmitting ? <Loader2 className="animate-spin" size={20} /> : <><Save size={18} /> Save Changes</>}
              </button>
            </form>
          </div>
        </div>

        {/* Right: Titles Grimoire */}
        <div className="space-y-8">
          <div className="bg-white rounded-[2.5rem] shadow-sm border border-gray-100 overflow-hidden">
            <div className="bg-amber-500 px-6 py-6 text-white flex items-center gap-3">
              <Award size={24} />
              <h2 className="text-xl font-black uppercase italic tracking-tighter text-white">Titles</h2>
            </div>
            
            <div className="p-6">
              <p className="text-xs font-bold text-gray-400 mb-6 uppercase tracking-widest">장착 중인 칭호</p>
              {user?.equipped_title ? (
                <div className="flex flex-col items-center gap-4 p-6 bg-gray-50 rounded-3xl border border-dashed border-gray-200">
                  <TitleBadge title={user.equipped_title} size="md" />
                  <button 
                    onClick={handleUnequip}
                    className="text-[10px] font-black text-red-400 hover:text-red-600 uppercase tracking-widest"
                  >
                    장착 해제
                  </button>
                </div>
              ) : (
                <div className="text-center py-6 text-gray-300 text-xs font-bold uppercase italic border border-dashed border-gray-100 rounded-3xl">
                  선택된 칭호 없음
                </div>
              )}

              <div className="mt-10">
                <p className="text-xs font-bold text-gray-400 mb-4 uppercase tracking-widest">나의 칭호 도감</p>
                <div className="space-y-3">
                  {isTitlesLoading ? (
                    <div className="text-center py-4"><Loader2 className="animate-spin text-gray-200 mx-auto" /></div>
                  ) : (
                    allTitles.map((title) => {
                      const isUnlocked = myTitles.some(mt => mt.id === title.id);
                      const isEquipped = user?.equipped_title_id === title.id;
                      
                      return (
                        <div 
                          key={title.id} 
                          onClick={() => isUnlocked && !isEquipped && handleEquip(title.id)}
                          className={`p-4 rounded-2xl border transition-all cursor-pointer flex items-center justify-between group ${
                            isUnlocked 
                              ? isEquipped ? 'bg-blue-50 border-blue-100 ring-2 ring-blue-500/20' : 'bg-white border-gray-100 hover:border-blue-200 hover:shadow-md'
                              : 'bg-gray-50 border-transparent opacity-40 grayscale cursor-not-allowed'
                          }`}
                        >
                          <div className="flex flex-col gap-1">
                            <TitleBadge title={title} />
                            <p className="text-[9px] font-medium text-gray-400 max-w-[150px] leading-tight">
                              {title.description}
                            </p>
                          </div>
                          {isUnlocked && !isEquipped && (
                            <span className="text-[9px] font-black text-blue-500 opacity-0 group-hover:opacity-100 uppercase tracking-widest">장착하기</span>
                          )}
                          {isEquipped && (
                            <div className="w-2 h-2 bg-blue-500 rounded-full" />
                          )}
                        </div>
                      );
                    })
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
