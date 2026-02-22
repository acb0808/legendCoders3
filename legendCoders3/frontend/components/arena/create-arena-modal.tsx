// frontend/components/arena/create-arena-modal.tsx
'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { arenaApi } from '@/lib/api';
import { Trophy, Swords, X } from 'lucide-react';

interface CreateArenaModalProps {
  onClose: () => void;
}

const DIFFICULTIES = [
  { id: 'BRONZE', label: 'Bronze', color: 'bg-orange-900/50 border-orange-700 text-orange-200' },
  { id: 'SILVER', label: 'Silver', color: 'bg-slate-400/30 border-slate-400 text-slate-100' },
  { id: 'GOLD', label: 'Gold', color: 'bg-yellow-600/30 border-yellow-500 text-yellow-200' },
  { id: 'PLATINUM', label: 'Platinum', color: 'bg-cyan-600/30 border-cyan-400 text-cyan-200' },
  { id: 'DIAMOND', label: 'Diamond', color: 'bg-blue-600/30 border-blue-400 text-blue-200' },
  { id: 'RANDOM', label: 'Random', color: 'bg-purple-600/30 border-purple-400 text-purple-200' },
];

export default function CreateArenaModal({ onClose }: CreateArenaModalProps) {
  const router = useRouter();
  const [selectedDifficulty, setSelectedDifficulty] = useState('GOLD');
  const [loading, setLoading] = useState(false);

  const handleCreate = async () => {
    try {
      setLoading(true);
      const data = await arenaApi.createArena(selectedDifficulty, "OPEN");
      router.push(`/arena/${data.id}`);
    } catch (error) {
      console.error("Failed to create arena:", error);
      alert("Failed to create arena. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
      <div className="w-full max-w-md bg-slate-900 border border-slate-700 rounded-2xl shadow-2xl overflow-hidden animate-in zoom-in-95 duration-200">
        
        {/* Header */}
        <div className="relative p-6 border-b border-slate-800 bg-gradient-to-r from-slate-900 to-slate-800">
          <button 
            onClick={onClose}
            className="absolute top-4 right-4 text-slate-400 hover:text-white transition-colors"
          >
            <X size={20} />
          </button>
          <div className="flex items-center gap-3">
            <div className="p-2 bg-rose-500/20 rounded-lg">
              <Swords className="w-6 h-6 text-rose-500" />
            </div>
            <div>
              <h2 className="text-xl font-bold text-white">Create Arena</h2>
              <p className="text-sm text-slate-400">Choose your battle difficulty</p>
            </div>
          </div>
        </div>

        {/* Body */}
        <div className="p-6 space-y-6">
          <div className="grid grid-cols-2 gap-3">
            {DIFFICULTIES.map((diff) => (
              <button
                key={diff.id}
                onClick={() => setSelectedDifficulty(diff.id)}
                className={`
                  relative p-4 rounded-xl border-2 transition-all duration-200
                  flex flex-col items-center justify-center gap-2 group
                  ${selectedDifficulty === diff.id 
                    ? diff.color + ' shadow-[0_0_20px_-5px_currentColor]' 
                    : 'bg-slate-800/50 border-slate-700 hover:border-slate-500 text-slate-400'}
                `}
              >
                <span className="font-bold tracking-wide">{diff.label}</span>
                {selectedDifficulty === diff.id && (
                  <div className="absolute inset-0 bg-white/5 animate-pulse rounded-xl" />
                )}
              </button>
            ))}
          </div>

          <div className="bg-slate-800/50 p-4 rounded-lg border border-slate-700">
            <h3 className="text-sm font-semibold text-slate-300 mb-2 flex items-center gap-2">
              <Trophy size={14} className="text-yellow-500" />
              Match Rules
            </h3>
            <ul className="text-xs text-slate-400 space-y-1 list-disc list-inside">
              <li>1vs1 Real-time Battle</li>
              <li>First to solve wins instantly</li>
              <li>Both players must not have solved the problem before</li>
            </ul>
          </div>
        </div>

        {/* Footer */}
        <div className="p-6 pt-0">
          <button
            onClick={handleCreate}
            disabled={loading}
            className="w-full py-4 bg-gradient-to-r from-rose-600 to-rose-500 hover:from-rose-500 hover:to-rose-400 text-white font-bold rounded-xl shadow-lg shadow-rose-900/20 transition-all active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
          >
            {loading ? (
              <>
                <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                Creating...
              </>
            ) : (
              <>
                <Swords size={20} />
                Start Battle
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
