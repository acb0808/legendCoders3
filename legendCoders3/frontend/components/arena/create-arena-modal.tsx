'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { arenaApi } from '@/lib/api';
import { toast } from 'sonner';
import { Swords, Lock, Globe, Zap, Shield, Crown, Star } from 'lucide-react';

interface CreateArenaModalProps {
  isOpen: boolean;
  onClose: () => void;
}

const DIFFICULTIES = [
  { id: 'BRONZE', label: 'Bronze', color: 'text-orange-500', bg: 'bg-orange-500/10', border: 'border-orange-500/50', icon: Shield },
  { id: 'SILVER', label: 'Silver', color: 'text-slate-400', bg: 'bg-slate-400/10', border: 'border-slate-400/50', icon: Shield },
  { id: 'GOLD', label: 'Gold', color: 'text-yellow-500', bg: 'bg-yellow-500/10', border: 'border-yellow-500/50', icon: Star },
  { id: 'PLATINUM', label: 'Platinum', color: 'text-cyan-500', bg: 'bg-cyan-500/10', border: 'border-cyan-500/50', icon: Zap },
  { id: 'DIAMOND', label: 'Diamond', color: 'text-blue-500', bg: 'bg-blue-500/10', border: 'border-blue-500/50', icon: Crown },
  { id: 'RANDOM', label: 'Random', color: 'text-purple-500', bg: 'bg-purple-500/10', border: 'border-purple-500/50', icon: Swords },
];

export default function CreateArenaModal({ isOpen, onClose }: CreateArenaModalProps) {
  const router = useRouter();
  const [difficulty, setDifficulty] = useState('SILVER');
  const [mode, setMode] = useState('OPEN');
  const [loading, setLoading] = useState(false);

  const handleCreate = async () => {
    setLoading(true);
    try {
      const arena = await arenaApi.createArena(difficulty, mode);
      toast.success('아레나가 생성되었습니다!');
      router.push(`/arena/${arena.id}`);
    } catch (error) {
      toast.error('아레나 생성 실패');
    } finally {
      setLoading(false);
      onClose();
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="bg-[#0f172a] border-slate-800 text-white sm:max-w-[600px] p-0 overflow-hidden gap-0">
        <div className="absolute inset-0 bg-gradient-to-br from-indigo-500/10 via-transparent to-rose-500/5 pointer-events-none" />
        
        <DialogHeader className="p-6 pb-4 relative z-10">
          <DialogTitle className="text-2xl font-black uppercase tracking-tight flex items-center gap-2">
            <Swords className="text-rose-500" /> 아레나 생성
          </DialogTitle>
        </DialogHeader>

        <div className="p-6 pt-0 space-y-8 relative z-10">
          {/* Difficulty Section */}
          <div className="space-y-3">
            <label className="text-xs font-bold text-slate-500 uppercase tracking-widest">난이도 선택</label>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
              {DIFFICULTIES.map((diff) => {
                const Icon = diff.icon;
                const isSelected = difficulty === diff.id;
                return (
                  <button
                    key={diff.id}
                    onClick={() => setDifficulty(diff.id)}
                    className={`relative p-4 rounded-xl border flex flex-col items-center justify-center gap-2 transition-all duration-300 group ${
                      isSelected 
                        ? `${diff.bg} ${diff.border} ring-1 ring-offset-0` 
                        : 'bg-slate-900/50 border-slate-800 hover:bg-slate-800 hover:border-slate-600'
                    }`}
                  >
                    <Icon 
                      size={24} 
                      className={`transition-colors duration-300 ${isSelected ? diff.color : 'text-slate-600 group-hover:text-slate-400'}`} 
                    />
                    <div className={`font-bold text-sm tracking-wide ${isSelected ? 'text-white' : 'text-slate-500 group-hover:text-slate-300'}`}>
                      {diff.label}
                    </div>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Mode Section */}
          <div className="space-y-3">
            <label className="text-xs font-bold text-slate-500 uppercase tracking-widest">공개 설정</label>
            <div className="grid grid-cols-2 gap-3">
              <button
                onClick={() => setMode('OPEN')}
                className={`p-4 rounded-xl border flex items-center justify-center gap-3 transition-all h-16 ${
                  mode === 'OPEN' 
                    ? 'bg-blue-500/10 border-blue-500/50 text-blue-400' 
                    : 'bg-slate-900/50 border-slate-800 text-slate-500 hover:bg-slate-800'
                }`}
              >
                <Globe size={20} />
                <span className="text-sm font-bold">공개 대전</span>
              </button>
              <button
                onClick={() => setMode('PRIVATE')}
                className={`p-4 rounded-xl border flex items-center justify-center gap-3 transition-all h-16 ${
                  mode === 'PRIVATE' 
                    ? 'bg-amber-500/10 border-amber-500/50 text-amber-400' 
                    : 'bg-slate-900/50 border-slate-800 text-slate-500 hover:bg-slate-800'
                }`}
              >
                <Lock size={20} />
                <span className="text-sm font-bold">비공개 대전</span>
              </button>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="p-6 pt-0 flex justify-end gap-3 relative z-10">
          <Button variant="ghost" onClick={onClose} className="text-slate-400 hover:text-white hover:bg-white/5">
            취소
          </Button>
          <Button 
            onClick={handleCreate} 
            disabled={loading}
            className="bg-rose-600 hover:bg-rose-500 text-white font-bold px-8 shadow-lg shadow-rose-900/20"
          >
            {loading ? '생성 중...' : '아레나 생성'}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
