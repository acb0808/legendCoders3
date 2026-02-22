'use client';

import React, { useEffect, useState } from 'react';
import { useAuth } from '@/components/auth-provider';
import { useRouter } from 'next/navigation';
import api from '@/lib/api';
import { Trophy, Flame, Calendar, CheckCircle2, ArrowRight, Crown, RefreshCw, Snowflake, Swords } from 'lucide-react';
import Link from 'next/link';

export default function DashboardPage() {
  const { user, loading } = useAuth();
  const router = useRouter();
  const [stats, setStats] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    if (!loading && !user) {
      router.push('/login');
    }
  }, [user, loading, router]);

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const response = await api.get('/stats/me');
        setStats(response.data);
      } catch (error) {
        console.error('Failed to fetch stats:', error);
      } finally {
        setIsLoading(false);
      }
    };

    if (user) {
      fetchStats();
    }
  }, [user]);

  if (loading || isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="animate-pulse text-blue-600 font-bold">로딩 중...</div>
      </div>
    );
  }

  if (!user) return null;

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
      {/* Legend Pro 전용 프리미엄 배너 */}
      {user.is_pro && (
        <div className="mb-8 p-6 bg-gradient-to-r from-amber-500 via-yellow-400 to-amber-500 rounded-3xl shadow-xl shadow-amber-200/40 flex items-center justify-between border border-white/20 relative overflow-hidden group">
          <div className="flex items-center gap-5 relative z-10">
            <div className="w-16 h-16 bg-white/20 rounded-[1.5rem] flex items-center justify-center backdrop-blur-md border border-white/30 shadow-inner">
              <Crown className="text-white fill-white" size={36} />
            </div>
            <div>
              <div className="flex items-center gap-2 mb-1">
                <h2 className="text-2xl font-black uppercase italic tracking-tighter text-white">Legend Pro Member</h2>
                <div className="px-2 py-0.5 bg-white/20 rounded-md text-[10px] font-black text-white border border-white/20 uppercase">Premium</div>
              </div>
              <p className="text-white/90 font-bold text-sm">모든 자동 동기화 기능과 {user.streak_freeze_count}개의 스트릭 보호권이 활성화되어 있습니다.</p>
            </div>
          </div>
          <div className="hidden lg:block relative z-10">
            <div className="px-6 py-2 bg-black/10 rounded-2xl border border-white/10 backdrop-blur-sm text-white text-xs font-black uppercase tracking-widest">
              Elite Status
            </div>
          </div>
          <Crown className="absolute -right-8 -bottom-8 text-white/10 size-48 rotate-12 group-hover:rotate-6 transition-transform duration-700" />
        </div>
      )}

      <div className="mb-10">
        <h1 className="text-3xl font-bold text-gray-900">안녕하세요, {user.nickname}님! 👋</h1>
        <p className="text-gray-500 mt-2">오늘도 당신의 성장을 응원합니다.</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-10">
        {/* 해결한 문제 수 카드 */}
        <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-100 flex items-center gap-5">
          <div className="w-14 h-14 bg-blue-50 text-blue-600 rounded-2xl flex items-center justify-center">
            <CheckCircle2 size={28} />
          </div>
          <div>
            <p className="text-sm font-medium text-gray-500 uppercase tracking-wider">해결한 문제</p>
            <p className="text-3xl font-black text-gray-900">{stats?.total_solved || 0}</p>
          </div>
        </div>

        {/* 현재 스트릭 카드 */}
        <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-100 flex items-center gap-5 relative overflow-hidden">
          <div className="w-14 h-14 bg-orange-50 text-orange-600 rounded-2xl flex items-center justify-center">
            <Flame size={28} />
          </div>
          <div className="relative z-10">
            <div className="flex items-center gap-2 mb-0.5">
              <p className="text-sm font-medium text-gray-500 uppercase tracking-wider">연속 해결 (스트릭)</p>
              {user.is_pro && (
                <div className="flex items-center gap-1 text-[10px] font-black text-blue-500 bg-blue-50 px-1.5 py-0.5 rounded-full border border-blue-100 shadow-sm">
                  <Snowflake size={10} className="text-blue-400" /> FREEZE {user.streak_freeze_count}
                </div>
              )}
            </div>
            <p className="text-3xl font-black text-gray-900">{stats?.streak_days || 0}일</p>
          </div>
          {user.is_pro && <div className="absolute -right-2 -bottom-2 text-blue-500/5 rotate-12"><Snowflake size={80} /></div>}
        </div>

        {/* 랭킹 카드 */}
        <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-100 flex items-center gap-5">
          <div className="w-14 h-14 bg-yellow-50 text-yellow-600 rounded-2xl flex items-center justify-center">
            <Trophy size={28} />
          </div>
          <div>
            <p className="text-sm font-medium text-gray-500 uppercase tracking-wider">나의 순위</p>
            <Link href="/ranking" className="inline-flex items-center text-blue-600 font-bold hover:underline gap-1">
              전체 랭킹 확인 <ArrowRight size={16} />
            </Link>
          </div>
        </div>
      </div>

    <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <div className="bg-gray-900 p-8 rounded-[2.5rem] text-white relative overflow-hidden group border-2 border-rose-500/20">
          <div className="relative z-10">
            <h2 className="text-2xl font-black uppercase italic mb-2 text-rose-500">Battle Arena</h2>
            <p className="text-gray-400 font-medium mb-8">실시간으로 라이벌과 알고리즘 대결을 펼쳐보세요.</p>
            <Link 
              href="/arena"
              className="inline-flex items-center gap-2 bg-rose-600 hover:bg-rose-700 text-white px-6 py-3 rounded-2xl font-bold transition-all shadow-xl shadow-rose-500/20 active:scale-95"
            >
              경쟁전 입장하기 <Swords size={18} />
            </Link>
          </div>
          <Swords size={180} className="absolute -right-12 -bottom-12 text-rose-500/10 rotate-12 group-hover:scale-110 group-hover:rotate-6 transition-transform duration-500" />
        </div>

        <div className="bg-blue-600 p-8 rounded-[2.5rem] text-white relative overflow-hidden group">
          <div className="relative z-10">
            <h2 className="text-2xl font-black uppercase italic mb-2">Today's Problem</h2>
            <p className="text-blue-100 font-medium mb-8">매일 새로운 알고리즘으로 성장의 즐거움을 느껴보세요.</p>
            <Link 
              href="/problems/today"
              className="inline-flex items-center gap-2 bg-white text-blue-600 px-6 py-3 rounded-2xl font-bold transition-all shadow-xl shadow-white/10 active:scale-95 hover:bg-blue-50"
            >
              오늘의 문제 풀기 <ArrowRight size={18} />
            </Link>
          </div>
          <Calendar size={180} className="absolute -right-12 -bottom-12 text-white/10 rotate-12 group-hover:scale-110 group-hover:rotate-6 transition-transform duration-500" />
        </div>

        {/* 활동 통계 섹션 */}
        <div className="bg-white p-8 rounded-[2.5rem] border border-gray-100 shadow-sm flex flex-col justify-center text-center">
          <div className="w-20 h-20 bg-gray-50 rounded-3xl flex items-center justify-center mx-auto mb-6">
            <RefreshCw className="text-gray-300" size={32} />
          </div>
          <h3 className="text-xl font-bold text-gray-900 mb-2">활동 그래프 준비 중</h3>
          <p className="text-gray-500 font-medium">더 나은 분석을 위해 데이터를 수집하고 있습니다.</p>
        </div>
      </div>
    </div>
  );
}
