"use client";

import { useState, useRef, useEffect, useCallback } from 'react';
import { Upload, Mic, Activity, TrendingUp, Users, AlertTriangle, CheckCircle, Info, ChevronRight, Dumbbell, Target, Zap, BarChart3, Calendar, Clock, Send, LogOut, User } from 'lucide-react';

const API_BASE = 'http://localhost:8000';

interface MuscleData { [key: string]: number; }
interface FormFeedbackItem { timestamp_sec: number; severity: 'info' | 'warning' | 'critical'; note: string; }
interface Exercise { name: string; start_sec: number; end_sec: number; duration_sec: number; reps: number; sets?: number; form_feedback: FormFeedbackItem[]; muscle_activation?: MuscleData; }
interface Workout { id: string; created_at: string; video_filename: string; video_duration_sec: number; exercises: Exercise[]; muscle_activation: { muscles: MuscleData; primary_muscles: string[]; secondary_muscles: string[]; }; form_score: number | null; summary: string | null; status: string; }
interface DashboardData { workout_count: number; total_duration_min: number; avg_form_score: number | null; muscle_balance: MuscleData; category_balance: MuscleData; exercise_frequency: Record<string, number>; insights: { type: string; severity: string; message: string; }[]; recent_workouts: { id: string; date: string; exercises: string[]; duration_min: number; form_score: number | null; }[]; }

const MuscleHeatmap = ({ muscleData }: { muscleData: MuscleData }) => {
  const getColor = (v: number) => v === 0 ? '#1e293b' : v < 0.3 ? '#164e63' : v < 0.5 ? '#0e7490' : v < 0.7 ? '#06b6d4' : v < 0.85 ? '#22d3ee' : '#67e8f9';
  const muscles = [
    { id: 'chest', x: 85, y: 75 }, { id: 'shoulders', x: 50, y: 55 }, { id: 'biceps', x: 30, y: 95 },
    { id: 'triceps', x: 140, y: 95 }, { id: 'forearms', x: 25, y: 130 }, { id: 'core', x: 85, y: 115 },
    { id: 'lats', x: 130, y: 80 }, { id: 'traps', x: 85, y: 45 }, { id: 'quadriceps', x: 70, y: 175 },
    { id: 'hamstrings', x: 100, y: 180 }, { id: 'glutes', x: 85, y: 150 }, { id: 'lower_back', x: 120, y: 120 },
    { id: 'rhomboids', x: 140, y: 65 },
  ];
  return (
    <div className="relative">
      <svg viewBox="0 0 170 240" className="w-full max-w-xs mx-auto">
        <ellipse cx="85" cy="25" rx="20" ry="22" fill="#334155" />
        <rect x="65" y="45" width="40" height="60" rx="5" fill="#334155" />
        <rect x="45" y="50" width="20" height="8" rx="3" fill="#334155" />
        <rect x="105" y="50" width="20" height="8" rx="3" fill="#334155" />
        <rect x="40" y="58" width="15" height="50" rx="4" fill="#334155" />
        <rect x="115" y="58" width="15" height="50" rx="4" fill="#334155" />
        <rect x="35" y="108" width="12" height="35" rx="3" fill="#334155" />
        <rect x="123" y="108" width="12" height="35" rx="3" fill="#334155" />
        <rect x="65" y="105" width="40" height="45" rx="5" fill="#334155" />
        <rect x="60" y="150" width="22" height="55" rx="5" fill="#334155" />
        <rect x="88" y="150" width="22" height="55" rx="5" fill="#334155" />
        <rect x="58" y="205" width="18" height="30" rx="4" fill="#334155" />
        <rect x="94" y="205" width="18" height="30" rx="4" fill="#334155" />
        {muscles.map(m => (
          <g key={m.id}>
            <circle cx={m.x} cy={m.y} r={12} fill={getColor(muscleData[m.id] || 0)} className="transition-all duration-500" opacity={0.9} />
            {(muscleData[m.id] || 0) > 0 && <text x={m.x} y={m.y + 4} textAnchor="middle" fontSize="8" fill="white" fontWeight="bold">{Math.round((muscleData[m.id] || 0) * 100)}%</text>}
          </g>
        ))}
      </svg>
      <div className="mt-4 flex items-center justify-center gap-2">
        <span className="text-xs text-slate-400">Less</span>
        <div className="flex gap-1">{['#1e293b', '#164e63', '#0e7490', '#06b6d4', '#22d3ee', '#67e8f9'].map((c, i) => <div key={i} className="w-4 h-3 rounded-sm" style={{ backgroundColor: c }} />)}</div>
        <span className="text-xs text-slate-400">More</span>
      </div>
    </div>
  );
};

