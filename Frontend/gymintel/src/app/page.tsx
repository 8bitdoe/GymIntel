"use client";
import { useState, useEffect, useRef } from 'react';

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";

// Types
interface User {
  id: string; _id?: string; email: string; name: string;
  height_cm?: number; weight_kg?: number; experience_level: string;
  total_workouts: number; total_duration_min: number;
}
interface Workout {
  id: string; date: string; exercises: string[];
  duration_min: number; form_score: number;
}
interface DashboardData {
  workout_count: number; total_duration_min: number; avg_form_score: number | null;
  muscle_balance: Record<string, number>; category_balance: Record<string, number>;
  recent_workouts: Workout[]; insights: { type: string; severity: string; message: string }[];
}
interface PublicStats {
  total_users: number; total_workouts: number; avg_form_score: number;
  avg_muscle_activation: Record<string, number>; avg_depth_metrics: Record<string, number>;
  percentiles: Record<string, Record<string, number>>;
}
interface ComparisonData {
  user_stats: { muscle_activation: Record<string, number>; avg_knee_depth: number; avg_form_score: number };
  public_stats: PublicStats;
  percentile_rank: Record<string, number>;
}

// Extended Types for Detail View
interface FormFeedback {
  timestamp_sec: number; severity: string; note: string;
}
interface ExerciseSegment {
  name: string; reps: number; duration_sec: number; form_feedback: FormFeedback[];
}
interface WorkoutDetail extends Workout {
  created_at: string;
  summary: string;
  exercises: any[]; // using any for raw exercise array from backend which maps to ExerciseSegment
  muscle_activation: { muscles: Record<string, number> };
  hls_url?: string;
  video_url?: string;
}

// Icons
const Icons = {
  Dumbbell: () => <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 8h2m12 0h2M6 8v8m12-8v8M8 6h8a2 2 0 012 2v8a2 2 0 01-2 2H8a2 2 0 01-2-2V8a2 2 0 012-2z" /></svg>,
  Chart: () => <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" /></svg>,
  Upload: () => <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" /></svg>,
  Chat: () => <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" /></svg>,
  User: () => <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" /></svg>,
  Eye: () => <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" /><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" /></svg>,
  EyeOff: () => <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21" /></svg>,
  ArrowRight: () => <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 8l4 4m0 0l-4 4m4-4H3" /></svg>,
  Fire: () => <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20"><path fillRule="evenodd" d="M12.395 2.553a1 1 0 00-1.45-.385c-.345.23-.614.558-.822.88-.214.33-.403.713-.57 1.116-.334.804-.614 1.768-.84 2.734a31.365 31.365 0 00-.613 3.58 2.64 2.64 0 01-.945-1.067c-.328-.68-.398-1.534-.398-2.654A1 1 0 005.05 6.05 6.981 6.981 0 003 11a7 7 0 1011.95-4.95c-.592-.591-.98-.985-1.348-1.467-.363-.476-.724-1.063-1.207-2.03zM12.12 15.12A3 3 0 017 13s.879.5 2.5.5c0-1 .5-4 1.25-4.5.5 1 .786 1.293 1.371 1.879A2.99 2.99 0 0113 13a2.99 2.99 0 01-.879 2.121z" clipRule="evenodd" /></svg>,
  Sparkles: () => <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20"><path d="M5 2a1 1 0 011 1v1h1a1 1 0 010 2H6v1a1 1 0 01-2 0V6H3a1 1 0 010-2h1V3a1 1 0 011-1zm0 10a1 1 0 011 1v1h1a1 1 0 110 2H6v1a1 1 0 11-2 0v-1H3a1 1 0 110-2h1v-1a1 1 0 011-1zm7-10a1 1 0 01.967.744L14.146 7.2 17.5 9.134a1 1 0 010 1.732l-3.354 1.935-1.18 4.455a1 1 0 01-1.933 0L9.854 12.8 6.5 10.866a1 1 0 010-1.732l3.354-1.935 1.18-4.455A1 1 0 0112 2z" /></svg>,
  Globe: () => <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3.055 11H5a2 2 0 012 2v1a2 2 0 002 2 2 2 0 012 2v2.945M8 3.935V5.5A2.5 2.5 0 0010.5 8h.5a2 2 0 012 2 2 2 0 104 0 2 2 0 012-2h1.064M15 20.488V18a2 2 0 012-2h3.064M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>,
  LogOut: () => <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" /></svg>,
  Send: () => <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" /></svg>,
  TrendUp: () => <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" /></svg>,
  TrendDown: () => <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 17h8m0 0V9m0 8l-8-8-4 4-6-6" /></svg>,
};

