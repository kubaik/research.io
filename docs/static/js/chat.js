/* HealthAssist CDST v1 — Auto-generated */
/* EVAH-Aligned Clinical Decision Support Tool */
/* Provider: anthropic | Model: claude-sonnet-4-20250514 | Built: 2026-05-22 08:47 UTC | Hash: 01d835b3 */

'use strict';

// ─── PROVIDER CONFIG ──────────────────────────────────────────────────────
// __API_TOKEN__ is replaced by GitHub Actions at deploy time.
// No secret is ever stored in the repository.
const PROVIDER = {
  token:      `__API_TOKEN__`,
  endpoint:   `https://api.anthropic.com/v1/messages`,
  model:      `claude-sonnet-4-20250514`,
  name:       `anthropic`,
  authHeader: `x-api-key`,
  apiVersion: `2023-06-01`,
  type:       `anthropic`,
};

// ─── BOT CONFIG ───────────────────────────────────────────────────────────
const BOT_CONFIG = {
  system:         `You are HealthAssist, a clinical decision support tool for community health workers (CHWs) at primary health centres in Sub-Saharan Africa, South Asia, and Southeast Asia. Your role is to assist frontline workers with evidence-based guidance on triage, diagnosis, referral, and treatment within WHO and national protocol standards.\n\nCORE PRINCIPLES:\n1. SAFETY FIRST: Always flag red flag symptoms requiring immediate referral.\n2. EVIDENCE-BASED: Ground all guidance in WHO IMCI, national formularies, and established clinical protocols.\n3. APPROPRIATE SCOPE: You support CHWs — not replace physician judgment. Recommend escalation when beyond CHW scope.\n4. STRUCTURED OUTPUT: For every clinical query respond ONLY in this exact JSON structure (no prose outside the JSON):\n{\n  "assessment": "2-3 sentence summary of the clinical picture",\n  "differentials": ["Differential 1", "Differential 2"],\n  "actions": ["Action 1 — specific and numbered", "Action 2"],\n  "red_flags": ["Red flag 1", "Red flag 2"],\n  "referral": "IMMEDIATE|URGENT|ROUTINE|MONITOR",\n  "referral_reason": "One sentence explaining referral urgency",\n  "confidence": "HIGH|MEDIUM|LOW",\n  "confidence_reason": "One sentence explaining confidence level",\n  "formulary_note": "null or short note if prescription beyond CHW scope"\n}\n5. LANGUAGE: Use clear, simple language appropriate for CHW literacy.\n\nSAFETY RULES:\n- Altered consciousness, severe breathing difficulty, signs of shock, severe malnutrition, convulsions, severe dehydration → referral: IMMEDIATE in every case.\n- Never recommend prescription medications beyond the CHW formulary (amoxicillin, ORS, zinc, paracetamol, artesunate pre-referral, vitamin A, iron-folate, misoprostol). Flag in formulary_note.\n- Always include weight-based dosing for paediatric cases.\n- For maternal health, apply SAFE MOTHERHOOD protocols.\n\nEVALUATION CONTEXT:\nThis is an EVAH-aligned evaluation tool. The confidence field is used for Pathway A/B accuracy measurement — calibrate it honestly.`,
  greeting:       `Hello, I'm HealthAssist — your AI clinical decision support tool.\n\nI can help you with:\n• Symptom assessment & triage guidance\n• Treatment protocol references\n• Referral decision support\n• Medication dosage guidance\n\n⚠️ This tool supports clinical decision-making. Always apply your clinical judgment and follow your facility's protocols.\n\nHow can I assist you today?`,
  quickReplies:   ["Child fever & symptoms", "Malaria assessment", "Respiratory illness", "Maternal health", "Malnutrition screening", "Referral criteria", "Medication dosages", "View protocols"],
  safetyKeywords: ["unconscious", "not breathing", "fitting", "convulsion", "severe", "emergency", "shock", "collapsed", "unresponsive", "bleeding heavily", "difficulty breathing", "chest pain", "cannot walk", "very pale", "yellow eyes", "swollen face", "not waking", "limp", "floppy"],
};

// ─── EVALUATION CONFIG ────────────────────────────────────────────────────
const EVAL = {
  enabled:         true,
  studyId:         'EVAH-CDST-001',
  pathway:         'A',
  arm:             'intervention',
  facilityId:      'FACILITY-001',
  protocolVersion: '1.0.0',
  buildHash:       '01d835b3',
  serverLogUrl:    ``,
  sessionId:       _genSessionId(),
  log:             [],
};

