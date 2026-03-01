'use client';

import React, { useEffect, useState } from 'react';
import { useAuth } from '@/components/auth-provider';
import { useRouter } from 'next/navigation';
import api from '@/lib/api';
import { Trophy, Medal, Flame, Hash, User, Calendar, ArrowRight } from 'lucide-react';
import TitleBadge from '@/components/title-badge';
import Link from 'next/link';

interface RankingUser {
  user_id: string;
  nickname: string;
  solved_count: number;
  consecutive_days: number;
  equipped_title?: {
    name: string;
    color_code: string;
    has_glow?: boolean;
    animation_type?: string | null;
    icon?: string | null;
  } | null;
}

export default function RankingPage() {
  const { user, loading } = useAuth();
  const router = useRouter();
  const [rankings, setRankings] = useState<RankingUser[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    if (!loading && !user) {
      router.push('/login');
    }
  }, [user, loading, router]);

  useEffect(() => {
    const fetchRankings = async () => {
      try {
        const response = await api.get('/stats/ranking?limit=50');
        setRankings(response.data);
      } catch (error) {
        console.error('Failed to fetch rankings:', error);
      } finally {
        setIsLoading(false);
      }
    };

    if (user) {
      fetchRankings();
    }
  }, [user]);

  const getRankIcon = (index: number) => {
    switch (index) {
      case 0: return <Trophy className="text-yellow-500" size={24} />;
      case 1: return <Medal className="text-gray-400" size={24} />;
      case 2: return <Medal className="text-amber-600" size={24} />;
      default: return <span className="text-gray-400 font-bold ml-1">{index + 1}</span>;
    }
  };

  if (loading || isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="animate-pulse text-blue-600 font-bold">랭킹 집계 중...</div>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
      <div className="flex flex-col md:flex-row items-center justify-between gap-6 mb-12 bg-white p-8 rounded-[2.5rem] border border-gray-100 shadow-sm">
        <div className="flex items-center gap-5">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-yellow-50 text-yellow-600 rounded-2xl shadow-inner">
            <Trophy size={32} />
          </div>
          <div>
            <h1 className="text-3xl font-black text-gray-900 tracking-tight italic uppercase">Legend Board</h1>
            <p className="text-gray-500 font-medium">레전드 코더 명예의 전당</p>
          </div>
        </div>
        
        <Link 
          href="/ranking/weekly"
          className="inline-flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white px-6 py-3 rounded-2xl font-black uppercase text-[10px] tracking-widest transition-all active:scale-95 shadow-xl shadow-blue-100"
        >
          <Calendar size={16} /> 주간 현황판 보기 <ArrowRight size={16} />
        </Link>
      </div>

      <div className="bg-white rounded-3xl shadow-sm border border-gray-100 overflow-hidden">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="bg-gray-50/50">
              <th className="px-6 py-5 text-xs font-bold text-gray-400 uppercase tracking-widest text-center w-20">Rank</th>
              <th className="px-6 py-5 text-xs font-bold text-gray-400 uppercase tracking-widest ml-4">User</th>
              <th className="px-6 py-5 text-xs font-bold text-gray-400 uppercase tracking-widest text-right">Solved</th>
              <th className="px-6 py-5 text-xs font-bold text-gray-400 uppercase tracking-widest text-right">Streak</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-50">
            {rankings.map((rk, idx) => {
              const isMe = rk.user_id === user?.id;
              return (
                <tr 
                  key={rk.user_id} 
                  className={isMe ? "bg-blue-50/30" : "hover:bg-gray-50/50 transition-colors"}
                >
                  <td className="px-6 py-5 text-center">
                    <div className="flex justify-center">
                      {getRankIcon(idx)}
                    </div>
                  </td>
                  <td className="px-6 py-5">
                    <div className="flex items-center gap-3">
                      <div className={`w-10 h-10 rounded-full flex items-center justify-center font-bold ${isMe ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-500'}`}>
                        {rk.nickname.charAt(0).toUpperCase()}
                      </div>
                      <div>
                        <div className="flex items-center gap-1.5 mb-0.5">
                          <TitleBadge title={rk.equipped_title} size="xs" />
                          <p className={`font-bold ${isMe ? 'text-blue-700' : 'text-gray-900'}`}>
                            {rk.nickname}
                          </p>
                          {isMe && <span className="text-[8px] font-black bg-blue-100 text-blue-600 px-1 py-0.5 rounded uppercase">Me</span>}
                        </div>
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-5 text-right">
                    <span className="font-black text-gray-900">{rk.solved_count}</span>
                  </td>
                  <td className="px-6 py-5 text-right">
                    <div className="flex items-center justify-end gap-1.5">
                      <span className={`font-bold ${rk.consecutive_days > 0 ? 'text-orange-600' : 'text-gray-400'}`}>
                        {rk.consecutive_days}
                      </span>
                      <Flame size={16} className={rk.consecutive_days > 0 ? 'text-orange-500' : 'text-gray-300'} />
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
        
        {rankings.length === 0 && (
          <div className="text-center py-20 text-gray-400 italic bg-white">
            아직 랭킹 정보가 없습니다. 첫 번째 주인공이 되어보세요!
          </div>
        )}
      </div>
    </div>
  );
}
