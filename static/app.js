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
        html += `<div class="event-row">
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

    // NPCs
    const npcs = state.npcs || [];
    for (const npc of npcs) {
        const pos = npc.position || { x: 50, z: 50 };
        const sx = ox + pos.x * scale;
        const sy = oy + pos.z * scale;
        const occ = (npc.identity?.occupation || 'civilian').toLowerCase();
        const color = OCC_COLORS[occ] || '#a78bfa';
        const isSelected = npc.identity?.npc_id === selectedNpcId;
        const r = isSelected ? 8 : 5;

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

        // Name label
        ctx.fillStyle = '#e2e8f0';
        ctx.font = `${isSelected ? 'bold ' : ''}${isSelected ? 11 : 9}px Inter, sans-serif`;
        ctx.textAlign = 'center';
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
        <span class="detail-label">Faction</span><span class="detail-value">${npc.identity?.faction}</span>
        <span class="detail-label">Age</span><span class="detail-value">${npc.identity?.age}</span>
        <span class="detail-label">Action</span><span class="detail-value" style="color:var(--accent-3)">${npc.current_action || 'Idle'}</span>
    </div>`;

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
    document.getElementById('speed-value').textContent = parseFloat(val).toFixed(1) + '×';
    fetch('/api/control', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ speed: parseFloat(val) })
    });
}

function resetSim() {
    const seed = parseInt(document.getElementById('seed-input').value) || 42;
    isPaused = false;
    document.getElementById('btn-play').textContent = '▶ Play';
    document.getElementById('btn-play').classList.add('active');
    selectedNpcId = null;
    document.getElementById('detail-panel').style.display = 'none';
    fetch('/api/control', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ reset: true, seed: seed })
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
