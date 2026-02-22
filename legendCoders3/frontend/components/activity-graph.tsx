'use client';

import React from 'react';
import { CheckCircle, Snowflake } from 'lucide-react';
import Link from 'next/link';
import { Tooltip as ReactTooltip } from 'react-tooltip';

interface Activity {
  date: string; // "YYYY-MM-DD"
  type: 'SOLVED' | 'FROZEN' | 'NONE';
  solved_count: number;
}

interface ActivityGraphProps {
  data: Activity[];
  months?: number;
  userId?: string;
}

const ActivityGraph: React.FC<ActivityGraphProps> = ({ data, months = 3, userId }) => {
  if (!data) return null;

  // 타임존 영향을 받지 않게 날짜 객체 생성 (KST 기준 YYYY-MM-DD를 로컬 YYYY-MM-DD로 매핑)
  const parseISODate = (dateStr: string) => {
    const [y, m, d] = dateStr.split('-').map(Number);
    return new Date(y, m - 1, d).toDateString();
  };

  const today = new Date();
  today.setHours(0, 0, 0, 0);

  const startDate = new Date();
  startDate.setMonth(today.getMonth() - months);
  startDate.setHours(0, 0, 0, 0);
  startDate.setDate(startDate.getDate() + 1);

  // 백엔드 데이터를 맵에 저장 (날짜 문자열 기준)
  const activityMap = new Map(data.map(d => [parseISODate(d.date), d]));

  // 시작일부터 오늘까지의 모든 날짜 생성 (정확한 일수 계산)
  const diffTime = Math.abs(today.getTime() - startDate.getTime());
  const totalDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24)) + 1; // 오늘 포함

  const days = Array.from({ length: totalDays }, (_, i) => {
    const d = new Date(startDate);
    d.setDate(d.getDate() + i);
    const dateStr = d.toDateString();
    const activity = activityMap.get(dateStr);
    
    return { 
      date: d, 
      type: activity?.type || 'NONE',
      count: activity?.solved_count || 0
    };
  });

  const totalSolved = data.reduce((sum, day) => sum + (day.type === 'SOLVED' ? day.solved_count : 0), 0);
  const activeDays = data.filter(d => d.type === 'SOLVED').length;
  const frozenDays = data.filter(d => d.type === 'FROZEN').length;

  const getCellColor = (type: string) => {
    switch (type) {
      case 'SOLVED': return 'bg-green-500';
      case 'FROZEN': return 'bg-sky-400';
      default: return 'bg-gray-700/50';
    }
  };

  const getTooltipText = (type: string, count: number) => {
    switch(type) {
      case 'SOLVED': return `${count}문제 해결`;
      case 'FROZEN': return '스트릭 프리즈 사용';
      default: return '활동 없음';
    }
  }

  return (
    <div className="bg-gray-900/95 backdrop-blur-sm p-6 rounded-3xl border border-white/10 shadow-lg lg:col-span-2 overflow-hidden">
      <div className="flex justify-between items-start mb-6">
        <div>
          <h3 className="text-xl font-bold text-white flex items-center gap-2">
            최근 {months}개월 활동
            <span className="text-[10px] bg-white/10 text-gray-400 px-2 py-0.5 rounded-full font-medium uppercase tracking-widest">KST 기준</span>
          </h3>
          {userId && (
            <Link href={`/history/${userId}`} className="text-xs font-bold text-cyan-400 hover:text-cyan-300 transition-colors">
              전체 기록 상세 보기 &rarr;
            </Link>
          )}
        </div>
        <div className="text-right">
          <p className="text-3xl font-black text-white leading-none">{totalSolved}</p>
          <p className="text-[10px] font-bold text-cyan-400 uppercase tracking-widest mt-1">Total Solved</p>
        </div>
      </div>
      
      {/* 활동 그리드: 최신 날짜가 오른쪽 끝에 오도록 reverse 처리 */}
      <div className="flex flex-wrap gap-1.5" style={{ direction: 'ltr' }}>
        {days.map(({ date, type, count }) => (
          <div 
            key={date.toDateString()} 
            className={`w-3 h-3 md:w-3.5 md:h-3.5 rounded-[2px] transition-all duration-200 hover:scale-150 hover:z-10 cursor-help ${getCellColor(type)}`}
            data-tooltip-id="activity-tooltip"
            data-tooltip-html={`<div class="text-center font-sans"><strong>${date.toLocaleDateString('ko-KR', { month: 'long', day: 'numeric', weekday: 'short' })}</strong><br/><span class="text-xs">${getTooltipText(type, count)}</span></div>`}
          >
          </div>
        ))}
      </div>
      <ReactTooltip 
        id="activity-tooltip" 
        style={{ backgroundColor: '#0f172a', borderRadius: '12px', fontSize: '12px', fontWeight: 'bold', padding: '8px 12px', border: '1px solid rgba(255,255,255,0.1)' }}
      />

      <div className="grid grid-cols-2 gap-4 mt-8">
        <div className="bg-black/30 p-4 rounded-2xl flex items-center gap-4 border border-white/5">
          <div className="w-10 h-10 bg-green-500/20 text-green-500 rounded-xl flex items-center justify-center">
            <CheckCircle size={20} />
          </div>
          <div>
            <p className="text-xl font-black text-white">{activeDays}일</p>
            <p className="text-[10px] font-bold text-gray-500 uppercase tracking-widest">Active Days</p>
          </div>
        </div>
        <div className="bg-black/30 p-4 rounded-2xl flex items-center gap-4 border border-white/5">
          <div className="w-10 h-10 bg-sky-500/20 text-sky-400 rounded-xl flex items-center justify-center">
            <Snowflake size={20} />
          </div>
          <div>
            <p className="text-xl font-black text-white">{frozenDays}일</p>
            <p className="text-[10px] font-bold text-gray-500 uppercase tracking-widest">Freezes Used</p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ActivityGraph;
