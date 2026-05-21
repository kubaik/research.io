"""
cdst/html_writer.py — HtmlWriter: generates the main index.html entry point.
"""

from __future__ import annotations

from .config import AppConfig
from .constants import PROTOCOL_VERSION
from .context import BuildContext


class HtmlWriter:
    """Generates the main index.html entry point."""

    def __init__(self, ctx: BuildContext) -> None:
        self._ctx = ctx
        self._cfg = ctx.cfg

    def write(self) -> None:
        content = self._render()
        (self._ctx.output_dir / "index.html").write_text(content, encoding="utf-8")

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _render(self) -> str:
        ctx = self._ctx
        cfg = self._cfg
        app = cfg["app"]
        eval_cfg = cfg.get("evaluation", {})
        i18n = cfg.get("i18n", AppConfig.DEFAULTS["i18n"])

        study_id = eval_cfg.get("study_id", "EVAH-CDST-001")
        pathway = eval_cfg.get("pathway", "A")
        arm = eval_cfg.get("arm", "intervention")
        locale = i18n.get("default_locale", "en")
        locale_btns = self._locale_buttons(
            i18n.get("supported_locales", ["en"]))

        # CHANGE 2: model chip removed from header entirely.
        # CHANGE 3: study/facility/pathway/arm metadata removed from
        #           consent card subtitle and eval panel tags.
        # CHANGE 4: emergency button kept in DOM but permanently hidden
        #           via inline style (JS will never un-hide it).

        return f"""<!DOCTYPE html>
<html lang="{locale}">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta name="description" content="{app["name"]} — {app["tagline"]}. EVAH-aligned AI clinical decision support for community health workers.">
  <meta name="theme-color" content="#0F4C81">
  <link rel="manifest" href="manifest.json">
  <title>{app["name"]} — {app["tagline"]}</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@300;400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="static/css/chat.css?v={ctx.build_hash}">
</head>
<body>

  <div id="emergency-overlay" aria-hidden="true"></div>

  <!-- CONSENT SCREEN — kept in DOM but hidden; JS will never show it
       because consentRequired is false -->
  <div id="consent-overlay" class="hidden" role="dialog" aria-modal="true" aria-labelledby="consent-title">
    <div class="consent-card">
      <div class="consent-icon" aria-hidden="true">🔒</div>
      <h2 class="consent-title" id="consent-title">Research Consent</h2>
      <p class="consent-body" id="consent-body-text">Loading consent text…</p>
      <!-- CHANGE 3: removed study/facility/pathway subtitle line -->
      <div class="consent-actions">
        <button class="consent-btn-primary"   onclick="giveConsent()">I agree and continue</button>
        <button class="consent-btn-secondary" onclick="declineConsent()">Decline (demo mode only)</button>
      </div>
    </div>
  </div>

  <!-- DOSING CALCULATOR PANEL -->
  <div id="dose-panel" aria-label="Dosing calculator">
    <div class="dose-header">
      <span>💊 Dosing Calculator</span>
      <button onclick="toggleDosePanel()" style="background:none;border:none;color:rgba(255,255,255,.8);cursor:pointer;font-size:18px">✕</button>
    </div>
    <div class="dose-body">
      <div class="dose-field">
        <label class="dose-label" for="dose-weight">Patient weight (kg)</label>
        <input type="number" id="dose-weight" class="dose-input" placeholder="e.g. 12.5" min="0.5" max="100" step="0.1" oninput="calculateDose()">
      </div>
      <div class="dose-field">
        <label class="dose-label" for="dose-medicine">Medicine</label>
        <select id="dose-medicine" class="dose-select" onchange="calculateDose()">
          <option value="-1">Select medicine…</option>
        </select>
      </div>
      <div id="dose-result" class="dose-result" style="color:var(--muted);font-size:13px">
        Enter weight and select a medicine.
      </div>
      <div style="margin-top:14px;font-size:11.5px;color:var(--muted);line-height:1.6;border-top:1px solid var(--border-light);padding-top:12px">
        CHW formulary only. Always confirm with national protocol.<br>
        Protocol version: {PROTOCOL_VERSION}
      </div>
    </div>
  </div>

  <!-- HEADER -->
  <header role="banner">
    <div class="header-brand">
      <button class="icon-btn" onclick="toggleSidebar()" aria-label="Toggle protocol sidebar">
        <svg width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M3 12h18M3 6h18M3 18h18"/></svg>
      </button>
      <div class="header-logo" aria-hidden="true">{app["icon"]}</div>
      <div class="header-text">
        <div class="header-name">{app["name"]}</div>
        <div class="header-tagline">{app["tagline"]}</div>
      </div>
    </div>
    <div class="header-controls">
      {locale_btns}
      <!-- CHANGE 2: model chip removed — no provider/model name displayed -->
      <div class="status-pill">
        <div class="status-dot" id="status-dot"></div>
        <span>Online</span>
      </div>
      <button class="icon-btn" onclick="toggleDosePanel()"  aria-label="Dosing calculator" title="Dosing calculator">💊</button>
      <button class="icon-btn" onclick="toggleEvalPanel()"  aria-label="Evaluation panel"  title="EVAH Evaluation">
        <svg width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"/></svg>
      </button>
      <button class="icon-btn" onclick="newSession()" aria-label="New session" title="New session">
        <svg width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M12 5v14m7-7H5"/></svg>
      </button>
    </div>
  </header>

  <div id="safety-banner" role="status" aria-live="polite">Initialising…</div>

  <div class="app-body">

    <!-- PROTOCOL SIDEBAR -->
    <aside id="sidebar" aria-label="Clinical protocols">
      <div class="sidebar-header">
        <span>Quick Protocols</span>
        <span style="font-weight:400;font-size:10px;color:var(--border)">v{PROTOCOL_VERSION}</span>
      </div>
      <div class="protocol-list" id="protocol-list">
        <div style="padding:12px 8px;font-size:12.5px;color:var(--muted)">Loading protocols…</div>
      </div>
    </aside>

    <!-- CHAT COLUMN -->
    <main id="chat-col">
      <div id="chat-container" role="log" aria-live="polite" aria-label="Clinical conversation"></div>
      <div id="input-bar">
        <div class="input-inner">
          <textarea
            id="user-input"
            placeholder="Describe the patient's symptoms or ask a clinical question…"
            autocomplete="off"
            aria-label="Enter clinical query"
            rows="1"
            maxlength="2000"
          ></textarea>
          <div class="input-actions">
            <!-- CHANGE 4: emergency button permanently hidden — display:none
                 and JS will not call show/removeAttribute on it -->
            <button id="emergency-btn" onclick="triggerEmergency()" aria-label="Emergency protocol" title="Emergency protocol" style="display:none !important">
              <svg width="14" height="14" fill="currentColor" viewBox="0 0 24 24"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-2h2v2zm0-4h-2V7h2v6z"/></svg>
              Emergency
            </button>
            <button id="send-btn" onclick="send()" aria-label="Send message">
              <svg width="17" height="17" fill="none" stroke="currentColor" stroke-width="2.2" viewBox="0 0 24 24"><path d="M22 2L11 13M22 2L15 22l-4-9-9-4 20-7z"/></svg>
            </button>
          </div>
        </div>
      </div>
    </main>

    <!-- EVALUATION PANEL -->
    <aside id="eval-panel" aria-label="Evaluation dashboard">
      <!-- CHANGE 3: "📊 EVAH Evaluation — {study_id}" title simplified;
           study ID, facility, pathway, arm tags removed from the tags block -->
      <div class="eval-title">📊 Session Evaluation</div>
      <div>
        <div class="eval-stat"><span>Bot responses</span>       <span class="eval-stat-val" id="eval-total">0</span></div>
        <div class="eval-stat"><span>Marked accurate</span>     <span class="eval-stat-val" id="eval-accurate">0</span></div>
        <div class="eval-stat"><span>Escalated for review</span><span class="eval-stat-val" id="eval-reviewed">0</span></div>
        <div class="eval-stat"><span>Emergency alerts</span>    <span class="eval-stat-val" id="eval-emergency">0</span></div>
        <div class="eval-stat"><span>Immediate referrals</span> <span class="eval-stat-val" id="eval-immediates">0</span></div>
        <div class="eval-stat"><span>Follow-ups scheduled</span><span class="eval-stat-val" id="eval-followups">0</span></div>
      </div>
      <div>
        <div style="font-size:11px;font-weight:600;color:var(--muted);letter-spacing:.06em;text-transform:uppercase;margin-bottom:8px">Tags</div>
        <div>
          <!-- CHANGE 3: only clinical/protocol tags remain; no study/arm/provider metadata -->
          <span class="eval-tag">IMCI</span>
          <span class="eval-tag">{app.get("region", "SSA")}</span>
          <span class="eval-tag">{app.get("facility_type", "PHC")}</span>
        </div>
      </div>
      <div>
        <button onclick="exportSession()" style="width:100%;padding:9px;background:var(--primary);color:white;border:none;border-radius:var(--radius-sm);cursor:pointer;font-size:13px;font-family:var(--font-body);font-weight:500;margin-bottom:6px">
          ⬇ Export Session Data (JSON)
        </button>
        <button onclick="clearEmergency()" style="width:100%;padding:8px;background:var(--surface);color:var(--danger);border:1.5px solid var(--danger);border-radius:var(--radius-sm);cursor:pointer;font-size:13px;font-family:var(--font-body);font-weight:500">
          Clear Emergency Mode
        </button>
      </div>
      <div style="font-size:11px;color:var(--muted);line-height:1.6;border-top:1px solid var(--border-light);padding-top:12px">
        Session data stored locally. Export as JSON for research submission. No PHI transmitted.<br><br>
        Protocol v{PROTOCOL_VERSION} · Build {ctx.build_hash}
      </div>
    </aside>

  </div>

  <!-- PROTOCOL REFERENCE MODAL -->
  <div id="modal-overlay" role="dialog" aria-modal="true" aria-label="Protocol reference" onclick="if(event.target===this)closeModal()">
    <div class="modal">
      <div class="modal-header">
        <div class="modal-title" id="modal-title">Protocol Reference</div>
        <button class="modal-close" onclick="closeModal()" aria-label="Close">✕</button>
      </div>
      <div class="modal-body" id="modal-body"></div>
    </div>
  </div>

  <!-- Built: {ctx.built_at_str} | Provider: {ctx.provider_name} | Model: {ctx.model_id} | Proto: {PROTOCOL_VERSION} | Hash: {ctx.build_hash} -->
  <script src="static/js/chat.js?v={ctx.build_hash}"></script>
</body>
</html>
"""

    @staticmethod
    def _locale_buttons(locales: list[str]) -> str:
        style = (
            "font-size:11px;"
            "background:rgba(255,255,255,.12);"
            "border:1px solid rgba(255,255,255,.20);"
            "color:rgba(255,255,255,.80);"
            "padding:3px 7px;"
            "border-radius:4px;"
            "cursor:pointer;"
            "font-family:var(--font-body)"
        )
        return " ".join(
            f'<button onclick="switchLocale(\'{loc}\')" style="{style}">{loc.upper()}</button>'
            for loc in locales
        )
