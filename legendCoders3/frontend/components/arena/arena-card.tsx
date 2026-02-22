'use client';

import { Swords, User as UserIcon, Clock, Zap, Crown } from 'lucide-react';
import Link from 'next/link';
import { ArenaResponse } from '@/types/arena';

const DIFFICULTIES: Record<string, { color: string, glow: string }> = {
  'BRONZE': { color: 'text-orange-500 border-orange-500/20 bg-orange-500/10', glow: 'shadow-orange-500/10' },
  'SILVER': { color: 'text-slate-400 border-slate-400/20 bg-slate-400/10', glow: 'shadow-slate-400/10' },
  'GOLD': { color: 'text-yellow-500 border-yellow-500/20 bg-yellow-500/10', glow: 'shadow-yellow-500/10' },
  'PLATINUM': { color: 'text-emerald-400 border-emerald-400/20 bg-emerald-400/10', glow: 'shadow-emerald-400/10' },
  'DIAMOND': { color: 'text-blue-500 border-blue-500/20 bg-blue-500/10', glow: 'shadow-blue-500/10' },
  'RANDOM': { color: 'text-purple-500 border-purple-500/20 bg-purple-500/10', glow: 'shadow-purple-500/10' },
};

function formatTime(dateStr: string) {
  try {
    const date = new Date(dateStr);
    const now = new Date();
    const diffInSeconds = Math.floor((now.getTime() - date.getTime()) / 1000);
    
    if (diffInSeconds < 60) return '방금 전';
    if (diffInSeconds < 3600) return `${Math.floor(diffInSeconds / 60)}분 전`;
    if (diffInSeconds < 86400) return `${Math.floor(diffInSeconds / 3600)}시간 전`;
    return `${Math.floor(diffInSeconds / 86400)}일 전`;
  } catch (e) {
    return '방금 전';
  }
}

export default function ArenaCard({ arena }: { arena: ArenaResponse }) {
  const style = DIFFICULTIES[arena.difficulty] || DIFFICULTIES['RANDOM'];
  const hostNickname = arena.host?.nickname || "Unknown Host";
  const isPro = arena.host?.is_pro;

  return (
    <Link 
      href={`/arena/${arena.id}`}
      className={`group relative overflow-hidden rounded-3xl border border-white/5 bg-slate-900/40 backdrop-blur-xl hover:bg-slate-800/60 transition-all duration-500 hover:border-rose-500/30 hover:shadow-2xl ${style.glow} block`}
    >
      <div className="absolute -right-4 -top-4 opacity-[0.03] group-hover:opacity-[0.07] transition-opacity rotate-12 group-hover:rotate-0 duration-700">
        <Swords size={120} />
      </div>
      
      <div className="relative p-6 flex flex-col gap-6">
        <div className="flex justify-between items-center">
          <div className={`px-3 py-1 rounded-full text-[10px] font-black uppercase tracking-widest border ${style.color}`}>
            {arena.difficulty}
          </div>
          <div className="flex items-center gap-1.5 text-[10px] font-bold text-slate-500 uppercase tracking-tighter">
            <Clock size={12} className="text-slate-600" />
            {formatTime(arena.created_at)}
          </div>
        </div>

        <div className="flex items-center justify-between gap-4">
          <div className="flex flex-col items-center gap-2 flex-1">
            <div className={`w-12 h-12 rounded-2xl bg-slate-800 flex items-center justify-center border-2 transition-transform duration-500 group-hover:rotate-3 ${isPro ? 'border-amber-500/50' : 'border-slate-700'}`}>
              {isPro ? <Crown size={20} className="text-amber-400 fill-amber-400" /> : <UserIcon size={20} className="text-slate-400" />}
            </div>
            <span className="text-xs font-black text-white truncate max-w-[80px]">{hostNickname}</span>
          </div>

          <div className="flex flex-col items-center gap-1">
            <span className="text-[10px] font-black text-slate-600 italic uppercase">VS</span>
            <Zap size={14} className="text-rose-500 animate-pulse" />
          </div>

          <div className="flex flex-col items-center gap-2 flex-1 opacity-40 group-hover:opacity-60 transition-opacity">
            <div className="w-12 h-12 rounded-2xl bg-slate-900 border-2 border-dashed border-slate-700 flex items-center justify-center">
              <UserIcon size={20} className="text-slate-600" />
            </div>
            <span className="text-[10px] font-bold text-slate-500 uppercase tracking-widest italic">대기 중</span>
          </div>
        </div>

        <div className="pt-4 border-t border-white/5">
          <div className="flex items-center justify-between">
            <div className="flex flex-col">
              <span className="text-[8px] font-black text-slate-500 uppercase tracking-[0.2em]">Match Type</span>
              <span className="text-[10px] font-bold text-slate-300">공개 대전</span>
            </div>
            <div className="px-4 py-2 bg-rose-600 group-hover:bg-rose-500 text-white rounded-xl text-[10px] font-black uppercase tracking-tighter flex items-center gap-2 transition-colors shadow-lg shadow-rose-950/20">
              아레나 입장 <Swords size={12} />
            </div>
          </div>
        </div>
      </div>
    </Link>
  );
}
