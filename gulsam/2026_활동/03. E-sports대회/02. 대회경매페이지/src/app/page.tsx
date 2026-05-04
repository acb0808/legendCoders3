'use client';

import { useState } from 'react';
import useSWR, { mutate } from 'swr';
import { motion, AnimatePresence } from 'framer-motion';
import { Database, Player, Captain } from '@/lib/db';
import Roulette from '@/components/auction/Roulette';

const fetcher = (url: string) => fetch(url).then((res) => res.json());

export default function AuctionPage() {
  const { data: db, error } = useSWR<Database>('/api/db', fetcher);
  const [isSpinning, setIsSpinning] = useState(false);
  const [selectedPlayer, setSelectedPlayer] = useState<Player | null>(null);
  const [showBidModal, setShowBidModal] = useState(false);
  const [bidAmount, setBidAmount] = useState<number>(0);
  const [winningCaptainId, setWinningCaptainId] = useState<string>('');

  if (error) return <div className="p-8 text-red-500">Failed to load data</div>;
  if (!db) return <div className="p-8">Loading...</div>;

  const unassignedPlayers = db.players.filter((p) => p.status === 'unassigned');
  const availableCaptains = db.captains.filter((c) => c.team.length < 5); // Assuming 5-6 members, limit to 5 for now

  const startSpin = () => {
    setIsSpinning(true);
    setSelectedPlayer(null);
  };

  const onSpinFinish = (player: Player) => {
    setIsSpinning(false);
    setSelectedPlayer(player);
  };

  const handleBidding = async () => {
    if (!selectedPlayer || !db) return;

    const newDb = { ...db };
    const playerIndex = newDb.players.findIndex((p) => p.id === selectedPlayer.id);

    if (winningCaptainId) {
      // Normal bid
      const captainIndex = newDb.captains.findIndex((c) => c.id === winningCaptainId);
      const captain = newDb.captains[captainIndex];

      if (captain.points < bidAmount) {
        alert('Not enough points!');
        return;
      }

      newDb.captains[captainIndex] = {
        ...captain,
        points: captain.points - bidAmount,
        team: [...captain.team, selectedPlayer.id],
      };
      newDb.players[playerIndex].status = 'assigned';
      newDb.auctionHistory.push({
        round: newDb.config.currentRound,
        playerId: selectedPlayer.id,
        winnerId: winningCaptainId,
        bidPrice: bidAmount,
      });
    } else {
      // Skipped
      newDb.players[playerIndex].status = 'skipped';
      newDb.auctionHistory.push({
        round: newDb.config.currentRound,
        playerId: selectedPlayer.id,
        winnerId: null,
        bidPrice: 0,
      });
    }

    newDb.config.currentRound += 1;
    newDb.config.activePlayerId = null;

    await fetch('/api/db', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(newDb),
    });

    mutate('/api/db');
    setSelectedPlayer(null);
    setShowBidModal(false);
    setBidAmount(0);
    setWinningCaptainId('');
  };

  return (
    <div className="flex flex-col items-center p-8 gap-12">
      <header className="text-center">
        <h1 className="text-4xl font-black gold-gradient-text italic tracking-tighter">AUCTION PHASE</h1>
        <p className="text-gray-400 mt-2">ROUND {db.config.currentRound}</p>
      </header>

      <section className="w-full max-w-4xl flex flex-col gap-8">
        {!selectedPlayer && !isSpinning && (
          <div className="flex justify-center py-20">
            <button onClick={startSpin} className="btn-hextech text-2xl px-12 py-4">
              START SELECTION
            </button>
          </div>
        )}

        {(isSpinning || (!selectedPlayer && isSpinning)) && (
          <Roulette players={unassignedPlayers} isSpinning={isSpinning} onFinish={onSpinFinish} />
        )}

        {selectedPlayer && (
          <motion.div
            initial={{ scale: 0.8, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            className="hextech-border p-8 flex flex-col items-center gap-6 bg-gradient-to-b from-blue/10 to-transparent"
          >
            <div className="text-blue-400 font-bold tracking-widest uppercase text-sm">{selectedPlayer.position}</div>
            <div className="text-6xl font-black italic gold-gradient-text uppercase tracking-tighter">
              {selectedPlayer.name}
            </div>
            <div className="px-4 py-1 border border-gold/30 rounded-full text-xs font-bold text-gold/80 uppercase">
              {selectedPlayer.tier}
            </div>

            <div className="flex gap-4 mt-8">
              <button onClick={() => setShowBidModal(true)} className="btn-hextech">
                PLACE BID
              </button>
              <button onClick={() => handleBidding()} className="text-gray-500 hover:text-white transition-colors text-sm underline uppercase">
                SKIP PLAYER
              </button>
            </div>
          </motion.div>
        )}
      </section>

      {/* Captains Footer */}
      <section className="w-full mt-auto grid grid-cols-4 gap-4 max-w-6xl">
        {db.captains.map((captain) => (
          <div key={captain.id} className="hextech-border p-4 bg-background/50">
            <div className="text-xs text-gray-500 uppercase tracking-widest mb-1">CAPTAIN</div>
            <div className="text-lg font-bold text-white">{captain.name}</div>
            <div className="text-xl font-black text-gold mt-2">{captain.points} <span className="text-[10px] font-normal text-gold/50">pts</span></div>
            <div className="mt-3 flex gap-1">
              {Array.from({ length: 5 }).map((_, i) => (
                <div key={i} className={`w-3 h-3 border border-gold/20 ${captain.team[i] ? 'bg-gold' : 'bg-transparent'}`} />
              ))}
            </div>
          </div>
        ))}
      </section>

      {/* Bidding Modal */}
      {showBidModal && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/80 backdrop-blur-sm">
          <motion.div
            initial={{ y: 20, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            className="hextech-border p-8 w-full max-w-md bg-background"
          >
            <h2 className="text-2xl font-bold gold-gradient-text mb-6">BIDDING ENTRY</h2>
            
            <div className="space-y-6">
              <div>
                <label className="block text-xs text-gray-400 uppercase tracking-widest mb-2">Winning Captain</label>
                <select
                  value={winningCaptainId}
                  onChange={(e) => setWinningCaptainId(e.target.value)}
                  className="w-full bg-black/50 border border-gold/30 p-3 text-white outline-none focus:border-gold"
                >
                  <option value="">Select Captain</option>
                  {db.captains.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.name} ({c.points} pts)
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs text-gray-400 uppercase tracking-widest mb-2">Bid Amount</label>
                <input
                  type="number"
                  value={bidAmount}
                  onChange={(e) => setBidAmount(parseInt(e.target.value) || 0)}
                  className="w-full bg-black/50 border border-gold/30 p-3 text-white outline-none focus:border-gold text-2xl font-black text-center"
                />
              </div>

              <div className="flex gap-4 pt-4">
                <button onClick={handleBidding} className="btn-hextech flex-1">
                  CONFIRM BID
                </button>
                <button onClick={() => setShowBidModal(false)} className="text-gray-500 px-4">
                  CANCEL
                </button>
              </div>
            </div>
          </motion.div>
        </div>
      )}
    </div>
  );
}
