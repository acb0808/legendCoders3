'use client';

import { useState, useCallback } from 'react';
import useSWR, { mutate } from 'swr';
import {
  DndContext,
  DragOverlay,
  closestCorners,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  DragStartEvent,
  DragOverEvent,
  DragEndEvent,
} from '@dnd-kit/core';
import {
  arrayMove,
  SortableContext,
  sortableKeyboardCoordinates,
  verticalListSortingStrategy,
  useSortable,
} from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { Database, Player, Captain } from '@/lib/db';

const fetcher = (url: string) => fetch(url).then((res) => res.json());

// Sortable Player Item
function SortablePlayer({ player, isAssigned }: { player: Player; isAssigned: boolean }) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({
    id: player.id,
  });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  };

  return (
    <div
      ref={setNodeRef}
      style={style}
      {...attributes}
      {...listeners}
      className={`p-2 mb-2 text-sm border border-gold/20 flex justify-between items-center cursor-move ${
        isAssigned ? 'bg-black/40 text-gray-300' : 'bg-gold/10 text-gold font-bold'
      }`}
    >
      <span>{player.name}</span>
      <span className="text-[10px] opacity-50 uppercase">{player.position}</span>
    </div>
  );
}

// Droppable Captain Card
function CaptainCard({ captain, players }: { captain: Captain; players: Player[] }) {
  const { setNodeRef } = useSortable({
    id: captain.id,
  });

  return (
    <div ref={setNodeRef} className="hextech-border p-4 bg-background/50 min-h-[300px]">
      <div className="flex justify-between items-center mb-4 border-b border-gold/20 pb-2">
        <h3 className="font-bold text-white uppercase tracking-wider">{captain.name}</h3>
        <span className="text-gold font-black">{captain.points}</span>
      </div>
      <SortableContext items={players.map((p) => p.id)} strategy={verticalListSortingStrategy}>
        {players.map((p) => (
          <SortablePlayer key={p.id} player={p} isAssigned={true} />
        ))}
        {players.length === 0 && (
          <div className="text-gray-600 text-xs text-center py-8 italic">No members yet</div>
        )}
      </SortableContext>
    </div>
  );
}

export default function BoardPage() {
  const { data: db, error } = useSWR<Database>('/api/db', fetcher);
  const [activeId, setActiveId] = useState<string | null>(null);

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 5 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates })
  );

  if (error) return <div className="p-8 text-red-500">Failed to load data</div>;
  if (!db) return <div className="p-8">Loading...</div>;

  const handleDragStart = (event: DragStartEvent) => {
    setActiveId(event.active.id as string);
  };

  const handleDragEnd = async (event: DragEndEvent) => {
    const { active, over } = event;
    if (!over) return;

    const activePlayerId = active.id as string;
    const overId = over.id as string;

    const newDb = { ...db };
    
    // Find where the player was
    let sourceCaptain = newDb.captains.find(c => c.team.includes(activePlayerId));
    let targetCaptain = newDb.captains.find(c => c.id === overId || c.team.includes(overId));

    if (!targetCaptain) {
        // Handle unassigned pool or other cases if needed
        return;
    }

    if (sourceCaptain) {
        sourceCaptain.team = sourceCaptain.team.filter(id => id !== activePlayerId);
    }
    
    if (!targetCaptain.team.includes(activePlayerId)) {
        targetCaptain.team.push(activePlayerId);
    }

    // Update player status
    const playerIndex = newDb.players.findIndex(p => p.id === activePlayerId);
    newDb.players[playerIndex].status = 'assigned';

    await fetch('/api/db', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(newDb),
    });

    mutate('/api/db');
    setActiveId(null);
  };

  const unassignedPlayers = db.players.filter(p => p.status !== 'assigned');

  return (
    <div className="p-8">
      <header className="mb-12 text-center">
        <h1 className="text-4xl font-black gold-gradient-text italic tracking-tighter uppercase">STATUS BOARD</h1>
        <p className="text-gray-500 mt-2">Team composition and remaining points</p>
      </header>

      <DndContext
        sensors={sensors}
        collisionDetection={closestCorners}
        onDragStart={handleDragStart}
        onDragEnd={handleDragEnd}
      >
        <div className="grid grid-cols-4 gap-6 mb-12">
          {db.captains.map((captain) => (
            <CaptainCard
              key={captain.id}
              captain={captain}
              players={db.players.filter((p) => captain.team.includes(p.id))}
            />
          ))}
        </div>

        <section className="mt-16">
          <h2 className="text-xl font-bold gold-gradient-text mb-6 uppercase tracking-widest border-b border-gold/20 pb-2">
            Unassigned Players Pool
          </h2>
          <div className="grid grid-cols-5 gap-4">
            {unassignedPlayers.map((player) => (
              <div 
                key={player.id} 
                className={`p-3 border border-gold/10 ${player.status === 'skipped' ? 'opacity-30' : 'bg-gold/5'}`}
              >
                <div className="text-xs text-blue-400 font-bold">{player.position}</div>
                <div className="text-lg font-bold text-white">{player.name}</div>
                <div className="text-[10px] text-gold/60 uppercase">{player.tier}</div>
              </div>
            ))}
          </div>
        </section>

        <DragOverlay>
          {activeId ? (
            <div className="p-2 bg-gold text-black font-bold border border-white/50 shadow-xl">
              {db.players.find(p => p.id === activeId)?.name}
            </div>
          ) : null}
        </DragOverlay>
      </DndContext>
    </div>
  );
}