// Radar Chart Component
function RadarChart({ data, comparisonData, size = 200 }: { 
  data: Record<string, number>; 
  comparisonData?: Record<string, number>;
  size?: number;
}) {
  const muscles = ['chest', 'shoulders', 'lats', 'biceps', 'triceps', 'quadriceps', 'hamstrings', 'glutes', 'core'];
  const center = size / 2;
  const maxRadius = size / 2 - 30;
  const angleStep = (2 * Math.PI) / muscles.length;
  
  const getPoint = (index: number, value: number) => {
    const angle = index * angleStep - Math.PI / 2;
    const radius = value * maxRadius;
    return { x: center + radius * Math.cos(angle), y: center + radius * Math.sin(angle) };
  };
  
  const userPoints = muscles.map((m, i) => getPoint(i, data[m] || 0));
  const userPath = userPoints.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x} ${p.y}`).join(' ') + ' Z';
  
  const compPath = comparisonData ? 
    muscles.map((m, i) => getPoint(i, comparisonData[m] || 0))
      .map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x} ${p.y}`).join(' ') + ' Z' : '';
  
  return (
    <svg width={size} height={size} className="mx-auto">
      {/* Grid circles */}
      {[0.25, 0.5, 0.75, 1].map(r => (
        <circle key={r} cx={center} cy={center} r={maxRadius * r} fill="none" stroke="#334155" strokeWidth="1" />
      ))}
      {/* Axes */}
      {muscles.map((_, i) => {
        const end = getPoint(i, 1);
        return <line key={i} x1={center} y1={center} x2={end.x} y2={end.y} stroke="#334155" strokeWidth="1" />;
      })}
      {/* Comparison area (public average) */}
      {compPath && <path d={compPath} fill="rgba(239, 68, 68, 0.2)" stroke="#ef4444" strokeWidth="2" />}
      {/* User area */}
      <path d={userPath} fill="rgba(59, 130, 246, 0.3)" stroke="#3b82f6" strokeWidth="2" />
      {/* Labels */}
      {muscles.map((m, i) => {
        const p = getPoint(i, 1.15);
        return (
          <text key={m} x={p.x} y={p.y} fill="#94a3b8" fontSize="10" textAnchor="middle" dominantBaseline="middle"
            className="capitalize">{m.replace('_', ' ').slice(0, 6)}</text>
        );
      })}
      {/* Dots */}
      {userPoints.map((p, i) => <circle key={i} cx={p.x} cy={p.y} r="4" fill="#3b82f6" />)}
    </svg>
  );
}

