'use client';

import React, { useState, use } from 'react';
import { useAuth } from '@/components/auth-provider';
import { useRouter } from 'next/navigation';
import api from '@/lib/api';
import { ChevronLeft, Send, Loader2, Tag as TagIcon, X } from 'lucide-react';
import Link from 'next/link';

export default function NewPostPage({ params }: { params: Promise<{ id: string }> }) {
  const { id: problemId } = use(params);
  const { user, loading } = useAuth();
  const router = useRouter();
  
  const [title, setTitle] = useState('');
  const [content, setContent] = useState('');
  const [tagInput, setTagInput] = useState('');
  const [tags, setTags] = useState<string[]>([]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState('');

  const handleAddTag = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && tagInput.trim()) {
      e.preventDefault();
      if (!tags.includes(tagInput.trim())) {
        setTags([...tags, tagInput.trim()]);
      }
      setTagInput('');
    }
  };

  const removeTag = (index: number) => {
    setTags(tags.filter((_, i) => i !== index));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim() || !content.trim()) return;
    
    setIsSubmitting(true);
    setError('');

    try {
      await api.post('/posts/', {
        daily_problem_id: problemId,
        title,
        content,
        tags
      });
      router.push(`/problems/${problemId}/posts`);
    } catch (err: any) {
      setError(err.response?.data?.detail || '게시글 저장에 실패했습니다.');
      setIsSubmitting(false);
    }
  };

  if (loading) return null;

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
      <Link 
        href={`/problems/${problemId}/posts`} 
        className="inline-flex items-center text-sm font-bold text-gray-400 hover:text-blue-600 transition-colors mb-8 group"
      >
        <ChevronLeft size={16} className="group-hover:-translate-x-1 transition-transform" />
        목록으로 돌아가기
      </Link>

      <div className="bg-white rounded-3xl shadow-xl border border-gray-100 overflow-hidden">
        <div className="bg-gray-900 px-8 py-6 text-white">
          <h1 className="text-2xl font-black tracking-tight uppercase">New Post</h1>
          <p className="text-gray-400 text-sm mt-1">질문이나 풀이 아이디어를 자유롭게 공유하세요.</p>
        </div>

        <form onSubmit={handleSubmit} className="p-8 space-y-6">
          {error && (
            <div className="p-4 bg-red-50 text-red-600 text-sm rounded-2xl border border-red-100 font-medium">
              {error}
            </div>
          )}

          <div className="space-y-2">
            <label className="text-xs font-black text-gray-400 uppercase tracking-widest ml-1">Title</label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className="w-full px-6 py-4 rounded-2xl bg-gray-50 border border-transparent focus:bg-white focus:border-blue-500 focus:ring-4 focus:ring-blue-50 focus:outline-none transition-all text-xl font-bold placeholder:text-gray-300"
              placeholder="게시글 제목을 입력하세요"
              required
            />
          </div>

          <div className="space-y-2">
            <label className="text-xs font-black text-gray-400 uppercase tracking-widest ml-1">Tags</label>
            <div className="flex flex-wrap gap-2 p-2 bg-gray-50 rounded-2xl border border-transparent focus-within:bg-white focus-within:border-blue-500 focus-within:ring-4 focus-within:ring-blue-50 transition-all">
              {tags.map((tag, idx) => (
                <span key={idx} className="inline-flex items-center gap-1 px-3 py-1 bg-blue-100 text-blue-700 text-sm font-bold rounded-xl">
                  #{tag}
                  <button type="button" onClick={() => removeTag(idx)} className="hover:text-blue-900">
                    <X size={14} />
                  </button>
                </span>
              ))}
              <input
                type="text"
                value={tagInput}
                onChange={(e) => setTagInput(e.target.value)}
                onKeyDown={handleAddTag}
                className="flex-grow bg-transparent px-3 py-2 text-sm font-medium focus:outline-none placeholder:text-gray-400"
                placeholder={tags.length === 0 ? "태그 입력 후 Enter (예: DP, BFS)" : ""}
              />
            </div>
          </div>

          <div className="space-y-2">
            <label className="text-xs font-black text-gray-400 uppercase tracking-widest ml-1">Content</label>
            <textarea
              value={content}
              onChange={(e) => setContent(e.target.value)}
              className="w-full min-h-[400px] px-6 py-4 rounded-2xl bg-gray-50 border border-transparent focus:bg-white focus:border-blue-500 focus:ring-4 focus:ring-blue-50 focus:outline-none transition-all text-gray-700 leading-relaxed font-medium placeholder:text-gray-300 resize-none"
              placeholder="내용을 작성하세요. 풀이 방식이나 궁금한 점을 상세히 적어주시면 좋습니다."
              required
            />
          </div>

          <div className="pt-4 border-t border-gray-50 flex justify-end">
            <button
              type="submit"
              disabled={isSubmitting}
              className="inline-flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white px-10 py-4 rounded-2xl font-black uppercase tracking-tighter transition-all shadow-xl shadow-blue-100 active:scale-95 disabled:opacity-70 disabled:active:scale-100"
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="animate-spin" size={20} />
                  Posting...
                </>
              ) : (
                <>
                  Submit Post <Send size={20} />
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
