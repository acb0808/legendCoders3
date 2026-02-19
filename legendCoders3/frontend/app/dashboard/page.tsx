'use client';

import React, { useEffect, useState } from 'react';
import { useAuth } from '@/components/auth-provider';
import { useRouter } from 'next/navigation';
import api from '@/lib/api';
import { Trophy, Flame, Calendar, CheckCircle2, ArrowRight } from 'lucide-react';
import Link from 'next/link';

interface DashboardData {
  total_solved: int;
  streak_days: int;
  solve_history: string[];
}

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
        <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-100 flex items-center gap-5">
          <div className="w-14 h-14 bg-orange-50 text-orange-600 rounded-2xl flex items-center justify-center">
            <Flame size={28} />
          </div>
          <div>
            <p className="text-sm font-medium text-gray-500 uppercase tracking-wider">연속 해결 (스트릭)</p>
            <p className="text-3xl font-black text-gray-900">{stats?.streak_days || 0}일</p>
          </div>
        </div>

        {/* 랭킹 카드 (임시 링크) */}
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
        {/* 오늘의 문제 바로가기 */}
        <div className="bg-gradient-to-br from-blue-600 to-indigo-700 p-8 rounded-3xl shadow-xl shadow-blue-100 text-white flex flex-col justify-between">
          <div>
            <h2 className="text-2xl font-bold mb-2">오늘의 문제 풀러 가기</h2>
            <p className="text-blue-100 mb-6">AI가 엄선한 오늘의 백준 문제를 풀고 성취감을 느껴보세요!</p>
          </div>
          <Link 
            href="/problems/today"
            className="inline-flex items-center justify-center bg-white text-blue-700 font-bold py-4 px-6 rounded-2xl transition-all hover:bg-blue-50 active:scale-95 text-center"
          >
            문제 확인하기
          </Link>
        </div>

        {/* 해결 기록 목록 (최근 5개) */}
        <div className="bg-white p-8 rounded-3xl shadow-sm border border-gray-100">
          <div className="flex items-center gap-2 mb-6">
            <Calendar className="text-gray-400" size={20} />
            <h2 className="text-xl font-bold text-gray-900">최근 해결 기록</h2>
          </div>
          <div className="space-y-4">
            {stats?.solve_history && stats.solve_history.length > 0 ? (
              stats.solve_history.slice(0, 5).map((date: string, idx: number) => (
                <div key={idx} className="flex items-center justify-between p-4 bg-gray-50 rounded-2xl border border-gray-100">
                  <span className="font-medium text-gray-700">{date}</span>
                  <span className="text-green-600 font-bold text-sm bg-green-50 px-3 py-1 rounded-full">성공</span>
                </div>
              ))
            ) : (
              <div className="text-center py-10 text-gray-400 italic">
                아직 해결한 문제가 없습니다.
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
