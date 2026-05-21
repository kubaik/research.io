"""
cdst/js_writer.py — JavaScriptWriter: generates the entire client-side
JavaScript bundle (chat.js).
"""

from __future__ import annotations

import json

from .config import AppConfig
from .constants import PROTOCOL_VERSION
from .context import BuildContext


class JavaScriptWriter:
    """Generates the entire client-side JavaScript bundle."""

    def __init__(self, ctx: BuildContext) -> None:
        self._ctx = ctx
        self._cfg = ctx.cfg

    def write(self) -> None:
        content = self._render()
        (self._ctx.output_dir / "static" / "js" / "chat.js").write_text(
            content, encoding="utf-8"
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _js_escape(text: str) -> str:
        return text.replace("\\", "\\\\").replace("`", "\\`").replace("\n", "\\n")

    def _render(self) -> str:
        ctx = self._ctx
        cfg = self._cfg
        bot = cfg["bot"]
        app = cfg["app"]
        eval_cfg = cfg.get("evaluation", {})
        i18n_cfg = cfg.get("i18n", AppConfig.DEFAULTS["i18n"])
        formulary = cfg.get("formulary", AppConfig.DEFAULTS["formulary"])

        provider = ctx.provider
        provider_type = provider.get(
            "provider_type", "openai") if provider else "demo"
        auth_header = provider.get(
            "auth_header", "Bearer") if provider else "Bearer"
        api_version = provider.get("api_version", "") if provider else ""

        return f"""/* HealthAssist CDST v1 — Auto-generated */
/* EVAH-Aligned Clinical Decision Support Tool */
/* Provider: {ctx.provider_name} | Model: {ctx.model_id} | Built: {ctx.built_at_str} | Hash: {ctx.build_hash} */

'use strict';

// ─── PROVIDER CONFIG ──────────────────────────────────────────────────────
const PROVIDER = {{
  token:      `{self._js_escape(ctx.token)}`,
  endpoint:   `{provider["endpoint"] if provider else ""}`,
  model:      `{ctx.model_id}`,
  name:       `{ctx.provider_name}`,
  authHeader: `{auth_header}`,
  apiVersion: `{api_version}`,
  type:       `{provider_type}`,
}};

// ─── BOT CONFIG ───────────────────────────────────────────────────────────
const BOT_CONFIG = {{
  system:         `{self._js_escape(bot["system_prompt"])}`,
  greeting:       `{self._js_escape(bot["greeting"])}`,
  quickReplies:   {json.dumps(bot["quick_replies"], ensure_ascii=False)},
  safetyKeywords: {json.dumps(bot.get("safety_keywords", []), ensure_ascii=False)},
}};

// ─── EVALUATION CONFIG ────────────────────────────────────────────────────
const EVAL = {{
  enabled:         {str(eval_cfg.get("enabled", True)).lower()},
  studyId:         '{eval_cfg.get("study_id", "EVAH-CDST-001")}',
  pathway:         '{eval_cfg.get("pathway", "A")}',
  arm:             '{eval_cfg.get("arm", "intervention")}',
  facilityId:      '{app.get("facility_id", "FACILITY-001")}',
  protocolVersion: '{PROTOCOL_VERSION}',
  buildHash:       '{ctx.build_hash}',
  consentRequired: {str(eval_cfg.get("consent_required", True)).lower()},
  consentText:     `{self._js_escape(eval_cfg.get("consent_text", ""))}`,
  serverLogUrl:    `{eval_cfg.get("server_log_url", "")}`,
  sessionId:       _genSessionId(),
  consentGiven:    false,
  log:             [],
}};

// ─── FORMULARY ────────────────────────────────────────────────────────────
const FORMULARY = {json.dumps(formulary.get("medicines", []), ensure_ascii=False)};

// ─── I18N ─────────────────────────────────────────────────────────────────
const I18N_STRINGS = {json.dumps(i18n_cfg.get("strings", {}), ensure_ascii=False)};
let LOCALE = navigator.language?.startsWith('sw') ? 'sw' : '{i18n_cfg.get("default_locale", "en")}';
function t(key) {{ return (I18N_STRINGS[LOCALE] || I18N_STRINGS['{i18n_cfg.get("default_locale", "en")}'] || {{}})[key] || key; }}

// ─── EMERGENCY CONTACTS ───────────────────────────────────────────────────
const EMERGENCY_CONTACTS = {json.dumps(app.get("emergency_contacts", {}), ensure_ascii=False)};

// ─── OFFLINE QUEUE ────────────────────────────────────────────────────────
let offlineQueue = [];
let isOnline     = navigator.onLine;

window.addEventListener('online',  () => {{ isOnline = true;  flushOfflineQueue(); updateConnectionStatus(); }});
window.addEventListener('offline', () => {{ isOnline = false; updateConnectionStatus(); }});

function updateConnectionStatus() {{
  const dot = document.getElementById('status-dot');
  if (dot) dot.className = 'status-dot' + (isOnline ? '' : ' offline');
}}

async function flushOfflineQueue() {{
  if (!EVAL.serverLogUrl || !offlineQueue.length) return;
  const batch = [...offlineQueue];
  offlineQueue = [];
  try {{
    await fetch(EVAL.serverLogUrl, {{
      method: 'POST',
      headers: {{'Content-Type': 'application/json'}},
      body: JSON.stringify({{ batch, sessionId: EVAL.sessionId }}),
    }});
  }} catch (e) {{
    offlineQueue = [...batch, ...offlineQueue];
  }}
}}

// ─── STATE ────────────────────────────────────────────────────────────────
let history       = [];
let busy          = false;
let msgCounter    = 0;
let emergencyMode = false;
let protocolData  = null;

// ─── UTILS ────────────────────────────────────────────────────────────────
function _genSessionId() {{
  return crypto.randomUUID ? crypto.randomUUID() : Math.random().toString(36).slice(2);
}}

function _hashChain(prev, data) {{
  return btoa(prev.slice(-8) + JSON.stringify(data)).slice(0, 16);
}}

function esc(t) {{
  return String(t || '')
    .replace(/&/g, '&amp;').replace(/</g, '&lt;')
    .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}}

function sleep(ms) {{ return new Promise(r => setTimeout(r, ms)); }}

// ─── INIT ─────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', async () => {{
  if ('serviceWorker' in navigator) {{
    navigator.serviceWorker.register('./sw.js').catch(e => console.warn('SW:', e));
  }}
  EVAL.consentRequired ? showConsentScreen() : initApp();
}});

function initApp() {{
  renderProviderBanner();
  showGreeting();
  loadProtocols();
  updateEvalStats();
  updateConnectionStatus();
  loadLocaleFromStorage();

  const inp = document.getElementById('user-input');
  inp?.addEventListener('keydown', e => {{ if (e.key === 'Enter' && !e.shiftKey) {{ e.preventDefault(); send(); }} }});
  inp?.addEventListener('input', autoResize);
}}

function autoResize() {{
  const el = document.getElementById('user-input');
  el.style.height = 'auto';
  el.style.height = Math.min(el.scrollHeight, 120) + 'px';
}}

// ─── CONSENT ──────────────────────────────────────────────────────────────
function showConsentScreen() {{
  const overlay = document.getElementById('consent-overlay');
  if (!overlay) {{ initApp(); return; }}
  const studyBadge = document.getElementById('consent-study-id');
  if (studyBadge) studyBadge.textContent = `Study: ${{EVAL.studyId}} | Pathway ${{EVAL.pathway}} | Facility: ${{EVAL.facilityId}}`;
  const bodyEl = document.getElementById('consent-body-text');
  if (bodyEl) bodyEl.textContent = EVAL.consentText;
  overlay.classList.remove('hidden');
}}

function giveConsent() {{
  EVAL.consentGiven     = true;
  EVAL.consentTimestamp = new Date().toISOString();
  document.getElementById('consent-overlay')?.classList.add('hidden');
  initApp();
  logEvalEvent({{ type: 'consent', given: true, ts: EVAL.consentTimestamp }});
}}

function declineConsent() {{
  EVAL.consentGiven = false;
  EVAL.enabled      = false;
  document.getElementById('consent-overlay')?.classList.add('hidden');
  initApp();
  logEvalEvent({{ type: 'consent', given: false }});
}}

// ─── PROVIDER BANNER ──────────────────────────────────────────────────────
function renderProviderBanner() {{
  const el  = document.getElementById('safety-banner');
  const dot = document.getElementById('status-dot');
  if (!el) return;

  if (!PROVIDER.token || PROVIDER.name === 'demo') {{
    el.className = 'status-demo';
    el.innerHTML = '⚠️ &nbsp;Demo mode — set <strong>ANTHROPIC_API_KEY</strong> or another API key in GitHub Secrets.';
    if (dot) dot.className = 'status-dot offline';
  }} else {{
    el.className = 'status-live';
    el.innerHTML = '✅ &nbsp;Live AI — Clinical Decision Support Tool';
  }}
}}

// ─── GREETING ─────────────────────────────────────────────────────────────
function showGreeting() {{
  addMsg('bot', BOT_CONFIG.greeting, {{ noFeedback: true }});
  setTimeout(renderQuickReplies, 400);
}}

// ─── SAFETY / EMERGENCY ───────────────────────────────────────────────────
function detectEmergency(text) {{
  const lower = text.toLowerCase();
  return BOT_CONFIG.safetyKeywords.some(kw => lower.includes(kw));
}}

function setEmergencyMode(on) {{
  emergencyMode = on;
  const overlay = document.getElementById('emergency-overlay');
  const banner  = document.getElementById('safety-banner');
  const amb     = EMERGENCY_CONTACTS.ambulance || '999';
  if (on) {{
    overlay?.classList.add('active');
    if (banner) {{
      banner.className = 'status-emergency';
      banner.innerHTML = `🚨 &nbsp;<strong>EMERGENCY ALERT</strong> — Refer immediately. Ambulance: <strong>${{amb}}</strong>`;
    }}
  }} else {{
    overlay?.classList.remove('active');
    renderProviderBanner();
  }}
}}

// ─── STRUCTURED CLINICAL CARD ─────────────────────────────────────────────
function parseClinicalJSON(text) {{
  const match = text.match(/\\{{[\\s\\S]*\\}}/);
  if (!match) return null;
  try {{ return JSON.parse(match[0]); }} catch {{ return null; }}
}}

function renderClinicalCard(data) {{
  const refClass = {{ IMMEDIATE: 'immediate', URGENT: 'urgent', ROUTINE: 'routine', MONITOR: 'monitor' }}[data.referral] || 'monitor';
  const refLabel = {{
    IMMEDIATE: '🔴 EMERGENCY REFERRAL REQUIRED',
    URGENT:    '🟠 Urgent referral (2–4h)',
    ROUTINE:   '🟡 Routine referral',
    MONITOR:   '🟢 Monitor at facility',
  }}[data.referral] || data.referral;

  const actionsHtml = (data.actions || []).map((a, i) =>
    `<div style="display:flex;gap:8px;padding:4px 0;font-size:13.5px;border-bottom:1px solid var(--border-light)">
      <span style="font-family:var(--font-mono);font-size:11px;color:var(--muted);min-width:18px;padding-top:2px">${{i+1}}</span>
      <span>${{esc(a)}}</span>
    </div>`
  ).join('');

  const flagsHtml = (data.red_flags     || []).map(f => `<span class="tag red">${{esc(f)}}</span>`).join('');
  const diffsHtml = (data.differentials || []).map(d => `<span class="tag blue">${{esc(d)}}</span>`).join('');

  const formularyNote = data.formulary_note && data.formulary_note !== 'null'
    ? `<div class="clinical-section">
        <div class="clinical-section-label warning">⚠ Formulary note</div>
        <div class="clinical-content">${{esc(data.formulary_note)}}</div>
       </div>`
    : '';

  return `<div class="clinical-card">
    <div class="clinical-section">
      <div class="clinical-section-label">Assessment</div>
      <div class="clinical-content">${{esc(data.assessment || '')}}</div>
    </div>
    ${{diffsHtml ? `<div class="clinical-section"><div class="clinical-section-label">Differentials</div><div class="tag-list">${{diffsHtml}}</div></div>` : ''}}
    ${{actionsHtml ? `<div class="clinical-section"><div class="clinical-section-label">Actions</div>${{actionsHtml}}</div>` : ''}}
    ${{flagsHtml   ? `<div class="clinical-section"><div class="clinical-section-label danger">⚠ Red flags</div><div class="tag-list">${{flagsHtml}}</div></div>` : ''}}
    <div class="clinical-section">
      <div class="clinical-section-label">Referral</div>
      <span class="referral-badge ${{refClass}}">${{refLabel}}</span>
      ${{data.referral_reason ? `<div class="clinical-content" style="margin-top:6px;font-size:12.5px;color:var(--text-2)">${{esc(data.referral_reason)}}</div>` : ''}}
    </div>
    ${{formularyNote}}
    <div class="clinical-section" style="background:var(--bg)">
      <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;font-size:12px;color:var(--muted)">
        <span>Confidence: <span class="confidence-chip ${{data.confidence || 'MEDIUM'}}">${{data.confidence || 'MEDIUM'}}</span></span>
        ${{data.confidence_reason ? `<span>${{esc(data.confidence_reason)}}</span>` : ''}}
      </div>
    </div>
  </div>`;
}}

// ─── MESSAGE RENDERING ────────────────────────────────────────────────────
function addMsg(role, text, opts = {{}}) {{
  const container = document.getElementById('chat-container');
  if (!container) return;

  const id  = 'msg-' + (++msgCounter);
  const ts  = new Date().toLocaleTimeString([], {{ hour: '2-digit', minute: '2-digit' }});
  const el  = document.createElement('div');

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
      : esc(text).replace(/\\n/g, '<br>');

  const confidence = clinicalData?.confidence || extractConfidence(text);

  const feedbackHtml = (role === 'bot' && !opts.noFeedback) ? `
    <div class="msg-feedback">
      <button class="feedback-btn" onclick="rateMsgAccuracy('${{id}}', 'accurate')">✓ Accurate</button>
      <button class="feedback-btn" onclick="rateMsgAccuracy('${{id}}', 'inaccurate')">✗ Inaccurate</button>
      <button class="feedback-btn" onclick="rateMsgAccuracy('${{id}}', 'escalate')">⬆ Review</button>
      ${{confidence ? `<span class="confidence-chip ${{confidence}}">${{confidence}}</span>` : ''}}
    </div>
    <div class="followup-form">
      <div style="font-size:11px;color:var(--muted);margin-bottom:6px;font-weight:600">Schedule follow-up</div>
      <div class="followup-row">
        <input type="date" class="followup-input" id="fu-date-${{id}}" min="${{new Date().toISOString().split('T')[0]}}">
        <input type="text" class="followup-input" id="fu-reason-${{id}}" placeholder="Reason…" style="flex:2">
        <button class="followup-btn" onclick="saveFollowUp('${{id}}')">Save</button>
      </div>
    </div>` : '';

  el.innerHTML = `
    <div class="msg-avatar">${{avatar}}</div>
    <div class="msg-body">
      <div class="msg-bubble">${{bubbleHtml}}</div>
      <div class="msg-meta">
        <span>${{ts}}</span>
        ${{isEmergency ? '<span style="font-weight:600;color:var(--danger)">⚠ EMERGENCY</span>' : ''}}
        ${{!isOnline   ? '<span class="offline-badge">📡 Offline</span>' : ''}}
      </div>
      ${{feedbackHtml}}
    </div>`;

  container.appendChild(el);
  container.scrollTop = container.scrollHeight;

  if (EVAL.enabled) {{
    const prev  = EVAL.log.length ? EVAL.log[EVAL.log.length - 1].chainHash || '' : '';
    const entry = {{
      t: Date.now(), role, len: text.length, emergency: isEmergency,
      referral: clinicalData?.referral || null, confidence: clinicalData?.confidence || confidence || null,
      feedback: null, followUp: null, msgId: id,
      chainHash: _hashChain(prev, {{ role, len: text.length }})
    }};
    EVAL.log.push(entry);
    updateEvalStats();
    serverLog(entry);
  }}

  return id;
}}

function saveFollowUp(msgId) {{
  const date   = document.getElementById(`fu-date-${{msgId}}`)?.value;
  const reason = document.getElementById(`fu-reason-${{msgId}}`)?.value;
  if (!date) return;
  const entry = EVAL.log.find(e => e.msgId === msgId);
  if (entry) entry.followUp = {{ date, reason, savedAt: new Date().toISOString() }};
  const btn = document.querySelector(`#${{msgId}} .followup-btn`);
  if (btn) {{ btn.textContent = '✓'; btn.style.background = 'var(--accent)'; btn.disabled = true; }}
  updateEvalStats();
}}

function extractConfidence(text) {{
  if (/confidence.*HIGH|HIGH.*confidence/i.test(text))     return 'HIGH';
  if (/confidence.*MEDIUM|MEDIUM.*confidence/i.test(text)) return 'MEDIUM';
  if (/confidence.*LOW|LOW.*confidence/i.test(text))       return 'LOW';
  return null;
}}

function showTyping() {{
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
}}

function removeTyping() {{ document.getElementById('typing-indicator')?.remove(); }}

function renderQuickReplies() {{
  const c  = document.getElementById('chat-container');
  const el = document.createElement('div');
  el.className = 'quick-replies';
  el.id        = 'quick-replies';
  BOT_CONFIG.quickReplies.forEach(r => {{
    const btn      = document.createElement('button');
    btn.className  = 'quick-btn';
    btn.textContent = r;
    btn.onclick    = () => {{ el.remove(); send(r); }};
    el.appendChild(btn);
  }});
  c.appendChild(el);
  c.scrollTop = c.scrollHeight;
}}

function formatBotText(text) {{
  return esc(text)
    .replace(/\\n\\n/g, '</p><p style="margin-top:8px">')
    .replace(/\\n/g,   '<br>')
    .replace(/\\*\\*(.+?)\\*\\*/g, '<strong>$1</strong>')
    .replace(/\\*(.+?)\\*/g,   '<em>$1</em>')
    .replace(/`(.+?)`/g,  '<code style="font-family:var(--font-mono);font-size:12.5px;background:var(--bg);padding:1px 5px;border-radius:3px">$1</code>')
    .replace(/(EMERGENCY REFERRAL REQUIRED|REFER URGENTLY|REFER IMMEDIATELY)/g,
             '<span style="color:var(--danger);font-weight:700">⚠ $1</span>');
}}

// ─── SEND + RETRY ─────────────────────────────────────────────────────────
async function send(override) {{
  if (busy) return;
  const inp  = document.getElementById('user-input');
  const text = (override || inp?.value || '').trim();
  if (!text) return;

  document.getElementById('quick-replies')?.remove();
  if (inp) {{ inp.value = ''; inp.style.height = ''; }}
  if (detectEmergency(text)) setEmergencyMode(true);

  addMsg('user', text);
  history.push({{ role: 'user', content: text }});

  busy = true;
  const sendBtn = document.getElementById('send-btn');
  if (sendBtn) sendBtn.disabled = true;
  showTyping();

  try {{
    let reply;
    if (PROVIDER.token && PROVIDER.name !== 'demo' && isOnline) {{
      reply = await callAIWithRetry();
    }} else if (!isOnline) {{
      offlineQueue.push({{ text, ts: Date.now() }});
      reply = await demoReply(text);
      addMsg('system', '📡 Offline — response from local protocols. Will retry with AI when connection restores.', {{ noFeedback: true }});
    }} else {{
      reply = await demoReply(text);
    }}
    removeTyping();
    addMsg('bot', reply);
    history.push({{ role: 'assistant', content: reply }});
  }} catch (err) {{
    removeTyping();
    const amb = EMERGENCY_CONTACTS.ambulance || '999';
    addMsg('bot', `⚠️ Connection error: ${{esc(err.message || 'Unknown error')}}\\n\\nFor emergencies call: ${{amb}}`);
    console.error('[HealthAssist CDST]', err);
  }}

  busy = false;
  if (sendBtn) sendBtn.disabled = false;
  inp?.focus();
}}

async function callAIWithRetry(maxRetries = 2, timeoutMs = 15000) {{
  let lastErr;
  for (let attempt = 0; attempt <= maxRetries; attempt++) {{
    try {{
      const controller = new AbortController();
      const timer      = setTimeout(() => controller.abort(), timeoutMs);
      try {{
        const reply = await callAI(controller.signal);
        clearTimeout(timer);
        return reply;
      }} finally {{
        clearTimeout(timer);
      }}
    }} catch (err) {{
      lastErr = err;
      if (err.name === 'AbortError') throw new Error(`Request timed out after ${{timeoutMs/1000}}s`);
      if (attempt < maxRetries) {{
        await sleep(1000 * (attempt + 1));
        console.warn(`[CDST] Retry ${{attempt + 1}}/${{maxRetries}}`);
      }}
    }}
  }}
  throw lastErr;
}}

async function callAI(signal) {{
  return PROVIDER.type === 'anthropic' ? callAnthropic(signal) : callOpenAICompat(signal);
}}

async function callAnthropic(signal) {{
  const messages = history.map(m => ({{ role: m.role === 'assistant' ? 'assistant' : 'user', content: m.content }}));
  const res = await fetch(PROVIDER.endpoint, {{
    method: 'POST', signal,
    headers: {{
      'Content-Type': 'application/json',
      'x-api-key': PROVIDER.token,
      'anthropic-version': PROVIDER.apiVersion || '2023-06-01',
      'anthropic-dangerous-direct-browser-access': 'true',
    }},
    body: JSON.stringify({{ model: PROVIDER.model, max_tokens: 1024, system: BOT_CONFIG.system, messages }}),
  }});
  if (!res.ok) {{ const e = await res.json().catch(() => ({{}})); throw new Error(e.error?.message || `HTTP ${{res.status}}`); }}
  const data = await res.json();
  return data.content?.[0]?.text?.trim() || 'No response received.';
}}

async function callOpenAICompat(signal) {{
  const res = await fetch(PROVIDER.endpoint, {{
    method: 'POST', signal,
    headers: {{ 'Content-Type': 'application/json', 'Authorization': `${{PROVIDER.authHeader}} ${{PROVIDER.token}}` }},
    body: JSON.stringify({{
      model: PROVIDER.model,
      messages: [{{ role: 'system', content: BOT_CONFIG.system }}, ...history],
      max_tokens: 1024, temperature: 0.2,
    }}),
  }});
  if (!res.ok) {{ const e = await res.json().catch(() => ({{}})); throw new Error(e.error?.message || `HTTP ${{res.status}}`); }}
  const data = await res.json();
  return data.choices?.[0]?.message?.content?.trim() || 'No response received.';
}}

// ─── DEMO MODE ────────────────────────────────────────────────────────────
async function demoReply(text) {{
  await sleep(700 + Math.random() * 400);
  const t = text.toLowerCase();

  if (t.includes('fever') || t.includes('malaria') || t.includes('temperature')) {{
    return JSON.stringify({{
      assessment: "Child presenting with fever in a malaria-endemic setting. Systematic IMCI assessment required before treatment.",
      differentials: ["Uncomplicated malaria", "Bacterial infection (pneumonia, UTI)", "Viral illness", "Meningitis (if stiff neck)"],
      actions: ["Measure temperature (axillary) — document reading","Check ALL IMCI danger signs","Perform malaria RDT if available","Assess respiratory rate vs age-specific threshold","Check for stiff neck and bulging fontanelle","Document weight for weight-based dosing"],
      red_flags: ["Cannot drink or breastfeed", "Had convulsions", "Lethargic or unconscious", "Stiff neck", "Severe respiratory distress"],
      referral: "URGENT", referral_reason: "Fever with any danger sign requires urgent facility assessment within 2–4h.",
      confidence: "MEDIUM", confidence_reason: "Demo mode — limited patient context.",
      formulary_note: "If RDT positive: ACT per national protocol. Paracetamol 15mg/kg/dose for fever ≥38.5°C."
    }});
  }}

  if (t.includes('malnutrition') || t.includes('muac') || t.includes('wasting')) {{
    return JSON.stringify({{
      assessment: "Child presenting for nutritional assessment. MUAC is the primary screening tool for 6–59 month age group.",
      differentials: ["Severe acute malnutrition (SAM)", "Moderate acute malnutrition (MAM)", "Well-nourished"],
      actions: ["Measure MUAC on left mid-upper arm — document in mm","Check for bilateral pitting oedema","Conduct RUTF appetite test if MUAC <115mm","Weigh and plot on growth chart","Assess for medical complications"],
      red_flags: ["MUAC <115mm", "Bilateral pitting oedema", "Failed appetite test", "Unconscious or lethargic"],
      referral: "IMMEDIATE", referral_reason: "SAM with any medical complication requires inpatient stabilisation.",
      confidence: "HIGH", confidence_reason: "MUAC thresholds are evidence-based WHO standards.",
      formulary_note: "RUTF for OTP. Amoxicillin 40mg/kg/day 5 days. Vitamin A 200,000IU once if not given in last 6 months."
    }});
  }}

  if (t.includes('maternal') || t.includes('pregnant') || t.includes('antenatal')) {{
    return JSON.stringify({{
      assessment: "Maternal health query — applying Safe Motherhood protocol. Full obstetric assessment including BP required.",
      differentials: ["Normal pregnancy requiring routine ANC", "Pre-eclampsia", "Antepartum haemorrhage", "Preterm labour"],
      actions: ["Measure BP immediately — target <140/90","Check for headache, visual disturbance, epigastric pain","Assess fetal movement (after quickening)","Check for vaginal bleeding","Document gestational age and ANC contact number"],
      red_flags: ["BP ≥140/90", "Severe headache + visual disturbance", "Heavy vaginal bleeding", "Convulsions", "No fetal movement >12h"],
      referral: "URGENT", referral_reason: "Any danger sign in pregnancy requires urgent obstetric assessment.",
      confidence: "HIGH", confidence_reason: "Safe Motherhood red flags are evidence-based WHO criteria.",
      formulary_note: "Misoprostol 600mcg for PPH prevention. Iron-folate 60mg/0.4mg daily throughout pregnancy."
    }});
  }}

  return JSON.stringify({{
    assessment: "Clinical query received in demo mode. A full response requires an active API key.",
    differentials: ["Diagnosis requires full clinical context", "Please describe specific symptoms for guidance"],
    actions: ["Provide patient age, weight, and chief complaint","Use the protocol sidebar for offline reference","Use the dosing calculator (💊) for weight-based doses"],
    red_flags: ["Any altered consciousness", "Severe breathing difficulty", "Signs of shock"],
    referral: "MONITOR", referral_reason: "Insufficient information to determine referral urgency.",
    confidence: "LOW", confidence_reason: "Demo mode with no patient information.",
    formulary_note: "null"
  }});
}}

// ─── DOSING CALCULATOR ────────────────────────────────────────────────────
function toggleDosePanel() {{
  const panel = document.getElementById('dose-panel');
  panel?.classList.toggle('open');
  if (panel?.classList.contains('open')) renderFormulary();
}}

function renderFormulary() {{
  const sel = document.getElementById('dose-medicine');
  if (!sel || sel.options.length > 1) return;
  FORMULARY.forEach((med, i) => {{
    const opt       = document.createElement('option');
    opt.value       = i;
    opt.textContent = med.name;
    sel.appendChild(opt);
  }});
}}

function calculateDose() {{
  const medIdx = parseInt(document.getElementById('dose-medicine')?.value);
  const weight = parseFloat(document.getElementById('dose-weight')?.value);
  const result = document.getElementById('dose-result');
  if (!result) return;

  if (isNaN(weight) || weight <= 0 || isNaN(medIdx) || medIdx < 0) {{
    result.innerHTML = '<span style="color:var(--muted);font-size:13px">Enter weight and select medicine.</span>';
    return;
  }}

  const med = FORMULARY[medIdx];
  if (!med) return;

  let doseText = '', warningText = '';

  switch (med.name) {{
    case 'Paracetamol': {{
      const dose    = (weight * 15).toFixed(0);
      const syrupMl = ((weight * 15) / (120/5)).toFixed(1);
      const tabQty  = (weight * 15 / 500).toFixed(2);
      doseText = `${{dose}} mg per dose<br><small style="font-size:12px;color:var(--text-2)">= ${{syrupMl}} ml syrup or ${{parseFloat(tabQty).toFixed(1)}} × 500mg tab</small><br><small style="font-size:12px;color:var(--muted)">Every 4–6h, max 4 doses/day</small>`;
      if (weight * 15 * 4 > 60 * weight) warningText = 'Max dose: do not exceed 60mg/kg/day';
      break;
    }}
    case 'Amoxicillin': {{
      const dose    = (weight * 40 / 3).toFixed(0);
      const syrupMl = ((weight * 40 / 3) / (250/5)).toFixed(1);
      doseText = `${{dose}} mg per dose (3x daily)<br><small style="font-size:12px;color:var(--text-2)">= ${{syrupMl}} ml syrup (250mg/5ml)</small><br><small style="font-size:12px;color:var(--muted)">Duration: 5 days</small>`;
      break;
    }}
    case 'ORS': {{
      doseText = `${{(weight * 75).toFixed(0)}} ml over 3–4h (moderate)<br><small style="font-size:12px;color:var(--text-2)">Severe: ${{(weight * 100).toFixed(0)}} ml over 3h</small>`;
      break;
    }}
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
    case 'Artesunate rectal': {{
      const dose = (weight * 10).toFixed(0);
      doseText   = `${{dose}} mg single pre-referral dose<br><small style="font-size:12px;color:var(--text-2)">= ${{Math.ceil(weight * 10 / 200)}} × 200mg suppository</small>`;
      warningText = 'PRE-REFERRAL ONLY — transfer to facility immediately after';
      break;
    }}
    default:
      doseText = esc(med.dosing);
  }}

  result.innerHTML = `
    <span class="dose-qty">${{doseText}}</span>
    <span style="font-size:12px;color:var(--muted)">Based on ${{weight}} kg · ${{med.name}}</span>
    ${{warningText ? `<div class="dose-warning">⚠ ${{warningText}}</div>` : ''}}
    <div style="font-size:11px;color:var(--muted);margin-top:8px">Confirm with national formulary. Supports — does not replace — clinical judgment.</div>`;
}}

// ─── PROTOCOLS SIDEBAR ────────────────────────────────────────────────────
async function loadProtocols() {{
  try {{
    const res  = await fetch('static/data/protocols.json');
    protocolData = await res.json();
    renderProtocolSidebar();
  }} catch (e) {{ console.warn('Protocol data not loaded:', e); }}
}}

function renderProtocolSidebar() {{
  const list = document.getElementById('protocol-list');
  if (!list || !protocolData) return;
  const items = [
    {{ key: 'imci',            icon: '👶', label: 'IMCI Danger Signs',   badge: 'Emergency', color: 'red'    }},
    {{ key: 'muac',            icon: '📏', label: 'MUAC Screening',       badge: 'Nutrition',  color: 'orange' }},
    {{ key: 'malaria_rdt',     icon: '🦟', label: 'Malaria RDT Protocol', badge: 'Malaria',    color: 'orange' }},
    {{ key: 'maternal',        icon: '🤱', label: 'Safe Motherhood',       badge: 'Maternal',   color: 'green'  }},
    {{ key: 'newborn',         icon: '🍼', label: 'Newborn Danger Signs',  badge: '0–28d',      color: 'red'    }},
    {{ key: 'referral_levels', icon: '🚑', label: 'Referral Levels',       badge: 'Guide',      color: 'green'  }},
  ];
  list.innerHTML = items.map(item => `
    <div class="protocol-item" onclick="showProtocol('${{item.key}}')" role="button" tabindex="0">
      <div class="protocol-title">${{item.icon}} ${{item.label}} <span class="protocol-badge ${{item.color}}">${{item.badge}}</span></div>
      <div class="protocol-sub">Tap for quick reference</div>
    </div>`).join('');
}}

function showProtocol(key) {{
  if (!protocolData?.[key]) return;
  const p     = protocolData[key];
  const modal = document.getElementById('modal-overlay');
  const title = document.getElementById('modal-title');
  const body  = document.getElementById('modal-body');
  if (!modal) return;
  title.textContent = p.title || key;
  body.innerHTML    = buildProtocolHTML(key, p);
  modal.classList.add('open');
}}

function buildProtocolHTML(key, p) {{
  const listItems = arr => (arr || []).map(s => `
    <div class="protocol-list-item"><div class="protocol-bullet"></div><span>${{esc(s)}}</span></div>`).join('');

  if (key === 'imci') return `
    <div class="protocol-section"><div class="protocol-section-title" style="color:var(--danger)">⚠ Emergency signs</div>${{listItems(p.emergency_signs)}}</div>
    <div class="protocol-section"><div class="protocol-section-title">Fever classification</div>${{Object.entries(p.classify_fever||{{}}).map(([k,v])=>`<div class="protocol-list-item"><div class="protocol-bullet orange"></div><span><strong>${{k.replace('_',' ')}}:</strong> ${{esc(v)}}</span></div>`).join('')}}</div>
    <div class="protocol-section"><div class="protocol-section-title">Respiratory rate thresholds</div>${{Object.entries(p.respiratory_rate_thresholds||{{}}).map(([k,v])=>`<div class="protocol-list-item"><div class="protocol-bullet orange"></div><span><strong>${{k.replace(/_/g,' ')}}:</strong> ${{esc(v)}}</span></div>`).join('')}}</div>`;

  if (key === 'muac') return `
    <div class="protocol-section"><div class="protocol-section-title">MUAC thresholds</div>${{Object.entries(p.thresholds||{{}}).map(([k,v])=>`<div class="protocol-list-item"><div class="protocol-bullet ${{k==='green'?'green':k==='yellow'?'orange':''}}"></div><span><strong>${{k.toUpperCase()}}:</strong> ${{esc(v)}}</span></div>`).join('')}}</div>
    <div class="protocol-section"><div class="protocol-section-title" style="color:var(--danger)">Bilateral oedema</div><p style="font-size:13.5px">${{esc(p.bilateral_oedema||'')}}</p></div>
    ${{p.appetite_test ? `<div class="protocol-section"><div class="protocol-section-title">Appetite test</div><p style="font-size:13.5px">${{esc(p.appetite_test)}}</p></div>` : ''}}`;

  if (key === 'malaria_rdt') return `
    <div class="protocol-section"><div class="protocol-section-title">RDT results</div><p style="font-size:13.5px;margin-bottom:8px"><strong>Positive:</strong> ${{esc(p.positive||'')}}</p><p style="font-size:13.5px"><strong>Negative:</strong> ${{esc(p.negative_clinical||'')}}</p></div>
    <div class="protocol-section"><div class="protocol-section-title" style="color:var(--danger)">⚠ Severe malaria</div>${{listItems(p.severe_signs)}}<p style="font-size:13px;margin-top:8px;color:var(--danger)">${{esc(p.severe_action||'')}}</p></div>`;

  if (key === 'maternal') return `
    <div class="protocol-section"><div class="protocol-section-title" style="color:var(--danger)">⚠ Refer immediately</div>${{listItems(p.refer_immediately)}}</div>
    ${{p.anc_schedule ? `<div class="protocol-section"><div class="protocol-section-title">ANC schedule</div><p style="font-size:13px">${{esc(p.anc_schedule)}}</p></div>` : ''}}`;

  if (key === 'newborn') return `
    <div class="protocol-section"><div class="protocol-section-title" style="color:var(--danger)">⚠ Newborn danger signs</div>${{listItems(p.danger_signs)}}</div>`;

  if (key === 'referral_levels') {{
    const icons = {{ immediate:'🔴', urgent:'🟠', routine:'🟡', monitor:'🟢' }};
    return `<div class="protocol-section">${{Object.entries(p).map(([k,v])=>`<div class="protocol-list-item"><span style="font-size:16px">${{icons[k]||'•'}}</span><span><strong style="text-transform:capitalize">${{k}}:</strong> ${{esc(v)}}</span></div>`).join('')}}</div>`;
  }}

  return `<p style="font-size:13.5px">${{esc(JSON.stringify(p, null, 2))}}</p>`;
}}

function closeModal() {{ document.getElementById('modal-overlay')?.classList.remove('open'); }}

// ─── EVALUATION ───────────────────────────────────────────────────────────
function rateMsgAccuracy(msgId, rating) {{
  const entry = EVAL.log.find(e => e.msgId === msgId);
  if (entry) entry.feedback = rating;
  const msg = document.getElementById(msgId);
  if (msg) {{
    msg.querySelectorAll('.feedback-btn').forEach(btn => btn.classList.remove('active'));
    msg.querySelector(`[onclick*="${{rating}}"]`)?.classList.add('active');
  }}
  updateEvalStats();
  logEvalEvent({{ type: 'rating', msgId, rating }});
}}

function updateEvalStats() {{
  const bot   = EVAL.log.filter(e => e.role === 'bot');
  const stats = {{
    'eval-total':      bot.length,
    'eval-accurate':   EVAL.log.filter(e => e.feedback === 'accurate').length,
    'eval-reviewed':   EVAL.log.filter(e => e.feedback === 'escalate').length,
    'eval-emergency':  EVAL.log.filter(e => e.emergency).length,
    'eval-followups':  EVAL.log.filter(e => e.followUp).length,
    'eval-immediates': EVAL.log.filter(e => e.referral === 'IMMEDIATE').length,
  }};
  Object.entries(stats).forEach(([id, val]) => {{
    const el = document.getElementById(id);
    if (el) el.textContent = val;
  }});
}}

function toggleEvalPanel() {{ document.getElementById('eval-panel')?.classList.toggle('open'); }}

function logEvalEvent(data) {{
  if (!EVAL.enabled) return;
  const payload = {{ ...data, sessionId: EVAL.sessionId, studyId: EVAL.studyId, pathway: EVAL.pathway, arm: EVAL.arm, facilityId: EVAL.facilityId, protocolVersion: EVAL.protocolVersion, ts: data.ts || Date.now() }};
  if (EVAL.serverLogUrl && isOnline) {{
    fetch(EVAL.serverLogUrl, {{ method: 'POST', headers: {{'Content-Type':'application/json'}}, body: JSON.stringify(payload), keepalive: true }}).catch(() => offlineQueue.push(payload));
  }} else if (EVAL.serverLogUrl) {{
    offlineQueue.push(payload);
  }}
}}

function serverLog(entry) {{ logEvalEvent({{ type: 'message', ...entry }}); }}

function exportSession() {{
  const bot  = EVAL.log.filter(e => e.role === 'bot');
  const data = {{
    studyId: EVAL.studyId, pathway: EVAL.pathway, arm: EVAL.arm,
    facilityId: EVAL.facilityId, protocolVersion: EVAL.protocolVersion,
    buildHash: EVAL.buildHash, sessionId: EVAL.sessionId,
    exportedAt: new Date().toISOString(),
    consentGiven: EVAL.consentGiven, consentTimestamp: EVAL.consentTimestamp || null,
    summary: {{
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
    }},
    auditChain:          EVAL.log.map(e => ({{ msgId: e.msgId, chainHash: e.chainHash }})),
    conversationHistory: history,
    evalLog:             EVAL.log,
  }};
  const blob = new Blob([JSON.stringify(data, null, 2)], {{ type: 'application/json' }});
  const url  = URL.createObjectURL(blob);
  const a    = document.createElement('a');
  a.href     = url;
  a.download = `evah-${{EVAL.studyId}}-${{EVAL.facilityId}}-${{EVAL.sessionId.slice(0,8)}}-${{Date.now()}}.json`;
  a.click();
  URL.revokeObjectURL(url);
}}

// ─── EMERGENCY BUTTON ─────────────────────────────────────────────────────
function triggerEmergency() {{
  setEmergencyMode(true);
  addMsg('system', '🚨 Emergency protocol activated', {{ noFeedback: true }});
  send('EMERGENCY: Patient presenting with potential life-threatening condition. Provide immediate triage and referral guidance.');
  logEvalEvent({{ type: 'emergency_triggered' }});
}}

function clearEmergency() {{
  setEmergencyMode(false);
  addMsg('system', 'Emergency mode cleared — continuing normal assessment', {{ noFeedback: true }});
}}

// ─── SESSION / LOCALE ─────────────────────────────────────────────────────
function toggleSidebar() {{ document.getElementById('sidebar')?.classList.toggle('collapsed'); }}

function switchLocale(locale) {{
  LOCALE = locale;
  localStorage.setItem('cdst-locale', locale);
  const inp = document.getElementById('user-input');
  if (inp) inp.placeholder = t('placeholder');
}}

function loadLocaleFromStorage() {{
  const saved = localStorage.getItem('cdst-locale');
  if (saved) switchLocale(saved);
}}

function newSession() {{
  if (emergencyMode && !confirm('Emergency mode is active. Start a new session?')) return;
  history = []; EVAL.log = []; EVAL.sessionId = _genSessionId(); EVAL.consentGiven = false;
  emergencyMode = false; setEmergencyMode(false);
  document.getElementById('chat-container').innerHTML = '';
  renderProviderBanner();
  EVAL.consentRequired ? showConsentScreen() : showGreeting();
  updateEvalStats();
}}
"""
