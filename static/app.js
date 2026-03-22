/* ═══════════════════════════════════════════════════════════════════════════════
   NPC-Sim Web Client
   Copyright 2025-2026 Sadık Abdusselam Albayrak
   ═══════════════════════════════════════════════════════════════════════════════ */

// ── Globals ──
let socket = null;
let state = {};
let selectedNpcId = null;
let isPaused = false;
let canvas, ctx;
const OCC_COLORS = {
    guard: '#60a5fa', merchant: '#fbbf24', civilian: '#a78bfa',
    scholar: '#34d399', farmer: '#fb923c', priest: '#f472b6'
};
const EVENT_ICONS = {
    eat: '🍖', sleep: '😴', flee: '🏃', gather: '🌾', heal: '💊',
    combat: '⚔️', attack: '⚔️', attackattempt: '⚔️', socialize: '💬',
    trade: '💰', work: '🔨', pray: '🙏', walkto: '🚶'
};

const ZONES = {
    "Town Square": {x: 50, z: 50, radius: 10, color: 'rgba(255, 255, 255, 0.05)'},
    "Farm": {x: 20, z: 80, radius: 12, color: 'rgba(251, 146, 60, 0.1)'},
    "Barracks": {x: 80, z: 80, radius: 8, color: 'rgba(96, 165, 250, 0.1)'},
    "Academy": {x: 80, z: 20, radius: 8, color: 'rgba(52, 211, 153, 0.1)'},
    "Temple": {x: 20, z: 20, radius: 8, color: 'rgba(244, 114, 182, 0.1)'},
    "Market": {x: 50, z: 40, radius: 8, color: 'rgba(251, 191, 36, 0.1)'},
    "Tavern": {x: 60, z: 60, radius: 6, color: 'rgba(167, 139, 250, 0.1)'},
    "Riverside": {x: 10, z: 50, radius: 12, color: 'rgba(56, 189, 248, 0.1)'},
    "Forest Edge": {x: 50, z: 90, radius: 15, color: 'rgba(74, 222, 128, 0.1)'},
    "Cemetery": {x: 90, z: 50, radius: 8, color: 'rgba(156, 163, 175, 0.1)'},
};

const npcTrails = {};

// ── Init ──
document.addEventListener('DOMContentLoaded', () => {
    canvas = document.getElementById('map-canvas');
    ctx = canvas.getContext('2d');
    resizeCanvas();
    window.addEventListener('resize', resizeCanvas);
    canvas.addEventListener('click', onMapClick);
    connectSocket();
});

function resizeCanvas() {
    const container = canvas.parentElement;
    const headerH = container.querySelector('.card-header')?.offsetHeight || 40;
    canvas.width = container.clientWidth;
    canvas.height = container.clientHeight - headerH;
}

// ── WebSocket ──
function connectSocket() {
    socket = io({ transports: ['websocket', 'polling'] });
    socket.on('connect', () => console.log('Connected to NPC-Sim'));
    socket.on('tick', onTick);
    socket.on('disconnect', () => console.log('Disconnected'));
}

function onTick(data) {
    state = data;
    
    // Update trails
    if (state.npcs) {
        state.npcs.forEach(npc => {
            if (!npcTrails[npc.identity.npc_id]) npcTrails[npc.identity.npc_id] = [];
            npcTrails[npc.identity.npc_id].push({x: npc.position.x, z: npc.position.z});
            if (npcTrails[npc.identity.npc_id].length > 15) {
                npcTrails[npc.identity.npc_id].shift();
            }
        });
    }

    updateHeader();
    updatePopStats();
    updateNpcList();
    updateEventLog();
    drawMap();
    if (selectedNpcId) updateDetail();
}

// ── Header Updates ──
function updateHeader() {
    document.getElementById('stat-day').textContent = state.day || 0;
    const h = state.hour || 0;
    const hh = Math.floor(h);
    const mm = Math.floor((h - hh) * 60);
    document.getElementById('stat-hour').textContent = `${hh}:${String(mm).padStart(2, '0')}`;
    document.getElementById('stat-tick').textContent = state.tick || 0;
    document.getElementById('stat-pop').textContent = state.population?.total_population || 0;
}

