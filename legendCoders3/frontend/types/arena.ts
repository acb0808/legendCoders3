import { User } from './user';

export interface ArenaResponse {
  id: string;
  host_id: string;
  guest_id: string | null;
  baekjoon_problem_id: number | null;
  status: 'WAITING' | 'READY' | 'PLAYING' | 'FINISHED' | 'CANCELLED';
  difficulty: string;
  host_ready: boolean;
  guest_ready: boolean;
  host_surrender: boolean;
  guest_surrender: boolean;
  draw_agreed: boolean;
  skip_agreed: boolean;
  start_time: string | null;
  end_time: string | null;
  winner_id: string | null;
  created_at: string;
  
  host?: User;
  guest?: User;
  winner?: User;
}
