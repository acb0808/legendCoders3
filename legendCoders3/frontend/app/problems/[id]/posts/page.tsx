'use client';

import React, { useEffect, useState, use } from 'react';
import { useAuth } from '@/components/auth-provider';
import { useRouter } from 'next/navigation';
import api from '@/lib/api';
import { 
  MessageSquare, 
  Plus, 
  ChevronLeft, 
  User, 
  Clock, 
  Eye, 
  ThumbsUp, 
  Tag as TagIcon,
  Search,
  Filter
} from 'lucide-react';
import Link from 'next/link';
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

interface Post {
  id: string;
  title: string;
  content: string;
  tags: string[] | null;
  view_count: number;
  like_count: number;
  created_at: string;
  nickname: string;
}

export default function ProblemPostsPage({ params }: { params: Promise<{ id: string }> }) {
  const { id: problemId } = use(params);
  const { user, loading } = useAuth();
  const router = useRouter();
  
  const [posts, setPosts] = useState<Post[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [problemTitle, setProblemTitle] = useState('문제 토론');

  useEffect(() => {
    if (!loading && !user) {
      router.push('/login');
    }
  }, [user, loading, router]);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [postsRes, problemRes] = await Promise.all([
          api.get(`/posts/problem/${problemId}`),
          api.get(`/daily-problems/${problemId}`) // UUID로 조회하는 엔드포인트가 있다고 가정
        ]);
        setPosts(postsRes.data);
        setProblemTitle(problemRes.data.title);
      } catch (error) {
        console.error('Failed to fetch posts:', error);
        // 만약 UUID로 문제 조회가 안되면 그냥 기본 타이틀 유지
      } finally {
        setIsLoading(false);
      }
    };

    if (user) {
      fetchData();
    }
  }, [user, problemId]);

  if (loading || isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="animate-pulse text-blue-600 font-bold">토론 목록을 가져오는 중...</div>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
      {/* Header Section */}
      <div className="mb-10">
        <Link 
          href="/problems/today" 
          className="inline-flex items-center text-sm font-bold text-gray-400 hover:text-blue-600 transition-colors mb-4 group"
        >
          <ChevronLeft size={16} className="group-hover:-translate-x-1 transition-transform" />
          문제로 돌아가기
        </Link>
        
        <div className="flex flex-col md:flex-row md:items-end justify-between gap-6">
          <div>
            <div className="flex items-center gap-2 mb-2">
              <span className="w-2 h-2 bg-blue-600 rounded-full animate-pulse" />
              <span className="text-xs font-black text-blue-600 uppercase tracking-widest">Community</span>
            </div>
            <h1 className="text-4xl font-black text-gray-900 tracking-tight">
              {problemTitle} <span className="text-gray-300 ml-2">Discussion</span>
            </h1>
          </div>
          
          <Link
            href={`/problems/${problemId}/posts/new`}
            className="inline-flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white px-6 py-3.5 rounded-2xl font-bold transition-all shadow-lg shadow-blue-100 active:scale-95"
          >
            <Plus size={20} />
            새 게시글 작성
          </Link>
        </div>
      </div>

      {/* Toolbar */}
      <div className="flex flex-wrap items-center justify-between gap-4 mb-8 bg-white p-4 rounded-2xl border border-gray-100 shadow-sm">
        <div className="flex items-center gap-2 bg-gray-50 px-4 py-2 rounded-xl border border-gray-100 w-full md:w-80">
          <Search size={18} className="text-gray-400" />
          <input 
            type="text" 
            placeholder="제목이나 내용 검색..." 
            className="bg-transparent border-none focus:outline-none text-sm w-full"
          />
        </div>
        
        <div className="flex items-center gap-2">
          <button className="flex items-center gap-2 px-4 py-2 text-sm font-bold text-gray-500 hover:bg-gray-50 rounded-xl transition-all">
            <Filter size={18} />
            필터
          </button>
          <select className="bg-transparent text-sm font-bold text-gray-700 focus:outline-none cursor-pointer p-2">
            <option>최신순</option>
            <option>인기순</option>
            <option>댓글순</option>
          </select>
        </div>
      </div>

      {/* Posts List */}
      <div className="grid grid-cols-1 gap-4">
        {posts.length > 0 ? (
          posts.map((post) => (
            <Link 
              key={post.id} 
              href={`/problems/${problemId}/posts/${post.id}`}
              className="group bg-white p-6 rounded-3xl border border-gray-100 shadow-sm hover:shadow-xl hover:shadow-blue-50 transition-all flex flex-col md:flex-row md:items-center justify-between gap-6"
            >
              <div className="flex-grow">
                <div className="flex items-center gap-3 mb-3">
                  <div className="flex items-center gap-1.5 px-2.5 py-1 bg-gray-50 text-gray-500 rounded-lg text-[10px] font-black uppercase tracking-wider">
                    <User size={12} />
                    {post.nickname}
                  </div>
                  <div className="flex items-center gap-1.5 text-gray-400 text-[10px] font-bold uppercase tracking-wider">
                    <Clock size={12} />
                    {new Date(post.created_at).toLocaleDateString()}
                  </div>
                </div>
                
                <h2 className="text-xl font-bold text-gray-900 group-hover:text-blue-600 transition-colors mb-2">
                  {post.title}
                </h2>
                
                <div className="flex flex-wrap gap-2">
                  {post.tags?.map((tag, idx) => (
                    <span key={idx} className="text-[10px] font-bold text-blue-500 bg-blue-50 px-2 py-0.5 rounded">
                      #{tag}
                    </span>
                  ))}
                </div>
              </div>
              
              <div className="flex items-center gap-6 shrink-0 border-t md:border-t-0 md:border-l border-gray-50 pt-4 md:pt-0 md:pl-8">
                <div className="flex flex-col items-center gap-1 text-gray-400">
                  <Eye size={18} />
                  <span className="text-xs font-bold">{post.view_count}</span>
                </div>
                <div className="flex flex-col items-center gap-1 text-gray-400">
                  <ThumbsUp size={18} />
                  <span className="text-xs font-bold">{post.like_count}</span>
                </div>
                <div className="flex flex-col items-center gap-1 text-blue-500">
                  <MessageSquare size={18} />
                  <span className="text-xs font-bold">0</span> {/* 댓글 수는 나중에 추가 */}
                </div>
              </div>
            </Link>
          ))
        ) : (
          <div className="text-center py-32 bg-white rounded-3xl border border-dashed border-gray-200">
            <MessageSquare size={48} className="mx-auto text-gray-200 mb-4" />
            <h3 className="text-lg font-bold text-gray-400">아직 등록된 게시글이 없습니다.</h3>
            <p className="text-sm text-gray-300 mt-1">첫 번째 질문이나 풀이를 공유해보세요!</p>
          </div>
        )}
      </div>
    </div>
  );
}