// ── Population Stats ──
function updatePopStats() {
    const p = state.population || {};
    document.getElementById('ps-hunger').textContent = pct(p.avg_hunger);
    document.getElementById('ps-thirst').textContent = pct(p.avg_thirst);
    document.getElementById('ps-happy').textContent = (p.avg_happiness || 0).toFixed(2);
    document.getElementById('ps-stress').textContent = pct(p.avg_stress);
}

// ── NPC List ──
function updateNpcList() {
    const body = document.getElementById('npc-list-body');
    const npcs = state.npcs || [];
    let html = '';
    for (const npc of npcs) {
        const id = npc.identity?.npc_id || '';
        const name = npc.identity?.display_name || 'Unknown';
        const occ = (npc.identity?.occupation || 'civilian').toLowerCase();
        const color = OCC_COLORS[occ] || '#a78bfa';
        const mood = npc.psychology?.mood_label || 'Calm';
        const moodClass = 'mood-' + mood.toLowerCase();
        const action = npc.current_action || 'Idle';
        const sel = id === selectedNpcId ? ' selected' : '';
        html += `<div class="npc-row${sel}" onclick="selectNpc('${id}')">
            <div class="npc-dot" style="color:${color};background:${color}"></div>
            <div class="npc-info">
                <div class="npc-name">${name}</div>
                <div class="npc-occ occ-${occ}">${occ}</div>
            </div>
            <div class="npc-status">
                <div class="npc-mood ${moodClass}">${mood}</div>
                <div class="npc-action">${action}</div>
            </div>
        </div>`;
    }
    body.innerHTML = html;
}

// ── Event Log ──
function updateEventLog() {
    const body = document.getElementById('event-log-body');
    const events = (state.recent_events || []).slice(-15).reverse();
    let html = '';
    for (const ev of events) {
        const evType = (ev.event_type || '').toLowerCase();
        const icon = EVENT_ICONS[evType] || '📌';
        const t = (ev.timestamp || 0);
        const hh = Math.floor(t / 60) % 24;
        const mm = Math.floor(t % 60);
        const ts = `${hh}:${String(mm).padStart(2, '0')}`;
        html += `<div class="event-row event-${evType}">
            <span class="event-icon">${icon}</span>
            <span class="event-time">${ts}</span>
            <span class="event-desc">${ev.description || ev.event_type}</span>
        </div>`;
    }
    body.innerHTML = html;
}