// ─── FORMULARY ────────────────────────────────────────────────────────────
const FORMULARY = [{"name": "Amoxicillin", "forms": ["250mg/5ml syrup", "500mg tablet"], "dosing": "40mg/kg/day divided 3x daily, 5 days"}, {"name": "Paracetamol", "forms": ["120mg/5ml syrup", "500mg tablet"], "dosing": "15mg/kg/dose every 4-6h, max 4 doses/day"}, {"name": "ORS", "forms": ["1L sachets"], "dosing": "50-100ml/kg over 3-4h for moderate dehydration"}, {"name": "Zinc sulfate", "forms": ["20mg dispersible tablet"], "dosing": "<6mo: 10mg/day 10 days; ≥6mo: 20mg/day 10 days"}, {"name": "Vitamin A", "forms": ["100,000IU capsule", "200,000IU capsule"], "dosing": "<12mo: 100,000IU once; ≥12mo: 200,000IU once"}, {"name": "Artesunate rectal", "forms": ["200mg suppository"], "dosing": "10mg/kg single pre-referral dose for severe malaria"}, {"name": "Iron-folate", "forms": ["60mg/0.4mg tablet"], "dosing": "1 tablet daily (pregnancy), 3mo postpartum"}, {"name": "Misoprostol", "forms": ["200mcg tablet"], "dosing": "600mcg oral single dose for PPH prevention"}];

// ─── I18N ─────────────────────────────────────────────────────────────────
const I18N_STRINGS = {"en": {"greeting_label": "Hello", "send": "Send", "emergency": "Emergency", "new_session": "New session", "export": "Export session data", "consent_title": "Research Consent", "consent_agree": "I agree and continue", "consent_decline": "Decline (demo mode only)", "placeholder": "Describe the patient's symptoms…"}, "sw": {"greeting_label": "Habari", "send": "Tuma", "emergency": "Dharura", "new_session": "Kikao kipya", "export": "Hamisha data ya kikao", "consent_title": "Idhini ya Utafiti", "consent_agree": "Nakubaliana na kuendelea", "consent_decline": "Kataa (hali ya maonyesho tu)", "placeholder": "Elezea dalili za mgonjwa…"}};
let LOCALE = navigator.language?.startsWith('sw') ? 'sw' : 'en';
function t(key) { return (I18N_STRINGS[LOCALE] || I18N_STRINGS['en'] || {})[key] || key; }

// ─── EMERGENCY CONTACTS ───────────────────────────────────────────────────
const EMERGENCY_CONTACTS = {"ambulance": "911", "referral_hospital": "+254 000 000 000", "district_health_officer": "+254 000 000 001"};

// ─── CONNECTIVITY ─────────────────────────────────────────────────────────
let offlineQueue = [];
let isOnline     = navigator.onLine;

window.addEventListener('online',  () => { isOnline = true;  flushOfflineQueue(); updateConnectionStatus(); });
window.addEventListener('offline', () => { isOnline = false; updateConnectionStatus(); });

function updateConnectionStatus() {
  const dot = document.getElementById('status-dot');
  if (dot) dot.className = 'status-dot' + (isOnline ? '' : ' offline');
}

async function flushOfflineQueue() {
  if (!EVAL.serverLogUrl || !offlineQueue.length) return;
  const batch = [...offlineQueue];
  offlineQueue = [];
  try {
    await fetch(EVAL.serverLogUrl, {
      method:  'POST',
      headers: {'Content-Type': 'application/json'},
      body:    JSON.stringify({ batch, sessionId: EVAL.sessionId }),
    });
  } catch { offlineQueue = [...batch, ...offlineQueue]; }
}

// ─── STATE ────────────────────────────────────────────────────────────────
let history       = [];
let busy          = false;
let msgCounter    = 0;
let emergencyMode = false;
let protocolData  = null;

// ─── UTILS ────────────────────────────────────────────────────────────────
function _genSessionId() {
  return crypto.randomUUID ? crypto.randomUUID() : Math.random().toString(36).slice(2);
}

function _hashChain(prev, data) {
  return btoa(prev.slice(-8) + JSON.stringify(data)).slice(0, 16);
}

function esc(s) {
  return String(s || '')
    .replace(/&/g, '&amp;').replace(/</g, '&lt;')
    .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

// ─── BOOT ─────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  navigator.serviceWorker?.register('./sw.js').catch(e => console.warn('SW:', e));
  initApp();
});

function initApp() {
  hideBanner();
  showGreeting();
  loadProtocols();
  updateEvalStats();
  updateConnectionStatus();
  loadLocaleFromStorage();

  const inp = document.getElementById('user-input');
  inp?.addEventListener('keydown', e => {
    // Desktop: Enter submits; mobile uses the send button
    if (e.key === 'Enter' && !e.shiftKey && navigator.maxTouchPoints === 0) {
      e.preventDefault();
      send();
    }
  });
  inp?.addEventListener('input', autoResize);
}

function autoResize() {
  const el = document.getElementById('user-input');
  if (!el) return;
  el.style.height = 'auto';
  el.style.height = Math.min(el.scrollHeight, 120) + 'px';
}

// ─── SAFETY BANNER — emergency use only ───────────────────────────────────
function hideBanner() {
  const el = document.getElementById('safety-banner');
  if (!el) return;
  el.style.display = 'none';
  el.setAttribute('aria-hidden', 'true');
}

// ─── EMERGENCY ────────────────────────────────────────────────────────────
function detectEmergency(text) {
  const lower = text.toLowerCase();
  return BOT_CONFIG.safetyKeywords.some(kw => lower.includes(kw));
}

