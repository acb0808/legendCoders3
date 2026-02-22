export interface Title {
  id: string;
  name: string;
  description: string;
  color_code: string;
  is_pro_only: boolean;
  has_glow: boolean;
  animation_type: string | null;
  icon: string | null;
}

export interface User {
  id: string;
  email: string;
  nickname: string;
  baekjoon_id: string;
  is_pro: boolean;
  streak_freeze_count: number;
  equipped_title?: Title;
  last_sync_at?: string;
}