// ── Map Drawing ──
function drawMap() {
    if (!ctx || !canvas.width) return;
    const w = canvas.width, h = canvas.height;

    // Background
    ctx.fillStyle = '#0a0d14';
    ctx.fillRect(0, 0, w, h);

    // Grid
    ctx.strokeStyle = 'rgba(42, 51, 70, 0.4)';
    ctx.lineWidth = 0.5;
    const gridSize = 20;
    const scale = Math.min(w, h) / 120;
    const ox = w / 2 - 50 * scale, oy = h / 2 - 50 * scale;

    for (let gx = 0; gx <= 100; gx += gridSize) {
        ctx.beginPath();
        ctx.moveTo(ox + gx * scale, oy);
        ctx.lineTo(ox + gx * scale, oy + 100 * scale);
        ctx.stroke();
    }
    for (let gy = 0; gy <= 100; gy += gridSize) {
        ctx.beginPath();
        ctx.moveTo(ox, oy + gy * scale);
        ctx.lineTo(ox + 100 * scale, oy + gy * scale);
        ctx.stroke();
    }

    // Draw Zones
    for (const [name, zone] of Object.entries(ZONES)) {
        const zx = ox + zone.x * scale;
        const zy = oy + zone.z * scale;
        const zr = zone.radius * scale;
        
        ctx.beginPath();
        ctx.arc(zx, zy, zr, 0, Math.PI * 2);
        ctx.fillStyle = zone.color;
        ctx.fill();
        ctx.strokeStyle = zone.color.replace('0.1)', '0.3)').replace('0.05)', '0.2)');
        ctx.lineWidth = 1;
        ctx.stroke();

        ctx.fillStyle = 'rgba(255, 255, 255, 0.4)';
        ctx.font = '10px Inter, sans-serif';
        ctx.textAlign = 'center';
        ctx.fillText(name, zx, zy - zr - 4);
    }

    // NPCs
    const npcs = state.npcs || [];
    const currentTime = state.time || 0;
    const recentEvents = state.recent_events || [];

    for (const npc of npcs) {
        const pos = npc.position || { x: 50, z: 50 };
        const id = npc.identity?.npc_id;
        const sx = ox + pos.x * scale;
        const sy = oy + pos.z * scale;
        const occ = (npc.identity?.occupation || 'civilian').toLowerCase();
        const color = OCC_COLORS[occ] || '#a78bfa';
        const isSelected = id === selectedNpcId;
        const r = isSelected ? 8 : 5;

        // Draw Trails
        const trail = npcTrails[id];
        if (trail && trail.length > 1) {
            ctx.beginPath();
            ctx.moveTo(ox + trail[0].x * scale, oy + trail[0].z * scale);
            for (let i = 1; i < trail.length; i++) {
                ctx.lineTo(ox + trail[i].x * scale, oy + trail[i].z * scale);
            }
            ctx.strokeStyle = color + '40'; // 25% opacity
            ctx.lineWidth = 2;
            ctx.stroke();
        }

        // Draw Destination Line
        if (npc.destination) {
            const dx = ox + npc.destination.x * scale;
            const dy = oy + npc.destination.z * scale;
            ctx.beginPath();
            ctx.setLineDash([4, 4]);
            ctx.moveTo(sx, sy);
            ctx.lineTo(dx, dy);
            ctx.strokeStyle = color + '80'; // 50% opacity dashed
            ctx.lineWidth = 1;
            ctx.stroke();
            ctx.setLineDash([]); // Reset
        }

        // Glow
        const grd = ctx.createRadialGradient(sx, sy, 0, sx, sy, r * 3);
        grd.addColorStop(0, color + '40');
        grd.addColorStop(1, 'transparent');
        ctx.fillStyle = grd;
        ctx.fillRect(sx - r * 3, sy - r * 3, r * 6, r * 6);

        // Dot
        ctx.beginPath();
        ctx.arc(sx, sy, r, 0, Math.PI * 2);
        ctx.fillStyle = color;
        ctx.fill();

        if (isSelected) {
            ctx.strokeStyle = '#fff';
            ctx.lineWidth = 2;
            ctx.stroke();
        }

        // Map labels + speech bubble
        ctx.textAlign = 'center';
        
        // Find recent speech/event bubble
        const bubbleEvents = ['socialize', 'trade', 'pray'];
        const recentEv = recentEvents.find(e => 
            e.initiator_id === id && 
            bubbleEvents.includes((e.event_type || '').toLowerCase()) && 
            currentTime - e.timestamp < 10.0
        );

        if (recentEv) {
            const icon = EVENT_ICONS[recentEv.event_type.toLowerCase()] || '💬';
            ctx.fillStyle = '#ffffff';
            ctx.font = '14px sans-serif';
            ctx.fillText(icon, sx + 10, sy - 15);
        }

        // Name label
        ctx.fillStyle = '#e2e8f0';
        ctx.font = `${isSelected ? 'bold ' : ''}${isSelected ? 11 : 9}px Inter, sans-serif`;
        ctx.fillText(npc.identity?.display_name || '', sx, sy - r - 4);

        // Action label
        ctx.fillStyle = '#64748b';
        ctx.font = '8px Inter, sans-serif';
        ctx.fillText(npc.current_action || '', sx, sy + r + 10);
    }

    // Map info
    document.getElementById('map-info').textContent =
        `${npcs.length} agents | Scale: ${scale.toFixed(1)}px/u`;
}

function onMapClick(e) {
    if (!state.npcs) return;
    const rect = canvas.getBoundingClientRect();
    const mx = e.clientX - rect.left;
    const my = e.clientY - rect.top;
    const w = canvas.width, h = canvas.height;
    const scale = Math.min(w, h) / 120;
    const ox = w / 2 - 50 * scale, oy = h / 2 - 50 * scale;

    let closest = null, closestDist = Infinity;
    for (const npc of state.npcs) {
        const pos = npc.position || { x: 50, z: 50 };
        const sx = ox + pos.x * scale;
        const sy = oy + pos.z * scale;
        const d = Math.sqrt((mx - sx) ** 2 + (my - sy) ** 2);
        if (d < 20 && d < closestDist) {
            closestDist = d;
            closest = npc;
        }
    }
    if (closest) selectNpc(closest.identity.npc_id);
}

