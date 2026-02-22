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
  Snowflake
} from 'lucide-react';
import TitleBadge from '@/components/title-badge';

export default function AdminPage() {
  const { user, loading, refreshUser } = useAuth();
  const router = useRouter();
  
  const [activeTab, setActiveTab] = useState<'users' | 'problems' | 'titles'>('users');
  const [usersList, setUsersList] = useState<any[]>([]);
  const [problemsList, setProblemsList] = useState<any[]>([]);
  const [allTitles, setAllTitles] = useState<any[]>([]);
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
      } else {
        const res = await api.get('/titles/all');
        setAllTitles(res.data);
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
                    <td className="px-6 py-5 text-right">
                      <button 
                        onClick={() => {
                          setEditingUser(u);
                          setEditNickname(u.nickname);
                          setEditBaekjoonId(u.baekjoon_id);
                          setEditIsPro(u.is_pro);
                          setEditFreezeCount(u.streak_freeze_count || 0);
                        }}
                        className="p-2 text-gray-300 hover:text-blue-500 transition-colors"
                      >
                        <Edit2 size={18} />
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
        ) : (
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
