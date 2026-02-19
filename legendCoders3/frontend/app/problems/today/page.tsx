'use client';

import React, { useEffect, useState } from 'react';
import { useAuth } from '@/components/auth-provider';
import { useRouter } from 'next/navigation';
import api from '@/lib/api';
import { BookOpen, ExternalLink, Send, CheckCircle2, AlertCircle, Loader2, MessageSquare } from 'lucide-react';
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
  const { user, loading } = useAuth();
  const router = useRouter();
  const [problem, setProblem] = useState<Problem | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [submitSuccess, setSubmitSuccess] = useState(false);

  useEffect(() => {
    if (!loading && !user) {
      router.push('/login');
    }
  }, [user, loading, router]);

  const fetchTodayProblem = async () => {
    try {
      setIsLoading(true);
      const response = await api.get('/daily-problems/today');
      setProblem(response.data);
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
    setIsSubmitting(true);
    setError('');
    setSubmitSuccess(false);

    try {
      // baekjoon_submission_id를 비워두면 자동으로 크롤링함
      const response = await api.post('/submissions/register', {
        daily_problem_id: problem.id
      });
      setSubmitSuccess(true);
    } catch (err: any) {
      setError(err.response?.data?.detail || '제출 결과 확인에 실패했습니다. 백준에서 문제를 먼저 해결했는지 확인해주세요.');
    } finally {
      setIsSubmitting(false);
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
          <div className="w-12 h-12 bg-blue-600 rounded-xl flex items-center justify-center text-white shadow-lg shadow-blue-100">
            <BookOpen size={24} />
          </div>
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="px-2 py-0.5 bg-blue-50 text-blue-700 text-xs font-bold rounded uppercase tracking-wider">
                Today
              </span>
              <span className="text-sm font-bold text-gray-400">#{problem.baekjoon_problem_id}</span>
            </div>
            <h1 className="text-3xl font-black text-gray-900 tracking-tight">{problem.title}</h1>
          </div>
        </div>

        <div className="flex flex-wrap gap-3">
          <a
            href={`https://www.acmicpc.net/problem/${problem.baekjoon_problem_id}`}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-2 bg-gray-900 text-white px-6 py-3 rounded-xl font-bold hover:bg-gray-800 transition-all active:scale-95"
          >
            백준에서 풀기 <ExternalLink size={18} />
          </a>
          <Link
            href={`/problems/${problem.id}/posts`}
            className="inline-flex items-center gap-2 bg-white text-gray-700 border border-gray-200 px-6 py-3 rounded-xl font-bold hover:bg-gray-50 transition-all active:scale-95"
          >
            토론 게시판 <MessageSquare size={18} />
          </Link>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div className="lg:col-span-2 space-y-8">
          {/* 문제 설명 */}
          <div className="bg-white p-8 rounded-3xl shadow-sm border border-gray-100">
            <h2 className="text-xl font-bold text-gray-900 mb-6 border-b border-gray-50 pb-4">문제 설명</h2>
            <div 
              className="prose prose-blue max-w-none text-gray-700 leading-relaxed overflow-x-auto"
              dangerouslySetInnerHTML={{ __html: problem.description }}
            />
          </div>

          {/* 입출력 예시 */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-100">
              <h3 className="font-bold text-gray-900 mb-4">입력 예시</h3>
              <pre className="bg-gray-50 p-4 rounded-xl text-sm font-mono text-gray-700 overflow-x-auto whitespace-pre-wrap">
                {problem.input_example}
              </pre>
            </div>
            <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-100">
              <h3 className="font-bold text-gray-900 mb-4">출력 예시</h3>
              <pre className="bg-gray-50 p-4 rounded-xl text-sm font-mono text-gray-700 overflow-x-auto whitespace-pre-wrap">
                {problem.output_example}
              </pre>
            </div>
          </div>
        </div>

        <div className="space-y-6">
          {/* 문제 정보 사이드바 */}
          <div className="bg-white p-6 rounded-3xl shadow-sm border border-gray-100">
            <h2 className="font-bold text-gray-900 mb-6">문제 정보</h2>
            <div className="space-y-4">
              <div>
                <p className="text-xs font-bold text-gray-400 uppercase mb-1">난이도</p>
                <p className="font-bold text-blue-600">{problem.difficulty_level}</p>
              </div>
              <div>
                <p className="text-xs font-bold text-gray-400 uppercase mb-1">알고리즘 유형</p>
                <div className="flex flex-wrap gap-2 mt-1">
                  {problem.algorithm_type.map((type, idx) => (
                    <span key={idx} className="px-2 py-1 bg-gray-100 text-gray-600 text-xs font-medium rounded-lg">
                      {type}
                    </span>
                  ))}
                </div>
              </div>
            </div>
          </div>

          {/* 제출 등록 섹션 */}
          <div className="bg-white p-6 rounded-3xl shadow-sm border border-gray-100 ring-4 ring-blue-50">
            <h2 className="font-bold text-gray-900 mb-4">해결 확인</h2>
            <p className="text-sm text-gray-500 mb-6">백준에서 정답을 맞추셨나요? 아래 버튼을 눌러 제출 기록을 플랫폼에 등록하세요.</p>
            
            {submitSuccess ? (
              <div className="bg-green-50 text-green-700 p-4 rounded-2xl flex flex-col items-center text-center gap-2">
                <CheckCircle2 size={32} />
                <p className="font-bold uppercase tracking-tight">해결 완료!</p>
                <p className="text-xs">오늘의 문제를 성공적으로 기록했습니다.</p>
              </div>
            ) : (
              <>
                {error && (
                  <div className="mb-4 p-3 bg-red-50 text-red-600 text-xs rounded-xl flex items-start gap-2">
                    <AlertCircle size={16} className="shrink-0 mt-0.5" />
                    <span>{error}</span>
                  </div>
                )}
                <button
                  onClick={handleRegisterSubmission}
                  disabled={isSubmitting}
                  className="w-full bg-blue-600 hover:bg-blue-700 text-white font-bold py-4 rounded-2xl transition-all shadow-lg shadow-blue-100 flex items-center justify-center gap-2 active:scale-95 disabled:opacity-70 disabled:active:scale-100"
                >
                  {isSubmitting ? (
                    <Loader2 className="animate-spin" size={20} />
                  ) : (
                    <>
                      내 결과 등록하기 <Send size={18} />
                    </>
                  )}
                </button>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