// ── NPC Selection ──
function selectNpc(npcId) {
    selectedNpcId = npcId;
    updateNpcList();
    updateDetail();
    document.getElementById('detail-panel').style.display = 'block';
    drawMap();
}

function closeDetail() {
    selectedNpcId = null;
    document.getElementById('detail-panel').style.display = 'none';
    updateNpcList();
    drawMap();
}

function updateDetail() {
    const npc = (state.npcs || []).find(n => n.identity?.npc_id === selectedNpcId);
    if (!npc) return;

    document.getElementById('detail-name').textContent =
        `🧑 ${npc.identity?.display_name || 'Unknown'}`;

    const v = npc.vitals || {};
    const p = npc.psychology || {};
    const inv = npc.inventory || {};
    const traits = npc.traits?.tags || [];

    let html = '';

    // Identity
    html += `<div class="section-title">Identity</div>`;
    html += `<div class="detail-grid">
        <span class="detail-label">ID</span><span class="detail-value" style="font-size:0.7rem">${npc.identity?.npc_id}</span>
        <span class="detail-label">Occupation</span><span class="detail-value">${npc.identity?.occupation}</span>
        <span class="detail-label">Action</span><span class="detail-value" style="color:var(--accent-3);font-weight:700">${npc.current_action || 'Idle'}</span>
    </div>`;

    // Active Goal
    const activeGoal = npc.goals?.active?.[0]; // Assuming goals.to_dict() returns {active: [{desc...}]}
    if (activeGoal) {
        html += `<div class="section-title">Active Goal</div>`;
        html += `<div style="background:var(--bg-card);border:1px solid var(--border);padding:0.4rem;border-radius:var(--radius-sm);font-size:0.75rem;">
            <div style="font-weight:600;color:var(--accent-1);margin-bottom:0.2rem">📌 ${activeGoal.goal_type || 'Task'} (${Math.round((activeGoal.progress||0)*100)}%)</div>
            <div style="color:var(--text-secondary)">${activeGoal.description || ''}</div>
        </div>`;
    }

    // Vitals
    html += `<div class="section-title">Vitals</div>`;
    html += bar('Health', v.health, v.max_health, '#10b981');
    html += bar('Energy', v.energy, v.max_energy, '#06b6d4');
    html += bar('Hunger', v.hunger * 100, 100, '#f59e0b');
    html += bar('Thirst', v.thirst * 100, 100, '#3b82f6');
    html += bar('Stress', v.stress * 100, 100, '#ef4444');

    // Psychology
    html += `<div class="section-title">Psychology (Big Five)</div>`;
    html += bar('Extraversion', p.extraversion * 100, 100, '#8b5cf6');
    html += bar('Agreeableness', p.agreeableness * 100, 100, '#ec4899');
    html += bar('Conscientiousness', p.conscientiousness * 100, 100, '#06b6d4');
    html += bar('Neuroticism', p.neuroticism * 100, 100, '#ef4444');
    html += bar('Openness', p.openness * 100, 100, '#10b981');

    // Emotions
    html += `<div class="section-title">Emotions</div>`;
    html += `<div class="detail-grid">
        <span class="detail-label">Mood</span><span class="detail-value mood-${(p.mood_label||'calm').toLowerCase()}">${p.mood_label}</span>
        <span class="detail-label">Happiness</span><span class="detail-value">${(p.happiness||0).toFixed(3)}</span>
        <span class="detail-label">Fear</span><span class="detail-value">${(p.fear||0).toFixed(3)}</span>
        <span class="detail-label">Anger</span><span class="detail-value">${(p.anger||0).toFixed(3)}</span>
    </div>`;

    // Traits
    if (traits.length) {
        html += `<div class="section-title">Traits</div>`;
        html += `<div style="display:flex;gap:0.3rem;flex-wrap:wrap">`;
        for (const t of traits) {
            html += `<span style="background:var(--bg-surface);border:1px solid var(--border);padding:0.15rem 0.45rem;border-radius:99px;font-size:0.72rem;color:var(--text-accent)">${t}</span>`;
        }
        html += `</div>`;
    }

    // Inventory
    const stacks = inv.stacks || [];
    if (stacks.length) {
        html += `<div class="section-title">Inventory (${stacks.length}/${inv.capacity})</div>`;
        html += `<div style="display:flex;gap:0.3rem;flex-wrap:wrap">`;
        for (const s of stacks) {
            html += `<span style="background:var(--bg-surface);border:1px solid var(--border);padding:0.15rem 0.45rem;border-radius:var(--radius-sm);font-size:0.72rem;font-family:'JetBrains Mono',monospace">${s.item_id} ×${s.amount}</span>`;
        }
        html += `</div>`;
    }

    // Social
    const rels = npc.social?.relations || [];
    if (rels.length) {
        html += `<div class="section-title">Relations</div>`;
        for (const r of rels.slice(0, 5)) {
            const relColor = r.relation_type === 'Friend' ? '#10b981' : r.relation_type === 'Enemy' ? '#ef4444' : '#94a3b8';
            html += `<div style="font-size:0.75rem;color:var(--text-secondary)">→ ${r.target_id.substring(0,12)}… <span style="color:${relColor}">${r.relation_type}</span> T:${r.trust.toFixed(2)}</div>`;
        }
    }

    document.getElementById('detail-body').innerHTML = html;
}

