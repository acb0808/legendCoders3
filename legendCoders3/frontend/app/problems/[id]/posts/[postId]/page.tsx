'use client';

import React, { useEffect, useState, use, useMemo } from 'react';
import { useAuth } from '@/components/auth-provider';
import { useRouter } from 'next/navigation';
import api from '@/lib/api';
import DOMPurify from 'isomorphic-dompurify';
import { 
  ChevronLeft, 
  User, 
  Clock, 
  ThumbsUp, 
  MessageSquare, 
  Send, 
  Loader2,
  Trash2,
  CornerDownRight,
  X
} from 'lucide-react';
import Link from 'next/link';

interface Comment {
  id: string;
  user_id: string;
  content: string;
  nickname: string;
  created_at: string;
  parent_comment_id?: string;
}

interface Post {
  id: string;
  user_id: string;
  title: string;
  content: string;
  tags: string[] | null;
  view_count: number;
  like_count: number;
  created_at: string;
  nickname: string;
  comments: Comment[];
}

export default function PostDetailPage({ params }: { params: Promise<{ id: string, postId: string }> }) {
  const { id: problemId, postId } = use(params);
  const { user, loading } = useAuth();
  const router = useRouter();
  
  const [post, setPost] = useState<Post | null>(null);
  const [commentContent, setCommentContent] = useState('');
  const [replyTo, setReplyTo] = useState<Comment | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  // XSS 방지를 위한 본문 새니타이징
  const sanitizedPostContent = useMemo(() => 
    DOMPurify.sanitize(post?.content || ''), [post?.content]
  );

  const fetchPost = async () => {
    try {
      const response = await api.get(`/posts/${postId}?t=${Date.now()}`);
      setPost(response.data);
    } catch (error) {
      console.error('Failed to fetch post:', error);
      router.push(`/problems/${problemId}/posts`);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (!loading && !user) {
      router.push('/login');
    }
  }, [user, loading, router]);

  useEffect(() => {
    if (user) {
      fetchPost();
    }
  }, [user, postId]);

  const handleCommentSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!commentContent.trim()) return;
    
    setIsSubmitting(true);
    try {
      await api.post('/comments/', {
        post_id: postId,
        content: commentContent,
        parent_comment_id: replyTo?.id || null
      });
      setCommentContent('');
      setReplyTo(null);
      await fetchPost();
    } catch (error) {
      console.error('Failed to submit comment:', error);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDeletePost = async () => {
    if (!window.confirm('정말 이 게시글을 삭제하시겠습니까?')) return;
    try {
      await api.delete(`/posts/${postId}`);
      router.push(`/problems/${problemId}/posts`);
    } catch (error) {
      alert('게시글 삭제에 실패했습니다.');
    }
  };

  const handleDeleteComment = async (commentId: string) => {
    if (!window.confirm('댓글을 삭제하시겠습니까?')) return;
    try {
      await api.delete(`/comments/${commentId}`);
      await fetchPost();
    } catch (error) {
      alert('댓글 삭제에 실패했습니다.');
    }
  };

  const renderComments = () => {
    if (!post) return null;
    
    const parentComments = post.comments.filter(c => !c.parent_comment_id);
    const childComments = post.comments.filter(c => c.parent_comment_id);

    return parentComments.map(parent => (
      <div key={parent.id} className="space-y-4">
        <div className="bg-white p-6 rounded-[1.5rem] border border-gray-100 shadow-sm transition-all hover:shadow-md">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 bg-gray-100 rounded-full flex items-center justify-center font-bold text-gray-500 text-xs uppercase">
                {parent.nickname.charAt(0)}
              </div>
              <span className="font-bold text-gray-900 text-sm">{parent.nickname}</span>
              <span className="text-[10px] font-bold text-gray-300 uppercase tracking-widest ml-2">
                {new Date(parent.created_at).toLocaleDateString()}
              </span>
            </div>
            <div className="flex items-center gap-2">
              <button 
                onClick={() => {
                  setReplyTo(parent);
                  window.scrollTo({ top: document.getElementById('comment-form')?.offsetTop ? document.getElementById('comment-form')!.offsetTop - 100 : 0, behavior: 'smooth' });
                }}
                className="text-xs font-bold text-blue-500 hover:text-blue-700"
              >
                답글
              </button>
              {(user?.id === parent.user_id || user?.is_admin) && (
                <button onClick={() => handleDeleteComment(parent.id)} className="text-gray-300 hover:text-red-500">
                  <Trash2 size={14} />
                </button>
              )}
            </div>
          </div>
          <div 
            className="text-gray-600 text-sm font-medium leading-relaxed whitespace-pre-wrap"
            dangerouslySetInnerHTML={{ __html: DOMPurify.sanitize(parent.content) }}
          />
        </div>

        {childComments.filter(child => child.parent_comment_id === parent.id).map(child => (
          <div key={child.id} className="ml-10 flex gap-3">
            <CornerDownRight className="text-gray-200 mt-2 shrink-0" size={20} />
            <div className="flex-grow bg-gray-50/50 p-5 rounded-[1.5rem] border border-gray-100 shadow-sm">
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <div className="w-6 h-6 bg-white rounded-full flex items-center justify-center font-bold text-gray-400 text-[10px] uppercase border border-gray-100">
                    {child.nickname.charAt(0)}
                  </div>
                  <span className="font-bold text-gray-800 text-xs">{child.nickname}</span>
                  <span className="text-[9px] font-bold text-gray-300 uppercase tracking-widest ml-1">
                    {new Date(child.created_at).toLocaleDateString()}
                  </span>
                </div>
                {(user?.id === child.user_id || user?.is_admin) && (
                  <button onClick={() => handleDeleteComment(child.id)} className="text-gray-300 hover:text-red-500">
                    <Trash2 size={12} />
                  </button>
                )}
              </div>
              <div 
                className="text-gray-600 text-sm font-medium whitespace-pre-wrap"
                dangerouslySetInnerHTML={{ __html: DOMPurify.sanitize(child.content) }}
              />
            </div>
          </div>
        ))}
      </div>
    ));
  };

  if (loading || isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="animate-pulse text-blue-600 font-bold">게시글 읽어오는 중...</div>
      </div>
    );
  }

  if (!post) return null;

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
      <Link 
        href={`/problems/${problemId}/posts`} 
        className="inline-flex items-center text-sm font-bold text-gray-400 hover:text-blue-600 transition-colors mb-8 group"
      >
        <ChevronLeft size={16} className="group-hover:-translate-x-1 transition-transform" />
        목록으로 돌아가기
      </Link>

      <article className="bg-white rounded-[2rem] shadow-sm border border-gray-100 overflow-hidden mb-10">
        <header className="p-10 border-b border-gray-50 bg-gray-50/30">
          <div className="flex flex-wrap items-center gap-4 mb-6">
            <div className="flex items-center gap-2 px-3 py-1.5 bg-blue-600 text-white rounded-xl text-xs font-black uppercase tracking-wider">
              <User size={14} />
              {post.nickname}
            </div>
            <div className="flex items-center gap-2 text-gray-400 text-xs font-bold uppercase tracking-wider">
              <Clock size={14} />
              {new Date(post.created_at).toLocaleString()}
            </div>
            {(user?.id === post.user_id || user?.is_admin) && (
              <button 
                onClick={handleDeletePost}
                className="ml-auto flex items-center gap-1.5 text-red-400 hover:text-red-600 text-xs font-bold transition-colors"
              >
                <Trash2 size={14} />
                삭제
              </button>
            )}
          </div>
          
          <h1 className="text-4xl font-black text-gray-900 tracking-tight leading-tight">
            {post.title}
          </h1>
          
          <div className="flex flex-wrap gap-2 mt-6">
            {post.tags?.map((tag, idx) => (
              <span key={idx} className="text-xs font-bold text-blue-500 bg-blue-50 px-3 py-1 rounded-full">
                #{tag}
              </span>
            ))}
          </div>
        </header>

        <div 
          className="p-10 text-gray-700 leading-relaxed text-lg whitespace-pre-wrap font-medium"
          dangerouslySetInnerHTML={{ __html: sanitizedPostContent }}
        />

        <footer className="px-10 py-6 bg-gray-50/50 flex items-center gap-6 border-t border-gray-50">
          <div className="flex items-center gap-2 text-gray-500">
            <ThumbsUp size={20} className="hover:text-blue-600 cursor-pointer transition-colors" />
            <span className="font-bold">{post.like_count}</span>
          </div>
          <div className="flex items-center gap-2 text-blue-600">
            <MessageSquare size={20} />
            <span className="font-bold">{post.comments.length} Comments</span>
          </div>
        </footer>
      </article>

      <section className="space-y-8 pb-20">
        <h2 className="text-2xl font-black text-gray-900 px-2 tracking-tight uppercase">Discussion</h2>
        
        <div id="comment-form" className="relative group">
          {replyTo && (
            <div className="absolute -top-10 left-0 right-0 flex items-center justify-between bg-blue-50 px-4 py-2 rounded-t-2xl text-xs font-bold text-blue-600 border-x border-t border-blue-100">
              <div className="flex items-center gap-2">
                <CornerDownRight size={14} />
                <span>{replyTo.nickname}님에게 답글 남기는 중...</span>
              </div>
              <button onClick={() => setReplyTo(null)} className="hover:text-blue-800">
                <X size={14} />
              </button>
            </div>
          )}
          <form onSubmit={handleCommentSubmit}>
            <textarea
              value={commentContent}
              onChange={(e) => setCommentContent(e.target.value)}
              placeholder={replyTo ? "답글을 입력하세요..." : "생각을 공유해주세요..."}
              className={`w-full min-h-[120px] p-6 bg-white border border-gray-200 focus:border-blue-500 focus:ring-4 focus:ring-blue-50 focus:outline-none transition-all font-medium text-gray-700 shadow-sm ${replyTo ? 'rounded-b-3xl rounded-tr-3xl' : 'rounded-3xl'}`}
            />
            <button
              type="submit"
              disabled={isSubmitting || !commentContent.trim()}
              className="absolute bottom-4 right-4 bg-blue-600 text-white p-3 rounded-2xl hover:bg-blue-700 transition-all shadow-lg shadow-blue-100 disabled:opacity-50 active:scale-95"
            >
              {isSubmitting ? <Loader2 className="animate-spin" size={20} /> : <Send size={20} />}
            </button>
          </form>
        </div>

        <div className="space-y-8">
          {post.comments.length > 0 ? (
            renderComments()
          ) : (
            <div className="text-center py-10 text-gray-400 font-medium italic">
              첫 번째 의견을 남겨주세요!
            </div>
          )}
        </div>
      </section>
    </div>
  );
}
