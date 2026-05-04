'use client';

import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Player } from '@/lib/db';

interface RouletteProps {
  players: Player[];
  onFinish: (selectedPlayer: Player) => void;
  isSpinning: boolean;
}

export default function Roulette({ players, onFinish, isSpinning }: RouletteProps) {
  const [currentIndex, setCurrentIndex] = useState(0);

  useEffect(() => {
    let interval: NodeJS.Timeout;
    if (isSpinning) {
      let speed = 50;
      let count = 0;
      const totalSteps = 50 + Math.floor(Math.random() * 20); // Random duration

      const spin = () => {
        setCurrentIndex((prev) => (prev + 1) % players.length);
        count++;

        if (count < totalSteps) {
          // Slowly decelerate
          speed = speed * 1.05;
          interval = setTimeout(spin, speed);
        } else {
          // Selection finished
          const finalIndex = (currentIndex + 1) % players.length;
          onFinish(players[finalIndex]);
        }
      };

      interval = setTimeout(spin, speed);
    }
    return () => clearTimeout(interval);
  }, [isSpinning, players, onFinish]);

  return (
    <div className="h-24 overflow-hidden relative hextech-border w-full max-w-2xl mx-auto flex items-center justify-center">
      <div className="absolute inset-y-0 left-0 w-1/4 bg-gradient-to-r from-background to-transparent z-10" />
      <div className="absolute inset-y-0 right-0 w-1/4 bg-gradient-to-l from-background to-transparent z-10" />
      <div className="absolute left-1/2 -translate-x-1/2 top-0 bottom-0 w-1 bg-gold/50 z-20" />
      
      <AnimatePresence mode="wait">
        <motion.div
          key={currentIndex}
          initial={{ y: 50, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          exit={{ y: -50, opacity: 0 }}
          transition={{ duration: 0.1, ease: "linear" }}
          className="text-3xl font-bold gold-gradient-text tracking-wider uppercase"
        >
          {players[currentIndex]?.name}
        </motion.div>
      </AnimatePresence>
    </div>
  );
}
