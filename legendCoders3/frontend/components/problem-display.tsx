'use client';

import React, { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { ProblemDetail } from '@/types/problem'; 
import { toast } from 'sonner';
import { API_BASE_URL } from '@/config';
import { ExternalLink, Info, BrainCircuit, ShieldAlert } from 'lucide-react';
import { Badge } from '@/components/ui/badge';

interface ProblemDisplayProps {
  baekjoonProblemId: number;
  arenaId?: string;
}

export const ProblemDisplay: React.FC<ProblemDisplayProps> = ({ baekjoonProblemId, arenaId }) => {
  const [problem, setProblem] = useState<ProblemDetail | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchProblemDetails = async () => {
      setLoading(true);
      try {
        const url = new URL(`${API_BASE_URL}/daily-problems/baekjoon/${baekjoonProblemId}`);
        if (arenaId) url.searchParams.append('arena_id', arenaId);
        
        const response = await fetch(url.toString());
        if (!response.ok) throw new Error("Failed to fetch");
        const data: ProblemDetail = await response.json();
        setProblem(data);
      } catch (err) {
        toast.error("문제 정보를 불러오는 데 실패했습니다.");
      } finally {
        setLoading(false);
      }
    };

    if (baekjoonProblemId) fetchProblemDetails();
  }, [baekjoonProblemId, arenaId]);

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center py-20 animate-pulse">
        <BrainCircuit className="w-12 h-12 text-slate-700 mb-4" />
        <p className="text-slate-500 font-bold uppercase tracking-widest text-[10px]">Identifying Problem...</p>
      </div>
    );
  }

  if (!problem) return null;

  return (
    <div className="space-y-8 p-4">
      {/* Problem Identification Header */}
      <div className="text-center space-y-4">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-slate-800/50 border border-white/5 text-[10px] font-black uppercase tracking-widest text-slate-400">
          <Info size={12} />
          Challenge Identification
        </div>
        <h2 className="text-5xl font-black text-white tracking-tighter uppercase italic">
          #{problem.baekjoon_problem_id} <span className="text-rose-500">{problem.title}</span>
        </h2>
        <div className="flex justify-center gap-3">
          <Badge variant="outline" className="bg-rose-500/10 border-rose-500/20 text-rose-400 font-black">
            {problem.difficulty_level}
          </Badge>
          {problem.algorithm_type.map((tag, idx) => (
            <Badge key={idx} variant="outline" className="bg-blue-500/10 border-blue-500/20 text-blue-400 font-black">
              {tag}
            </Badge>
          ))}
        </div>
      </div>

      {/* Main Action Area */}
      <Card className="bg-slate-950/50 border-white/10 backdrop-blur-sm overflow-hidden rounded-3xl group transition-all hover:border-rose-500/30">
        <div className="p-8 flex flex-col items-center text-center space-y-6">
          <div className="w-20 h-20 rounded-full bg-white/5 flex items-center justify-center group-hover:scale-110 transition-transform duration-500">
            <ExternalLink className="text-rose-500" size={32} />
          </div>
          <div className="space-y-2">
            <h3 className="text-xl font-bold text-white uppercase tracking-tight">문제를 확인하고 해결하세요</h3>
            <p className="text-slate-400 text-sm max-w-md mx-auto">
              보안 및 가독성을 위해 외부 사이트에서 직접 문제를 확인해 주시기 바랍니다. <br/>
              해결 후 돌아와 <b>'제출 확인'</b> 버튼을 눌러 승리를 쟁취하세요!
            </p>
          </div>
          <a 
            href={`https://www.acmicpc.net/problem/${problem.baekjoon_problem_id}`} 
            target="_blank" 
            rel="noreferrer"
            className="w-full max-w-sm py-5 bg-white text-slate-950 rounded-2xl font-black uppercase tracking-tighter text-lg hover:bg-rose-500 hover:text-white transition-all shadow-xl shadow-white/5"
          >
            백준에서 문제 보기
          </a>
        </div>
      </Card>

      {/* Safety Notice */}
      <div className="flex items-center justify-center gap-4 text-slate-600">
        <div className="h-px flex-grow bg-white/5" />
        <div className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-widest">
          <ShieldAlert size={12} />
          Verified Secure Challenge
        </div>
        <div className="h-px flex-grow bg-white/5" />
      </div>
    </div>
  );
};
