const API_URL = "http://localhost:8000/api";
let currentUser = null;

// ==========================================
// Initialization & Navigation
// ==========================================

document.addEventListener('DOMContentLoaded', () => {
    const savedUserId = localStorage.getItem('gymintel_user_id');
    if (savedUserId) {
        fetchUser(savedUserId);
    } else {
        switchView('view-login');
    }
});

function switchView(viewId) {
    document.querySelectorAll('.view').forEach(el => el.classList.add('hidden'));
    const view = document.getElementById(viewId);
    if (view) view.classList.remove('hidden');

    document.querySelectorAll('.nav-btn').forEach(btn => btn.classList.remove('active'));
    if (viewId === 'view-dashboard') document.querySelector('button[onclick*="dashboard"]').classList.add('active');
    if (viewId === 'view-coach') document.querySelector('button[onclick*="coach"]').classList.add('active');
    if (viewId === 'view-upload') document.querySelector('button[onclick*="upload"]').classList.add('active');

    if (viewId === 'view-dashboard' && currentUser) loadDashboard();
}

// ==========================================
// User Management
// ==========================================

async function handleLogin(e) {
    e.preventDefault();
    const email = document.getElementById('login-email').value;
    const name = document.getElementById('login-name').value || "User";

    try {
        const response = await fetch(`${API_URL}/users`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, name })
        });
        const data = await response.json();
        if (data.user_id) {
            localStorage.setItem('gymintel_user_id', data.user_id);
            await fetchUser(data.user_id);
        }
    } catch (err) {
        console.error("Login failed", err);
        alert("Login failed. Check console.");
    }
}

async function fetchUser(userId) {
    try {
        const response = await fetch(`${API_URL}/users/${userId}`);
        if (!response.ok) throw new Error("User not found");
        currentUser = await response.json();
        
        // FIX: Backend returns 'id', not '_id'
        // Normalize to ensure we have both for compatibility
        if (!currentUser._id && currentUser.id) {
            currentUser._id = currentUser.id;
        }
        
        document.getElementById('user-name').textContent = currentUser.name;
        document.getElementById('user-profile').classList.remove('hidden');
        document.querySelector('footer').classList.remove('hidden');
        switchView('view-dashboard');
    } catch (err) {
        console.error("Fetch user failed", err);
        localStorage.removeItem('gymintel_user_id');
        switchView('view-login');
    }
}

function logout() {
    localStorage.removeItem('gymintel_user_id');
    location.reload();
}

// ==========================================
// Dashboard
// ==========================================

async function loadDashboard() {
    if (!currentUser) return;
    
    // FIX: Use .id instead of ._id (backend returns 'id')
    const userId = currentUser.id || currentUser._id;

    try {
        const response = await fetch(`${API_URL}/users/${userId}/dashboard`);
        const data = await response.json();

        document.getElementById('dash-workouts-count').textContent = data.workout_count;
        document.getElementById('dash-minutes').textContent = Math.round(data.total_duration_min);
        document.getElementById('dash-form-score').textContent = data.avg_form_score ? Math.round(data.avg_form_score) : "--";

        // FIX: Render muscle activation map
        renderMuscleMap(data.muscle_balance || {});

        // Render Recent Workouts
        const list = document.getElementById('workouts-list');
        list.innerHTML = '';

        if (data.recent_workouts.length === 0) {
            list.innerHTML = '<div class="text-center text-slate-500 py-8">No workouts yet. Upload one!</div>';
        } else {
            data.recent_workouts.forEach(w => {
                const el = document.createElement('div');
                el.className = 'bg-slate-800 p-3 rounded-xl border border-slate-700 flex items-center gap-4 cursor-pointer hover:bg-slate-750 transition';
                el.onclick = () => loadWorkoutDetail(w.id);
                const scoreColor = w.form_score >= 80 ? 'text-green-400' : (w.form_score >= 60 ? 'text-yellow-400' : 'text-red-400');
                el.innerHTML = `
                    <div class="h-12 w-12 bg-slate-700 rounded-lg flex items-center justify-center text-xl">🏋️</div>
                    <div class="flex-1">
                        <h4 class="font-semibold text-sm line-clamp-1">${w.exercises.join(', ') || 'Workout'}</h4>
                        <div class="text-xs text-slate-400">${new Date(w.date).toLocaleDateString()} • ${Math.round(w.duration_min)} min</div>
                    </div>
                    <div class="text-right">
                        <div class="text-lg font-bold ${scoreColor}">${w.form_score || '--'}</div>
                        <div class="text-[10px] text-slate-500 uppercase">Score</div>
                    </div>
                `;
                list.appendChild(el);
            });
        }
    } catch (err) {
        console.error("Dashboard error", err);
    }
}