function setEmergencyMode(on) {
  emergencyMode = on;
  const overlay = document.getElementById('emergency-overlay');
  const banner  = document.getElementById('safety-banner');
  const amb     = EMERGENCY_CONTACTS.ambulance || '999';
  if (on) {
    overlay?.classList.add('active');
    if (banner) {
      banner.style.display = '';
      banner.removeAttribute('aria-hidden');
      banner.className = 'status-emergency';
      banner.innerHTML = `🚨 &nbsp;<strong>EMERGENCY ALERT</strong> — Refer immediately. Ambulance: <strong>${amb}</strong>`;
    }
  } else {
    overlay?.classList.remove('active');
    hideBanner();
  }
}

// ─── CLINICAL CARD ────────────────────────────────────────────────────────
function parseClinicalJSON(text) {
  const match = text.match(/\{[\s\S]*\}/);
  if (!match) return null;
  try { return JSON.parse(match[0]); } catch { return null; }
}

function renderClinicalCard(data) {
  const refClass = { IMMEDIATE:'immediate', URGENT:'urgent', ROUTINE:'routine', MONITOR:'monitor' }[data.referral] || 'monitor';
  const refLabel = {
    IMMEDIATE: '🔴 EMERGENCY REFERRAL REQUIRED',
    URGENT:    '🟠 Urgent referral (2–4h)',
    ROUTINE:   '🟡 Routine referral',
    MONITOR:   '🟢 Monitor at facility',
  }[data.referral] || data.referral;

  const actionsHtml = (data.actions || []).map((a, i) =>
    `<div style="display:flex;gap:8px;padding:4px 0;font-size:13.5px;border-bottom:1px solid var(--border-light)">
      <span style="font-family:var(--font-mono);font-size:11px;color:var(--muted);min-width:18px;padding-top:2px">${i+1}</span>
      <span>${esc(a)}</span>
    </div>`
  ).join('');

  const flagsHtml = (data.red_flags     || []).map(f => `<span class="tag red">${esc(f)}</span>`).join('');
  const diffsHtml = (data.differentials || []).map(d => `<span class="tag blue">${esc(d)}</span>`).join('');

  const formularyNote = data.formulary_note && data.formulary_note !== 'null'
    ? `<div class="clinical-section">
         <div class="clinical-section-label warning">⚠ Formulary note</div>
         <div class="clinical-content">${esc(data.formulary_note)}</div>
       </div>`
    : '';

  return `<div class="clinical-card">
    <div class="clinical-section">
      <div class="clinical-section-label">Assessment</div>
      <div class="clinical-content">${esc(data.assessment || '')}</div>
    </div>
    ${diffsHtml ? `<div class="clinical-section"><div class="clinical-section-label">Differentials</div><div class="tag-list">${diffsHtml}</div></div>` : ''}
    ${actionsHtml ? `<div class="clinical-section"><div class="clinical-section-label">Actions</div>${actionsHtml}</div>` : ''}
    ${flagsHtml   ? `<div class="clinical-section"><div class="clinical-section-label danger">⚠ Red flags</div><div class="tag-list">${flagsHtml}</div></div>` : ''}
    <div class="clinical-section">
      <div class="clinical-section-label">Referral</div>
      <span class="referral-badge ${refClass}">${refLabel}</span>
      ${data.referral_reason ? `<div class="clinical-content" style="margin-top:6px;font-size:12.5px;color:var(--text-2)">${esc(data.referral_reason)}</div>` : ''}
    </div>
    ${formularyNote}
    <div class="clinical-section" style="background:var(--bg)">
      <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;font-size:12px;color:var(--muted)">
        <span>Confidence: <span class="confidence-chip ${data.confidence || 'MEDIUM'}">${data.confidence || 'MEDIUM'}</span></span>
        ${data.confidence_reason ? `<span>${esc(data.confidence_reason)}</span>` : ''}
      </div>
    </div>
  </div>`;
}

