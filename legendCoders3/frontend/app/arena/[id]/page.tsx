'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import { useRouter, useParams } from 'next/navigation';
import { useAuth } from '@/components/auth-provider';
import { arenaApi } from '@/lib/api';
import { API_BASE_URL } from '@/config';
import { toast } from 'sonner';
import { Swords, Share2, Trophy, Loader2 } from 'lucide-react';
import confetti from 'canvas-confetti';

// Import UI Components
import { ChatBox } from '@/components/arena/chat-box';
import { ReadyView } from '@/components/arena/ready-view';
import { GameView } from '@/components/arena/game-view';
import { PlayerStatsCard } from '@/components/arena/player-stats-card';

import { ArenaResponse } from '@/types/arena'; 
import { User } from '@/types/user'; 

export default function ArenaBattle() {
  const { user, accessToken, loading: authLoading, refreshUser } = useAuth();
  const params = useParams();
  const router = useRouter();
  const arenaId = params.id as string;

  // --- States ---
  const [arena, setArena] = useState<ArenaResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [messages, setMessages] = useState<any[]>([]); 
  const [countdown, setCountdown] = useState<number | null>(null);
  const [isConnected, setIsConnected] = useState(false);

  // --- Refs for Persistence ---
  const arenaRef = useRef<ArenaResponse | null>(null);
  const userRef = useRef<User | null>(null);
  const tokenRef = useRef<string | null>(null);
  const ws = useRef<WebSocket | null>(null);
  const reconnectTimeout = useRef<NodeJS.Timeout | null>(null);
  const onMessageRef = useRef<(msg: any) => void>(() => {});

  useEffect(() => { arenaRef.current = arena; }, [arena]);
  useEffect(() => { userRef.current = user; }, [user]);
  useEffect(() => { tokenRef.current = accessToken; }, [accessToken]);

  const addSystemMessage = useCallback((content: string) => {
    setMessages((prev) => [...prev, {
      sender_id: 'system',
      content,
      timestamp: new Date().toISOString()
    }]);
  }, []);

  const launchFireworks = () => {
    const duration = 5 * 1000;
    const animationEnd = Date.now() + duration;
    const defaults = { startVelocity: 30, spread: 360, ticks: 60, zIndex: 1000 };
    const randomInRange = (min: number, max: number) => Math.random() * (max - min) + min;

    const interval: any = setInterval(function() {
      const timeLeft = animationEnd - Date.now();
      if (timeLeft <= 0) return clearInterval(interval);
      const particleCount = 50 * (timeLeft / duration);
      confetti({ ...defaults, particleCount, origin: { x: randomInRange(0.1, 0.3), y: Math.random() - 0.2 } });
      confetti({ ...defaults, particleCount, origin: { x: randomInRange(0.7, 0.9), y: Math.random() - 0.2 } });
    }, 250);
  };

  // --- Socket Handler ---
  const handleSocketMessage = useCallback((message: any) => {
    console.log("[ArenaWS] Event:", message.type);
    switch (message.type) {
      case 'ARENA_STATE':
        if (arenaRef.current && !arenaRef.current.guest_id && message.payload.guest_id) {
          addSystemMessage(`${message.payload.guest?.nickname} 님이 입장했습니다.`);
        }
        setArena(message.payload);
        setLoading(false);
        break;
      case 'CHAT':
        setMessages((prev) => [...prev, message.payload]);
        break;
      case 'COUNTDOWN':
        setCountdown(message.payload);
        break;
      case 'GAME_START':
        setCountdown(null); 
        toast.success("전투 시작!");
        addSystemMessage("전투가 시작되었습니다. 행운을 빕니다!");
        break;
      case 'GAME_OVER':
        const winnerId = message.payload.winner_id;
        const reason = message.payload.reason;
        const isWinner = winnerId === userRef.current?.id;
        
        if (winnerId === null) {
          toast.info("무승부!");
          addSystemMessage(`대전 종료: 무승부 (${reason || '상호 합의'})`);
        } else {
          const winnerName = winnerId === arenaRef.current?.host_id ? arenaRef.current?.host?.nickname : arenaRef.current?.guest?.nickname;
          addSystemMessage(`대전 종료: ${winnerName} 님 승리 (${reason || '문제 해결'})`);
          if (isWinner) {
            toast.success("축하합니다! 승리하셨습니다!");
            setTimeout(launchFireworks, 100);
          } else {
            toast.error("아쉽게 패배하셨습니다.");
          }
        }
        setArena((prev) => prev ? { ...prev, status: 'FINISHED', winner_id: winnerId } : null);
        break;
      case 'PROBLEM_LOADED':
        setArena((prev) => prev ? { ...prev, baekjoon_problem_id: message.payload.problem_id } : null);
        break;
      case 'PROBLEM_CHANGED':
        toast.info("문제가 변경되었습니다.");
        addSystemMessage("상호 합의하에 문제가 새로운 문제로 변경되었습니다.");
        setArena((prev) => prev ? { ...prev, baekjoon_problem_id: message.payload.problem_id, draw_agreed: false, skip_agreed: false, host_skip_agreed: false, guest_skip_agreed: false, host_draw_agreed: false, guest_draw_agreed: false } : null);
        break;
      case 'DRAW_PROPOSED':
        if (message.payload.proposer_id !== userRef.current?.id) {
          addSystemMessage("상대방이 무승부를 제안했습니다.");
        }
        break;
      case 'SKIP_PROPOSED':
        if (message.payload.proposer_id !== userRef.current?.id) {
          addSystemMessage("상대방이 문제 변경을 제안했습니다.");
        }
        break;
      case 'GUEST_LEFT': 
        addSystemMessage("상대방이 퇴장했습니다.");
        setArena((prev) => prev ? { ...prev, guest_id: null, guest: null, status: 'WAITING', guest_ready: false } : null);
        break;
      case 'ERROR':
        toast.error(`서버 오류: ${message.payload}`);
        if (message.payload.includes("인증") || message.payload.includes("실패")) {
          refreshUser();
        }
        break;
    }
  }, [addSystemMessage, refreshUser]);

  useEffect(() => {
    onMessageRef.current = handleSocketMessage;
  }, [handleSocketMessage]);

  // --- Socket Logic ---
  const connect = useCallback(() => {
    if (!arenaId || !userRef.current || !tokenRef.current) return;
    if (ws.current && (ws.current.readyState === WebSocket.CONNECTING || ws.current.readyState === WebSocket.OPEN)) return;

    const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
    let host = API_BASE_URL.replace(/^https?:\/\//, '');
    if (!host.includes(':')) host = `${host}:8000`;
    
    const url = `${protocol}://${host}/api/arena/${arenaId}/ws?token=${tokenRef.current}&user_id=${userRef.current.id}`;
    console.log(`[ArenaWS] Initiating connection: ${url}`);
    const socket = new WebSocket(url);
    ws.current = socket;

    socket.onopen = () => {
      console.log('[ArenaWS] Established');
      setIsConnected(true);
    };

    socket.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data);
        onMessageRef.current(message);
      } catch (e) {}
    };

    socket.onclose = (event) => {
      console.log('[ArenaWS] Closed', event.code);
      setIsConnected(false);
      ws.current = null;
      if (event.code !== 1000) {
        reconnectTimeout.current = setTimeout(connect, 3000);
      }
    };

    socket.onerror = () => setIsConnected(false);
  }, [arenaId]);

  const disconnect = useCallback(() => {
    if (reconnectTimeout.current) {
      clearTimeout(reconnectTimeout.current);
      reconnectTimeout.current = null;
    }
    if (ws.current) {
      ws.current.onopen = null;
      ws.current.onmessage = null;
      ws.current.onclose = null;
      ws.current.onerror = null;
      if (ws.current.readyState === WebSocket.OPEN || ws.current.readyState === WebSocket.CONNECTING) {
        ws.current.close(1000);
      }
      ws.current = null;
    }
    setIsConnected(false);
  }, []);

  const sendMessage = useCallback((msg: any) => {
    if (ws.current?.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify(msg));
    }
  }, []);

  const sendChat = (content: string) => sendMessage({ type: 'CHAT', payload: { content } });
  const sendReadyToggle = () => sendMessage({ type: 'READY_TOGGLE', payload: {} });
  const sendSurrender = () => sendMessage({ type: 'SURRENDER', payload: {} });
  const sendProposeDraw = () => sendMessage({ type: 'PROPOSE_DRAW', payload: {} });
  const sendProposeSkip = () => sendMessage({ type: 'PROPOSE_SKIP', payload: {} });
  const sendLeaveArena = () => sendMessage({ type: 'LEAVE_ARENA', payload: {} });

  // --- Initial Sync ---
  useEffect(() => {
    const sync = async () => {
      if (!user || !arenaId) return;
      try {
        let data = await arenaApi.getArena(arenaId);
        if (data.status === 'WAITING' && data.host_id !== user.id && !data.guest_id) {
          data = await arenaApi.joinArena(arenaId);
          toast.success("경기에 참여했습니다!");
          addSystemMessage("경기에 참여했습니다.");
        }
        setArena(data);
        setLoading(false);
        connect();
      } catch (e: any) {
        router.push('/arena');
      }
    };
    sync();
    return () => disconnect();
  }, [arenaId, user?.id, accessToken, connect, disconnect, router, addSystemMessage, user]);

  const handleLeaveArena = useCallback(() => {
    if (window.confirm("정말 나가시겠습니까?")) {
      sendLeaveArena();
      setTimeout(() => {
        disconnect();
        router.push('/arena');
      }, 100);
    }
  }, [sendLeaveArena, disconnect, router]);

  if (authLoading || (loading && !arena)) {
    return (
      <div className="min-h-screen bg-[#020617] flex items-center justify-center">
        <Loader2 className="w-8 h-8 text-rose-500 animate-spin" />
      </div>
    );
  }

  if (!arena) return null;

  return (
    <div className="min-h-screen bg-[#020617] text-slate-200 font-sans flex flex-col selection:bg-rose-500/30">
      <header className="fixed top-0 left-0 right-0 h-16 bg-slate-950/40 backdrop-blur-xl border-b border-white/5 z-50 flex items-center justify-between px-8">
        <div className="flex items-center gap-6">
          <button onClick={handleLeaveArena} className="text-slate-400 hover:text-white transition-all text-xs font-bold uppercase tracking-widest group">
            <span className="group-hover:-translate-x-1 transition-transform inline-block mr-2">&larr;</span> Leave
          </button>
          <div className="flex items-center gap-3">
            <Swords className="text-rose-500" size={18} />
            <h1 className="text-sm font-black uppercase tracking-widest text-white">Arena #{arena.id.slice(0, 8)}</h1>
          </div>
        </div>
        <div className="flex items-center gap-4">
          <div className={`px-3 py-1 rounded-full text-[9px] font-black uppercase tracking-widest border transition-all duration-500 ${
            arena.status === 'PLAYING' ? 'bg-rose-500/10 border-rose-500/50 text-rose-400' : 
            arena.status === 'FINISHED' ? 'bg-slate-500/10 border-slate-500/50 text-slate-400' : 'bg-emerald-500/10 border-emerald-500/50 text-emerald-400'
          }`}>
            {arena.status}
          </div>
          <button onClick={() => { navigator.clipboard.writeText(window.location.href); toast.success("복사됨"); }} className="p-2 text-slate-400 hover:text-white bg-white/5 rounded-lg border border-white/5 transition-colors">
            <Share2 size={16} />
          </button>
        </div>
      </header>

      <main className="flex-grow pt-24 pb-8 px-6 max-w-[1600px] mx-auto w-full grid grid-cols-1 md:grid-cols-12 gap-6 relative z-10">
        <div className="md:col-span-3 lg:col-span-2 space-y-4">
          <h2 className="text-[10px] font-black text-slate-500 uppercase tracking-[0.2em] px-2">Players</h2>
          <PlayerStatsCard user={arena.host} isHost={true} isReady={arena.host_ready} isWinner={arena.winner_id === arena.host_id} isMe={user?.id === arena.host_id} />
          <div className="flex justify-center py-2 opacity-20"><Swords size={20} className="text-slate-500" /></div>
          <PlayerStatsCard user={arena.guest} isHost={false} isReady={arena.guest_ready} isWinner={arena.winner_id === arena.guest_id} isMe={user?.id === arena.guest_id} />
        </div>

        <div className="md:col-span-9 lg:col-span-7 flex flex-col h-full min-h-[600px]">
          <div className="flex-grow bg-slate-900/40 rounded-[2rem] border border-white/10 backdrop-blur-xl overflow-hidden flex flex-col shadow-2xl">
            {arena.status === 'WAITING' || arena.status === 'READY' ? (
              <ReadyView arena={arena} currentUser={user!} countdown={countdown} onLeave={handleLeaveArena} onReadyToggle={sendReadyToggle} />
            ) : arena.status === 'PLAYING' && arena.baekjoon_problem_id ? (
              <GameView arena={arena} currentUser={user!} problemId={arena.baekjoon_problem_id} onSurrender={sendSurrender} onProposeDraw={sendProposeDraw} onProposeSkip={sendProposeSkip} />
            ) : (
              <div className="flex flex-col items-center justify-center h-full text-center p-8 animate-in zoom-in duration-500">
                <div className="relative mb-8">
                  <div className="absolute inset-0 bg-yellow-500/20 blur-[60px] rounded-full animate-pulse" />
                  <Trophy className={`w-24 h-24 text-yellow-500 drop-shadow-[0_0_30px_rgba(234,179,8,0.6)] ${arena.winner_id === user?.id ? 'animate-bounce' : ''}`} />
                </div>
                
                <h2 className="text-5xl font-black text-white mb-4 uppercase italic tracking-tighter">
                  {arena.winner_id === user?.id ? (
                    <span className="text-transparent bg-clip-text bg-gradient-to-r from-yellow-400 to-orange-500">Victory!</span>
                  ) : arena.winner_id ? (
                    <span className="text-slate-400">Match Concluded</span>
                  ) : (
                    <span className="text-slate-400">Draw</span>
                  )}
                </h2>
                
                <p className="text-slate-400 mb-10 font-medium text-lg max-w-md mx-auto">
                  {arena.winner_id === user?.id 
                    ? "축하합니다! 뛰어난 실력으로 승리를 거머쥐셨습니다."
                    : arena.winner_id 
                    ? "아쉽게 패배했습니다. 다음 기회를 노려보세요."
                    : "치열한 접전 끝에 무승부로 마무리되었습니다."}
                </p>
                
                <button 
                  onClick={() => router.push('/arena')} 
                  className="group relative px-10 py-4 bg-white text-slate-950 rounded-2xl font-black uppercase tracking-tighter hover:scale-105 active:scale-95 transition-all shadow-xl shadow-white/10 overflow-hidden"
                >
                  <div className="absolute inset-0 bg-gradient-to-r from-transparent via-rose-500/10 to-transparent -translate-x-full group-hover:translate-x-full transition-transform duration-700" />
                  Return to Lobby
                </button>
              </div>
            )}
          </div>
        </div>

        <div className="md:col-span-12 lg:col-span-3 flex flex-col h-full max-h-[850px]">
          <h2 className="text-[10px] font-black text-slate-500 uppercase tracking-[0.2em] px-2 mb-4 text-center sm:text-left">Battle Logs & Comms</h2>
          <div className="flex-grow overflow-hidden rounded-[2rem] border border-white/10 backdrop-blur-xl bg-slate-900/40 shadow-2xl">
            <ChatBox messages={messages} currentUserId={user!.id} isConnected={isConnected} onSendChat={sendChat} />
          </div>
        </div>
      </main>
    </div>
  );
}