// FIX: Add muscle map rendering function
function renderMuscleMap(muscleBalance) {
    const container = document.getElementById('muscle-map-container');
    
    // Get sorted muscles by activation
    const muscles = Object.entries(muscleBalance)
        .filter(([_, v]) => v > 0.05)
        .sort(([,a], [,b]) => b - a);
    
    if (muscles.length === 0) {
        container.innerHTML = '<div class="text-slate-500 text-sm">No muscle data yet</div>';
        return;
    }
    
    // Render as a simple bar chart
    const html = `
        <div class="w-full space-y-2 p-2">
            ${muscles.slice(0, 8).map(([muscle, value]) => {
                const pct = Math.round(value * 100);
                const barColor = value > 0.7 ? 'bg-red-500' : value > 0.4 ? 'bg-blue-500' : 'bg-blue-400';
                return `
                    <div class="flex items-center gap-2">
                        <span class="text-xs text-slate-400 w-24 capitalize truncate">${muscle.replace('_', ' ')}</span>
                        <div class="flex-1 bg-slate-700 rounded-full h-2">
                            <div class="${barColor} h-2 rounded-full transition-all" style="width: ${pct}%"></div>
                        </div>
                        <span class="text-xs text-slate-500 w-8 text-right">${pct}%</span>
                    </div>
                `;
            }).join('')}
        </div>
    `;
    container.innerHTML = html;
}

// ==========================================
// Workout Detail
// ==========================================

async function loadWorkoutDetail(workoutId) {
    try {
        const response = await fetch(`${API_URL}/workouts/${workoutId}`);
        const workout = await response.json();
        const container = document.getElementById('workout-detail-content');
        
        const muscles = workout.muscle_activation?.muscles || {};
        const muscleList = Object.entries(muscles)
            .sort(([,a], [,b]) => b - a)
            .slice(0, 5)
            .map(([m, v]) => `
                <div class="flex justify-between text-sm mb-1">
                    <span class="capitalize text-slate-300">${m.replace('_', ' ')}</span>
                    <span class="text-blue-400 font-mono">${Math.round(v * 100)}%</span>
                </div>
                <div class="w-full bg-slate-700 rounded-full h-1.5 mb-2">
                    <div class="bg-blue-500 h-1.5 rounded-full" style="width: ${v * 100}%"></div>
                </div>
            `).join('');

        const exercisesList = workout.exercises.map(ex => {
            const feedback = ex.form_feedback.map(f => `
                <div class="flex gap-2 text-xs mt-1 ${f.severity === 'warning' ? 'text-yellow-400' : 'text-slate-400'}">
                    <i class="fa-solid fa-circle-info mt-0.5"></i>
                    <span>@${Math.round(f.timestamp_sec)}s: ${f.note}</span>
                </div>
            `).join('');
            return `
                <div class="bg-slate-800 p-4 rounded-xl border border-slate-700 mb-3">
                    <div class="flex justify-between items-start mb-2">
                        <div>
                            <h4 class="font-bold text-lg capitalize">${ex.name}</h4>
                            <div class="text-xs text-slate-400">${ex.reps} Reps • ${Math.round(ex.duration_sec)}s duration</div>
                        </div>
                    </div>
                    ${feedback}
                </div>
            `;
        }).join('');

        // FIX: Removed duplicate back button - only render content, HTML has the button
        container.innerHTML = `
            <h2 class="text-2xl font-bold mb-1">Workout Analysis</h2>
            <div class="text-sm text-slate-400 mb-6">${new Date(workout.created_at).toLocaleString()}</div>

            ${workout.hls_url ? `
            <div class="bg-black rounded-xl overflow-hidden mb-6 relative aspect-video">
                <video id="workout-video" controls class="w-full h-full"></video>
            </div>
            ` : ''}

            <div class="bg-slate-800 p-4 rounded-xl border border-slate-700 mb-6">
                <h3 class="font-semibold mb-2">AI Summary</h3>
                <p class="text-sm text-slate-300 leading-relaxed">${workout.summary || "No summary available."}</p>
            </div>

            <div class="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
                <div>
                    <h3 class="font-semibold mb-3">Muscle Activation</h3>
                    <div class="bg-slate-800 p-4 rounded-xl border border-slate-700">
                        ${muscleList || '<div class="text-slate-500 text-sm">No data</div>'}
                    </div>
                </div>
                <div>
                    <h3 class="font-semibold mb-3">Exercises</h3>
                    ${exercisesList || '<div class="text-slate-500 text-sm">No exercises detected</div>'}
                </div>
            </div>
        `;

        if (workout.hls_url) {
            const video = document.getElementById('workout-video');
            if (Hls.isSupported()) {
                const hls = new Hls();
                hls.loadSource(workout.hls_url);
                hls.attachMedia(video);
            } else if (video.canPlayType('application/vnd.apple.mpegurl')) {
                video.src = workout.hls_url;
            }
        }

        switchView('view-workout-detail');
    } catch (err) {
        console.error("Detail error", err);
    }
}

// ==========================================
// Upload Handling
// ==========================================