// ─── MESSAGE RENDERING ────────────────────────────────────────────────────
function addMsg(role, text, opts = {}) {
  const container = document.getElementById('chat-container');
  if (!container) return;

  const id = 'msg-' + (++msgCounter);
  const ts = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  const el = document.createElement('div');

  const clinicalData = (role === 'bot' && !opts.noFeedback) ? parseClinicalJSON(text) : null;
  const isEmergency  = role === 'bot' && (
    clinicalData?.referral === 'IMMEDIATE' ||
    text.includes('EMERGENCY REFERRAL') ||
    text.includes('REFER URGENTLY') ||
    opts.emergency === true
  );

  if (isEmergency) setEmergencyMode(true);

  el.id        = id;
  el.className = 'message ' + role + (isEmergency ? ' emergency' : '');

  const avatar     = role === 'bot' ? '🏥' : (role === 'user' ? 'CHW' : '');
  const bubbleHtml = clinicalData
    ? renderClinicalCard(clinicalData)
    : role === 'bot'
      ? formatBotText(text)
      : esc(text).replace(/\n/g, '<br>');

  const confidence   = clinicalData?.confidence || extractConfidence(text);
  const feedbackHtml = (role === 'bot' && !opts.noFeedback) ? `
    <div class="msg-feedback">
      <button class="feedback-btn" onclick="rateMsgAccuracy('${id}','accurate')">✓ Accurate</button>
      <button class="feedback-btn" onclick="rateMsgAccuracy('${id}','inaccurate')">✗ Inaccurate</button>
      <button class="feedback-btn" onclick="rateMsgAccuracy('${id}','escalate')">⬆ Review</button>
      ${confidence ? `<span class="confidence-chip ${confidence}">${confidence}</span>` : ''}
    </div>
    <div class="followup-form">
      <div style="font-size:11px;color:var(--muted);margin-bottom:6px;font-weight:600">Schedule follow-up</div>
      <div class="followup-row">
        <input type="date" class="followup-input" id="fu-date-${id}" min="${new Date().toISOString().split('T')[0]}">
        <input type="text"  class="followup-input" id="fu-reason-${id}" placeholder="Reason…" style="flex:2">
        <button class="followup-btn" onclick="saveFollowUp('${id}')">Save</button>
      </div>
    </div>` : '';

  el.innerHTML = `
    <div class="msg-avatar">${avatar}</div>
    <div class="msg-body">
      <div class="msg-bubble">${bubbleHtml}</div>
      <div class="msg-meta">
        <span>${ts}</span>
        ${isEmergency ? '<span style="font-weight:600;color:var(--danger)">⚠ EMERGENCY</span>' : ''}
        ${!isOnline   ? '<span class="offline-badge">📡 Offline</span>'                        : ''}
      </div>
      ${feedbackHtml}
    </div>`;

  container.appendChild(el);
  container.scrollTop = container.scrollHeight;

  if (EVAL.enabled) {
    const prev  = EVAL.log.length ? (EVAL.log[EVAL.log.length - 1].chainHash || '') : '';
    const entry = {
      t: Date.now(), role, len: text.length, emergency: isEmergency,
      referral:   clinicalData?.referral   || null,
      confidence: clinicalData?.confidence || confidence || null,
      feedback: null, followUp: null, msgId: id,
      chainHash: _hashChain(prev, { role, len: text.length }),
    };
    EVAL.log.push(entry);
    updateEvalStats();
    serverLog(entry);
  }

  return id;
}

function saveFollowUp(msgId) {
  const date   = document.getElementById(`fu-date-${msgId}`)?.value;
  const reason = document.getElementById(`fu-reason-${msgId}`)?.value;
  if (!date) return;
  const entry = EVAL.log.find(e => e.msgId === msgId);
  if (entry) entry.followUp = { date, reason, savedAt: new Date().toISOString() };
  const btn = document.querySelector(`#${msgId} .followup-btn`);
  if (btn) { btn.textContent = '✓'; btn.style.background = 'var(--accent)'; btn.disabled = true; }
  updateEvalStats();
}

function extractConfidence(text) {
  if (/confidence.*HIGH|HIGH.*confidence/i.test(text))     return 'HIGH';
  if (/confidence.*MEDIUM|MEDIUM.*confidence/i.test(text)) return 'MEDIUM';
  if (/confidence.*LOW|LOW.*confidence/i.test(text))       return 'LOW';
  return null;
}

function showTyping() {
  const c  = document.getElementById('chat-container');
  const el = document.createElement('div');
  el.id        = 'typing-indicator';
  el.className = 'message bot';
  el.innerHTML = `
    <div class="msg-avatar">🏥</div>
    <div class="msg-body">
      <div class="typing-indicator">
        <div class="typing-dot"></div><div class="typing-dot"></div><div class="typing-dot"></div>
      </div>
    </div>`;
  c.appendChild(el);
  c.scrollTop = c.scrollHeight;
}

function removeTyping() { document.getElementById('typing-indicator')?.remove(); }

function renderQuickReplies() {
  const c  = document.getElementById('chat-container');
  const el = document.createElement('div');
  el.className = 'quick-replies';
  el.id        = 'quick-replies';
  BOT_CONFIG.quickReplies.forEach(r => {
    const btn       = document.createElement('button');
    btn.className   = 'quick-btn';
    btn.textContent = r;
    btn.onclick     = () => { el.remove(); send(r); };
    el.appendChild(btn);
  });
  c.appendChild(el);
  c.scrollTop = c.scrollHeight;
}

function formatBotText(text) {
  return esc(text)
    .replace(/\n\n/g, '</p><p style="margin-top:8px">')
    .replace(/\n/g,    '<br>')
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.+?)\*/g,   '<em>$1</em>')
    .replace(/`(.+?)`/g,  '<code style="font-family:var(--font-mono);font-size:12.5px;background:var(--bg);padding:1px 5px;border-radius:3px">$1</code>')
    .replace(/(EMERGENCY REFERRAL REQUIRED|REFER URGENTLY|REFER IMMEDIATELY)/g,
             '<span style="color:var(--danger);font-weight:700">⚠ $1</span>');
}

