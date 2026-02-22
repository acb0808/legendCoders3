'use client';

import React from 'react';
import { Button } from '@/components/ui/button';
import { ArenaResponse } from '@/types/arena';
import { User } from '@/types/user';

interface ReadyViewProps {
  arena: ArenaResponse;
  currentUser: User;
  countdown: number | null;
  onLeave: () => void;
  onReadyToggle: () => void;
}

export const ReadyView: React.FC<ReadyViewProps> = ({ 
  arena, 
  currentUser, 
  countdown, 
  onLeave, 
  onReadyToggle 
}) => {
  const isCurrentUserHost = currentUser.id === arena.host_id;
  const isCurrentUserGuest = currentUser.id === arena.guest_id;
  const currentUserReady = isCurrentUserHost ? arena.host_ready : arena.guest_ready;

  return (
    <div className="flex flex-col items-center justify-center h-full p-12 text-center">
      {countdown !== null && countdown > 0 ? (
        <div className="space-y-8 animate-in zoom-in duration-300">
          <div className="relative">
            <div className="text-[12rem] font-black text-white leading-none tracking-tighter drop-shadow-[0_0_30px_rgba(244,63,94,0.3)]">
              {countdown}
            </div>
            <div className="absolute inset-0 bg-rose-500/20 blur-[100px] -z-10 rounded-full" />
          </div>
          <p className="text-xl font-black text-rose-500 uppercase tracking-[0.3em] animate-pulse">
            Prepare for Battle
          </p>
        </div>
      ) : (
        <>
          <div className="mb-12 space-y-4">
            <h2 className="text-5xl font-black text-white tracking-tight uppercase italic">
              Ready <span className="text-slate-500">Check</span>
            </h2>
            <p className="text-slate-400 font-medium max-w-md mx-auto">
              상대방이 모두 준비되면 대결이 시작됩니다. <br/>
              행운을 빕니다, 코더여.
            </p>
          </div>

          <div className="flex flex-col items-center gap-6">
            {arena.guest ? (
              <Button
                onClick={onReadyToggle}
                className={`group relative w-64 h-20 text-xl font-black uppercase tracking-tighter rounded-2xl transition-all duration-300 overflow-hidden ${
                  currentUserReady 
                    ? 'bg-orange-500 text-white hover:bg-orange-600' 
                    : 'bg-emerald-500 text-white hover:bg-emerald-600 shadow-[0_0_30px_rgba(16,185,129,0.3)]'
                }`}
              >
                <div className="absolute inset-0 bg-white/10 translate-y-full group-hover:translate-y-0 transition-transform duration-300" />
                <span className="relative flex items-center justify-center gap-3">
                  {currentUserReady ? 'Waiting...' : 'Ready to Start'}
                </span>
              </Button>
            ) : (
              <div className="flex flex-col items-center gap-4 text-slate-500">
                <div className="w-12 h-12 border-4 border-slate-800 border-t-slate-600 rounded-full animate-spin" />
                <p className="font-bold uppercase tracking-widest text-xs">상대방을 기다리는 중...</p>
              </div>
            )}

            <button 
              onClick={onLeave}
              className="text-xs font-bold text-slate-500 hover:text-rose-400 transition-colors uppercase tracking-widest"
            >
              Cancel & Leave Arena
            </button>
          </div>
        </>
      )}
    </div>
  );
};