async function handleFileSelect(event) {
    const file = event.target.files[0];
    if (!file || !currentUser) return;

    const progressDiv = document.getElementById('upload-progress');
    const progressBar = document.getElementById('progress-bar');
    const progressText = document.getElementById('progress-text');
    const statusText = document.getElementById('status-text');
    const dropZone = document.getElementById('drop-zone');

    dropZone.classList.add('hidden');
    progressDiv.classList.remove('hidden');

    const formData = new FormData();
    // FIX: Use .id instead of ._id (backend returns 'id')
    const userId = currentUser.id || currentUser._id;
    formData.append('user_id', userId);
    formData.append('file', file);

    try {
        statusText.textContent = "Uploading video...";
        const response = await fetch(`${API_URL}/workouts/upload`, {
            method: 'POST',
            body: formData
        });
        const data = await response.json();
        const workoutId = data.workout_id;
        pollStatus(workoutId);
    } catch (err) {
        console.error("Upload error", err);
        statusText.textContent = "Upload failed!";
        statusText.classList.add('text-red-500');
    }
}

function pollStatus(workoutId) {
    const progressBar = document.getElementById('progress-bar');
    const progressText = document.getElementById('progress-text');
    const statusText = document.getElementById('status-text');

    const interval = setInterval(async () => {
        try {
            const res = await fetch(`${API_URL}/workouts/${workoutId}/status`);
            const status = await res.json();
            
            progressBar.style.width = `${status.progress}%`;
            progressText.textContent = `${status.progress}%`;
            statusText.textContent = status.message || `Status: ${status.status}`;

            if (status.db_status === 'complete') {
                clearInterval(interval);
                setTimeout(() => {
                    alert("Analysis Complete!");
                    loadWorkoutDetail(workoutId);
                }, 1000);
            } else if (status.db_status === 'failed') {
                clearInterval(interval);
                statusText.textContent = "Analysis Failed";
                statusText.classList.add('text-red-500');
            }
        } catch (err) {
            console.error("Polling error", err);
        }
    }, 2000);
}

// ==========================================
// Coach Chat
// ==========================================

async function handleChat(e) {
    e.preventDefault();
    const input = document.getElementById('chat-input');
    const message = input.value.trim();
    if (!message || !currentUser) return;

    addMessage(message, 'user');
    input.value = '';
    const loadingId = addLoadingMessage();

    try {
        // FIX: Use .id instead of ._id
        const userId = currentUser.id || currentUser._id;
        const response = await fetch(`${API_URL}/coach/${userId}/chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message })
        });
        const data = await response.json();
        removeMessage(loadingId);
        addMessage(data.response, 'ai');
    } catch (err) {
        removeMessage(loadingId);
        addMessage("Sorry, I'm having trouble connecting right now.", 'ai');
        console.error("Chat error", err);
    }
}

function addMessage(text, sender) {
    const container = document.getElementById('chat-messages');
    const div = document.createElement('div');
    div.className = `flex items-end gap-3 ${sender === 'user' ? 'justify-end' : ''}`;
    
    if (sender === 'ai') {
        div.innerHTML = `
            <div class="w-8 h-8 rounded-full bg-blue-600 flex items-center justify-center flex-shrink-0 mb-1">
                <i class="fa-solid fa-robot text-white text-xs"></i>
            </div>
            <div class="chat-bubble-ai p-3 max-w-[80%] text-sm leading-relaxed">
                ${marked.parse(text)}
            </div>
        `;
    } else {
        div.innerHTML = `
            <div class="chat-bubble-user p-3 max-w-[80%] text-sm">${text}</div>
        `;
    }
    
    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
    return div.id = 'msg-' + Date.now();
}

function addLoadingMessage() {
    const container = document.getElementById('chat-messages');
    const div = document.createElement('div');
    div.className = `flex items-start gap-3`;
    div.id = 'loading-' + Date.now();
    // FIX: Use a contained loader that doesn't overflow
    div.innerHTML = `
        <div class="w-8 h-8 rounded-full bg-blue-600 flex items-center justify-center flex-shrink-0">
            <i class="fa-solid fa-robot text-white text-xs"></i>
        </div>
        <div class="chat-bubble-ai p-4 rounded-2xl rounded-tl-none border border-slate-700 min-w-[60px] flex items-center justify-center">
            <div class="typing-dots flex gap-1">
                <span class="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style="animation-delay: 0ms"></span>
                <span class="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style="animation-delay: 150ms"></span>
                <span class="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style="animation-delay: 300ms"></span>
            </div>
        </div>
    `;
    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
    return div.id;
}

function removeMessage(id) {
    const el = document.getElementById(id);
    if (el) el.remove();
}

const marked = {
  parse: (text) => {
    return text
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      .replace(/\*(.*?)\*/g, '<em>$1</em>')
      .replace(/\n/g, '<br>');
  }
};