// ─── SEND ─────────────────────────────────────────────────────────────────
async function send(override) {
  if (busy) return;
  const inp  = document.getElementById('user-input');
  const text = (override || inp?.value || '').trim();
  if (!text) return;

  document.getElementById('quick-replies')?.remove();
  if (inp) { inp.value = ''; inp.style.height = ''; }
  if (detectEmergency(text)) setEmergencyMode(true);

  addMsg('user', text);
  history.push({ role: 'user', content: text });

  busy = true;
  const sendBtn = document.getElementById('send-btn');
  if (sendBtn) sendBtn.disabled = true;
  showTyping();

  try {
    const reply = await callAIWithRetry();
    removeTyping();
    addMsg('bot', reply);
    history.push({ role: 'assistant', content: reply });
  } catch (err) {
    removeTyping();
    const amb = EMERGENCY_CONTACTS.ambulance || '999';
    addMsg('bot',
      `⚠️ Unable to reach the AI service: ${esc(err.message || 'Unknown error')}\n\n` +
      `Please check your connection and try again. For emergencies call: ${amb}`
    );
    console.error('[HealthAssist CDST]', err);
  }

  busy = false;
  if (sendBtn) sendBtn.disabled = false;
  inp?.focus();
}

// ─── AI CALL STACK ────────────────────────────────────────────────────────
async function callAIWithRetry(maxRetries = 2, timeoutMs = 20000) {
  let lastErr;
  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    const controller = new AbortController();
    const timer      = setTimeout(() => controller.abort(), timeoutMs);
    try {
      const reply = await callAI(controller.signal);
      clearTimeout(timer);
      return reply;
    } catch (err) {
      clearTimeout(timer);
      lastErr = err;
      if (err.name === 'AbortError') throw new Error(`Request timed out after ${timeoutMs / 1000}s`);
      if (attempt < maxRetries) {
        await sleep(1000 * (attempt + 1));
        console.warn(`[CDST] Retry ${attempt + 1}/${maxRetries}: ${err.message}`);
      }
    }
  }
  throw lastErr;
}

async function callAI(signal) {
  return PROVIDER.type === 'anthropic' ? callAnthropic(signal) : callOpenAICompat(signal);
}

async function callAnthropic(signal) {
  const messages = history.map(m => ({
    role:    m.role === 'assistant' ? 'assistant' : 'user',
    content: m.content,
  }));
  const res = await fetch(PROVIDER.endpoint, {
    method: 'POST', signal,
    headers: {
      'Content-Type':    'application/json',
      'x-api-key':       PROVIDER.token,
      'anthropic-version': PROVIDER.apiVersion || '2023-06-01',
      'anthropic-dangerous-direct-browser-access': 'true',
    },
    body: JSON.stringify({
      model:      PROVIDER.model,
      max_tokens: 1024,
      system:     BOT_CONFIG.system,
      messages,
    }),
  });
  if (!res.ok) {
    const e = await res.json().catch(() => ({}));
    throw new Error(e.error?.message || `HTTP ${res.status}`);
  }
  const data = await res.json();
  return data.content?.[0]?.text?.trim() || 'No response received.';
}

async function callOpenAICompat(signal) {
  const res = await fetch(PROVIDER.endpoint, {
    method: 'POST', signal,
    headers: {
      'Content-Type':  'application/json',
      'Authorization': `${PROVIDER.authHeader} ${PROVIDER.token}`,
    },
    body: JSON.stringify({
      model:       PROVIDER.model,
      messages:    [{ role: 'system', content: BOT_CONFIG.system }, ...history],
      max_tokens:  1024,
      temperature: 0.2,
    }),
  });
  if (!res.ok) {
    const e = await res.json().catch(() => ({}));
    throw new Error(e.error?.message || `HTTP ${res.status}`);
  }
  const data = await res.json();
  return data.choices?.[0]?.message?.content?.trim() || 'No response received.';
}

// ─── DOSING CALCULATOR ────────────────────────────────────────────────────
function toggleDosePanel() {
  const panel = document.getElementById('dose-panel');
  panel?.classList.toggle('open');
  if (panel?.classList.contains('open')) renderFormulary();
}

function renderFormulary() {
  const sel = document.getElementById('dose-medicine');
  if (!sel || sel.options.length > 1) return;
  FORMULARY.forEach((med, i) => {
    const opt       = document.createElement('option');
    opt.value       = i;
    opt.textContent = med.name;
    sel.appendChild(opt);
  });
}