function bar(label, val, max, color) {
    const pctVal = max > 0 ? (val / max * 100) : 0;
    return `<div style="margin-bottom:0.35rem">
        <div style="display:flex;justify-content:space-between;font-size:0.75rem">
            <span class="detail-label">${label}</span>
            <span class="detail-value">${val.toFixed(1)}/${max.toFixed(0)}</span>
        </div>
        <div class="bar-container"><div class="bar-fill" style="width:${pctVal}%;background:${color}"></div></div>
    </div>`;
}

// ── Controls ──
function togglePause() {
    isPaused = !isPaused;
    const btn = document.getElementById('btn-play');
    btn.textContent = isPaused ? '⏸ Pause' : '▶ Play';
    btn.classList.toggle('active', !isPaused);
    fetch('/api/control', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ paused: isPaused })
    });
}

function changeSpeed(val) {
    fetch('/api/control', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ speed: parseFloat(val) })
    });
}

function resetSim() {
    isPaused = false;
    document.getElementById('btn-play').textContent = '▶ Play';
    document.getElementById('btn-play').classList.add('active');
    selectedNpcId = null;
    document.getElementById('detail-panel').style.display = 'none';
    fetch('/api/control', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ reset: true })
    }).then(() => {
        document.getElementById('config-screen').style.display = 'flex';
        state = {};
        if (ctx) ctx.clearRect(0, 0, canvas.width, canvas.height);
        updateHeader();
        updatePopStats();
        updateNpcList();
        updateEventLog();
    });
}

function startSimulation() {
    const data = {
        npc_count: parseInt(document.getElementById('cfg-npc').value) || 5,
        start_hour: document.getElementById('cfg-time').value || "06:00",
        time_scale: parseFloat(document.getElementById('cfg-speed').value) || 1.0,
        seed: document.getElementById('cfg-seed').value,
        llm_enabled: document.getElementById('cfg-llm').checked,
        logger_enabled: document.getElementById('cfg-log').checked
    };
    
    document.getElementById('btn-play').textContent = '⏸ Pause';
    document.getElementById('btn-play').classList.add('active');
    isPaused = false;
    document.getElementById('speed-select').value = data.time_scale;

    fetch('/api/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    }).then(r => r.json()).then(res => {
        if (!res.error) {
            document.getElementById('config-screen').style.display = 'none';
        } else {
            alert(res.error);
        }
    });
}

function toggleInject() {
    document.getElementById('inject-panel').classList.toggle('visible');
}

function injectStimulus() {
    const tag = document.getElementById('inject-type').value;
    const x = parseFloat(document.getElementById('inject-x').value) || 50;
    const z = parseFloat(document.getElementById('inject-z').value) || 50;
    const intensity = parseFloat(document.getElementById('inject-intensity').value) || 0.85;
    socket.emit('inject_stimulus', {
        type: tag === 'Threat' ? 'Visual' : tag === 'Food' ? 'Olfactory' : 'Social',
        source_id: 'manual_' + Date.now(),
        position: { x, y: 0, z },
        intensity,
        tag
    });
}

// ── Helpers ──
function pct(v) { return ((v || 0) * 100).toFixed(0) + '%'; }
