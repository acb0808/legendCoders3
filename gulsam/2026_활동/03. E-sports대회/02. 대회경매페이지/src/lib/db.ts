import fs from 'fs/promises';
import path from 'path';

const DB_PATH = path.join(process.cwd(), 'data', 'db.json');

export interface Captain {
  id: string;
  name: string;
  points: number;
  team: string[]; // Player IDs
}

export interface Player {
  id: string;
  name: string;
  tier: string;
  position: string;
  status: 'unassigned' | 'assigned' | 'skipped';
}

export interface AuctionHistory {
  round: number;
  playerId: string;
  winnerId: string | null; // null if skipped
  bidPrice: number;
}

export interface AppConfig {
  currentRound: number;
  phase: 'waiting' | 'roulette' | 'bidding' | 'result';
  activePlayerId: string | null;
}

export interface Database {
  captains: Captain[];
  players: Player[];
  auctionHistory: AuctionHistory[];
  config: AppConfig;
}

export async function readDb(): Promise<Database> {
  const data = await fs.readFile(DB_PATH, 'utf-8');
  return JSON.parse(data);
}

export async function writeDb(db: Database): Promise<void> {
  await fs.writeFile(DB_PATH, JSON.stringify(db, null, 2), 'utf-8');
}
