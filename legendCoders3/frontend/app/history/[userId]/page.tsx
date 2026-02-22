'use client';

import React, { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import api from '@/lib/api';
import ActivityGraph from '@/components/activity-graph';
import { ChevronLeft } from 'lucide-react';
import Link from 'next/link';

export default function HistoryPage() {
  const params = useParams();
  const userId = params.userId;
  const [activityData, setActivityData] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [year, setYear] = useState(new Date().getFullYear());

  useEffect(() => {
    if (userId) {
      const fetchActivity = async () => {
        setIsLoading(true);
        try {
          const response = await api.get(`/stats/activity/${userId}`);
          setActivityData(response.data);
        } catch (error) {
          console.error('Failed to fetch activity data:', error);
        } finally {
          setIsLoading(false);
        }
      };
      fetchActivity();
    }
  }, [userId]);

  const yearlyData = activityData.filter(d => new Date(d.date).getFullYear() === year);

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
      <div className="mb-8">
        <Link href="/dashboard" className="inline-flex items-center text-blue-600 font-bold hover:underline mb-4">
          <ChevronLeft size={20} />
          대시보드로 돌아가기
        </Link>
        <h1 className="text-3xl font-bold text-gray-900">전체 활동 기록</h1>
      </div>

      {/* 연도 네비게이션 */}
      <div className="flex justify-center items-center gap-4 my-6">
        <button onClick={() => setYear(year - 1)} className="font-bold">&lt;</button>
        <h2 className="text-2xl font-bold">{year}년</h2>
        <button onClick={() => setYear(year + 1)} className="font-bold" disabled={year >= new Date().getFullYear()}>&gt;</button>
      </div>

      {isLoading ? (
        <p>로딩 중...</p>
      ) : (
        <ActivityGraph data={yearlyData} months={12} />
      )}
    </div>
  );
}