const FormFeedback = ({ item }: { item: FormFeedbackItem }) => {
  const colors = { info: 'text-cyan-400 bg-cyan-400/10', warning: 'text-amber-400 bg-amber-400/10', critical: 'text-red-400 bg-red-400/10' };
  const Icon = item.severity === 'info' ? Info : AlertTriangle;
  return (
    <div className={`flex items-start gap-3 p-3 rounded-lg ${colors[item.severity]}`}>
      <Icon size={16} className="mt-0.5 shrink-0" />
      <div>
        <span className="text-slate-300 text-sm font-mono">{item.timestamp_sec.toFixed(1)}s</span>
        <p className="text-sm mt-0.5">{item.note}</p>
      </div>
    </div>
  );
};

export default function GymIntel() {
  // Auth state
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [userId, setUserId] = useState('');
  const [userName, setUserName] = useState('');
  const [loginEmail, setLoginEmail] = useState('');
  const [loginName, setLoginName] = useState('');
  const [loginError, setLoginError] = useState('');

  // App state
  const [activeTab, setActiveTab] = useState('upload');
  const [uploadState, setUploadState] = useState<'idle' | 'uploading' | 'processing' | 'complete' | 'error'>('idle');
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadMessage, setUploadMessage] = useState('');
  const [currentWorkoutId, setCurrentWorkoutId] = useState<string | null>(null);
  const [currentWorkout, setCurrentWorkout] = useState<Workout | null>(null);
  const [selectedExercise, setSelectedExercise] = useState<number | null>(null);
  
  // Dashboard state
  const [dashboard, setDashboard] = useState<DashboardData | null>(null);
  const [workoutHistory, setWorkoutHistory] = useState<Workout[]>([]);
  
  // Coach state
  const [coachMessages, setCoachMessages] = useState<{role: string, text: string}[]>([{ role: 'coach', text: "Hey! I'm your AI coach. Ask me about your training, form, or what you should work on next." }]);
  const [coachInput, setCoachInput] = useState('');
  const [isCoachLoading, setIsCoachLoading] = useState(false);
  
  const fileInputRef = useRef<HTMLInputElement>(null);
  const chatEndRef = useRef<HTMLDivElement>(null);
  const pollIntervalRef = useRef<NodeJS.Timeout | null>(null);

  // Login/Register
  const handleLogin = async () => {
    if (!loginEmail.trim()) { setLoginError('Email is required'); return; }
    setLoginError('');
    try {
      // Try to get existing user
      const res = await fetch(`${API_BASE}/api/users/email/${encodeURIComponent(loginEmail)}`);
      if (res.ok) {
        const user = await res.json();
        setUserId(user._id || user.id);
        setUserName(user.name);
        setIsLoggedIn(true);
        localStorage.setItem('gymintel_user', JSON.stringify({ id: user._id || user.id, name: user.name, email: loginEmail }));
      } else {
        // Create new user
        if (!loginName.trim()) { setLoginError('Name is required for new users'); return; }
        const createRes = await fetch(`${API_BASE}/api/users`, {
          method: 'POST', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ email: loginEmail, name: loginName })
        });
        if (createRes.ok) {
          const data = await createRes.json();
          setUserId(data.user_id);
          setUserName(loginName);
          setIsLoggedIn(true);
          localStorage.setItem('gymintel_user', JSON.stringify({ id: data.user_id, name: loginName, email: loginEmail }));
        } else { setLoginError('Failed to create user'); }
      }
    } catch { setLoginError('Server error - make sure backend is running'); }
  };

  const handleLogout = () => {
    setIsLoggedIn(false); setUserId(''); setUserName('');
    localStorage.removeItem('gymintel_user');
    setDashboard(null); setWorkoutHistory([]); setCurrentWorkout(null);
  };

  // Check for saved session
  useEffect(() => {
    const saved = localStorage.getItem('gymintel_user');
    if (saved) {
      try {
        const { id, name } = JSON.parse(saved);
        setUserId(id); setUserName(name); setIsLoggedIn(true);
      } catch { localStorage.removeItem('gymintel_user'); }
    }
  }, []);

  // Fetch dashboard data
  const fetchDashboard = useCallback(async () => {
    if (!userId) return;
    try {
      const res = await fetch(`${API_BASE}/api/users/${userId}/dashboard?days=30`);
      if (res.ok) setDashboard(await res.json());
    } catch (e) { console.error('Dashboard fetch error:', e); }
  }, [userId]);

  // Fetch workout history
  const fetchHistory = useCallback(async () => {
    if (!userId) return;
    try {
      const res = await fetch(`${API_BASE}/api/users/${userId}/workouts?limit=20`);
      if (res.ok) { const data = await res.json(); setWorkoutHistory(data.workouts || []); }
    } catch (e) { console.error('History fetch error:', e); }
  }, [userId]);

  useEffect(() => { if (isLoggedIn && userId) { fetchDashboard(); fetchHistory(); } }, [isLoggedIn, userId, fetchDashboard, fetchHistory]);

  // Poll for workout status
  const pollStatus = useCallback(async (workoutId: string) => {
    try {
      const res = await fetch(`${API_BASE}/api/workouts/${workoutId}/status`);
      if (!res.ok) return;
      const data = await res.json();
      setUploadProgress(data.progress || 0);
      setUploadMessage(data.message || '');
      if (data.status === 'complete' || data.db_status === 'complete') {
        if (pollIntervalRef.current) { clearInterval(pollIntervalRef.current); pollIntervalRef.current = null; }
        setUploadState('complete');
        // Fetch full workout data
        const workoutRes = await fetch(`${API_BASE}/api/workouts/${workoutId}`);
        if (workoutRes.ok) setCurrentWorkout(await workoutRes.json());
        fetchDashboard(); fetchHistory();
      } else if (data.status === 'failed') {
        if (pollIntervalRef.current) { clearInterval(pollIntervalRef.current); pollIntervalRef.current = null; }
        setUploadState('error'); setUploadMessage(data.message || 'Processing failed');
      }
    } catch (e) { console.error('Poll error:', e); }
  }, [fetchDashboard, fetchHistory]);

  // Upload video
  const handleUpload = async (file: File) => {
    setUploadState('uploading'); setUploadProgress(0); setUploadMessage('Uploading...');
    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('user_id', userId);
      const res = await fetch(`${API_BASE}/api/workouts/upload`, { method: 'POST', body: formData });
      if (!res.ok) { const err = await res.json(); throw new Error(err.detail || 'Upload failed'); }
      const data = await res.json();
      setCurrentWorkoutId(data.workout_id);
      setUploadState('processing'); setUploadMessage('Processing video...');
      // Start polling
      pollIntervalRef.current = setInterval(() => pollStatus(data.workout_id), 1000);
    } catch (e) { setUploadState('error'); setUploadMessage(e instanceof Error ? e.message : 'Upload failed'); }
  };

  // Coach chat
  const sendCoachMessage = async () => {
    if (!coachInput.trim() || isCoachLoading) return;
    const msg = coachInput.trim(); setCoachInput('');
    setCoachMessages(prev => [...prev, { role: 'user', text: msg }]);
    setIsCoachLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/coach/${userId}/chat`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ message: msg })
      });
      if (res.ok) { const data = await res.json(); setCoachMessages(prev => [...prev, { role: 'coach', text: data.response }]); }
      else setCoachMessages(prev => [...prev, { role: 'coach', text: "Sorry, I couldn't process that. Make sure the backend is running." }]);
    } catch { setCoachMessages(prev => [...prev, { role: 'coach', text: "Connection error. Is the backend running on localhost:8000?" }]); }
    setIsCoachLoading(false);
    setTimeout(() => chatEndRef.current?.scrollIntoView({ behavior: 'smooth' }), 100);
  };

  // Cleanup polling on unmount
  useEffect(() => { return () => { if (pollIntervalRef.current) clearInterval(pollIntervalRef.current); }; }, []);

  const tabs = [
    { id: 'upload', label: 'Upload', icon: Upload },
    { id: 'dashboard', label: 'Dashboard', icon: BarChart3 },
    { id: 'history', label: 'History', icon: Calendar },
    { id: 'coach', label: 'Coach', icon: Mic },
  ];

  // Login screen
  if (!isLoggedIn) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 text-white flex items-center justify-center p-4">
        <div className="w-full max-w-md">
          <div className="text-center mb-8">
            <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-cyan-500 to-blue-600 flex items-center justify-center mx-auto mb-4">
              <Dumbbell size={32} />
            </div>
            <h1 className="text-3xl font-bold">GymIntel</h1>
            <p className="text-slate-400 mt-2">AI-Powered Workout Intelligence</p>
          </div>
          <div className="bg-slate-800/50 rounded-2xl p-6 border border-slate-700/50">
            <h2 className="text-xl font-semibold mb-4">Sign In / Register</h2>
            <div className="space-y-4">
              <div>
                <label className="text-sm text-slate-400">Email</label>
                <input type="email" value={loginEmail} onChange={e => setLoginEmail(e.target.value)} placeholder="you@example.com" className="w-full mt-1 bg-slate-700/50 border border-slate-600 rounded-xl px-4 py-3 focus:outline-none focus:border-cyan-500" />
              </div>
              <div>
                <label className="text-sm text-slate-400">Name (for new accounts)</label>
                <input type="text" value={loginName} onChange={e => setLoginName(e.target.value)} placeholder="Your Name" className="w-full mt-1 bg-slate-700/50 border border-slate-600 rounded-xl px-4 py-3 focus:outline-none focus:border-cyan-500" />
              </div>
              {loginError && <p className="text-red-400 text-sm">{loginError}</p>}
              <button onClick={handleLogin} className="w-full py-3 rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 font-medium hover:from-cyan-400 hover:to-blue-500 transition-all">Continue</button>
            </div>
            <p className="text-xs text-slate-500 text-center mt-4">Make sure the backend is running: python main.py</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 text-white">
      {/* Header */}
      <header className="border-b border-slate-800/50 backdrop-blur-xl bg-slate-900/50 sticky top-0 z-50">
        <div className="max-w-6xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-cyan-500 to-blue-600 flex items-center justify-center"><Dumbbell size={20} /></div>
            <div><h1 className="font-bold text-lg">GymIntel</h1><p className="text-xs text-slate-400">AI Workout Coach</p></div>
          </div>
          <div className="flex items-center gap-3">
            <div className="px-3 py-1.5 rounded-full bg-cyan-500/10 text-cyan-400 border border-cyan-500/20 text-sm">{dashboard?.workout_count || 0} workouts</div>
            <div className="flex items-center gap-2 text-sm text-slate-400"><User size={16} />{userName}</div>
            <button onClick={handleLogout} className="p-2 text-slate-400 hover:text-white"><LogOut size={18} /></button>
          </div>
        </div>
      </header>

      {/* Tabs */}
      <nav className="border-b border-slate-800/50 bg-slate-900/30">
        <div className="max-w-6xl mx-auto px-4 flex gap-1">
          {tabs.map(tab => (
            <button key={tab.id} onClick={() => setActiveTab(tab.id)} className={`flex items-center gap-2 px-4 py-3 text-sm font-medium border-b-2 -mb-px transition-all ${activeTab === tab.id ? 'text-cyan-400 border-cyan-400' : 'text-slate-400 border-transparent hover:text-slate-200'}`}>
              <tab.icon size={16} />{tab.label}
            </button>
          ))}
        </div>
      </nav>

      {/* Main Content */}
      <main className="max-w-6xl mx-auto px-4 py-8">
        {/* Upload Tab */}
        {activeTab === 'upload' && (
          <div className="space-y-8">
            {uploadState === 'idle' && (
              <div onClick={() => fileInputRef.current?.click()} className="border-2 border-dashed border-slate-700 rounded-2xl p-12 text-center hover:border-cyan-500/50 hover:bg-cyan-500/5 transition-all cursor-pointer group">
                <input type="file" ref={fileInputRef} className="hidden" accept="video/*" onChange={e => e.target.files?.[0] && handleUpload(e.target.files[0])} />
                <div className="w-16 h-16 rounded-2xl bg-slate-800 flex items-center justify-center mx-auto mb-4 group-hover:bg-cyan-500/20"><Upload size={28} className="text-slate-400 group-hover:text-cyan-400" /></div>
                <h3 className="text-xl font-semibold mb-2">Upload Workout Video</h3>
                <p className="text-slate-400 max-w-md mx-auto">Drop your workout recording here. We&apos;ll detect exercises, analyze form, and track muscle activation.</p>
              </div>
            )}
            {(uploadState === 'uploading' || uploadState === 'processing') && (
              <div className="bg-slate-800/50 rounded-2xl p-8 text-center border border-slate-700/50">
                <div className="w-16 h-16 rounded-2xl bg-cyan-500/20 flex items-center justify-center mx-auto mb-4"><Activity size={28} className="text-cyan-400 animate-pulse" /></div>
                <h3 className="text-xl font-semibold mb-2">{uploadState === 'uploading' ? 'Uploading...' : 'Processing Video'}</h3>
                <p className="text-cyan-400 mb-4">{uploadMessage}</p>
                <div className="max-w-md mx-auto">
                  <div className="h-2 bg-slate-700 rounded-full overflow-hidden"><div className="h-full bg-gradient-to-r from-cyan-500 to-blue-500 transition-all duration-300" style={{ width: `${uploadProgress}%` }} /></div>
                  <p className="text-slate-400 mt-2">{uploadProgress}%</p>
                </div>
              </div>
            )}
            {uploadState === 'error' && (
              <div className="bg-red-500/10 border border-red-500/50 rounded-2xl p-8 text-center">
                <AlertTriangle size={48} className="text-red-400 mx-auto mb-4" />
                <h3 className="text-xl font-semibold mb-2 text-red-400">Error</h3>
                <p className="text-slate-300 mb-4">{uploadMessage}</p>
                <button onClick={() => { setUploadState('idle'); setCurrentWorkout(null); }} className="px-6 py-2 bg-slate-700 rounded-lg hover:bg-slate-600">Try Again</button>
              </div>
            )}
            {uploadState === 'complete' && currentWorkout && (
              <div className="space-y-6">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3 text-emerald-400"><CheckCircle size={24} /><span className="font-semibold">Analysis Complete!</span></div>
                  <button onClick={() => { setUploadState('idle'); setCurrentWorkout(null); setSelectedExercise(null); }} className="text-sm text-slate-400 hover:text-white">Upload Another</button>
                </div>
                {currentWorkout.summary && <div className="bg-slate-800/50 rounded-xl p-4 border border-slate-700/50"><p className="text-slate-300">{currentWorkout.summary}</p></div>}
                <div className="grid lg:grid-cols-3 gap-6">
                  <div className="lg:col-span-2 bg-slate-800/50 rounded-2xl p-6 border border-slate-700/50">
                    <h3 className="font-semibold mb-4 flex items-center gap-2"><Target size={18} className="text-cyan-400" />Detected Exercises ({currentWorkout.exercises?.length || 0})</h3>
                    <div className="space-y-3">
                      {(currentWorkout.exercises || []).map((ex, i) => (
                        <div key={i} onClick={() => setSelectedExercise(selectedExercise === i ? null : i)} className={`p-4 rounded-xl cursor-pointer transition-all ${selectedExercise === i ? 'bg-cyan-500/20 border-cyan-500/50' : 'bg-slate-700/50 hover:bg-slate-700'} border border-transparent`}>
                          <div className="flex items-center justify-between">
                            <div>
                              <h4 className="font-medium">{ex.name}</h4>
                              <p className="text-sm text-slate-400">{ex.start_sec.toFixed(1)}s - {ex.end_sec.toFixed(1)}s • {ex.reps} reps</p>
                            </div>
                            <div className="flex items-center gap-2">
                              {ex.form_feedback?.some(f => f.severity === 'critical') && <AlertTriangle size={16} className="text-red-400" />}
                              {ex.form_feedback?.some(f => f.severity === 'warning') && !ex.form_feedback?.some(f => f.severity === 'critical') && <AlertTriangle size={16} className="text-amber-400" />}
                              <ChevronRight size={16} className={`transition-transform ${selectedExercise === i ? 'rotate-90' : ''}`} />
                            </div>
                          </div>
                          {selectedExercise === i && ex.form_feedback && ex.form_feedback.length > 0 && (
                            <div className="mt-4 space-y-2">
                              <p className="text-sm text-slate-300 mb-3">Form Feedback:</p>
                              {ex.form_feedback.map((f, j) => <FormFeedback key={j} item={f} />)}
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                  <div className="bg-slate-800/50 rounded-2xl p-6 border border-slate-700/50">
                    <h3 className="font-semibold mb-4 flex items-center gap-2"><Zap size={18} className="text-cyan-400" />Session Activation</h3>
                    <MuscleHeatmap muscleData={currentWorkout.muscle_activation?.muscles || {}} />
                    {currentWorkout.form_score !== null && (
                      <div className="mt-4 text-center"><p className="text-slate-400 text-sm">Form Score</p><p className="text-3xl font-bold text-cyan-400">{currentWorkout.form_score.toFixed(0)}%</p></div>
                    )}
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Dashboard Tab */}
        {activeTab === 'dashboard' && (
          <div className="grid lg:grid-cols-3 gap-6">
            <div className="lg:col-span-2 space-y-6">
              <div className="grid grid-cols-3 gap-4">
                {[
                  { label: 'Workouts', value: dashboard?.workout_count?.toString() || '0', sub: 'this month', icon: Dumbbell },
                  { label: 'Total Time', value: `${((dashboard?.total_duration_min || 0) / 60).toFixed(1)}h`, sub: 'logged', icon: Clock },
                  { label: 'Form Score', value: dashboard?.avg_form_score ? `${dashboard.avg_form_score.toFixed(0)}%` : 'N/A', sub: 'average', icon: TrendingUp },
                ].map((s, i) => (
                  <div key={i} className="bg-slate-800/50 rounded-xl p-4 border border-slate-700/50">
                    <s.icon size={18} className="text-cyan-400 mb-2" /><p className="text-2xl font-bold">{s.value}</p><p className="text-xs text-slate-400">{s.label} {s.sub}</p>
                  </div>
                ))}
              </div>
              {(dashboard?.insights?.length || 0) > 0 && (
                <div className="bg-slate-800/50 rounded-2xl p-6 border border-slate-700/50">
                  <h3 className="font-semibold mb-4 flex items-center gap-2"><Activity size={18} className="text-cyan-400" />Training Insights</h3>
                  <div className="space-y-3">
                    {dashboard?.insights.map((insight, i) => (
                      <div key={i} className={`flex items-start gap-3 p-3 rounded-lg ${insight.severity === 'warning' ? 'bg-amber-400/10 text-amber-400' : insight.severity === 'success' ? 'bg-emerald-400/10 text-emerald-400' : 'bg-cyan-400/10 text-cyan-400'}`}>
                        {insight.severity === 'warning' ? <AlertTriangle size={16} className="mt-0.5 shrink-0" /> : <Info size={16} className="mt-0.5 shrink-0" />}
                        <p className="text-sm">{insight.message}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}
              {(dashboard?.category_balance && Object.keys(dashboard.category_balance).length > 0) && (
                <div className="bg-slate-800/50 rounded-2xl p-6 border border-slate-700/50">
                  <h3 className="font-semibold mb-4 flex items-center gap-2"><Users size={18} className="text-cyan-400" />Training Balance</h3>
                  <div className="space-y-4">
                    {Object.entries(dashboard.category_balance).map(([cat, val]) => (
                      <div key={cat}>
                        <div className="flex justify-between text-sm mb-1"><span className="capitalize">{cat}</span><span>{(val * 100).toFixed(0)}%</span></div>
                        <div className="h-2 bg-slate-700 rounded-full overflow-hidden"><div className="h-full bg-cyan-500 rounded-full" style={{ width: `${val * 100}%` }} /></div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
            <div className="bg-slate-800/50 rounded-2xl p-6 border border-slate-700/50">
              <h3 className="font-semibold mb-4 flex items-center gap-2"><Zap size={18} className="text-cyan-400" />30-Day Muscle Map</h3>
              <MuscleHeatmap muscleData={dashboard?.muscle_balance || {}} />
            </div>
          </div>
        )}

        {/* History Tab */}
        {activeTab === 'history' && (
          <div className="space-y-4">
            <h2 className="text-xl font-semibold">Workout History</h2>
            {workoutHistory.length === 0 ? (
              <div className="text-center py-12 text-slate-400"><p>No workouts yet. Upload your first video!</p></div>
            ) : workoutHistory.map(w => (
              <div key={w.id} className="bg-slate-800/50 rounded-xl p-5 border border-slate-700/50 hover:border-cyan-500/30 transition-all">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="font-medium">{w.created_at ? new Date(w.created_at).toLocaleDateString('en-US', { weekday: 'long', month: 'short', day: 'numeric' }) : 'Unknown date'}</p>
                    <p className="text-sm text-slate-400 mt-1">{w.exercises?.map(e => e.name).join(' • ') || 'No exercises detected'}</p>
                  </div>
                  <div className="text-right">
                    <p className="text-cyan-400 font-medium">{w.video_duration_sec ? `${(w.video_duration_sec / 60).toFixed(0)} min` : 'N/A'}</p>
                    <p className="text-xs text-slate-400">{w.exercises?.length || 0} exercises</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Coach Tab */}
        {activeTab === 'coach' && (
          <div className="max-w-2xl mx-auto">
            <div className="bg-slate-800/50 rounded-2xl border border-slate-700/50 overflow-hidden">
              <div className="p-4 border-b border-slate-700/50 flex items-center gap-3">
                <div className="w-10 h-10 rounded-full bg-gradient-to-br from-cyan-500 to-blue-600 flex items-center justify-center"><Mic size={18} /></div>
                <div><p className="font-medium">AI Coach</p><p className="text-xs text-emerald-400">Powered by Gemini</p></div>
              </div>
              <div className="h-96 overflow-y-auto p-4 space-y-4">
                {coachMessages.map((msg, i) => (
                  <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                    <div className={`max-w-[80%] p-3 rounded-2xl ${msg.role === 'user' ? 'bg-cyan-500 text-white' : 'bg-slate-700 text-slate-100'}`}>
                      <p className="text-sm whitespace-pre-wrap">{msg.text}</p>
                    </div>
                  </div>
                ))}
                {isCoachLoading && <div className="flex justify-start"><div className="bg-slate-700 p-3 rounded-2xl"><div className="flex gap-1">{[0,1,2].map(i => <div key={i} className="w-2 h-2 rounded-full bg-cyan-400 animate-bounce" style={{ animationDelay: `${i * 0.15}s` }} />)}</div></div></div>}
                <div ref={chatEndRef} />
              </div>
              <div className="p-4 border-t border-slate-700/50">
                <div className="flex gap-2">
                  <input type="text" value={coachInput} onChange={e => setCoachInput(e.target.value)} onKeyDown={e => e.key === 'Enter' && sendCoachMessage()} placeholder="Ask your coach..." className="flex-1 bg-slate-700/50 border border-slate-600 rounded-xl px-4 py-3 text-sm focus:outline-none focus:border-cyan-500" />
                  <button onClick={sendCoachMessage} disabled={!coachInput.trim() || isCoachLoading} className="px-4 py-3 rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 disabled:opacity-50"><Send size={18} /></button>
                </div>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}