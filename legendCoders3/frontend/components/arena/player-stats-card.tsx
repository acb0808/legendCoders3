'use client';

import React from 'react';
import { User } from '@/types/user';
import { Crown, Zap, ShieldCheck, User as UserIcon } from 'lucide-react';
import TitleBadge from '@/components/title-badge';
import { Card } from '@/components/ui/card';

interface PlayerStatsCardProps {
  user: User | null;
  isHost: boolean;
  isReady: boolean;
  isWinner: boolean;
  isMe: boolean;
}

export const PlayerStatsCard: React.FC<PlayerStatsCardProps> = ({ 
  user, 
  isHost, 
  isReady, 
  isWinner, 
  isMe 
}) => {
  if (!user) {
    return (
      <Card className="p-6 bg-slate-900/20 border-slate-800 border-dashed border-2 flex flex-col items-center justify-center h-48 backdrop-blur-sm">
        <div className="w-12 h-12 rounded-full bg-slate-800 animate-pulse mb-3" />
        <p className="text-slate-500 text-xs font-bold uppercase tracking-widest">도전자 대기 중</p>
      </Card>
    );
  }

  return (
    <Card className={`relative overflow-hidden p-6 transition-all duration-500 backdrop-blur-xl ${
      isReady 
        ? 'bg-emerald-500/10 border-emerald-500/30' 
        : 'bg-slate-900/40 border-white/10'
    } ${isWinner ? 'ring-2 ring-yellow-500 shadow-[0_0_20px_rgba(234,179,8,0.2)]' : ''}`}>
      
      {/* Background Icon Watermark */}
      <div className="absolute -right-4 -bottom-4 opacity-5 rotate-12">
        {isHost ? <Crown size={120} /> : <Zap size={120} />}
      </div>

      <div className="relative z-10 flex flex-col items-center text-center">
        {/* Profile Avatar Placeholder */}
        <div className={`w-16 h-16 rounded-2xl flex items-center justify-center mb-4 border-2 transition-transform duration-500 ${
          isReady ? 'border-emerald-500 rotate-0' : 'border-slate-700 rotate-3'
        }`}>
          {user.is_pro ? (
            <Crown className="text-amber-400 fill-amber-400" size={32} />
          ) : (
            <UserIcon className="text-slate-400" size={32} />
          )}
        </div>

        <div className="space-y-1 mb-4">
          <div className="flex items-center justify-center gap-2">
            <span className="text-white font-black tracking-tight">{user.nickname}</span>
            {isMe && <span className="px-1.5 py-0.5 rounded-md bg-blue-500/20 text-blue-400 text-[8px] font-black uppercase">Me</span>}
          </div>
          <TitleBadge title={user.equipped_title} size="xs" />
        </div>

        <div className="w-full pt-4 border-t border-white/5 flex flex-col gap-2">
          <div className="flex justify-between items-center text-[10px] font-bold uppercase tracking-wider">
            <span className="text-slate-500">역할</span>
            <span className={isHost ? 'text-rose-400' : 'text-blue-400'}>{isHost ? '방장' : '도전자'}</span>
          </div>
          <div className="flex justify-between items-center text-[10px] font-bold uppercase tracking-wider">
            <span className="text-slate-500">상태</span>
            <span className={isReady ? 'text-emerald-400' : 'text-slate-400'}>
              {isReady ? '준비 완료' : '대기 중'}
            </span>
          </div>
        </div>
      </div>

      {/* Winner Overlay */}
      {isWinner && (
        <div className="absolute top-2 right-2">
          <div className="bg-yellow-500 text-slate-950 p-1 rounded-md shadow-lg">
            <ShieldCheck size={16} />
          </div>
        </div>
      )}
    </Card>
  );
};
