'use client';

import React from 'react';
import { Button } from '@/components/ui/button';
import { ArenaResponse } from '@/types/arena';
import { User } from '@/types/user';
import { ProblemDisplay } from '@/components/problem-display'; 
import { Loader2, CheckCircle2 } from 'lucide-react';
import { arenaApi } from '@/lib/api';
import { toast } from 'sonner';

interface GameViewProps {
  arena: ArenaResponse;
  currentUser: User;
  problemId: number;
  onSurrender: () => void;
  onProposeDraw: () => void;
  onProposeSkip: () => void;
}

export const GameView: React.FC<GameViewProps> = ({ 
  arena, 
  currentUser, 
  problemId,
  onSurrender,
  onProposeDraw,
  onProposeSkip
}) => {
  const [isChecking, setIsChecking] = React.useState(false);

  const handleVerifySubmission = async () => {
    setIsChecking(true);
    try {
      console.log("[Arena] Verifying submission for problem:", problemId);
      const res = await arenaApi.checkSubmission(arena.id);
      if (res.success) {
        toast.success(res.message);
      } else {
        toast.error(res.message);
      }
    } catch (err: any) {
      console.error("[Arena] Submission check failed:", err);
      toast.error(err.response?.data?.detail || "제출 확인 중 오류가 발생했습니다.");
    } finally {
      setIsChecking(false);
    }
  };

  const isHost = currentUser.id === arena.host_id;
  const myDrawAgreed = isHost ? arena.host_draw_agreed : arena.guest_draw_agreed;
  const opponentDrawAgreed = isHost ? arena.guest_draw_agreed : arena.host_draw_agreed;
  
  const mySkipAgreed = isHost ? arena.host_skip_agreed : arena.guest_skip_agreed;
  const opponentSkipAgreed = isHost ? arena.guest_skip_agreed : arena.host_skip_agreed;

  return (
    <div className="flex flex-col h-full bg-[#020617]">
      {/* Problem Area */}
      <div className="flex-grow overflow-auto p-8 custom-scrollbar">
        {problemId ? (
          <div className="max-w-4xl mx-auto animate-in fade-in slide-in-from-bottom-4 duration-700">
            <ProblemDisplay baekjoonProblemId={problemId} arenaId={arena.id} />
            
            {/* Direct Verification CTA */}
            <div className="mt-8 flex justify-center">
              <Button 
                onClick={handleVerifySubmission}
                disabled={isChecking}
                className="group h-20 px-12 bg-emerald-600 hover:bg-emerald-500 text-white rounded-2xl font-black uppercase tracking-tighter text-xl shadow-[0_0_30px_rgba(16,185,129,0.2)] transition-all active:scale-95 overflow-hidden relative"
              >
                <div className="absolute inset-0 bg-white/10 -translate-x-full group-hover:translate-x-0 transition-transform duration-500" />
                <span className="relative flex items-center gap-3">
                  {isChecking ? <Loader2 className="animate-spin" /> : <CheckCircle2 />}
                  {isChecking ? 'Verifying...' : 'Submit & Verify Result'}
                </span>
              </Button>
            </div>
          </div>
        ) : (
          <div className="h-full flex items-center justify-center">
            <Loader2 className="animate-spin text-rose-500" size={40} />
          </div>
        )}
      </div>

      {/* Sleek Action Bar */}
      <div className="p-6 bg-slate-950/80 backdrop-blur-2xl border-t border-white/5 flex items-center justify-between gap-6">
        <div className="flex gap-3">
          <Button
            onClick={onProposeDraw}
            variant="outline"
            disabled={myDrawAgreed}
            className={`px-6 py-6 rounded-2xl font-black uppercase tracking-tighter transition-all ${
              opponentDrawAgreed 
                ? 'bg-amber-500 border-amber-400 text-slate-950 hover:bg-amber-400 animate-pulse' 
                : myDrawAgreed 
                ? 'bg-slate-800 border-white/10 text-slate-500 cursor-not-allowed'
                : 'border-white/10 text-slate-400 hover:bg-white/5 hover:text-white'
            }`}
          >
            {opponentDrawAgreed ? 'Accept Draw' : myDrawAgreed ? 'Draw Proposed' : 'Draw'}
          </Button>
          <Button
            onClick={onProposeSkip}
            variant="outline"
            disabled={mySkipAgreed}
            className={`px-6 py-6 rounded-2xl font-black uppercase tracking-tighter transition-all ${
              opponentSkipAgreed 
                ? 'bg-blue-500 border-blue-400 text-white hover:bg-blue-400 animate-pulse' 
                : mySkipAgreed
                ? 'bg-slate-800 border-white/10 text-slate-500 cursor-not-allowed'
                : 'border-white/10 text-slate-400 hover:bg-white/5 hover:text-white'
            }`}
          >
            {opponentSkipAgreed ? 'Accept Skip' : mySkipAgreed ? 'Skip Proposed' : 'Skip'}
          </Button>
        </div>

        <div className="flex-grow flex justify-center px-12">
          {(myDrawAgreed || opponentDrawAgreed || mySkipAgreed || opponentSkipAgreed) && (
            <div className="px-6 py-3 rounded-full bg-rose-500/10 border border-rose-500/20 text-rose-400 text-[10px] font-black uppercase tracking-[0.2em] animate-pulse">
              {myDrawAgreed || opponentDrawAgreed ? 'Draw Vote Active' : 'Skip Vote Active'} - Waiting for response
            </div>
          )}
        </div>

        <Button
          onClick={onSurrender}
          className="px-8 py-6 bg-rose-600 hover:bg-rose-500 text-white rounded-2xl font-black uppercase tracking-widest shadow-[0_0_20px_rgba(225,29,72,0.2)] transition-all active:scale-95"
        >
          Surrender
        </Button>
      </div>
    </div>
  );
};