function calculateDose() {
  const medIdx = parseInt(document.getElementById('dose-medicine')?.value);
  const weight = parseFloat(document.getElementById('dose-weight')?.value);
  const result = document.getElementById('dose-result');
  if (!result) return;

  if (isNaN(weight) || weight <= 0 || isNaN(medIdx) || medIdx < 0) {
    result.innerHTML = '<span style="color:var(--muted);font-size:13px">Enter weight and select medicine.</span>';
    return;
  }

  const med = FORMULARY[medIdx];
  if (!med) return;

  let doseText = '', warningText = '';

  switch (med.name) {
    case 'Paracetamol': {
      const dose    = (weight * 15).toFixed(0);
      const syrupMl = ((weight * 15) / (120 / 5)).toFixed(1);
      const tabQty  = (weight * 15 / 500).toFixed(2);
      doseText = `${dose} mg per dose<br>
        <small style="font-size:12px;color:var(--text-2)">= ${syrupMl} ml syrup or ${parseFloat(tabQty).toFixed(1)} × 500mg tab</small><br>
        <small style="font-size:12px;color:var(--muted)">Every 4–6h, max 4 doses/day</small>`;
      if (weight * 15 * 4 > 60 * weight) warningText = 'Max dose: do not exceed 60mg/kg/day';
      break;
    }
    case 'Amoxicillin': {
      const dose    = (weight * 40 / 3).toFixed(0);
      const syrupMl = ((weight * 40 / 3) / (250 / 5)).toFixed(1);
      doseText = `${dose} mg per dose (3× daily)<br>
        <small style="font-size:12px;color:var(--text-2)">= ${syrupMl} ml syrup (250mg/5ml)</small><br>
        <small style="font-size:12px;color:var(--muted)">Duration: 5 days</small>`;
      break;
    }
    case 'ORS':
      doseText = `${(weight * 75).toFixed(0)} ml over 3–4h (moderate)<br>
        <small style="font-size:12px;color:var(--text-2)">Severe: ${(weight * 100).toFixed(0)} ml over 3h</small>`;
      break;
    case 'Zinc sulfate':
      doseText  = weight < 5
        ? '10 mg daily (½ tablet × 10 days — under 6 months)'
        : '20 mg daily (1 tablet × 10 days)';
      doseText += '<br><small style="font-size:12px;color:var(--muted)">Give with ORS for diarrhoea</small>';
      break;
    case 'Vitamin A':
      doseText  = weight < 8 ? '100,000 IU once (under 12 months)' : '200,000 IU once (12 months and above)';
      doseText += '<br><small style="font-size:12px;color:var(--muted)">Do not repeat within 4–6 weeks</small>';
      break;
    case 'Artesunate rectal': {
      const dose = (weight * 10).toFixed(0);
      doseText   = `${dose} mg single pre-referral dose<br>
        <small style="font-size:12px;color:var(--text-2)">= ${Math.ceil(weight * 10 / 200)} × 200mg suppository</small>`;
      warningText = 'PRE-REFERRAL ONLY — transfer to facility immediately after';
      break;
    }
    default:
      doseText = esc(med.dosing);
  }

  result.innerHTML = `
    <span class="dose-qty">${doseText}</span>
    <span style="font-size:12px;color:var(--muted)">Based on ${weight} kg · ${med.name}</span>
    ${warningText ? `<div class="dose-warning">⚠ ${warningText}</div>` : ''}
    <div style="font-size:11px;color:var(--muted);margin-top:8px">
      Confirm with national formulary. Supports — does not replace — clinical judgment.
    </div>`;
}

// ─── PROTOCOLS SIDEBAR ────────────────────────────────────────────────────
async function loadProtocols() {
  try {
    const res = await fetch('static/data/protocols.json');
    protocolData = await res.json();
    renderProtocolSidebar();
  } catch (e) { console.warn('Protocol data unavailable:', e); }
}

function renderProtocolSidebar() {
  const list = document.getElementById('protocol-list');
  if (!list || !protocolData) return;
  const items = [
    { key: 'imci',            icon: '👶', label: 'IMCI Danger Signs',   badge: 'Emergency', color: 'red'    },
    { key: 'muac',            icon: '📏', label: 'MUAC Screening',       badge: 'Nutrition',  color: 'orange' },
    { key: 'malaria_rdt',     icon: '🦟', label: 'Malaria RDT Protocol', badge: 'Malaria',    color: 'orange' },
    { key: 'maternal',        icon: '🤱', label: 'Safe Motherhood',       badge: 'Maternal',   color: 'green'  },
    { key: 'newborn',         icon: '🍼', label: 'Newborn Danger Signs',  badge: '0–28d',      color: 'red'    },
    { key: 'referral_levels', icon: '🚑', label: 'Referral Levels',       badge: 'Guide',      color: 'green'  },
  ];
  list.innerHTML = items.map(item => `
    <div class="protocol-item" onclick="showProtocol('${item.key}')" role="button" tabindex="0"
         onkeydown="if(event.key==='Enter')showProtocol('${item.key}')">
      <div class="protocol-title">${item.icon} ${item.label} <span class="protocol-badge ${item.color}">${item.badge}</span></div>
      <div class="protocol-sub">Tap for quick reference</div>
    </div>`).join('');
}

function showProtocol(key) {
  if (!protocolData?.[key]) return;
  const p     = protocolData[key];
  const modal = document.getElementById('modal-overlay');
  const title = document.getElementById('modal-title');
  const body  = document.getElementById('modal-body');
  if (!modal) return;
  title.textContent = p.title || key;
  body.innerHTML    = buildProtocolHTML(key, p);
  modal.classList.add('open');
}

