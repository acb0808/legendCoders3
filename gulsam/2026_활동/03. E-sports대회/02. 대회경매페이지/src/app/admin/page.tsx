'use client';

import { useState } from 'react';
import useSWR, { mutate } from 'swr';
import { Database, Captain, Player } from '@/lib/db';

const fetcher = (url: string) => fetch(url).then((res) => res.json());

export default function AdminPage() {
  const { data: db, error } = useSWR<Database>('/api/db', fetcher);
  const [isResetting, setIsResetting] = useState(false);

  if (error) return <div className="p-8 text-red-500">Failed to load data</div>;
  if (!db) return <div className="p-8">Loading...</div>;

  const updateDb = async (newDb: Database) => {
    await fetch('/api/db', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(newDb),
    });
    mutate('/api/db');
  };

  const resetData = async () => {
    if (!confirm('Are you sure you want to reset all data? This cannot be undone.')) return;
    setIsResetting(true);
    
    const initialDb: Database = {
      ...db,
      captains: db.captains.map(c => ({ ...c, points: 1000, team: [] })),
      players: db.players.map(p => ({ ...p, status: 'unassigned' })),
      auctionHistory: [],
      config: {
        currentRound: 1,
        phase: 'waiting',
        activePlayerId: null
      }
    };

    await updateDb(initialDb);
    setIsResetting(false);
  };

  const updateCaptainPoints = (id: string, points: number) => {
    const newDb = { ...db };
    const idx = newDb.captains.findIndex(c => c.id === id);
    newDb.captains[idx].points = points;
    updateDb(newDb);
  };

  const revertToRound = (round: number) => {
    if (!confirm(`Revert to round ${round}? Recent history will be lost.`)) return;
    
    const newDb = { ...db };
    // Find history items to keep
    const historyToKeep = newDb.auctionHistory.filter(h => h.round < round);
    
    // Recalculate captains based on history
    newDb.captains = newDb.captains.map(c => ({ ...c, points: 1000, team: [] }));
    newDb.players = newDb.players.map(p => ({ ...p, status: 'unassigned' }));
    
    historyToKeep.forEach(h => {
        if (h.winnerId) {
            const cIdx = newDb.captains.findIndex(c => c.id === h.winnerId);
            const pIdx = newDb.players.findIndex(p => p.id === h.playerId);
            newDb.captains[cIdx].points -= h.bidPrice;
            newDb.captains[cIdx].team.push(h.playerId);
            newDb.players[pIdx].status = 'assigned';
        } else {
            const pIdx = newDb.players.findIndex(p => p.id === h.playerId);
            newDb.players[pIdx].status = 'skipped';
        }
    });

    newDb.auctionHistory = historyToKeep;
    newDb.config.currentRound = round;
    newDb.config.phase = 'waiting';
    newDb.config.activePlayerId = null;

    updateDb(newDb);
  };

  return (
    <div className="p-8 max-w-6xl mx-auto">
      <header className="mb-12">
        <h1 className="text-4xl font-black gold-gradient-text italic uppercase">ADMIN DASHBOARD</h1>
        <p className="text-gray-500 mt-2">Manage auction state, points, and history</p>
      </header>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
        {/* Captains Management */}
        <section className="hextech-border p-6 bg-background/50">
          <h2 className="text-xl font-bold text-white mb-6 uppercase tracking-widest border-b border-gold/20 pb-2">Captain Points</h2>
          <div className="space-y-4">
            {db.captains.map((c) => (
              <div key={c.id} className="flex items-center justify-between gap-4">
                <span className="text-gray-300 font-medium">{c.name}</span>
                <div className="flex items-center gap-2">
                    <input 
                        type="number" 
                        value={c.points} 
                        onChange={(e) => updateCaptainPoints(c.id, parseInt(e.target.value) || 0)}
                        className="bg-black/50 border border-gold/30 p-2 text-gold font-bold w-24 text-right"
                    />
                    <span className="text-[10px] text-gold/50 uppercase">pts</span>
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* System Controls */}
        <section className="hextech-border p-6 bg-background/50">
          <h2 className="text-xl font-bold text-white mb-6 uppercase tracking-widest border-b border-gold/20 pb-2">Danger Zone</h2>
          <div className="space-y-6">
            <div>
              <p className="text-xs text-gray-500 mb-2 uppercase">Reset everything to start a new game</p>
              <button 
                onClick={resetData} 
                disabled={isResetting}
                className="w-full btn-hextech border-red-900/50 hover:bg-red-900/20 text-red-500"
              >
                {isResetting ? 'RESETTING...' : 'RESET ALL DATA'}
              </button>
            </div>

            <div>
              <p className="text-xs text-gray-500 mb-2 uppercase">Current Round Control</p>
              <div className="flex items-center gap-4">
                <span className="text-2xl font-black text-white">{db.config.currentRound}</span>
                <div className="flex gap-2">
                    <button onClick={() => revertToRound(db.config.currentRound - 1)} className="p-2 border border-gold/20 hover:bg-gold/10 text-xs">REVERT LAST</button>
                    <button onClick={() => revertToRound(1)} className="p-2 border border-gold/20 hover:bg-gold/10 text-xs">REVERT TO START</button>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* Auction History */}
        <section className="hextech-border p-6 bg-background/50 md:col-span-2">
          <h2 className="text-xl font-bold text-white mb-6 uppercase tracking-widest border-b border-gold/20 pb-2">Auction History</h2>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="text-gray-500 border-b border-gold/10">
                  <th className="py-2">ROUND</th>
                  <th className="py-2">PLAYER</th>
                  <th className="py-2">WINNER</th>
                  <th className="py-2">PRICE</th>
                  <th className="py-2">ACTION</th>
                </tr>
              </thead>
              <tbody>
                {db.auctionHistory.slice().reverse().map((h, i) => {
                  const player = db.players.find(p => p.id === h.playerId);
                  const winner = db.captains.find(c => c.id === h.winnerId);
                  return (
                    <tr key={i} className="border-b border-gold/5 hover:bg-gold/5">
                      <td className="py-3 font-bold text-gold">{h.round}</td>
                      <td className="py-3 text-white">{player?.name}</td>
                      <td className="py-3">{winner?.name || <span className="text-gray-600">Skipped</span>}</td>
                      <td className="py-3 font-mono text-gold">{h.bidPrice}</td>
                      <td className="py-3">
                        <button onClick={() => revertToRound(h.round)} className="text-[10px] underline text-gray-500 hover:text-white uppercase">Revert here</button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </section>
      </div>
    </div>
  );
}
