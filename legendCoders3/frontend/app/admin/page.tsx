'use client';

import React, { useEffect, useState } from 'react';
import { useAuth } from '@/components/auth-provider';
import { useRouter } from 'next/navigation';
import api from '@/lib/api';
import { 
  Users, 
  Settings, 
  Trash2, 
  Plus, 
  Calendar, 
  Loader2, 
  CheckCircle2,
  BookOpen,
  Edit2,
  RefreshCw,
  X,
  Save,
  Hash,
  Award,
  Sparkles,
  User,
  Snowflake,
  Ticket,
  Copy,
  ExternalLink
} from 'lucide-react';
import TitleBadge from '@/components/title-badge';

export default function AdminPage() {
  const { user, loading, refreshUser } = useAuth();
  const router = useRouter();
  
  const [activeTab, setActiveTab] = useState<'users' | 'problems' | 'titles' | 'invitations'>('users');
  const [usersList, setUsersList] = useState<any[]>([]);
  const [problemsList, setProblemsList] = useState<any[]>([]);
  const [allTitles, setAllTitles] = useState<any[]>([]);
  const [invitationsList, setInvitationsList] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isActionLoading, setIsActionLoading] = useState(false);
  const [message, setMessage] = useState('');
  
  // Create Problem State
  const [seedDate, setSeedDate] = useState(new Date().toISOString().split('T')[0]);
  const [forceProblemId, setForceProblemId] = useState('');

  // Create Title State
  const [newTitleData, setNewTitleData] = useState({
    name: '',
    description: '',
    color_code: 'blue-500',
    icon: '',
    has_glow: false,
    animation_type: 'None',
    is_pro_only: false
  });

  // Edit User State
  const [editingUser, setEditingUser] = useState<any | null>(null);
  const [editNickname, setEditNickname] = useState('');
  const [editBaekjoonId, setEditBaekjoonId] = useState('');
  const [editIsPro, setEditIsPro] = useState(false);
  const [editFreezeCount, setEditFreezeCount] = useState(0);

  useEffect(() => {
    if (!loading) {
      if (!user || user.email !== "test@test.com") {
        alert("접근 권한이 없습니다.");
        router.push('/dashboard');
      } else {
        fetchData();
      }
    }
  }, [user, loading, activeTab]);

  const fetchData = async () => {
    setIsLoading(true);
    try {
      if (activeTab === 'users') {
        const res = await api.get('/admin/users');
        setUsersList(res.data);
      } else if (activeTab === 'problems') {
        const res = await api.get('/admin/problems');
        setProblemsList(res.data);
      } else if (activeTab === 'titles') {
        const res = await api.get('/titles/all');
        setAllTitles(res.data);
      } else if (activeTab === 'invitations') {
        const res = await api.get('/admin/invitations');
        setInvitationsList(res.data);
      }
      
      if (allTitles.length === 0) {
        const titleRes = await api.get('/titles/all');
        setAllTitles(titleRes.data);
      }
    } catch (error) {
      console.error('Failed to fetch data:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const generateInvitation = async () => {
    setIsActionLoading(true);
    try {
      await api.post('/admin/invitations');
      setMessage("새로운 초대 코드가 생성되었습니다.");
      fetchData();
    } catch (error) {
      alert("코드 생성 실패");
    } finally {
      setIsActionLoading(false);
    }
  };

  const deleteInvitation = async (id: string) => {
    if (!window.confirm("이 초대 코드를 삭제하시겠습니까?")) return;
    try {
      await api.delete(`/admin/invitations/${id}`);
      fetchData();
    } catch (error) {
      alert("삭제 실패");
    }
  };

  const saveUserEdit = async () => {
    if (!editingUser) return;
    setIsActionLoading(true);
    try {
      await api.put(`/admin/users/${editingUser.id}`, {
        nickname: editNickname,
        baekjoon_id: editBaekjoonId,
        is_pro: editIsPro,
        streak_freeze_count: editFreezeCount
      });
      setMessage("사용자 정보가 성공적으로 수정되었습니다.");
      setEditingUser(null);
      fetchData();
    } catch (error) {
      alert("수정 실패");
    } finally {
      setIsActionLoading(false);
    }
  };

  const deleteUser = async (userId: string, nickname: string) => {
    if (!window.confirm(`정말로 '${nickname}' 사용자를 삭제하시겠습니까?\n이 작업은 되돌릴 수 없으며 모든 제출 기록과 게시글이 삭제될 수 있습니다.`)) {
      return;
    }

    setIsActionLoading(true);
    try {
      await api.delete(`/admin/users/${userId}`);
      setMessage(`'${nickname}' 사용자가 성공적으로 삭제되었습니다.`);
      setEditingUser(null);
      fetchData();
    } catch (error) {
      alert("사용자 삭제 실패");
    } finally {
      setIsActionLoading(false);
    }
  };

  const grantTitleToUser = async (titleId: string) => {
    if (!editingUser) return;
    try {
      await api.post(`/admin/users/${editingUser.id}/titles/${titleId}`);
      alert("칭호가 부여되었습니다.");
    } catch (error) {
      alert("이미 보유 중이거나 부여에 실패했습니다.");
    }
  };

  const handleCreateTitle = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsActionLoading(true);
    try {
      await api.post('/admin/titles', newTitleData);
      setMessage("새로운 칭호가 생성되었습니다.");
      setNewTitleData({ name: '', description: '', color_code: 'blue-500', icon: '', has_glow: false, animation_type: 'None', is_pro_only: false });
      fetchData();
    } catch (error) {
      alert("칭호 생성 실패");
    } finally {
      setIsActionLoading(false);
    }
  };

  const seedProblem = async () => {
    setIsActionLoading(true);
    try {
      if (forceProblemId) {
        await api.post(`/admin/problems/force?problem_date=${seedDate}&baekjoon_problem_id=${forceProblemId}`);
        setMessage("문제가 성공적으로 설정되었습니다.");
      } else {
        await api.post(`/admin/problems/seed?problem_date=${seedDate}`);
        setMessage("문제가 AI에 의해 생성되었습니다.");
      }
      setForceProblemId('');
      fetchData();
    } catch (error) {
      alert("문제 설정 실패");
    } finally {
      setIsActionLoading(false);
    }
  };

  if (loading || isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <Loader2 className="animate-spin text-blue-600" size={48} />
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
      <div className="flex items-center gap-4 mb-10">
        <div className="w-12 h-12 bg-gray-900 rounded-xl flex items-center justify-center text-white shadow-xl">
          <Settings size={24} />
        </div>
        <div>
          <h1 className="text-3xl font-black text-gray-900 tracking-tight uppercase italic">Admin Panel</h1>
          <p className="text-gray-500 font-medium">플랫폼 데이터 및 시스템 관리</p>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-4 mb-8">
        <button 
          onClick={() => setActiveTab('users')}
          className={`flex items-center gap-2 px-6 py-3 rounded-2xl font-bold transition-all ${
            activeTab === 'users' ? "bg-blue-600 text-white shadow-lg" : "bg-white text-gray-500 hover:bg-gray-50 border border-gray-100"
          }`}
        >
          <Users size={20} /> 사용자 관리
        </button>
        <button 
          onClick={() => setActiveTab('problems')}
          className={`flex items-center gap-2 px-6 py-3 rounded-2xl font-bold transition-all ${
            activeTab === 'problems' ? "bg-blue-600 text-white shadow-lg" : "bg-white text-gray-500 hover:bg-gray-50 border border-gray-100"
          }`}
        >
          <BookOpen size={20} /> 문제 관리
        </button>
        <button 
          onClick={() => setActiveTab('titles')}
          className={`flex items-center gap-2 px-6 py-3 rounded-2xl font-bold transition-all ${
            activeTab === 'titles' ? "bg-blue-600 text-white shadow-lg" : "bg-white text-gray-500 hover:bg-gray-50 border border-gray-100"
          }`}
        >
          <Award size={20} /> 칭호 관리
        </button>
        <button 
          onClick={() => setActiveTab('invitations')}
          className={`flex items-center gap-2 px-6 py-3 rounded-2xl font-bold transition-all ${
            activeTab === 'invitations' ? "bg-blue-600 text-white shadow-lg" : "bg-white text-gray-500 hover:bg-gray-50 border border-gray-100"
          }`}
        >
          <Ticket size={20} /> 초대 코드
        </button>
      </div>

      {message && (
        <div className="mb-6 p-4 bg-green-50 text-green-700 rounded-2xl flex items-center gap-3 border border-green-100 font-bold animate-in fade-in slide-in-from-top-4">
          <CheckCircle2 size={20} /> {message}
        </div>
      )}

      {/* Content Area */}
      <div className="bg-white rounded-[2.5rem] border border-gray-100 shadow-sm overflow-hidden">
        {activeTab === 'users' ? (
          <div className="overflow-x-auto">
            {/* ... usersList mapping ... */}
            <table className="w-full text-left">
              <thead className="bg-gray-50/50 border-b border-gray-100">
                <tr>
                  <th className="px-6 py-4 text-xs font-black text-gray-400 uppercase tracking-widest">Nickname / Email</th>
                  <th className="px-6 py-4 text-xs font-black text-gray-400 uppercase tracking-widest">Baekjoon ID</th>
                  <th className="px-6 py-4 text-xs font-black text-gray-400 uppercase tracking-widest text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {usersList.map((u) => (
                  <tr key={u.id} className="hover:bg-gray-50/30 transition-colors">
                    <td className="px-6 py-5">
                      <div className="flex items-center gap-2">
                        <span className="font-bold text-gray-900">{u.nickname}</span>
                        {u.is_pro && <div className="px-1.5 py-0.5 bg-amber-100 text-amber-700 text-[8px] font-black rounded uppercase">PRO</div>}
                      </div>
                      <div className="text-xs text-gray-400">{u.email}</div>
                    </td>
                    <td className="px-6 py-5 font-mono text-sm text-blue-600 font-bold">{u.baekjoon_id}</td>
                    <td className="px-6 py-5 text-right flex justify-end gap-1">
                      <button 
                        onClick={() => {
                          setEditingUser(u);
                          setEditNickname(u.nickname);
                          setEditBaekjoonId(u.baekjoon_id);
                          setEditIsPro(u.is_pro);
                          setEditFreezeCount(u.streak_freeze_count || 0);
                        }}
                        className="p-2 text-gray-300 hover:text-blue-500 transition-colors"
                        title="수정"
                      >
                        <Edit2 size={18} />
                      </button>
                      <button 
                        onClick={() => deleteUser(u.id, u.nickname)}
                        className="p-2 text-gray-300 hover:text-rose-500 transition-colors"
                        title="삭제"
                      >
                        <Trash2 size={18} />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : activeTab === 'problems' ? (
          <div className="p-8">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-10 pb-8 border-b border-gray-50">
              <div className="space-y-2">
                <label className="text-xs font-black text-gray-400 uppercase tracking-widest ml-1">Date</label>
                <input type="date" value={seedDate} onChange={(e) => setSeedDate(e.target.value)} className="w-full px-4 py-2.5 rounded-xl border border-gray-200 font-bold text-gray-700" />
              </div>
              <div className="space-y-2">
                <label className="text-xs font-black text-gray-400 uppercase tracking-widest ml-1">Manual ID (Optional)</label>
                <input type="number" placeholder="Baekjoon ID" value={forceProblemId} onChange={(e) => setForceProblemId(e.target.value)} className="w-full px-4 py-2.5 rounded-xl border border-gray-200 font-bold text-gray-700" />
              </div>
              <div className="flex items-end">
                <button onClick={seedProblem} disabled={isActionLoading} className="w-full bg-gray-900 text-white py-2.5 rounded-xl font-bold flex items-center justify-center gap-2 hover:bg-gray-800 transition-all active:scale-95">
                  {isActionLoading ? <Loader2 className="animate-spin" size={18} /> : forceProblemId ? <Save size={18} /> : <Plus size={18} />}
                  문제 설정하기
                </button>
              </div>
            </div>

            <div className="space-y-4">
              <h2 className="text-sm font-black text-gray-400 uppercase tracking-widest mb-4">Problem History</h2>
              {problemsList.map((p) => (
                <div key={p.id} className="flex items-center justify-between p-5 bg-gray-50 rounded-2xl border border-gray-100">
                  <div className="flex items-center gap-4">
                    <div className="bg-white p-3 rounded-xl border border-gray-100"><Calendar size={20} className="text-blue-600" /></div>
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-bold text-gray-400">{new Date(p.problem_date).toLocaleDateString()}</span>
                        <span className="text-[10px] bg-blue-100 text-blue-700 px-1.5 py-0.5 rounded font-black uppercase">{p.difficulty_level}</span>
                      </div>
                      <h3 className="font-bold text-gray-900">#{p.baekjoon_problem_id} {p.title}</h3>
                    </div>
                  </div>
                  <div className="flex gap-2">
                    <button 
                      onClick={() => {
                        setSeedDate(p.problem_date.split('T')[0]);
                        setForceProblemId(p.baekjoon_problem_id.toString());
                        window.scrollTo({ top: 0, behavior: 'smooth' });
                      }}
                      title="날짜 수정"
                      className="p-2 text-gray-300 hover:text-amber-500 transition-colors"
                    >
                      <Edit2 size={18} />
                    </button>
                    <button onClick={() => api.post(`/admin/problems/${p.id}/reseed`).then(fetchData)} title="AI 재선정" className="p-2 text-gray-300 hover:text-blue-500 transition-colors"><RefreshCw size={18} /></button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        ) : activeTab === 'titles' ? (
          <div className="p-8">
            <form onSubmit={handleCreateTitle} className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-10 pb-8 border-b border-gray-50">
              <div className="space-y-2">
                <label className="text-xs font-black text-gray-400 uppercase tracking-widest ml-1">Title Name</label>
                <input placeholder="예: 슈퍼 코더" value={newTitleData.name} onChange={e => setNewTitleData({...newTitleData, name: e.target.value})} className="w-full px-4 py-2.5 rounded-xl border border-gray-200 font-bold" required />
              </div>
              <div className="space-y-2">
                <label className="text-xs font-black text-gray-400 uppercase tracking-widest ml-1">Description</label>
                <input placeholder="칭호 획득 조건 설명" value={newTitleData.description} onChange={e => setNewTitleData({...newTitleData, description: e.target.value})} className="w-full px-4 py-2.5 rounded-xl border border-gray-200 font-bold" required />
              </div>
              <div className="space-y-2">
                <label className="text-xs font-black text-gray-400 uppercase tracking-widest ml-1">Color (blue-500)</label>
                <input placeholder="blue-500" value={newTitleData.color_code} onChange={e => setNewTitleData({...newTitleData, color_code: e.target.value})} className="w-full px-4 py-2.5 rounded-xl border border-gray-200 font-bold" />
              </div>
              <div className="flex items-end">
                <button type="submit" disabled={isActionLoading} className="w-full bg-blue-600 text-white py-2.5 rounded-xl font-black uppercase tracking-tighter shadow-lg shadow-blue-100">칭호 생성하기</button>
              </div>
            </form>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {allTitles.map(t => (
                <div key={t.id} className="p-5 border border-gray-100 rounded-3xl flex items-center justify-between group hover:shadow-md transition-all">
                  <div><TitleBadge title={t} size="md" /><p className="text-[10px] text-gray-400 mt-2 font-medium">{t.description}</p></div>
                </div>
              ))}
            </div>
          </div>
        ) : (
          <div className="p-8">
            <div className="flex justify-between items-center mb-10 pb-8 border-b border-gray-50">
              <div>
                <h2 className="text-xl font-bold text-gray-900">클로즈 베타 초대권</h2>
                <p className="text-sm text-gray-500 font-medium">새로운 멤버를 초대하기 위한 고유 코드를 생성하세요.</p>
              </div>
              <button 
                onClick={generateInvitation} 
                disabled={isActionLoading}
                className="bg-gray-900 text-white px-6 py-3 rounded-2xl font-bold flex items-center gap-2 hover:bg-gray-800 transition-all active:scale-95 shadow-xl shadow-gray-200"
              >
                {isActionLoading ? <Loader2 className="animate-spin" size={20} /> : <Plus size={20} />}
                초대권 발급하기
              </button>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {invitationsList.map((inv) => (
                <div key={inv.id} className={`p-6 rounded-[2rem] border transition-all ${inv.is_used ? "bg-gray-50 border-transparent opacity-60" : "bg-white border-gray-100 hover:shadow-lg shadow-sm"}`}>
                  <div className="flex justify-between items-start mb-4">
                    <div className={`p-3 rounded-2xl ${inv.is_used ? "bg-gray-200 text-gray-400" : "bg-blue-50 text-blue-600"}`}>
                      <Ticket size={24} />
                    </div>
                    {!inv.is_used && (
                      <button 
                        onClick={() => {
                          navigator.clipboard.writeText(inv.code);
                          alert("코드가 복사되었습니다!");
                        }}
                        className="p-2 text-gray-300 hover:text-blue-500 transition-colors"
                      >
                        <Copy size={18} />
                      </button>
                    )}
                    <button onClick={() => deleteInvitation(inv.id)} className="p-2 text-gray-300 hover:text-rose-500 transition-colors">
                      <Trash2 size={18} />
                    </button>
                  </div>
                  
                  <div className="space-y-1 mb-6">
                    <p className="text-[10px] font-black text-gray-400 uppercase tracking-widest">Invitation Code</p>
                    <h3 className="text-2xl font-black text-gray-900 tracking-tighter font-mono">{inv.code}</h3>
                  </div>

                  <div className="pt-4 border-t border-gray-100">
                    {inv.is_used ? (
                      <div className="flex items-center gap-2">
                        <div className="w-6 h-6 bg-gray-200 rounded-full flex items-center justify-center text-[10px] font-black text-gray-500 uppercase">Used</div>
                        <p className="text-xs font-bold text-gray-500">
                          <span className="text-gray-900">{inv.nickname}</span>님이 사용함
                        </p>
                      </div>
                    ) : (
                      <div className="flex items-center gap-2">
                        <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
                        <p className="text-xs font-black text-green-600 uppercase tracking-widest">Available Now</p>
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
            {invitationsList.length === 0 && (
              <div className="text-center py-20 text-gray-300 font-bold italic">발급된 초대권이 없습니다.</div>
            )}
          </div>
        )}
      </div>

      {/* Unified User Edit & Title Grant Modal */}
      {editingUser && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-md z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-[3rem] w-full max-w-3xl overflow-hidden shadow-2xl flex flex-col md:flex-row animate-in zoom-in-95 duration-200">
            {/* Left Column: User Info */}
            <div className="p-10 border-r border-gray-50 bg-gray-50/50 flex-1">
              <div className="flex items-center gap-3 mb-8">
                <div className="w-10 h-10 bg-gray-900 rounded-xl flex items-center justify-center text-white"><User size={20}/></div>
                <h3 className="text-xl font-black uppercase italic tracking-tighter">Edit User</h3>
              </div>
              <div className="space-y-5">
                <div className="space-y-1.5"><label className="text-[10px] font-black text-gray-400 uppercase tracking-widest ml-1">Nickname</label><input value={editNickname} onChange={e => setEditNickname(e.target.value)} className="w-full p-4 bg-white border border-gray-200 rounded-2xl font-bold text-gray-900 focus:ring-4 focus:ring-blue-50 outline-none transition-all" /></div>
                <div className="space-y-1.5"><label className="text-[10px] font-black text-gray-400 uppercase tracking-widest ml-1">Baekjoon ID</label><input value={editBaekjoonId} onChange={e => setEditBaekjoonId(e.target.value)} className="w-full p-4 bg-white border border-gray-200 rounded-2xl font-bold text-gray-900 focus:ring-4 focus:ring-blue-50 outline-none transition-all" /></div>
                
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-1.5">
                    <label className="text-[10px] font-black text-amber-600 uppercase tracking-widest ml-1">Member Status</label>
                    <button onClick={() => setEditIsPro(!editIsPro)} className={`w-full p-4 rounded-2xl font-black uppercase text-xs transition-all border ${editIsPro ? "Pro Active" : "Basic Member"}`}>
                      {editIsPro ? "Pro Active" : "Basic Member"}
                    </button>
                  </div>
                  <div className="space-y-1.5">
                    <label className="text-[10px] font-black text-blue-600 uppercase tracking-widest ml-1 flex items-center gap-1"><Snowflake size={10}/> Streak Freezes</label>
                    <input type="number" value={editFreezeCount} onChange={e => setEditFreezeCount(parseInt(e.target.value))} className="w-full p-4 bg-white border border-gray-200 rounded-2xl font-bold text-gray-900 focus:ring-4 focus:ring-blue-50 outline-none" />
                  </div>
                </div>

                <button onClick={saveUserEdit} disabled={isActionLoading} className="w-full bg-blue-600 text-white py-5 rounded-2xl font-black uppercase tracking-widest shadow-xl shadow-blue-100 hover:bg-blue-700 transition-all active:scale-95 disabled:opacity-50 mt-4 flex items-center justify-center gap-2">
                  {isActionLoading ? <Loader2 className="animate-spin" size={20}/> : <><Save size={20}/> Save Changes</>}
                </button>

                <div className="mt-10 pt-8 border-t border-rose-100">
                  <div className="flex items-center gap-2 text-rose-500 mb-4">
                    <Trash2 size={16} />
                    <span className="text-[10px] font-black uppercase tracking-widest">Danger Zone</span>
                  </div>
                  <button 
                    onClick={() => deleteUser(editingUser.id, editingUser.nickname)}
                    disabled={isActionLoading}
                    className="w-full bg-rose-50 text-rose-600 py-4 rounded-2xl font-bold hover:bg-rose-600 hover:text-white transition-all border border-rose-100 flex items-center justify-center gap-2"
                  >
                    회원 영구 삭제
                  </button>
                </div>
              </div>
            </div>

            {/* Right Column: Title Management */}
            <div className="p-10 flex-1 flex flex-col">
              <div className="flex items-center justify-between mb-8">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 bg-blue-600 rounded-xl flex items-center justify-center text-white shadow-lg shadow-blue-100"><Sparkles size={20}/></div>
                  <h3 className="text-xl font-black uppercase italic tracking-tighter text-gray-900">Grant Title</h3>
                </div>
                <button onClick={() => setEditingUser(null)} className="p-2 hover:bg-gray-100 rounded-full transition-colors"><X size={24} /></button>
              </div>
              
              <div className="flex-grow space-y-3 overflow-y-auto pr-2 custom-scrollbar" style={{ maxHeight: '350px' }}>
                {allTitles.length > 0 ? allTitles.map(t => (
                  <button 
                    key={t.id} 
                    onClick={() => grantTitleToUser(t.id)}
                    className="w-full p-4 border border-gray-100 rounded-2xl hover:border-blue-500 hover:bg-blue-50/50 transition-all flex items-center justify-between group text-left"
                  >
                    <div><TitleBadge title={t} size="sm" /><p className="text-[9px] text-gray-400 mt-1 font-medium">{t.description}</p></div>
                    <div className="w-8 h-8 bg-white rounded-lg flex items-center justify-center text-blue-500 opacity-0 group-hover:opacity-100 border border-blue-100 shadow-sm transition-opacity"><Plus size={16}/></div>
                  </button>
                )) : (
                  <div className="text-center py-10 text-gray-300 font-bold italic">등록된 칭호가 없습니다.</div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
