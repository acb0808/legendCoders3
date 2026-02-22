'use client';

import React, { useEffect, useState, useRef } from 'react';
import { useAuth } from '@/components/auth-provider';
import { useRouter } from 'next/navigation';
import api from '@/lib/api';
import { BookOpen, ExternalLink, Send, CheckCircle2, AlertCircle, Loader2, MessageSquare, Crown, Clock, RefreshCw } from 'lucide-react';
import Link from 'next/link';

interface Problem {
  id: string;
  baekjoon_problem_id: number;
  title: string;
  description: string;
  input_example: string;
  output_example: string;
  difficulty_level: string;
  algorithm_type: string[];
}

export default function TodayProblemPage() {
  const { user, loading, refreshUser } = useAuth();
  const router = useRouter();
  const [problem, setProblem] = useState<Problem | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsLoadingSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [submitSuccess, setSubmitSuccess] = useState(false);
  
  // Pro Sync States
  const [nextSyncIn, setNextSyncIn] = useState<number>(300);
  const [isSyncing, setIsSyncing] = useState(false);
  const isSyncingRef = useRef(false);
  const pollingTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    if (!loading && !user) {
      router.push('/login');
    }
  }, [user, loading, router]);

  // 자동 채점 시각화 효과 및 폴링 로직
  const triggerSyncVisual = async () => {
    if (isSyncingRef.current || !problem) {
      return;
    }
    
    isSyncingRef.current = true;
    setIsSyncing(true);
    console.log(">>> AUTO-SYNC PROCESS STARTED <<<");
    
    let attempts = 0;
    const maxAttempts = 12; // 1분간 (5초 * 12회)
    const currentProblemId = problem.id;

    const performPoll = async () => {
      attempts++;
      console.log(`[Polling #${attempts}] Checking problem: ${currentProblemId}`);
      
      try {
        const res = await api.get(`/submissions/problem/${currentProblemId}?t=${Date.now()}`);
        if (res.data && res.data.length > 0) {
          console.log(">> SUCCESS: Solve detected!");
          setSubmitSuccess(true);
          refreshUser();
          finishSync();
          return;
        }
      } catch (e) {
        console.error("Polling API Error:", e);
      }
      
      if (attempts >= maxAttempts) {
        console.log(">> TIMEOUT: Stop polling.");
        finishSync();
        return;
      }
      
      pollingTimeoutRef.current = setTimeout(performPoll, 5000);
    };

    const finishSync = () => {
      setIsSyncing(false);
      isSyncingRef.current = false;
      if (pollingTimeoutRef.current) {
        clearTimeout(pollingTimeoutRef.current);
        pollingTimeoutRef.current = null;
      }
      console.log(">>> AUTO-SYNC PROCESS FINISHED <<<");
    };

    performPoll();
  };

  // 타이머 로직
  useEffect(() => {
    if (user?.is_pro && !submitSuccess) {
      const updateTimer = () => {
        const now = new Date();
        const secondsSinceEpoch = Math.floor(now.getTime() / 1000);
        const cycleSeconds = 300; 
        const remaining = cycleSeconds - (secondsSinceEpoch % cycleSeconds);
        
        if (remaining >= 299 && remaining <= 300) {
          if (!isSyncingRef.current) {
            console.log("TIMER MATCH: Launching sync at", remaining);
            triggerSyncVisual();
          }
        }
        
        if (remaining < 290 && isSyncingRef.current && !pollingTimeoutRef.current) {
          isSyncingRef.current = false;
          setIsSyncing(false);
        }

        setNextSyncIn(remaining);
      };

      const interval = setInterval(updateTimer, 1000);
      updateTimer();
      return () => clearInterval(interval);
    }
  }, [user?.is_pro, submitSuccess, problem]); 

  const fetchTodayProblem = async () => {
    try {
      setIsLoading(true);
      const response = await api.get('/daily-problems/today');
      setProblem(response.data);
      
      const res = await api.get(`/submissions/problem/${response.data.id}`);
      if (res.data && res.data.length > 0) {
        setSubmitSuccess(true);
      }
    } catch (err: any) {
      setError(err.response?.status === 404 ? '오늘의 문제가 아직 선정되지 않았습니다.' : '문제 정보를 가져오는데 실패했습니다.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (user) {
      fetchTodayProblem();
    }
  }, [user]);

  const handleRegisterSubmission = async () => {
    if (!problem) return;
    setIsLoadingSubmitting(true);
    setError('');
    
    try {
      await api.post('/submissions/register', { daily_problem_id: problem.id });
      setSubmitSuccess(true);
      refreshUser();
    } catch (err: any) {
      const detail = err.response?.data?.detail || '';
      if (detail.includes('already been registered') || detail.includes('UniqueViolation')) {
        setSubmitSuccess(true);
        refreshUser();
      } else {
        setError(detail || '제출 결과 확인에 실패했습니다.');
      }
    } finally {
      setIsLoadingSubmitting(false);
    }
  };

  if (loading || isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="animate-pulse text-blue-600 font-bold">오늘의 문제 가져오는 중...</div>
      </div>
    );
  }

  if (error && !problem) {
    return (
      <div className="max-w-3xl mx-auto px-4 py-20 text-center">
        <AlertCircle size={64} className="mx-auto text-gray-300 mb-6" />
        <h1 className="text-2xl font-bold text-gray-900 mb-2">{error}</h1>
        <p className="text-gray-500 mb-8">관리자에게 문의하거나 잠시 후 다시 시도해주세요.</p>
        <Link href="/dashboard" className="text-blue-600 font-bold hover:underline">대시보드로 돌아가기</Link>
      </div>
    );
  }

  if (!problem) return null;

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 mb-8">
        <div className="flex items-center gap-4">
          <div className="w-12 h-12 bg-blue-600 rounded-xl flex items-center justify-center text-white shadow-lg">
            <BookOpen size={24} />
          </div>
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="px-2 py-0.5 bg-blue-50 text-blue-700 text-xs font-bold rounded uppercase">Today</span>
              <span className="text-sm font-bold text-gray-400">#{problem.baekjoon_problem_id}</span>
            </div>
            <h1 className="text-3xl font-black text-gray-900 tracking-tight">{problem.title}</h1>
          </div>
        </div>

        <div className="flex flex-wrap gap-3">
          <a href={`https://www.acmicpc.net/problem/${problem.baekjoon_problem_id}`} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-2 bg-gray-900 text-white px-6 py-3 rounded-xl font-bold">
            백준에서 풀기 <ExternalLink size={18} />
          </a>
          <Link href={`/problems/${problem.id}/posts`} className="inline-flex items-center gap-2 bg-white text-gray-700 border border-gray-200 px-6 py-3 rounded-xl font-bold">
            토론 게시판 <MessageSquare size={18} />
          </Link>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div className="lg:col-span-2 space-y-8">
          <div className="bg-white p-8 rounded-3xl shadow-sm border border-gray-100">
            <h2 className="text-xl font-bold text-gray-900 mb-6 border-b border-gray-50 pb-4">문제 설명</h2>
            <div className="prose prose-blue max-w-none text-gray-700 leading-relaxed overflow-x-auto" dangerouslySetInnerHTML={{ __html: problem.description }} />
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-100">
              <h3 className="font-bold text-gray-900 mb-4">입력 예시</h3>
              <pre className="bg-gray-50 p-4 rounded-xl text-sm font-mono text-gray-700 whitespace-pre-wrap">{problem.input_example}</pre>
            </div>
            <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-100">
              <h3 className="font-bold text-gray-900 mb-4">출력 예시</h3>
              <pre className="bg-gray-50 p-4 rounded-xl text-sm font-mono text-gray-700 whitespace-pre-wrap">{problem.output_example}</pre>
            </div>
          </div>
        </div>

        <div className="space-y-6">
          <div className="bg-white p-6 rounded-3xl shadow-sm border border-gray-100">
            <h2 className="font-bold text-gray-900 mb-6">문제 정보</h2>
            <div className="space-y-4">
              <div><p className="text-xs font-bold text-gray-400 uppercase mb-1">난이도</p><p className="font-bold text-blue-600">{problem.difficulty_level}</p></div>
              <div><p className="text-xs font-bold text-gray-400 uppercase mb-1">알고리즘 유형</p>
                <div className="flex flex-wrap gap-2 mt-1">
                  {problem.algorithm_type.map((type, idx) => (<span key={idx} className="px-2 py-1 bg-gray-100 text-gray-600 text-xs font-medium rounded-lg">{type}</span>))}
                </div>
              </div>
            </div>
          </div>

          <div className="bg-white p-6 rounded-3xl shadow-sm border border-gray-100 ring-4 ring-blue-50 relative overflow-hidden">
            <h2 className="font-bold text-gray-900 mb-4">해결 확인</h2>
            <p className="text-sm text-gray-500 mb-6">정답을 맞추셨나요? 아래 버튼을 눌러 제출 기록을 플랫폼에 등록하세요.</p>
            
            {submitSuccess ? (
              <div className="bg-green-50 text-green-700 p-6 rounded-2xl flex flex-col items-center text-center gap-3">
                <CheckCircle2 size={32} />
                <p className="font-black uppercase tracking-tight text-lg">해결 완료!</p>
              </div>
            ) : (
              <>
                {error && <div className="mb-4 p-3 bg-red-50 text-red-600 text-xs rounded-xl flex items-start gap-2"><AlertCircle size={16} /><span>{error}</span></div>}
                <button onClick={handleRegisterSubmission} disabled={isSubmitting} className="w-full bg-blue-600 text-white font-bold py-4 rounded-2xl shadow-lg flex items-center justify-center gap-2 active:scale-95 disabled:opacity-70">
                  {isSubmitting ? <Loader2 className="animate-spin" size={20} /> : <>풀이 결과 등록하기 <Send size={18} /></>}
                </button>

                {user?.is_pro && (
                  <div className="mt-6 pt-6 border-t border-gray-50">
                    <div className="bg-amber-50 rounded-2xl p-4 border border-amber-100">
                      <div className="flex items-center justify-between mb-3">
                        <div className="flex items-center gap-2 text-amber-700">
                          <Crown size={16} className="fill-amber-500" />
                          <span className="text-xs font-black uppercase italic tracking-tighter">Auto Sync</span>
                        </div>
                        {isSyncing ? (
                          <div className="flex items-center gap-1.5 text-amber-600 text-[10px] font-bold"><RefreshCw size={12} className="animate-spin" />채점 확인 중...</div>
                        ) : (
                          <div className="text-[10px] font-black text-amber-500 bg-white px-2 py-0.5 rounded-full border border-amber-100">PRO</div>
                        )}
                      </div>
                      <div className="flex items-center justify-between">
                        <p className="text-[11px] font-bold text-amber-600/70">다음 자동 채점까지</p>
                        <div className="flex items-center gap-2">
                          <Clock size={14} className="text-amber-400" />
                          <span className="text-xl font-black font-mono text-amber-700 tabular-nums">
                            {Math.floor(nextSyncIn / 60)}:{(nextSyncIn % 60).toString().padStart(2, '0')}
                          </span>
                        </div>
                      </div>
                      <div className="mt-3 w-full h-1.5 bg-amber-100 rounded-full overflow-hidden">
                        <div className="h-full bg-amber-400 transition-all duration-1000 ease-linear" style={{ width: `${(nextSyncIn / 300) * 100}%` }} />
                      </div>
                    </div>
                  </div>
                )}
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
