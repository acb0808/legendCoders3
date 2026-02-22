// frontend/app/arena/page.tsx
'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/components/auth-provider';
import Link from 'next/link';
import { arenaApi } from '@/lib/api';
import { Swords, Plus, RefreshCcw } from 'lucide-react';
import ArenaCard from '@/components/arena/arena-card';
import CreateArenaModal from '@/components/arena/create-arena-modal';

export default function ArenaLobby() {
  const { user, loading } = useAuth();
  const router = useRouter();
  const [arenas, setArenas] = useState<any[]>([]);
  const [fetchLoading, setFetchLoading] = useState(true);
  const [showCreateModal, setShowCreateModal] = useState(false);

  // Authentication Guard & Active Arena Check
  useEffect(() => {
    if (!loading && !user) {
      router.push('/login?redirect=/arena');
      return;
    }

    const checkActiveArena = async () => {
      if (user) {
        try {
          const activeArena = await arenaApi.getActiveArena();
          if (activeArena) {
            router.push(`/arena/${activeArena.id}`);
          }
        } catch (error) {
          console.error("Failed to check active arena:", error);
        }
      }
    };

    checkActiveArena();
  }, [user, loading, router]);

  const fetchArenas = async () => {
    try {
      setFetchLoading(true);
      const data = await arenaApi.getOpenArenas();
      setArenas(data);
    } catch (error) {
      console.error("Failed to fetch arenas:", error);
    } finally {
      setFetchLoading(false);
    }
  };

  useEffect(() => {
    if (user) {
      fetchArenas();
      // Auto refresh every 10s
      const interval = setInterval(fetchArenas, 10000);
      return () => clearInterval(interval);
    }
  }, [user]);

  if (loading || !user) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center">
        <div className="w-10 h-10 border-4 border-rose-500 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-200">
      
      {/* Hero Section */}
      <section className="relative overflow-hidden pt-32 pb-20 px-6 sm:px-10 max-w-7xl mx-auto">
        <div className="absolute inset-0 bg-gradient-to-b from-rose-500/5 via-slate-900/0 to-slate-950 pointer-events-none" />
        
        <div className="relative z-10 flex flex-col md:flex-row justify-between items-end gap-8">
          <div className="space-y-4">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs font-bold uppercase tracking-wider">
              <span className="w-2 h-2 rounded-full bg-rose-500 animate-pulse" />
              실시간 대전 경기장
            </div>
            <h1 className="text-4xl md:text-6xl font-black text-white tracking-tight">
              실력으로 <span className="text-transparent bg-clip-text bg-gradient-to-r from-rose-500 to-orange-500">증명</span>하라
            </h1>
            <p className="text-lg text-slate-400 max-w-xl leading-relaxed">
              라이벌과 실시간 알고리즘 대결을 펼치세요. <br/>
              변명은 필요 없습니다. 오직 코드뿐.
            </p>
          </div>

          <button 
            onClick={() => setShowCreateModal(true)}
            className="group relative px-8 py-4 bg-white text-slate-950 font-bold text-lg rounded-xl overflow-hidden hover:scale-105 active:scale-95 transition-all shadow-[0_0_40px_-10px_rgba(255,255,255,0.3)] hover:shadow-[0_0_60px_-10px_rgba(255,255,255,0.5)]"
          >
            <div className="absolute inset-0 bg-gradient-to-r from-rose-500 to-orange-500 opacity-0 group-hover:opacity-10 transition-opacity" />
            <span className="relative flex items-center gap-3">
              <Swords className="w-6 h-6" />
              경기장 생성
            </span>
          </button>
        </div>
      </section>

      {/* Arena List */}
      <main className="max-w-7xl mx-auto px-6 sm:px-10 pb-20">
        <div className="flex items-center justify-between mb-8">
          <h2 className="text-2xl font-bold text-white flex items-center gap-3">
            대기 중인 매치
            <span className="text-sm font-normal text-slate-500 bg-slate-900 px-3 py-1 rounded-full border border-slate-800">
              {arenas.length}개 활성
            </span>
          </h2>
          <button 
            onClick={fetchArenas}
            className="p-2 text-slate-400 hover:text-white hover:bg-slate-900 rounded-lg transition-colors"
          >
            <RefreshCcw size={20} className={fetchLoading ? "animate-spin" : ""} />
          </button>
        </div>

        {fetchLoading && arenas.length === 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-48 bg-slate-900/50 rounded-xl animate-pulse border border-slate-800" />
            ))}
          </div>
        ) : arenas.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
            {arenas.map((arena) => (
              <ArenaCard key={arena.id} arena={arena} />
            ))}
          </div>
        ) : (
          <div className="text-center py-20 border border-dashed border-slate-800 rounded-2xl bg-slate-900/20">
            <Swords className="w-12 h-12 text-slate-600 mx-auto mb-4 opacity-50" />
            <h3 className="text-xl font-bold text-slate-500">활성화된 대결이 없습니다</h3>
            <p className="text-slate-600 mt-2">첫 번째로 방을 만들어 도전자를 기다려보세요!</p>
          </div>
        )}
      </main>

      {/* Modal */}
      {showCreateModal && (
        <CreateArenaModal onClose={() => setShowCreateModal(false)} />
      )}
    </div>
  );
}
