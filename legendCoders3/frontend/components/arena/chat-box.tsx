'use client';

import React, { useState, useEffect, useRef } from 'react';
import { Input } from '@/components/ui/input';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Send, MessageSquare, Clock, Info } from 'lucide-react'; 
import TitleBadge from '@/components/title-badge';

interface ChatMessage {
  sender_id: string; 
  sender_nickname?: string;
  sender_title?: string;
  content: string;
  timestamp: string;
}

interface ChatBoxProps {
  currentUserId: string;
  messages: ChatMessage[];
  isConnected: boolean;
  onSendChat: (content: string) => void;
}

export const ChatBox: React.FC<ChatBoxProps> = ({ 
  currentUserId, 
  messages = [], 
  isConnected, 
  onSendChat 
}) => {
  const [chatInput, setChatInput] = useState('');
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      const scrollContainer = scrollRef.current.querySelector('[data-radix-scroll-area-viewport]');
      if (scrollContainer) {
        scrollContainer.scrollTop = scrollContainer.scrollHeight;
      }
    }
  }, [messages]);

  const handleSendChat = () => {
    if (chatInput.trim() && isConnected) {
      onSendChat(chatInput.trim());
      setChatInput('');
    }
  };

  return (
    <div className="flex flex-col h-full text-white bg-slate-950/20">
      <div className="p-5 border-b border-white/5 flex justify-between items-center bg-slate-900/40">
        <div className="flex items-center gap-2">
          <MessageSquare size={14} className="text-rose-500" />
          <h3 className="text-[10px] font-black uppercase tracking-[0.2em] text-slate-400">Live Comms</h3>
        </div>
        <div className={`flex items-center gap-2 px-2 py-0.5 rounded-full border border-white/5 bg-slate-950/50`}>
          <div className={`w-1.5 h-1.5 rounded-full ${isConnected ? 'bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.5)]' : 'bg-rose-500 animate-pulse'}`} />
          <span className="text-[8px] font-black uppercase text-slate-500">{isConnected ? 'Online' : 'Offline'}</span>
        </div>
      </div>
      
      <ScrollArea ref={scrollRef} className="flex-grow p-5 overflow-y-auto">
        <div className="space-y-6 min-h-full pb-4">
          {messages.length === 0 ? (
            <div className="flex flex-col items-center justify-center opacity-20 py-20 text-center">
              <MessageSquare size={32} className="mb-4 mx-auto text-slate-500" />
              <p className="text-[10px] font-bold uppercase tracking-[0.3em] text-slate-400 font-sans">Awaiting transmissions</p>
            </div>
          ) : (
            messages.map((msg, index) => {
              const isSystem = msg.sender_id === 'system';
              const isMe = msg.sender_id === currentUserId;

              if (isSystem) {
                return (
                  <div key={index} className="flex items-center gap-4 animate-in fade-in zoom-in duration-500">
                    <div className="h-px flex-grow bg-gradient-to-r from-transparent to-white/5" />
                    <div className="flex items-center gap-2 px-4 py-1.5 rounded-full bg-white/5 border border-white/5">
                      <Info size={10} className="text-blue-400" />
                      <span className="text-[9px] font-black text-slate-400 uppercase tracking-widest">{msg.content}</span>
                    </div>
                    <div className="h-px flex-grow bg-gradient-to-l from-transparent to-white/5" />
                  </div>
                );
              }

              return (
                <div key={index} className={`flex flex-col ${isMe ? 'items-end' : 'items-start'} group animate-in slide-in-from-${isMe ? 'right' : 'left'}-2 duration-300`}>
                  <div className={`flex items-center gap-2 mb-1.5 ${isMe ? 'flex-row-reverse' : 'flex-row'}`}>
                    <span className="text-[9px] font-black text-slate-500 uppercase tracking-tight">{msg.sender_nickname}</span>
                    {msg.sender_title && (
                      <TitleBadge title={{ name: msg.sender_title, color_code: 'blue-500' }} size="xs" className="scale-90" />
                    )}
                  </div>
                  <div className={`px-4 py-2.5 rounded-2xl text-sm max-w-[85%] break-words transition-all ${
                    isMe 
                      ? 'bg-rose-600 text-white rounded-tr-none shadow-[0_5px_15px_rgba(225,29,72,0.2)]' 
                      : 'bg-slate-800 text-slate-200 rounded-tl-none border border-white/5'
                  }`}>
                    {msg.content}
                  </div>
                  <div className="mt-1 flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                    <Clock size={8} className="text-slate-600" />
                    <span className="text-[8px] font-bold text-slate-600 uppercase tracking-widest">
                      {new Date(msg.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </span>
                  </div>
                </div>
              );
            })
          )}
        </div>
      </ScrollArea>

      <div className="p-5 border-t border-white/5 bg-slate-900/40">
        <div className="relative">
          <Input
            type="text"
            placeholder={isConnected ? "메시지를 입력하세요..." : "아레나 연결 중..."}
            value={chatInput}
            disabled={!isConnected}
            onChange={(e) => setChatInput(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && handleSendChat()}
            className="w-full bg-slate-900/50 border-white/5 text-sm h-12 pr-12 rounded-2xl focus:ring-rose-500/50 focus:border-rose-500/50 transition-all placeholder:text-slate-600 font-medium disabled:opacity-50"
          />
          <button 
            onClick={handleSendChat}
            disabled={!isConnected || !chatInput.trim()}
            className={`absolute right-3 top-1/2 -translate-y-1/2 transition-colors p-1.5 rounded-xl ${
              isConnected && chatInput.trim() ? 'text-white bg-rose-600 hover:bg-rose-500' : 'text-slate-700'
            }`}
          >
            <Send size={16} />
          </button>
        </div>
      </div>
    </div>
  );
};