function buildProtocolHTML(key, p) {
  const listItems = arr => (arr || []).map(s =>
    `<div class="protocol-list-item"><div class="protocol-bullet"></div><span>${esc(s)}</span></div>`
  ).join('');

  if (key === 'imci') return `
    <div class="protocol-section"><div class="protocol-section-title" style="color:var(--danger)">⚠ Emergency signs</div>${listItems(p.emergency_signs)}</div>
    <div class="protocol-section"><div class="protocol-section-title">Fever classification</div>
      ${Object.entries(p.classify_fever || {}).map(([k,v]) =>
        `<div class="protocol-list-item"><div class="protocol-bullet orange"></div>
         <span><strong>${k.replace('_',' ')}:</strong> ${esc(v)}</span></div>`).join('')}
    </div>
    <div class="protocol-section"><div class="protocol-section-title">Respiratory rate thresholds</div>
      ${Object.entries(p.respiratory_rate_thresholds || {}).map(([k,v]) =>
        `<div class="protocol-list-item"><div class="protocol-bullet orange"></div>
         <span><strong>${k.replace(/_/g,' ')}:</strong> ${esc(v)}</span></div>`).join('')}
    </div>`;

  if (key === 'muac') return `
    <div class="protocol-section"><div class="protocol-section-title">MUAC thresholds</div>
      ${Object.entries(p.thresholds || {}).map(([k,v]) =>
        `<div class="protocol-list-item">
         <div class="protocol-bullet ${k==='green'?'green':k==='yellow'?'orange':''}"></div>
         <span><strong>${k.toUpperCase()}:</strong> ${esc(v)}</span></div>`).join('')}
    </div>
    <div class="protocol-section"><div class="protocol-section-title" style="color:var(--danger)">Bilateral oedema</div>
      <p style="font-size:13.5px">${esc(p.bilateral_oedema || '')}</p></div>
    ${p.appetite_test ? `<div class="protocol-section"><div class="protocol-section-title">Appetite test</div><p style="font-size:13.5px">${esc(p.appetite_test)}</p></div>` : ''}`;

  if (key === 'malaria_rdt') return `
    <div class="protocol-section"><div class="protocol-section-title">RDT results</div>
      <p style="font-size:13.5px;margin-bottom:8px"><strong>Positive:</strong> ${esc(p.positive || '')}</p>
      <p style="font-size:13.5px"><strong>Negative:</strong> ${esc(p.negative_clinical || '')}</p></div>
    <div class="protocol-section"><div class="protocol-section-title" style="color:var(--danger)">⚠ Severe malaria</div>
      ${listItems(p.severe_signs)}
      <p style="font-size:13px;margin-top:8px;color:var(--danger)">${esc(p.severe_action || '')}</p></div>`;

  if (key === 'maternal') return `
    <div class="protocol-section"><div class="protocol-section-title" style="color:var(--danger)">⚠ Refer immediately</div>
      ${listItems(p.refer_immediately)}</div>
    ${p.anc_schedule ? `<div class="protocol-section"><div class="protocol-section-title">ANC schedule</div><p style="font-size:13px">${esc(p.anc_schedule)}</p></div>` : ''}`;

  if (key === 'newborn') return `
    <div class="protocol-section"><div class="protocol-section-title" style="color:var(--danger)">⚠ Newborn danger signs</div>
      ${listItems(p.danger_signs)}</div>`;

  if (key === 'referral_levels') {
    const icons = { immediate:'🔴', urgent:'🟠', routine:'🟡', monitor:'🟢' };
    return `<div class="protocol-section">
      ${Object.entries(p).map(([k,v]) =>
        `<div class="protocol-list-item">
         <span style="font-size:16px">${icons[k] || '•'}</span>
         <span><strong style="text-transform:capitalize">${k}:</strong> ${esc(v)}</span></div>`).join('')}
    </div>`;
  }

  return `<p style="font-size:13.5px">${esc(JSON.stringify(p, null, 2))}</p>`;
}

function closeModal() { document.getElementById('modal-overlay')?.classList.remove('open'); }

// ─── EVALUATION ───────────────────────────────────────────────────────────
function rateMsgAccuracy(msgId, rating) {
  const entry = EVAL.log.find(e => e.msgId === msgId);
  if (entry) entry.feedback = rating;
  const msg = document.getElementById(msgId);
  if (msg) {
    msg.querySelectorAll('.feedback-btn').forEach(btn => btn.classList.remove('active'));
    msg.querySelector(`[onclick*="${rating}"]`)?.classList.add('active');
  }
  updateEvalStats();
  logEvalEvent({ type: 'rating', msgId, rating });
}