// Landing Page
function LandingPage({ onGetStarted }: { onGetStarted: () => void }) {
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900">
      <div className="relative overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-r from-blue-600/20 to-cyan-500/20 blur-3xl" />
        <div className="relative max-w-5xl mx-auto px-6 pt-12 pb-20">
          <nav className="flex justify-between items-center mb-16">
            <div className="flex items-center gap-2 text-white">
              <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-cyan-400 rounded-xl flex items-center justify-center">
                <Icons.Dumbbell />
              </div>
              <span className="text-2xl font-bold">GymIntel</span>
            </div>
            <button onClick={onGetStarted} className="px-5 py-2 bg-white/10 hover:bg-white/20 rounded-full text-white font-medium transition">
              Sign In
            </button>
          </nav>
          <div className="text-center max-w-3xl mx-auto">
            <div className="inline-flex items-center gap-2 px-4 py-2 bg-blue-500/20 rounded-full text-blue-300 text-sm mb-6">
              <Icons.Sparkles /> AI-Powered Workout Analysis
            </div>
            <h1 className="text-4xl md:text-6xl font-bold text-white mb-6 leading-tight">
              Your Personal<br />
              <span className="bg-gradient-to-r from-blue-400 to-cyan-300 bg-clip-text text-transparent">AI Gym Coach</span>
            </h1>
            <p className="text-lg text-slate-400 mb-8">
              Upload workout videos, get instant form feedback, track muscle balance, and compare yourself to others.
            </p>
            <button onClick={onGetStarted} className="px-8 py-4 bg-gradient-to-r from-blue-600 to-cyan-500 hover:from-blue-500 hover:to-cyan-400 rounded-2xl text-white font-bold text-lg transition shadow-2xl shadow-blue-500/25 inline-flex items-center gap-3">
              Start Training Smarter <Icons.ArrowRight />
            </button>
          </div>
        </div>
      </div>
      <div className="max-w-5xl mx-auto px-6 py-16 grid md:grid-cols-3 gap-6">
        {[
          { icon: <Icons.Upload />, title: "Video Analysis", desc: "AI detects exercises, counts reps, and analyzes form." },
          { icon: <Icons.Chart />, title: "Muscle Tracking", desc: "Visualize training balance with radar charts." },
          { icon: <Icons.Globe />, title: "Compare Publicly", desc: "See how you rank against other users." },
        ].map((f, i) => (
          <div key={i} className="p-5 bg-slate-800/50 rounded-2xl border border-slate-700/50">
            <div className="w-10 h-10 bg-blue-500/20 rounded-lg flex items-center justify-center text-blue-400 mb-3">{f.icon}</div>
            <h3 className="text-lg font-bold text-white mb-1">{f.title}</h3>
            <p className="text-slate-400 text-sm">{f.desc}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

// Auth Pages
function AuthPage({ onComplete }: { onComplete: (user: User) => void }) {
  const [mode, setMode] = useState<'login' | 'register'>('login');
  const [step, setStep] = useState(1);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPw, setShowPw] = useState(false);
  const [name, setName] = useState('');
  const [height, setHeight] = useState('');
  const [weight, setWeight] = useState('');
  const [experience, setExperience] = useState('intermediate');
  const [userId, setUserId] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleStep1 = async () => {
    if (!email || !password) return;
    setLoading(true); setError('');
    try {
      if (mode === 'register') {
        const res = await fetch(`${API_URL}/auth/register`, {
          method: 'POST', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ email, password })
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || 'Registration failed');
        setUserId(data.user_id);
        setStep(2);
      } else {
        const res = await fetch(`${API_URL}/auth/login`, {
          method: 'POST', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ email, password })
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || 'Login failed');
        localStorage.setItem('gymintel_user', JSON.stringify(data.user));
        onComplete(data.user);
      }
    } catch (e: any) { setError(e.message); }
    setLoading(false);
  };

  const handleStep2 = async () => {
    if (!name) return;
    setLoading(true); setError('');
    try {
      const res = await fetch(`${API_URL}/auth/register/complete`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: userId, name,
          height_cm: height ? parseFloat(height) : null,
          weight_kg: weight ? parseFloat(weight) : null,
          experience_level: experience
        })
      });
      if (!res.ok) throw new Error('Failed to complete registration');
      // Auto login
      const loginRes = await fetch(`${API_URL}/auth/login`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password })
      });
      const data = await loginRes.json();
      localStorage.setItem('gymintel_user', JSON.stringify(data.user));
      onComplete(data.user);
    } catch (e: any) { setError(e.message); }
    setLoading(false);
  };

  return (
    <div className="min-h-screen bg-slate-900 flex items-center justify-center p-6">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <div className="w-14 h-14 bg-gradient-to-br from-blue-500 to-cyan-400 rounded-2xl flex items-center justify-center mx-auto mb-4 text-white">
            <Icons.Dumbbell />
          </div>
          <h2 className="text-2xl font-bold text-white mb-1">
            {mode === 'login' ? 'Welcome Back' : step === 1 ? 'Create Account' : 'Complete Profile'}
          </h2>
          <p className="text-slate-400 text-sm">
            {mode === 'login' ? 'Sign in to continue' : step === 1 ? 'Step 1 of 2' : 'Step 2 of 2 - Tell us about yourself'}
          </p>
        </div>

        {error && <div className="mb-4 p-3 bg-red-500/20 border border-red-500/50 rounded-lg text-red-300 text-sm">{error}</div>}

        {step === 1 ? (
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-slate-400 mb-2">Email</label>
              <input type="email" value={email} onChange={e => setEmail(e.target.value)}
                className="w-full bg-slate-800 border border-slate-700 rounded-xl p-4 text-white focus:ring-2 focus:ring-blue-500 outline-none"
                placeholder="you@example.com" />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-400 mb-2">Password</label>
              <div className="relative">
                <input type={showPw ? 'text' : 'password'} value={password} onChange={e => setPassword(e.target.value)}
                  className="w-full bg-slate-800 border border-slate-700 rounded-xl p-4 pr-12 text-white focus:ring-2 focus:ring-blue-500 outline-none"
                  placeholder="••••••••" />
                <button type="button" onClick={() => setShowPw(!showPw)}
                  className="absolute right-4 top-1/2 -translate-y-1/2 text-slate-400 hover:text-white">
                  {showPw ? <Icons.EyeOff /> : <Icons.Eye />}
                </button>
              </div>
            </div>
            <button onClick={handleStep1} disabled={loading || !email || !password}
              className="w-full py-4 bg-gradient-to-r from-blue-600 to-cyan-500 hover:from-blue-500 hover:to-cyan-400 rounded-xl text-white font-bold text-lg transition shadow-lg disabled:opacity-50">
              {loading ? 'Please wait...' : mode === 'login' ? 'Sign In' : 'Continue'}
            </button>
            <p className="text-center text-slate-400 text-sm">
              {mode === 'login' ? "Don't have an account? " : "Already have an account? "}
              <button onClick={() => { setMode(mode === 'login' ? 'register' : 'login'); setError(''); }}
                className="text-blue-400 hover:underline">{mode === 'login' ? 'Sign up' : 'Sign in'}</button>
            </p>
          </div>
        ) : (
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-slate-400 mb-2">Name *</label>
              <input type="text" value={name} onChange={e => setName(e.target.value)}
                className="w-full bg-slate-800 border border-slate-700 rounded-xl p-4 text-white focus:ring-2 focus:ring-blue-500 outline-none"
                placeholder="Your name" />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-slate-400 mb-2">Height (cm)</label>
                <input type="number" value={height} onChange={e => setHeight(e.target.value)}
                  className="w-full bg-slate-800 border border-slate-700 rounded-xl p-4 text-white focus:ring-2 focus:ring-blue-500 outline-none"
                  placeholder="175" />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-400 mb-2">Weight (kg)</label>
                <input type="number" value={weight} onChange={e => setWeight(e.target.value)}
                  className="w-full bg-slate-800 border border-slate-700 rounded-xl p-4 text-white focus:ring-2 focus:ring-blue-500 outline-none"
                  placeholder="70" />
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-400 mb-2">Experience Level</label>
              <select value={experience} onChange={e => setExperience(e.target.value)}
                className="w-full bg-slate-800 border border-slate-700 rounded-xl p-4 text-white focus:ring-2 focus:ring-blue-500 outline-none">
                <option value="beginner">Beginner (0-1 years)</option>
                <option value="intermediate">Intermediate (1-3 years)</option>
                <option value="advanced">Advanced (3+ years)</option>
              </select>
            </div>
            <button onClick={handleStep2} disabled={loading || !name}
              className="w-full py-4 bg-gradient-to-r from-blue-600 to-cyan-500 hover:from-blue-500 hover:to-cyan-400 rounded-xl text-white font-bold text-lg transition shadow-lg disabled:opacity-50">
              {loading ? 'Creating account...' : 'Complete Registration'}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

// Dashboard
function Dashboard({ user, onNavigate }: { user: User; onNavigate: (tab: string) => void }) {
  const [data, setData] = useState<DashboardData | null>(null);
  const [comparison, setComparison] = useState<ComparisonData | null>(null);
  const [aiSummary, setAiSummary] = useState('');
  const [loading, setLoading] = useState(true);
  const [selectedWorkoutId, setSelectedWorkoutId] = useState<string | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      const userId = user.id || user._id;
      console.log(`Fetching dashboard for user: ${userId} at ${API_URL}`);
      try {
        const [dashRes, compRes] = await Promise.all([
          fetch(`${API_URL}/users/${userId}/dashboard`),
          fetch(`${API_URL}/stats/compare/${userId}`)
        ]);
        const dashData = await dashRes.json();
        const compData = await compRes.json();
        setData(dashData);
        setComparison(compData);
        
        // Generate AI summary based on data
        const summary = generateSummary(dashData, compData);
        setAiSummary(summary);
      } catch (e) {
        console.error('Dashboard fetch error:', e);
        // Use mock data for demo
        setData({
          workout_count: 8, total_duration_min: 240, avg_form_score: 78,
          muscle_balance: { chest: 0.7, shoulders: 0.6, lats: 0.4, biceps: 0.5, triceps: 0.55, quadriceps: 0.8, hamstrings: 0.5, glutes: 0.7, core: 0.45 },
          category_balance: { push: 0.65, pull: 0.42, legs: 0.75, core: 0.45 },
          recent_workouts: [{ id: '1', date: new Date().toISOString(), exercises: ['Squat', 'Leg Press'], duration_min: 45, form_score: 82 }],
          insights: [{ type: 'warning', severity: 'warning', message: 'Your pull muscles need more attention.' }]
        });
        setAiSummary("You've been consistent this week! Focus on adding more back exercises to balance your push/pull ratio.");
      }
      setLoading(false);
    };
    fetchData();
  }, [user]);

  const generateSummary = (dash: DashboardData, comp: ComparisonData | null) => {
    const parts = [];
    if (dash.workout_count > 0) {
      parts.push(`You've completed ${dash.workout_count} workouts totaling ${Math.round(dash.total_duration_min)} minutes.`);
    }
    if (dash.avg_form_score) {
      const rank = comp?.percentile_rank?.form_score || 50;
      parts.push(`Your form score of ${Math.round(dash.avg_form_score)} puts you in the top ${100 - rank}% of users.`);
    }
    if (dash.category_balance) {
      const { push, pull } = dash.category_balance;
      if (push > pull * 1.5) parts.push("Consider adding more pulling exercises for balance.");
      if (pull > push * 1.5) parts.push("Great back work! Don't neglect your pressing movements.");
    }
    return parts.join(' ') || "Upload your first workout to get personalized insights!";
  };

  if (loading) return <div className="flex items-center justify-center h-64"><div className="animate-spin w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full" /></div>;
  if (!data) return null;

  if (selectedWorkoutId) {
    return <WorkoutDetailPage workoutId={selectedWorkoutId} onBack={() => setSelectedWorkoutId(null)} />;
  }

  const { workout_count, total_duration_min, avg_form_score, muscle_balance, category_balance, recent_workouts, insights } = data;
  const publicMuscle = comparison?.public_stats?.avg_muscle_activation || {};

  return (
    <div className="space-y-5 pb-24">
      <div className="flex justify-between items-start">
        <div>
          <h1 className="text-xl font-bold text-white">Hey, {user.name} 👋</h1>
          <p className="text-slate-400 text-sm">Your training overview</p>
        </div>
        <div className="text-right">
          <div className="text-2xl font-bold text-green-400">{avg_form_score ? Math.round(avg_form_score) : '--'}</div>
          <div className="text-xs text-slate-500">Form Score</div>
        </div>
      </div>

      {/* AI Summary */}
      <div className="p-4 bg-gradient-to-r from-blue-600/20 to-cyan-500/20 rounded-xl border border-blue-500/30">
        <div className="flex items-start gap-3">
          <div className="w-8 h-8 bg-blue-500 rounded-lg flex items-center justify-center flex-shrink-0 text-white"><Icons.Sparkles /></div>
          <div>
            <div className="text-xs font-medium text-blue-300 mb-1">AI Coach Summary</div>
            <p className="text-sm text-slate-300 leading-relaxed">{aiSummary}</p>
          </div>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-2">
        {[
          { label: 'Workouts', value: workout_count, color: 'text-white' },
          { label: 'Minutes', value: Math.round(total_duration_min), color: 'text-white' },
          { label: 'Streak', value: Math.max(1, Math.floor(workout_count / 3)), icon: <Icons.Fire />, color: 'text-orange-400' },
        ].map((s, i) => (
          <div key={i} className="bg-slate-800/80 p-3 rounded-xl border border-slate-700/50 text-center">
            <div className={`text-xl font-bold ${s.color} flex items-center justify-center gap-1`}>{s.value}{s.icon}</div>
            <div className="text-xs text-slate-500">{s.label}</div>
          </div>
        ))}
      </div>

      {/* Radar Chart with Comparison */}
      <div className="bg-slate-800/80 p-4 rounded-xl border border-slate-700/50">
        <div className="flex justify-between items-center mb-2">
          <h3 className="font-semibold text-white text-sm">Muscle Activation</h3>
          <div className="flex items-center gap-3 text-xs">
            <span className="flex items-center gap-1"><span className="w-3 h-3 bg-blue-500 rounded-full" />You</span>
            <span className="flex items-center gap-1"><span className="w-3 h-3 bg-red-500 rounded-full" />Public Avg</span>
          </div>
        </div>
        <RadarChart data={muscle_balance || {}} comparisonData={publicMuscle} size={220} />
      </div>

      {/* Public Comparison */}
      {comparison && (
        <div className="bg-slate-800/80 p-4 rounded-xl border border-slate-700/50">
          <h3 className="font-semibold text-white text-sm mb-3 flex items-center gap-2"><Icons.Globe /> How You Compare</h3>
          <div className="space-y-3">
            {Object.entries(comparison.percentile_rank || {}).map(([metric, percentile]) => (
              <div key={metric} className="flex items-center justify-between">
                <span className="text-sm text-slate-400 capitalize">{metric.replace('_', ' ')}</span>
                <div className="flex items-center gap-2">
                  <div className="w-24 h-2 bg-slate-700 rounded-full overflow-hidden">
                    <div className={`h-full rounded-full ${percentile >= 75 ? 'bg-green-500' : percentile >= 50 ? 'bg-blue-500' : 'bg-yellow-500'}`}
                      style={{ width: `${percentile}%` }} />
                  </div>
                  <span className={`text-sm font-medium ${percentile >= 75 ? 'text-green-400' : percentile >= 50 ? 'text-blue-400' : 'text-yellow-400'}`}>
                    Top {100 - percentile}%
                  </span>
                </div>
              </div>
            ))}
            {comparison.public_stats && (
              <div className="pt-2 border-t border-slate-700 text-xs text-slate-500">
                Based on {comparison.public_stats.total_workouts} workouts from {comparison.public_stats.total_users} users
              </div>
            )}
          </div>
        </div>
      )}

      {/* Category Balance */}
      <div className="bg-slate-800/80 p-4 rounded-xl border border-slate-700/50">
        <h3 className="font-semibold text-white mb-3 text-sm">Training Balance</h3>
        <div className="grid grid-cols-4 gap-2">
          {Object.entries(category_balance || {}).map(([cat, val]) => (
            <div key={cat} className="text-center">
              <div className="relative h-16 bg-slate-700/50 rounded-lg overflow-hidden">
                <div className="absolute bottom-0 w-full bg-gradient-to-t from-blue-500 to-blue-400 transition-all" style={{ height: `${val * 100}%` }} />
              </div>
              <div className="text-xs text-slate-400 mt-1 capitalize">{cat}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Insights */}
      {insights?.map((insight, i) => (
        <div key={i} className={`p-3 rounded-xl border text-sm ${insight.severity === 'warning' ? 'bg-yellow-500/10 border-yellow-500/30 text-yellow-200' : 'bg-green-500/10 border-green-500/30 text-green-200'}`}>
          {insight.message}
        </div>
      ))}

      {/* Recent Workouts */}
      <div>
        <h3 className="font-semibold text-white mb-2 text-sm">Recent Workouts</h3>
        {recent_workouts.length === 0 ? (
          <div className="p-6 bg-slate-800/50 rounded-xl border border-dashed border-slate-600 text-center">
            <p className="text-slate-400 mb-3">No workouts yet</p>
            <button onClick={() => onNavigate('upload')} className="px-4 py-2 bg-blue-600 rounded-lg text-white text-sm font-medium">
              Upload Your First Workout
            </button>
          </div>
        ) : (
          <div className="space-y-2">
            {recent_workouts.map(w => (
              <div key={w.id} 
                onClick={() => setSelectedWorkoutId(w.id)}
                className="p-3 bg-slate-800/80 rounded-xl border border-slate-700/50 flex items-center gap-3 cursor-pointer hover:bg-slate-750 hover:border-blue-500/30 transition">
                <div className="w-10 h-10 bg-slate-700 rounded-lg flex items-center justify-center text-lg">🏋️</div>
                <div className="flex-1 min-w-0">
                  <div className="font-medium text-white text-sm truncate">{w.exercises.join(', ')}</div>
                  <div className="text-xs text-slate-500">{new Date(w.date).toLocaleDateString()} • {Math.round(w.duration_min)} min</div>
                </div>
                <div className={`text-lg font-bold ${w.form_score >= 80 ? 'text-green-400' : 'text-yellow-400'}`}>{w.form_score}</div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}


// Workout Detail View
function WorkoutDetailPage({ workoutId, onBack }: { workoutId: string; onBack: () => void }) {
  const [workout, setWorkout] = useState<WorkoutDetail | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`${API_URL}/workouts/${workoutId}`)
      .then(res => res.json())
      .then(data => {
        setWorkout(data);
        setLoading(false);
      })
      .catch(err => {
        console.error("Failed to load workout", err);
        setLoading(false);
      });
  }, [workoutId]);

  useEffect(() => {
    // HLS Support
    if (workout?.hls_url) {
      const video = document.getElementById('workout-video') as HTMLVideoElement;
      if (video) {
        import('hls.js').then((HlsModule) => {
          const Hls = HlsModule.default;
          if (Hls.isSupported()) {
            const hls = new Hls();
            hls.loadSource(workout.hls_url!);
            hls.attachMedia(video);
          } else if (video.canPlayType('application/vnd.apple.mpegurl')) {
            video.src = workout.hls_url!;
          }
        }).catch(() => console.log('HLS.js not loaded, assuming native support or simple video'));
      }
    }
  }, [workout]);

  if (loading) return <div className="flex items-center justify-center h-64"><div className="animate-spin w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full" /></div>;
  if (!workout) return <div className="text-center p-8 text-slate-400">Workout not found</div>;

  const muscles = workout.muscle_activation?.muscles || {};
  const sortedMuscles = Object.entries(muscles).sort(([,a], [,b]) => b - a).slice(0, 5);

  return (
    <div className="pb-24 space-y-6">
      <button onClick={onBack} className="flex items-center gap-2 text-slate-400 hover:text-white transition">
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" /></svg>
        Back to Dashboard
      </button>

      <div>
        <h2 className="text-2xl font-bold text-white mb-1">Workout Analysis</h2>
        <div className="text-sm text-slate-400">{new Date(workout.created_at).toLocaleString()}</div>
      </div>

      {workout.hls_url ? (
        <div className="bg-black rounded-xl overflow-hidden aspect-video relative shadow-lg">
          <video id="workout-video" controls className="w-full h-full" />
        </div>
      ) : workout.video_url ? (
           <div className="bg-black rounded-xl overflow-hidden aspect-video relative shadow-lg">
          <video controls className="w-full h-full" src={workout.video_url} />
        </div>
      ) : null}

      <div className="p-5 bg-slate-800/80 rounded-xl border border-slate-700/50">
        <h3 className="font-semibold text-white mb-2 flex items-center gap-2"><Icons.Sparkles /> AI Summary</h3>
        <p className="text-sm text-slate-300 leading-relaxed">{workout.summary || "No summary available."}</p>
      </div>

      <div className="grid md:grid-cols-2 gap-6">
        <div>
          <h3 className="font-semibold text-white mb-3">Muscle Activation</h3>
          <div className="bg-slate-800/80 p-4 rounded-xl border border-slate-700/50 space-y-3">
             {sortedMuscles.length > 0 ? sortedMuscles.map(([m, v]) => (
                <div key={m}>
                    <div className="flex justify-between text-xs mb-1">
                        <span className="capitalize text-slate-300">{m.replace('_', ' ')}</span>
                        <span className="text-blue-400 font-mono">{Math.round(v * 100)}%</span>
                    </div>
                    <div className="w-full bg-slate-700 rounded-full h-1.5">
                        <div className="bg-blue-500 h-1.5 rounded-full" style={{ width: `${v * 100}%` }} />
                    </div>
                </div>
             )) : <div className="text-slate-500 text-sm">No muscle data</div>}
          </div>
        </div>

        <div>
          <h3 className="font-semibold text-white mb-3">Exercises</h3>
          <div className="space-y-3">
            {(workout.exercises || []).map((ex: any, i: number) => (
              <div key={i} className="bg-slate-800/80 p-4 rounded-xl border border-slate-700/50">
                 <div className="flex justify-between items-start mb-2">
                    <div>
                        <h4 className="font-bold text-white capitalize">{ex.name}</h4>
                        <div className="text-xs text-slate-400">{ex.reps} Reps • {Math.round(ex.duration_sec || 0)}s duration</div>
                    </div>
                </div>
                {ex.form_feedback && ex.form_feedback.length > 0 && (
                  <div className="mt-2 space-y-1">
                    {ex.form_feedback.map((f: any, j: number) => (
                       <div key={j} className={`flex gap-2 text-xs ${f.severity === 'warning' ? 'text-yellow-400' : f.severity === 'critical' ? 'text-red-400' : 'text-slate-400'}`}>
                          <span>• @{Math.round(f.timestamp_sec)}s: {f.note}</span>
                       </div>
                    ))}
                  </div>
                )}
              </div>
            ))}
            {(!workout.exercises || workout.exercises.length === 0) && <div className="text-slate-500 text-sm">No exercises detected</div>}
          </div>
        </div>
      </div>
    </div>
  );
}

// Upload Page
function UploadPage({ user, onComplete }: { user: User; onComplete: () => void }) {
  const [file, setFile] = useState<File | null>(null);
  const [progress, setProgress] = useState(0);
  const [status, setStatus] = useState('');
  const [uploading, setUploading] = useState(false);

  const handleUpload = async (selectedFile: File) => {
    setFile(selectedFile);
    setUploading(true);
    setStatus('Uploading video...');
    
    const formData = new FormData();
    formData.append('file', selectedFile);
    formData.append('user_id', user.id || user._id || '');

    try {
      const res = await fetch(`${API_URL}/workouts/upload`, { method: 'POST', body: formData });
      const data = await res.json();
      const workoutId = data.workout_id;
      
      // Poll for status
      const poll = setInterval(async () => {
        const statusRes = await fetch(`${API_URL}/workouts/${workoutId}/status`);
        const statusData = await statusRes.json();
        setProgress(statusData.progress || 0);
        setStatus(statusData.message || 'Processing...');
        
        if (statusData.db_status === 'complete') {
          clearInterval(poll);
          setTimeout(onComplete, 1000);
        } else if (statusData.db_status === 'failed') {
          clearInterval(poll);
          setStatus('Processing failed');
        }
      }, 2000);
    } catch (e) {
      setStatus('Upload failed');
      setUploading(false);
    }
  };

  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] pb-24">
      <h2 className="text-xl font-bold text-white mb-6">Upload Workout</h2>
      {!uploading ? (
        <label className="w-full max-w-sm p-8 bg-slate-800/80 border-2 border-dashed border-slate-600 rounded-2xl flex flex-col items-center cursor-pointer hover:border-blue-500 transition">
          <input type="file" accept="video/*" onChange={e => e.target.files?.[0] && handleUpload(e.target.files[0])} className="hidden" />
          <div className="w-14 h-14 bg-slate-700 rounded-full flex items-center justify-center mb-3 text-blue-400"><Icons.Upload /></div>
          <div className="text-white font-medium mb-1">Drop video here</div>
          <div className="text-slate-400 text-sm">or click to browse</div>
        </label>
      ) : (
        <div className="w-full max-w-sm p-5 bg-slate-800/80 rounded-xl border border-slate-700">
          <div className="flex justify-between text-sm mb-2">
            <span className="text-slate-300">{status}</span>
            <span className="text-blue-400">{Math.round(progress)}%</span>
          </div>
          <div className="w-full h-2 bg-slate-700 rounded-full overflow-hidden">
            <div className="h-full bg-gradient-to-r from-blue-600 to-cyan-500 transition-all" style={{ width: `${progress}%` }} />
          </div>
        </div>
      )}
    </div>
  );
}

// Coach Chat
function CoachPage({ user }: { user: User }) {
  const [messages, setMessages] = useState([{ role: 'ai', text: `Hey ${user.name}! 💪 Ask me anything about your training!` }]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const endRef = useRef<HTMLDivElement>(null);

  const send = async () => {
    if (!input.trim()) return;
    setMessages(m => [...m, { role: 'user', text: input }]);
    const msg = input;
    setInput('');
    setLoading(true);
    try {
      const res = await fetch(`${API_URL}/coach/${user.id || user._id}/chat`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: msg })
      });
      const data = await res.json();
      setMessages(m => [...m, { role: 'ai', text: data.response }]);
    } catch {
      setMessages(m => [...m, { role: 'ai', text: "Based on your recent workouts, you're doing great with legs! Consider adding more back exercises for balance." }]);
    }
    setLoading(false);
  };

  useEffect(() => { endRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [messages]);

  return (
    <div className="flex flex-col h-full pb-20">
      <h2 className="text-lg font-bold text-white mb-3">AI Coach</h2>
      <div className="flex-1 overflow-y-auto space-y-3">
        {messages.map((m, i) => (
          <div key={i} className={`flex gap-2 ${m.role === 'user' ? 'justify-end' : ''}`}>
            {m.role === 'ai' && <div className="w-7 h-7 bg-blue-600 rounded-full flex items-center justify-center flex-shrink-0 text-white"><Icons.Sparkles /></div>}
            <div className={`max-w-[80%] p-3 rounded-xl text-sm ${m.role === 'user' ? 'bg-blue-600 text-white rounded-br-none' : 'bg-slate-800 text-slate-200 border border-slate-700 rounded-bl-none'}`}>
              {m.text}
            </div>
          </div>
        ))}
        {loading && (
          <div className="flex gap-2">
            <div className="w-7 h-7 bg-blue-600 rounded-full flex items-center justify-center text-white"><Icons.Sparkles /></div>
            <div className="bg-slate-800 border border-slate-700 rounded-xl p-3 flex gap-1">
              <span className="w-2 h-2 bg-slate-500 rounded-full animate-bounce" />
              <span className="w-2 h-2 bg-slate-500 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }} />
              <span className="w-2 h-2 bg-slate-500 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }} />
            </div>
          </div>
        )}
        <div ref={endRef} />
      </div>
      <div className="mt-3 flex gap-2">
        <input value={input} onChange={e => setInput(e.target.value)} onKeyDown={e => e.key === 'Enter' && send()}
          placeholder="Ask about your training..." className="flex-1 bg-slate-800 border border-slate-700 rounded-full px-4 py-2 text-white text-sm outline-none focus:ring-2 focus:ring-blue-500" />
        <button onClick={send} className="w-10 h-10 bg-blue-600 rounded-full flex items-center justify-center text-white"><Icons.Send /></button>
      </div>
    </div>
  );
}

// Profile
function ProfilePage({ user, onLogout }: { user: User; onLogout: () => void }) {
  return (
    <div className="pb-24">
      <h2 className="text-lg font-bold text-white mb-4">Profile</h2>
      <div className="flex items-center gap-3 p-4 bg-slate-800/80 rounded-xl border border-slate-700/50 mb-4">
        <div className="w-12 h-12 bg-gradient-to-br from-blue-500 to-cyan-400 rounded-full flex items-center justify-center text-xl font-bold text-white">
          {user.name?.charAt(0)?.toUpperCase() || 'U'}
        </div>
        <div>
          <div className="font-bold text-white">{user.name}</div>
          <div className="text-sm text-slate-400">{user.email}</div>
        </div>
      </div>
      <div className="space-y-2 mb-6">
        {[
          ['Experience', user.experience_level],
          ['Height', user.height_cm ? `${user.height_cm} cm` : 'Not set'],
          ['Weight', user.weight_kg ? `${user.weight_kg} kg` : 'Not set'],
          ['Workouts', user.total_workouts],
          ['Total Time', `${Math.round(user.total_duration_min || 0)} min`]
        ].map(([l, v]) => (
          <div key={String(l)} className="p-3 bg-slate-800/80 rounded-xl border border-slate-700/50">
            <div className="text-xs text-slate-400">{l}</div>
            <div className="text-white font-medium capitalize">{v}</div>
          </div>
        ))}
      </div>
      <button onClick={onLogout} className="w-full p-3 bg-red-500/20 border border-red-500/50 rounded-xl text-red-400 font-medium flex items-center justify-center gap-2">
        <Icons.LogOut /> Sign Out
      </button>
    </div>
  );
}

// Main App
export default function GymIntelApp() {
  const [view, setView] = useState<'landing' | 'auth' | 'app'>('landing');
  const [user, setUser] = useState<User | null>(null);
  const [tab, setTab] = useState('dashboard');

  useEffect(() => {
    const saved = localStorage.getItem('gymintel_user');
    if (saved) {
      try {
        setUser(JSON.parse(saved));
        setView('app');
      } catch {}
    }
  }, []);

  const handleLogout = () => {
    localStorage.removeItem('gymintel_user');
    setUser(null);
    setView('landing');
  };

  if (view === 'landing') return <LandingPage onGetStarted={() => setView('auth')} />;
  if (view === 'auth' || !user) return <AuthPage onComplete={u => { setUser(u); setView('app'); }} />;

  return (
    <div className="min-h-screen bg-slate-900 text-white">
      <div className="max-w-lg mx-auto p-4 min-h-screen">
        {tab === 'dashboard' && <Dashboard user={user} onNavigate={setTab} />}
        {tab === 'upload' && <UploadPage user={user} onComplete={() => setTab('dashboard')} />}
        {tab === 'coach' && <CoachPage user={user} />}
        {tab === 'profile' && <ProfilePage user={user} onLogout={handleLogout} />}
      </div>
      <nav className="fixed bottom-0 left-0 right-0 bg-slate-800 border-t border-slate-700 p-2 z-50">
        <div className="max-w-lg mx-auto flex justify-around">
          {[
            { id: 'dashboard', icon: <Icons.Chart />, label: 'Dashboard' },
            { id: 'upload', icon: <Icons.Upload />, label: 'Upload', accent: true },
            { id: 'coach', icon: <Icons.Chat />, label: 'Coach' },
            { id: 'profile', icon: <Icons.User />, label: 'Profile' },
          ].map(t => (
            <button key={t.id} onClick={() => setTab(t.id)}
              className={`flex flex-col items-center p-2 w-14 transition ${tab === t.id ? 'text-blue-400' : 'text-slate-500 hover:text-slate-300'}`}>
              {t.accent ? (
                <div className={`w-9 h-9 rounded-full flex items-center justify-center ${tab === t.id ? 'bg-blue-600' : 'bg-slate-700'}`}>{t.icon}</div>
              ) : t.icon}
              <span className="text-xs mt-1">{t.label}</span>
            </button>
          ))}
        </div>
      </nav>
    </div>
  );
}