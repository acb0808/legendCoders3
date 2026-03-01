'use client';

import React, { useEffect, useState } from 'react';
import api from '@/lib/api';
import { CheckCircle2, XCircle, Trophy, Calendar, Loader2, ArrowLeft } from 'lucide-react';
import Link from 'next/link';
import TitleBadge from '@/components/title-badge';

export default function WeeklyLeaderboardPage() {
  const [leaderboard, setLeaderboard] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const fetchLeaderboard = async () => {
      try {
        const res = await api.get('/stats/weekly/all');
        setLeaderboard(res.data);
      } catch (error) {
        console.error('Failed to fetch weekly leaderboard:', error);
      } finally {
        setIsLoading(false);
      }
    };

    fetchLeaderboard();
  }, []);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <Loader2 className="animate-spin text-blue-600" size={48} />
      </div>
    );
  }

  const dayNames = ["월", "화", "수", "목", "금", "토", "일"];

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
      <div className="mb-8 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Link href="/ranking" className="p-2 hover:bg-gray-100 rounded-full transition-colors">
            <ArrowLeft size={24} />
          </Link>
          <div>
            <h1 className="text-3xl font-black text-gray-900 tracking-tight italic uppercase">Weekly Legend Board</h1>
            <p className="text-gray-500 font-medium">전체 유저의 이번 주 문제 해결 현황</p>
          </div>
        </div>
        <div className="hidden md:flex items-center gap-4 bg-white px-6 py-3 rounded-2xl border border-gray-100 shadow-sm">
          <div className="flex items-center gap-1.5"><div className="w-2.5 h-2.5 bg-green-500 rounded-full" /> <span className="text-[10px] font-black uppercase text-gray-400">Solved</span></div>
          <div className="flex items-center gap-1.5"><div className="w-2.5 h-2.5 bg-rose-500 rounded-full" /> <span className="text-[10px] font-black uppercase text-gray-400">Missed</span></div>
          <div className="flex items-center gap-1.5"><div className="w-2.5 h-2.5 bg-gray-300 rounded-full" /> <span className="text-[10px] font-black uppercase text-gray-400">No Problem</span></div>
        </div>
      </div>

      <div className="bg-white rounded-[2.5rem] border border-gray-100 shadow-xl overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-gray-50/50 border-b border-gray-100">
                <th className="px-8 py-6 text-[10px] font-black text-gray-400 uppercase tracking-widest min-w-[200px]">User</th>
                {dayNames.map((day, idx) => (
                  <th key={idx} className="px-4 py-6 text-center text-[10px] font-black text-gray-400 uppercase tracking-widest">
                    {day}요일
                  </th>
                ))}
                <th className="px-8 py-6 text-right text-[10px] font-black text-gray-400 uppercase tracking-widest">Total</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {leaderboard.map((row) => {
                const solvedCount = row.status.filter((s: any) => s.is_solved).length;
                return (
                  <tr key={row.user_id} className="hover:bg-gray-50/30 transition-colors group">
                    <td className="px-8 py-5">
                      <div className="flex flex-col gap-1">
                        {row.equipped_title && (
                          <div className="scale-75 origin-left -ml-2 mb-[-4px]">
                            <TitleBadge title={row.equipped_title} size="sm" />
                          </div>
                        )}
                        <span className="font-bold text-gray-900 group-hover:text-blue-600 transition-colors">
                          {row.nickname}
                        </span>
                      </div>
                    </td>
                    {row.status.map((day: any, idx: number) => (
                      <td key={idx} className="px-4 py-5 text-center">
                        <div className="flex justify-center">
                          {day.is_solved ? (
                            <div className="w-10 h-10 bg-green-50 text-green-600 rounded-xl flex items-center justify-center shadow-sm border border-green-100">
                              <CheckCircle2 size={20} />
                            </div>
                          ) : !day.has_problem ? (
                            <div className="w-10 h-10 bg-gray-50 text-gray-300 rounded-xl flex items-center justify-center border border-gray-100">
                              <div className="w-1 h-1 bg-gray-300 rounded-full" />
                            </div>
                          ) : (
                            <div className="w-10 h-10 bg-rose-50 text-rose-500 rounded-xl flex items-center justify-center border border-rose-100 opacity-40 group-hover:opacity-100 transition-opacity">
                              <XCircle size={20} />
                            </div>
                          )}
                        </div>
                      </td>
                    ))}
                    <td className="px-8 py-5 text-right">
                      <div className="inline-flex items-center gap-1.5 px-3 py-1 bg-blue-50 text-blue-600 rounded-full text-xs font-black">
                        <Trophy size={12} /> {solvedCount}
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
        {leaderboard.length === 0 && (
          <div className="py-20 text-center text-gray-400 font-bold italic">
            데이터가 존재하지 않습니다.
          </div>
        )}
      </div>
    </div>
  );
}