function updateEvalStats() {
  const bot = EVAL.log.filter(e => e.role === 'bot');
  const stats = {
    'eval-total':      bot.length,
    'eval-accurate':   EVAL.log.filter(e => e.feedback === 'accurate').length,
    'eval-reviewed':   EVAL.log.filter(e => e.feedback === 'escalate').length,
    'eval-emergency':  EVAL.log.filter(e => e.emergency).length,
    'eval-followups':  EVAL.log.filter(e => e.followUp).length,
    'eval-immediates': EVAL.log.filter(e => e.referral === 'IMMEDIATE').length,
  };
  Object.entries(stats).forEach(([id, val]) => {
    const el = document.getElementById(id);
    if (el) el.textContent = val;
  });
}

function toggleEvalPanel() { document.getElementById('eval-panel')?.classList.toggle('open'); }

function logEvalEvent(data) {
  if (!EVAL.enabled) return;
  const payload = {
    ...data,
    sessionId:       EVAL.sessionId,
    studyId:         EVAL.studyId,
    pathway:         EVAL.pathway,
    arm:             EVAL.arm,
    facilityId:      EVAL.facilityId,
    protocolVersion: EVAL.protocolVersion,
    ts:              data.ts || Date.now(),
  };
  if (EVAL.serverLogUrl && isOnline) {
    fetch(EVAL.serverLogUrl, {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(payload),
      keepalive: true,
    }).catch(() => offlineQueue.push(payload));
  } else if (EVAL.serverLogUrl) {
    offlineQueue.push(payload);
  }
}

function serverLog(entry) { logEvalEvent({ type: 'message', ...entry }); }

function exportSession() {
  const bot  = EVAL.log.filter(e => e.role === 'bot');
  const data = {
    studyId:         EVAL.studyId,
    pathway:         EVAL.pathway,
    arm:             EVAL.arm,
    facilityId:      EVAL.facilityId,
    protocolVersion: EVAL.protocolVersion,
    buildHash:       EVAL.buildHash,
    sessionId:       EVAL.sessionId,
    exportedAt:      new Date().toISOString(),
    summary: {
      totalBotMessages:   bot.length,
      userMessages:       EVAL.log.filter(e => e.role === 'user').length,
      accurateRatings:    EVAL.log.filter(e => e.feedback === 'accurate').length,
      inaccurateRatings:  EVAL.log.filter(e => e.feedback === 'inaccurate').length,
      escalations:        EVAL.log.filter(e => e.feedback === 'escalate').length,
      emergencyAlerts:    EVAL.log.filter(e => e.emergency).length,
      immediateReferrals: EVAL.log.filter(e => e.referral === 'IMMEDIATE').length,
      followUpsScheduled: EVAL.log.filter(e => e.followUp).length,
      highConfidence:     bot.filter(e => e.confidence === 'HIGH').length,
      mediumConfidence:   bot.filter(e => e.confidence === 'MEDIUM').length,
      lowConfidence:      bot.filter(e => e.confidence === 'LOW').length,
    },
    auditChain:          EVAL.log.map(e => ({ msgId: e.msgId, chainHash: e.chainHash })),
    conversationHistory: history,
    evalLog:             EVAL.log,
  };
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
  const url  = URL.createObjectURL(blob);
  const a    = document.createElement('a');
  a.href     = url;
  a.download = `evah-${EVAL.studyId}-${EVAL.facilityId}-${EVAL.sessionId.slice(0, 8)}-${Date.now()}.json`;
  a.click();
  URL.revokeObjectURL(url);
}

// ─── EMERGENCY ACTIONS ────────────────────────────────────────────────────
function triggerEmergency() {
  setEmergencyMode(true);
  addMsg('system', '🚨 Emergency protocol activated', { noFeedback: true });
  send('EMERGENCY: Patient presenting with potential life-threatening condition. Provide immediate triage and referral guidance.');
  logEvalEvent({ type: 'emergency_triggered' });
}

function clearEmergency() {
  setEmergencyMode(false);
  addMsg('system', 'Emergency mode cleared — continuing normal assessment', { noFeedback: true });
}

// ─── SESSION / LOCALE ─────────────────────────────────────────────────────
function toggleSidebar() {
  document.getElementById('sidebar')?.classList.toggle('open');
  document.getElementById('sidebar-backdrop')?.classList.toggle('visible');
}

function switchLocale(locale) {
  LOCALE = locale;
  localStorage.setItem('cdst-locale', locale);
  const inp = document.getElementById('user-input');
  if (inp) inp.placeholder = t('placeholder');
}

function loadLocaleFromStorage() {
  const saved = localStorage.getItem('cdst-locale');
  if (saved) switchLocale(saved);
}

function showGreeting() {
  addMsg('bot', BOT_CONFIG.greeting, { noFeedback: true });
  setTimeout(renderQuickReplies, 400);
}

function newSession() {
  if (emergencyMode && !confirm('Emergency mode is active. Start a new session?')) return;
  history       = [];
  EVAL.log      = [];
  EVAL.sessionId = _genSessionId();
  emergencyMode  = false;
  setEmergencyMode(false);
  document.getElementById('chat-container').innerHTML = '';
  hideBanner();
  showGreeting();
  updateEvalStats();
}
