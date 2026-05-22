"""
cdst/static_writer.py — StaticFileWriter: writes all non-JS, non-HTML static
assets (CSS, service worker, manifest, protocol data, formulary, i18n, config).
"""

from __future__ import annotations

import json
from typing import Any

from .config import AppConfig
from .constants import PROTOCOL_VERSION
from .context import BuildContext
from .protocols import ProtocolsData


class StaticFileWriter:
    """
    Writes all non-JS, non-HTML static assets to the output directory.
    Each public method writes exactly one file.
    """

    def __init__(self, ctx: BuildContext) -> None:
        self._ctx = ctx
        self._cfg = ctx.cfg

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def write_all(self) -> None:
        self.write_css()
        self.write_service_worker()
        self.write_manifest()
        self.write_protocols()
        self.write_formulary()
        self.write_i18n()
        self.write_config_json()

    # ------------------------------------------------------------------
    # Individual writers
    # ------------------------------------------------------------------

    def write_css(self) -> None:
        t = self._cfg["theme"]
        primary = t["primary_color"]
        accent = t["accent_color"]
        warning = t.get("warning_color", "#E85D04")
        danger = t.get("danger_color",  "#D62828")

        css = f"""/* HealthAssist CDST v1 — Auto-generated | Mobile-first */
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@300;400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap');

:root {{
  --primary:       {primary};
  --primary-light: color-mix(in srgb, {primary} 12%, white);
  --primary-mid:   color-mix(in srgb, {primary} 30%, white);
  --accent:        {accent};
  --accent-light:  color-mix(in srgb, {accent} 10%, white);
  --warning:       {warning};
  --warning-light: color-mix(in srgb, {warning} 12%, white);
  --danger:        {danger};
  --danger-light:  color-mix(in srgb, {danger} 10%, white);
  --surface:       #FFFFFF;
  --bg:            #F0F4F8;
  --bg2:           #E6EDF5;
  --text:          #0D1B2A;
  --text-2:        #4A5568;
  --muted:         #718096;
  --border:        #CBD5E0;
  --border-light:  #E2E8F0;
  --radius-sm:     6px;
  --radius:        10px;
  --radius-lg:     16px;
  --shadow-sm:     0 1px 3px rgba(15,76,129,.08);
  --shadow:        0 4px 16px rgba(15,76,129,.12);
  --font-body:     'IBM Plex Sans', system-ui, sans-serif;
  --font-mono:     'IBM Plex Mono', monospace;
  --transition:    0.18s ease;
  /* Safe area insets for notched phones */
  --safe-top:    env(safe-area-inset-top,    0px);
  --safe-bottom: env(safe-area-inset-bottom, 0px);
  --safe-left:   env(safe-area-inset-left,   0px);
  --safe-right:  env(safe-area-inset-right,  0px);
  /* Header height — used in multiple layout calculations */
  --header-h: 56px;
  --banner-h: 36px;
}}

*, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
html {{ scroll-behavior: smooth; height: 100%; }}

body {{
  font-family: var(--font-body);
  background: var(--bg);
  height: 100%;
  /* Use dvh so the viewport shrinks correctly when the mobile keyboard appears */
  min-height: 100dvh;
  display: flex;
  flex-direction: column;
  color: var(--text);
  font-size: 15px;
  line-height: 1.6;
  -webkit-font-smoothing: antialiased;
  /* Prevent horizontal scroll on mobile */
  overflow-x: hidden;
}}

/* ── CONSENT OVERLAY ───────────────────────── */
#consent-overlay {{
  position: fixed; inset: 0;
  background: rgba(15,76,129,.85);
  z-index: 500;
  display: flex; align-items: center; justify-content: center;
  padding: 1.5rem;
  backdrop-filter: blur(4px);
}}
#consent-overlay.hidden {{ display: none; }}
.consent-card {{
  background: var(--surface); border-radius: var(--radius-lg);
  max-width: 520px; width: 100%; padding: 2rem;
  box-shadow: 0 20px 60px rgba(0,0,0,.35);
}}
.consent-icon   {{ font-size: 2.5rem; margin-bottom: 1rem; }}
.consent-title  {{ font-size: 18px; font-weight: 600; color: var(--text); margin-bottom: .75rem; }}
.consent-body   {{ font-size: 13.5px; color: var(--text-2); line-height: 1.7; margin-bottom: 1.5rem; border-left: 3px solid var(--primary-mid); padding-left: 12px; }}
.consent-actions {{ display: flex; flex-direction: column; gap: 8px; }}
.consent-btn-primary {{
  width: 100%; padding: 12px;
  background: var(--primary); color: white;
  border: none; border-radius: var(--radius);
  font-size: 14px; font-weight: 600; font-family: var(--font-body);
  cursor: pointer; transition: background var(--transition);
}}
.consent-btn-primary:hover {{ background: color-mix(in srgb, var(--primary) 85%, black); }}
.consent-btn-secondary {{
  width: 100%; padding: 10px;
  background: transparent; color: var(--muted);
  border: 1px solid var(--border); border-radius: var(--radius);
  font-size: 13px; font-family: var(--font-body);
  cursor: pointer; transition: all var(--transition);
}}
.consent-btn-secondary:hover {{ border-color: var(--primary); color: var(--primary); }}

/* ── DOSING CALCULATOR PANEL ───────────────── */
#dose-panel {{
  position: fixed; right: 0; top: calc(var(--header-h) + var(--banner-h)); bottom: 0;
  width: min(320px, 100vw);
  background: var(--surface); border-left: 1px solid var(--border-light);
  z-index: 250; display: none; flex-direction: column;
  box-shadow: -4px 0 20px rgba(15,76,129,.10);
  transform: translateX(100%); transition: transform .25s ease;
  padding-bottom: var(--safe-bottom);
}}
#dose-panel.open {{ display: flex; transform: translateX(0); animation: slide-in-right .25s ease; }}
@keyframes slide-in-right {{ from {{ transform: translateX(100%); }} to {{ transform: translateX(0); }} }}
.dose-header {{
  padding: 14px 16px; border-bottom: 1px solid var(--border-light);
  font-size: 13px; font-weight: 600;
  display: flex; align-items: center; justify-content: space-between;
  background: var(--primary); color: white;
  flex-shrink: 0;
}}
.dose-close-btn {{
  background: none; border: none; color: rgba(255,255,255,.8);
  cursor: pointer; font-size: 18px; line-height: 1;
  padding: 2px 4px; border-radius: 4px;
  transition: color var(--transition);
}}
.dose-close-btn:hover {{ color: white; }}
.dose-body   {{ flex: 1; overflow-y: auto; padding: 16px; -webkit-overflow-scrolling: touch; }}
.dose-field  {{ margin-bottom: 14px; }}
.dose-label  {{ font-size: 11px; font-weight: 600; color: var(--muted); letter-spacing: .06em; text-transform: uppercase; margin-bottom: 5px; display: block; }}
.dose-input  {{ width: 100%; border: 1.5px solid var(--border); border-radius: var(--radius-sm); padding: 10px 12px; font-size: 16px; /* 16px prevents iOS zoom */ font-family: var(--font-body); outline: none; background: var(--bg); transition: border-color var(--transition); }}
.dose-input:focus {{ border-color: var(--primary); background: var(--surface); }}
.dose-select {{ width: 100%; border: 1.5px solid var(--border); border-radius: var(--radius-sm); padding: 10px 12px; font-size: 16px; font-family: var(--font-body); background: var(--bg); outline: none; cursor: pointer; }}
.dose-result {{ background: var(--primary-light); border: 1px solid var(--primary-mid); border-radius: var(--radius); padding: 12px 14px; margin-top: 12px; font-size: 13.5px; line-height: 1.6; }}
.dose-result .dose-qty {{ font-size: 20px; font-weight: 600; color: var(--primary); font-family: var(--font-mono); display: block; margin-bottom: 4px; }}
.dose-warning {{ background: var(--warning-light); border: 1px solid color-mix(in srgb, var(--warning) 30%, white); border-radius: var(--radius-sm); padding: 8px 10px; font-size: 12px; color: color-mix(in srgb, var(--warning) 80%, black); margin-top: 8px; }}

/* ── HEADER ────────────────────────────────── */
header {{
  background: var(--primary); color: white;
  padding: 0 1rem;
  padding-left: max(1rem, var(--safe-left));
  padding-right: max(1rem, var(--safe-right));
  height: var(--header-h);
  display: flex; align-items: center; justify-content: space-between;
  position: sticky; top: 0; z-index: 200;
  box-shadow: 0 2px 12px rgba(0,0,0,.20);
  flex-shrink: 0;
}}
.header-brand   {{ display: flex; align-items: center; gap: 10px; min-width: 0; flex: 1; }}
.header-logo    {{ width: 34px; height: 34px; background: rgba(255,255,255,.15); border: 1.5px solid rgba(255,255,255,.30); border-radius: var(--radius); display: flex; align-items: center; justify-content: center; font-size: 16px; flex-shrink: 0; }}
.header-text    {{ min-width: 0; }}
.header-name    {{ font-size: 14px; font-weight: 600; letter-spacing: -.01em; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
.header-tagline {{ font-size: 10px; color: rgba(255,255,255,.55); display: none; }}
.header-controls {{ display: flex; align-items: center; gap: 6px; flex-shrink: 0; }}
.status-pill {{ display: flex; align-items: center; gap: 5px; background: rgba(255,255,255,.10); border: 1px solid rgba(255,255,255,.18); padding: 4px 8px; border-radius: 20px; font-size: 11px; color: rgba(255,255,255,.85); white-space: nowrap; }}
.status-label {{ display: none; }}
.status-dot  {{ width: 6px; height: 6px; background: #4ADE80; border-radius: 50%; animation: pulse-dot 2.5s ease-in-out infinite; flex-shrink: 0; }}
.status-dot.offline {{ background: #FCA5A5; animation: none; }}
@keyframes pulse-dot {{ 0%, 100% {{ opacity: 1; transform: scale(1); }} 50% {{ opacity: .5; transform: scale(.8); }} }}
.icon-btn   {{
  background: rgba(255,255,255,.08); border: 1px solid rgba(255,255,255,.15);
  color: rgba(255,255,255,.80);
  width: 34px; height: 34px;
  border-radius: var(--radius-sm); cursor: pointer;
  display: flex; align-items: center; justify-content: center;
  transition: background var(--transition);
  /* Minimum tap target 44×44 via padding trick */
  position: relative;
}}
.icon-btn::after {{
  content: ''; position: absolute;
  inset: -5px;
}}
.icon-btn:hover {{ background: rgba(255,255,255,.18); }}
.icon-btn:active {{ background: rgba(255,255,255,.25); }}

/* Sidebar close button styled like icon-btn but with primary bg context */
.sidebar-close-btn {{
  background: rgba(255,255,255,.08); border: 1px solid rgba(255,255,255,.15);
  color: rgba(255,255,255,.80);
  width: 28px; height: 28px;
  border-radius: var(--radius-sm); cursor: pointer;
  display: flex; align-items: center; justify-content: center;
}}

/* ── SAFETY BANNER ─────────────────────────── */
#safety-banner {{
  padding: 6px 1rem;
  padding-left: max(1rem, var(--safe-left));
  padding-right: max(1rem, var(--safe-right));
  font-size: 11.5px; display: flex; align-items: center; gap: 8px;
  border-bottom: 1px solid; font-weight: 500;
  height: var(--banner-h);
  flex-shrink: 0;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}}
#safety-banner.status-live      {{ background: var(--accent-light);   border-color: color-mix(in srgb, var(--accent) 30%, white);  color: color-mix(in srgb, var(--accent) 80%, black); }}
#safety-banner.status-demo      {{ background: var(--warning-light);  border-color: color-mix(in srgb, var(--warning) 30%, white); color: color-mix(in srgb, var(--warning) 80%, black); }}
#safety-banner.status-emergency {{ background: var(--danger-light);   border-color: color-mix(in srgb, var(--danger) 40%, white);  color: var(--danger); animation: blink-border 1s ease-in-out infinite; white-space: normal; }}
@keyframes blink-border {{ 0%, 100% {{ background: var(--danger-light); }} 50% {{ background: color-mix(in srgb, var(--danger) 18%, white); }} }}

/* ── LAYOUT ────────────────────────────────── */
.app-body {{
  display: flex;
  flex: 1;
  overflow: hidden;
  /* Subtract header + banner; use dvh so keyboard resize is handled */
  height: calc(100dvh - var(--header-h) - var(--banner-h));
  position: relative;
}}

/* ── SIDEBAR BACKDROP (mobile) ─────────────── */
#sidebar-backdrop {{
  display: none;
  position: fixed; inset: 0; z-index: 149;
  background: rgba(0,0,0,.4);
  backdrop-filter: blur(2px);
}}
#sidebar-backdrop.visible {{ display: block; animation: fade-in .2s ease; }}
@keyframes fade-in {{ from {{ opacity: 0; }} to {{ opacity: 1; }} }}

/* ── SIDEBAR ───────────────────────────────── */
#sidebar {{
  width: 260px;
  background: var(--primary); /* header-coloured sidebar on mobile */
  display: flex; flex-direction: column;
  overflow: hidden;
  flex-shrink: 0;
  /* Mobile: slide-over panel above the chat */
  position: fixed;
  top: 0; left: 0; bottom: 0;
  z-index: 150;
  transform: translateX(-100%);
  transition: transform .25s ease;
  padding-top: calc(var(--safe-top) + var(--header-h) + var(--banner-h));
  padding-bottom: var(--safe-bottom);
  box-shadow: 4px 0 20px rgba(0,0,0,.20);
  background: var(--surface);
}}
#sidebar.open {{
  transform: translateX(0);
}}
.sidebar-header {{
  padding: 14px 16px; border-bottom: 1px solid var(--border-light);
  font-size: 11px; font-weight: 600; color: var(--muted);
  letter-spacing: .08em; text-transform: uppercase;
  display: flex; align-items: center; justify-content: space-between;
  flex-shrink: 0;
}}
.protocol-list   {{ overflow-y: auto; flex: 1; padding: 8px; -webkit-overflow-scrolling: touch; }}
.protocol-item   {{ padding: 12px 12px; border-radius: var(--radius-sm); cursor: pointer; margin-bottom: 2px; transition: background var(--transition); border: 1px solid transparent; }}
.protocol-item:hover  {{ background: var(--primary-light); border-color: var(--primary-mid); }}
.protocol-item:active {{ background: var(--primary-light); }}
.protocol-title  {{ font-size: 13px; font-weight: 500; color: var(--text); display: flex; align-items: center; gap: 7px; flex-wrap: wrap; }}
.protocol-badge  {{ font-size: 10px; background: var(--danger); color: white; padding: 1px 6px; border-radius: 10px; font-weight: 600; }}
.protocol-badge.green  {{ background: var(--accent); }}
.protocol-badge.orange {{ background: var(--warning); }}
.protocol-sub    {{ font-size: 11.5px; color: var(--muted); margin-top: 2px; }}

/* ── CHAT COLUMN ───────────────────────────── */
#chat-col        {{ flex: 1; display: flex; flex-direction: column; overflow: hidden; min-width: 0; }}
#chat-container  {{
  flex: 1; overflow-y: auto; padding: 1rem;
  display: flex; flex-direction: column; gap: .875rem;
  scroll-behavior: smooth;
  -webkit-overflow-scrolling: touch;
  /* Prevent content hiding behind notch on landscape */
  padding-left: max(1rem, var(--safe-left));
  padding-right: max(1rem, var(--safe-right));
}}

/* ── MESSAGES ──────────────────────────────── */
.message {{ display: flex; gap: 8px; max-width: 92%; animation: msg-in .2s ease; }}
@keyframes msg-in {{ from {{ opacity: 0; transform: translateY(6px); }} to {{ opacity: 1; transform: translateY(0); }} }}
.message.user   {{ align-self: flex-end;   flex-direction: row-reverse; }}
.message.bot    {{ align-self: flex-start; }}
.message.system {{ align-self: center;     max-width: 100%; }}
.msg-avatar {{ width: 30px; height: 30px; border-radius: 8px; flex-shrink: 0; display: flex; align-items: center; justify-content: center; font-size: 13px; font-weight: 600; margin-top: 2px; }}
.message.bot  .msg-avatar {{ background: var(--primary); color: white; }}
.message.user .msg-avatar {{ background: var(--accent);  color: white; font-size: 10px; }}
.msg-body   {{ display: flex; flex-direction: column; min-width: 0; flex: 1; }}
.msg-bubble {{ padding: 10px 13px; border-radius: var(--radius); font-size: 14px; line-height: 1.65; word-break: break-word; }}
.message.bot    .msg-bubble {{ background: var(--surface); color: var(--text); border: 1px solid var(--border-light); border-bottom-left-radius: 3px; box-shadow: var(--shadow-sm); }}
.message.user   .msg-bubble {{ background: var(--primary); color: white; border-bottom-right-radius: 3px; }}
.message.system .msg-bubble {{ background: transparent; border: 1px dashed var(--border); color: var(--muted); font-size: 12px; text-align: center; border-radius: var(--radius); padding: 6px 12px; box-shadow: none; }}
.message.emergency .msg-bubble {{ background: var(--danger-light); border: 1.5px solid var(--danger); color: var(--text); }}
.message.emergency .msg-avatar {{ background: var(--danger); }}

/* ── CLINICAL CARD ─────────────────────────── */
.clinical-card {{ background: var(--surface); border: 1px solid var(--border-light); border-radius: var(--radius); overflow: hidden; box-shadow: var(--shadow-sm); }}
.clinical-section {{ padding: 10px 12px; border-bottom: 1px solid var(--border-light); }}
.clinical-section:last-child {{ border-bottom: none; }}
.clinical-section-label {{ font-size: 10px; font-weight: 600; letter-spacing: .07em; text-transform: uppercase; color: var(--muted); margin-bottom: 5px; display: flex; align-items: center; gap: 5px; }}
.clinical-section-label.danger  {{ color: var(--danger); }}
.clinical-section-label.warning {{ color: var(--warning); }}
.clinical-section-label.success {{ color: var(--accent); }}
.clinical-content {{ font-size: 13px; line-height: 1.6; }}
.tag-list {{ display: flex; flex-wrap: wrap; gap: 5px; margin-top: 5px; }}
.tag {{ font-size: 11.5px; padding: 3px 8px; border-radius: 20px; font-weight: 500; }}
.tag.red    {{ background: var(--danger-light);  color: var(--danger);  border: 1px solid color-mix(in srgb, var(--danger) 25%, white); }}
.tag.green  {{ background: var(--accent-light);  color: color-mix(in srgb, var(--accent) 80%, black); border: 1px solid color-mix(in srgb, var(--accent) 25%, white); }}
.tag.blue   {{ background: var(--primary-light); color: var(--primary); border: 1px solid var(--primary-mid); }}
.tag.orange {{ background: var(--warning-light); color: var(--warning); border: 1px solid color-mix(in srgb, var(--warning) 25%, white); }}
.referral-badge {{ display: inline-flex; align-items: center; gap: 6px; padding: 6px 10px; border-radius: var(--radius-sm); font-size: 12.5px; font-weight: 600; margin-top: 6px; }}
.referral-badge.immediate {{ background: var(--danger);  color: white; }}
.referral-badge.urgent    {{ background: var(--warning); color: white; }}
.referral-badge.routine   {{ background: var(--accent);  color: white; }}
.referral-badge.monitor   {{ background: var(--primary-light); color: var(--primary); }}

/* ── FOLLOW-UP ─────────────────────────────── */
.followup-form  {{ background: var(--bg); border: 1px solid var(--border-light); border-radius: var(--radius-sm); padding: 10px 12px; margin-top: 8px; font-size: 12.5px; }}
.followup-row   {{ display: flex; gap: 6px; align-items: center; flex-wrap: wrap; }}
.followup-input {{ border: 1px solid var(--border); border-radius: 4px; padding: 7px 8px; font-size: 14px; font-family: var(--font-body); background: var(--surface); outline: none; flex: 1; min-width: 90px; }}
.followup-btn   {{ background: var(--primary); color: white; border: none; border-radius: 4px; padding: 7px 10px; font-size: 13px; font-family: var(--font-body); cursor: pointer; white-space: nowrap; }}

/* ── FEEDBACK ──────────────────────────────── */
.msg-feedback    {{ display: flex; align-items: center; gap: 5px; margin-top: 6px; font-size: 11.5px; color: var(--muted); flex-wrap: wrap; }}
.feedback-btn    {{ background: none; border: 1px solid var(--border); border-radius: 4px; padding: 4px 8px; cursor: pointer; font-size: 12px; color: var(--muted); transition: all var(--transition); font-family: var(--font-body); white-space: nowrap; }}
.feedback-btn:active {{ border-color: var(--primary); color: var(--primary); }}
.feedback-btn.active {{ background: var(--primary-light); border-color: var(--primary); color: var(--primary); }}
.confidence-chip {{ font-family: var(--font-mono); font-size: 10.5px; padding: 2px 6px; border-radius: 3px; border: 1px solid var(--border); color: var(--muted); }}
.confidence-chip.HIGH   {{ border-color: var(--accent);   color: var(--accent); }}
.confidence-chip.MEDIUM {{ border-color: var(--warning);  color: var(--warning); }}
.confidence-chip.LOW    {{ border-color: var(--danger);   color: var(--danger); }}

/* ── TYPING INDICATOR ──────────────────────── */
.typing-indicator {{ display: flex; align-items: center; gap: 4px; padding: 12px 13px; background: var(--surface); border: 1px solid var(--border-light); border-radius: var(--radius); border-bottom-left-radius: 3px; width: fit-content; }}
.typing-dot {{ width: 6px; height: 6px; background: var(--muted); border-radius: 50%; animation: typing-bounce 1.2s ease-in-out infinite; }}
.typing-dot:nth-child(2) {{ animation-delay: .2s; }}
.typing-dot:nth-child(3) {{ animation-delay: .4s; }}
@keyframes typing-bounce {{ 0%, 80%, 100% {{ transform: translateY(0); opacity: .5; }} 40% {{ transform: translateY(-5px); opacity: 1; }} }}

/* ── QUICK REPLIES ─────────────────────────── */
.quick-replies {{ display: flex; flex-wrap: wrap; gap: 7px; padding: 2px 0 8px 38px; animation: msg-in .25s ease; }}
.quick-btn {{ background: var(--surface); border: 1.5px solid var(--border); color: var(--primary); padding: 7px 12px; border-radius: 20px; font-size: 12.5px; font-family: var(--font-body); font-weight: 500; cursor: pointer; transition: all var(--transition); white-space: nowrap; }}
.quick-btn:active {{ background: var(--primary-light); border-color: var(--primary); }}

/* ── META / BADGES ─────────────────────────── */
.msg-meta {{ font-size: 10px; color: var(--muted); margin-top: 4px; display: flex; align-items: center; gap: 6px; }}
.message.user .msg-meta {{ justify-content: flex-end; }}
.offline-badge {{ display: inline-flex; align-items: center; gap: 5px; font-size: 11px; background: var(--warning-light); color: color-mix(in srgb, var(--warning) 80%, black); border: 1px solid color-mix(in srgb, var(--warning) 30%, white); padding: 3px 8px; border-radius: 20px; }}

/* ── INPUT BAR ─────────────────────────────── */
#input-bar {{
  background: var(--surface); border-top: 1px solid var(--border-light);
  padding: .625rem 1rem;
  padding-left: max(1rem, var(--safe-left));
  padding-right: max(1rem, var(--safe-right));
  padding-bottom: max(.625rem, var(--safe-bottom));
  box-shadow: 0 -2px 12px rgba(15,76,129,.06);
  flex-shrink: 0;
}}
.input-inner {{ display: flex; gap: 8px; align-items: flex-end; max-width: 900px; margin: 0 auto; }}
#user-input {{
  flex: 1; border: 1.5px solid var(--border); border-radius: var(--radius);
  padding: 10px 13px; font-size: 16px; /* 16px stops iOS auto-zoom */
  font-family: var(--font-body); outline: none; background: var(--bg);
  color: var(--text); resize: none; max-height: 120px; line-height: 1.5;
  transition: border-color var(--transition), box-shadow var(--transition);
}}
#user-input:focus {{ border-color: var(--primary); box-shadow: 0 0 0 3px var(--primary-light); background: var(--surface); }}
#user-input::placeholder {{ color: var(--muted); }}
.input-actions {{ display: flex; gap: 6px; }}
#send-btn {{
  width: 44px; height: 44px;
  border-radius: var(--radius-sm); background: var(--primary); border: none;
  color: white; cursor: pointer; display: flex; align-items: center; justify-content: center;
  transition: background var(--transition), transform var(--transition);
  flex-shrink: 0; box-shadow: 0 2px 6px rgba(15,76,129,.30);
  /* Accessible tap target */
  -webkit-tap-highlight-color: transparent;
}}
#send-btn:active   {{ background: color-mix(in srgb, var(--primary) 80%, black); transform: scale(.94); }}
#send-btn:disabled {{ background: var(--border); cursor: not-allowed; box-shadow: none; }}
/* Emergency button hidden by design — auto-triggers on keyword detection */
#emergency-btn {{ display: none !important; }}

/* ── MODAL ─────────────────────────────────── */
#modal-overlay {{ display: none; position: fixed; inset: 0; background: rgba(0,0,0,.40); z-index: 300; align-items: flex-end; justify-content: center; padding: 0; backdrop-filter: blur(3px); }}
#modal-overlay.open {{ display: flex; }}
.modal {{
  background: var(--surface); border-radius: var(--radius-lg) var(--radius-lg) 0 0;
  box-shadow: var(--shadow); width: 100%; max-height: 85dvh; overflow-y: auto;
  animation: sheet-up .25s ease;
  padding-bottom: var(--safe-bottom);
}}
@keyframes sheet-up {{ from {{ transform: translateY(60px); opacity: 0; }} to {{ transform: translateY(0); opacity: 1; }} }}
.modal-header {{ padding: 16px 20px 12px; border-bottom: 1px solid var(--border-light); display: flex; align-items: center; justify-content: space-between; position: sticky; top: 0; background: var(--surface); z-index: 1; }}
.modal-title  {{ font-size: 15px; font-weight: 600; }}
.modal-close  {{ background: none; border: none; color: var(--muted); cursor: pointer; font-size: 20px; padding: 4px 8px; border-radius: 4px; }}
.modal-close:active {{ color: var(--text); }}
.modal-body   {{ padding: 14px 20px 20px; }}
.protocol-section       {{ margin-bottom: 16px; }}
.protocol-section-title {{ font-size: 11.5px; font-weight: 600; color: var(--muted); letter-spacing: .06em; text-transform: uppercase; margin-bottom: 8px; }}
.protocol-list-item {{ display: flex; align-items: flex-start; gap: 8px; padding: 6px 0; border-bottom: 1px solid var(--border-light); font-size: 13px; }}
.protocol-list-item:last-child {{ border-bottom: none; }}
.protocol-bullet        {{ width: 7px; height: 7px; border-radius: 50%; background: var(--danger); flex-shrink: 0; margin-top: 5px; }}
.protocol-bullet.green  {{ background: var(--accent); }}
.protocol-bullet.orange {{ background: var(--warning); }}

/* ── EVALUATION PANEL ──────────────────────── */
#eval-panel {{
  /* Mobile: slide up from bottom */
  position: fixed; bottom: 0; left: 0; right: 0;
  z-index: 250;
  background: var(--surface); border-top: 1px solid var(--border-light);
  overflow-y: auto; -webkit-overflow-scrolling: touch;
  padding: 14px;
  padding-bottom: max(14px, var(--safe-bottom));
  display: none; flex-direction: column; gap: 14px;
  max-height: 85dvh;
  border-radius: var(--radius-lg) var(--radius-lg) 0 0;
  box-shadow: 0 -4px 20px rgba(0,0,0,.12);
  transform: translateY(100%);
  transition: transform .25s ease;
}}
#eval-panel.open {{
  display: flex;
  transform: translateY(0);
  animation: sheet-up .25s ease;
}}
.eval-header {{ display: flex; align-items: center; justify-content: space-between; padding-bottom: 10px; border-bottom: 1px solid var(--border-light); }}
.eval-title    {{ font-size: 11px; font-weight: 600; color: var(--muted); letter-spacing: .08em; text-transform: uppercase; }}
.eval-close-btn {{ background: none; border: 1px solid var(--border); color: var(--muted); width: 28px; height: 28px; border-radius: var(--radius-sm); cursor: pointer; display: flex; align-items: center; justify-content: center; }}
.eval-stat     {{ display: flex; justify-content: space-between; align-items: center; padding: 7px 0; font-size: 13px; border-bottom: 1px solid var(--border-light); }}
.eval-stat-val {{ font-family: var(--font-mono); font-size: 13px; font-weight: 600; color: var(--primary); }}
.eval-tag      {{ display: inline-flex; align-items: center; gap: 4px; background: var(--primary-light); border: 1px solid var(--primary-mid); color: var(--primary); padding: 4px 9px; border-radius: 4px; font-size: 11.5px; font-weight: 500; margin-bottom: 4px; margin-right: 4px; }}
.eval-export-btn {{
  width: 100%; padding: 11px; background: var(--primary); color: white;
  border: none; border-radius: var(--radius-sm); cursor: pointer;
  font-size: 13px; font-family: var(--font-body); font-weight: 500; margin-bottom: 6px;
  -webkit-tap-highlight-color: transparent;
}}
.eval-export-btn:active {{ background: color-mix(in srgb, var(--primary) 85%, black); }}
.eval-clear-btn {{
  width: 100%; padding: 10px; background: var(--surface); color: var(--danger);
  border: 1.5px solid var(--danger); border-radius: var(--radius-sm); cursor: pointer;
  font-size: 13px; font-family: var(--font-body); font-weight: 500;
}}

/* ── EMERGENCY OVERLAY ─────────────────────── */
#emergency-overlay {{ display: none; position: fixed; inset: 0; background: rgba(214,40,40,.08); z-index: 100; pointer-events: none; border: 4px solid var(--danger); animation: emergency-pulse 1s ease-in-out infinite; }}
#emergency-overlay.active {{ display: block; }}
@keyframes emergency-pulse {{ 0%, 100% {{ opacity: 1; }} 50% {{ opacity: .4; }} }}

/* ── SCROLLBAR ─────────────────────────────── */
::-webkit-scrollbar       {{ width: 4px; }}
::-webkit-scrollbar-track {{ background: transparent; }}
::-webkit-scrollbar-thumb {{ background: var(--border); border-radius: 10px; }}

/* ── UTILITY ───────────────────────────────── */
.sr-only {{ position: absolute; width: 1px; height: 1px; padding: 0; margin: -1px; overflow: hidden; clip: rect(0,0,0,0); white-space: nowrap; border: 0; }}
strong {{ font-weight: 600; }}
-webkit-tap-highlight-color: transparent;

/* ══════════════════════════════════════════════
   TABLET  ≥ 640px
   ══════════════════════════════════════════════ */
@media (min-width: 640px) {{
  :root {{ --header-h: 60px; --banner-h: 37px; }}

  .header-tagline  {{ display: block; }}
  .status-label    {{ display: inline; }}
  .message         {{ max-width: 86%; }}
  .quick-replies   {{ padding-left: 42px; }}

  /* Sidebar: still overlay but wider */
  #sidebar {{ width: 280px; padding-top: calc(var(--header-h) + var(--banner-h)); }}

  /* Modal: centred dialog instead of bottom sheet */
  #modal-overlay {{ align-items: center; padding: 1rem; }}
  .modal {{
    border-radius: var(--radius-lg);
    max-width: 540px; max-height: 80dvh;
    animation: modal-in .2s ease;
  }}
  @keyframes modal-in {{ from {{ opacity: 0; transform: scale(.96) translateY(10px); }} to {{ opacity: 1; transform: scale(1) translateY(0); }} }}

  /* Eval panel: right-side drawer */
  #eval-panel {{
    position: fixed; top: calc(var(--header-h) + var(--banner-h)); right: 0; bottom: 0; left: auto;
    width: 300px; max-height: none; border-radius: 0; border-top: none;
    border-left: 1px solid var(--border-light);
    box-shadow: -4px 0 20px rgba(15,76,129,.08);
    transform: translateX(100%);
    animation: none;
  }}
  #eval-panel.open {{
    transform: translateX(0);
    animation: slide-in-right .25s ease;
  }}
  .eval-header {{ padding-bottom: 10px; }}

  /* Dose panel full-height on tablet+ */
  #dose-panel {{ top: calc(var(--header-h) + var(--banner-h)); }}
}}

/* ══════════════════════════════════════════════
   DESKTOP  ≥ 1024px
   ══════════════════════════════════════════════ */
@media (min-width: 1024px) {{
  :root {{ --header-h: 64px; --banner-h: 37px; }}

  .header-logo {{ width: 38px; height: 38px; font-size: 18px; }}
  .header-name {{ font-size: 15px; }}
  .icon-btn    {{ width: 36px; height: 36px; }}

  /* Sidebar: always-visible inline panel */
  #sidebar {{
    position: relative;
    width: 260px; padding-top: 0;
    transform: translateX(0) !important;
    box-shadow: none;
    border-right: 1px solid var(--border-light);
  }}
  /* Collapsed state on desktop */
  #sidebar.collapsed {{ width: 0; overflow: hidden; }}
  #sidebar-backdrop {{ display: none !important; }}
  .sidebar-close-btn {{ display: none; }}

  /* Eval panel: inline right column */
  #eval-panel {{
    position: relative; top: auto; right: auto; bottom: auto;
    width: 280px; max-height: none; border-radius: 0;
    border-top: none; border-left: 1px solid var(--border-light);
    box-shadow: none; padding-bottom: 14px;
    transform: translateX(100%);
  }}
  #eval-panel.open {{
    transform: translateX(0);
    animation: none;
  }}

  .message {{ max-width: 82%; }}
  #user-input {{ font-size: 14px; }}
  #send-btn {{ width: 40px; height: 40px; }}

  .feedback-btn:hover {{ border-color: var(--primary); color: var(--primary); }}
  .quick-btn:hover {{ background: var(--primary-light); border-color: var(--primary); }}
  .protocol-item:hover {{ background: var(--primary-light); border-color: var(--primary-mid); }}
}}

/* ── PRINT ─────────────────────────────────── */
@media print {{
  header, #input-bar, #sidebar, #eval-panel, .quick-replies,
  .feedback-btn, #safety-banner, #consent-overlay, #dose-panel,
  #sidebar-backdrop {{ display: none !important; }}
  .msg-bubble {{ border: 1px solid #ccc !important; box-shadow: none !important; }}
  body {{ background: white; }}
}}
"""
        (self._ctx.output_dir / "static" / "css" /
         "chat.css").write_text(css, encoding="utf-8")

    # ------------------------------------------------------------------

    def write_service_worker(self) -> None:
        h = self._ctx.build_hash
        sw = f"""/* HealthAssist CDST — Service Worker v1  hash={h} */
'use strict';

const CACHE = 'cdst-v{h}';
const OFFLINE_ASSETS = [
  './', './index.html',
  './static/css/chat.css', './static/js/chat.js',
  './static/data/protocols.json', './static/data/formulary.json',
  './static/data/i18n.json', './config.json', './manifest.json',
];

self.addEventListener('install', e => {{
  e.waitUntil(
    caches.open(CACHE)
      .then(c => c.addAll(OFFLINE_ASSETS))
      .then(() => self.skipWaiting())
  );
}});

self.addEventListener('activate', e => {{
  e.waitUntil(
    caches.keys()
      .then(keys => Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k))))
      .then(() => self.clients.claim())
  );
}});

self.addEventListener('fetch', e => {{
  const url   = new URL(e.request.url);
  const isAPI = url.hostname !== self.location.hostname;

  if (isAPI) {{
    e.respondWith(
      Promise.race([
        fetch(e.request),
        new Promise((_, rej) => setTimeout(() => rej(new Error('timeout')), 10000)),
      ]).catch(() => new Response(
        JSON.stringify({{error:'offline'}}),
        {{status:503, headers:{{'Content-Type':'application/json'}}}}
      ))
    );
    return;
  }}

  e.respondWith(
    caches.match(e.request).then(cached => {{
      if (cached) return cached;
      return fetch(e.request).then(res => {{
        if (res.ok) {{
          const clone = res.clone();
          caches.open(CACHE).then(c => c.put(e.request, clone));
        }}
        return res;
      }}).catch(() => caches.match('./index.html'));
    }})
  );
}});
"""
        (self._ctx.output_dir / "sw.js").write_text(sw, encoding="utf-8")

    # ------------------------------------------------------------------

    def write_manifest(self) -> None:
        app = self._cfg["app"]
        t = self._cfg["theme"]
        i18n = self._cfg.get("i18n", AppConfig.DEFAULTS["i18n"])
        manifest = {
            "name":             app["name"],
            "short_name":       "HealthAssist",
            "description":      app["tagline"],
            "start_url":        "./",
            "display":          "standalone",
            "background_color": t["bg"],
            "theme_color":      t["primary_color"],
            "icons": [
                {"src": "static/images/icon-192.png",
                    "sizes": "192x192", "type": "image/png"},
                {"src": "static/images/icon-512.png",
                    "sizes": "512x512", "type": "image/png"},
            ],
            "categories": ["medical", "health"],
            "lang": i18n.get("default_locale", "en"),
        }
        (self._ctx.output_dir / "manifest.json").write_text(
            json.dumps(manifest, indent=2), encoding="utf-8"
        )

    # ------------------------------------------------------------------

    def write_protocols(self) -> None:
        data = ProtocolsData().build()
        (self._ctx.output_dir / "static" / "data" / "protocols.json").write_text(
            json.dumps(data, indent=2), encoding="utf-8"
        )

    # ------------------------------------------------------------------

    def write_formulary(self) -> None:
        formulary = self._cfg.get("formulary", AppConfig.DEFAULTS["formulary"])
        payload = {
            **formulary,
            "calculator_note": (
                "All doses are for guidance only. Apply clinical judgment. "
                "Refer to national formulary for definitive dosing."
            ),
            "version": PROTOCOL_VERSION,
        }
        (self._ctx.output_dir / "static" / "data" / "formulary.json").write_text(
            json.dumps(payload, indent=2), encoding="utf-8"
        )

    # ------------------------------------------------------------------

    def write_i18n(self) -> None:
        i18n = self._cfg.get("i18n", AppConfig.DEFAULTS["i18n"])
        (self._ctx.output_dir / "static" / "data" / "i18n.json").write_text(
            json.dumps(i18n, indent=2), encoding="utf-8"
        )

    # ------------------------------------------------------------------

    def write_config_json(self) -> None:
        """Write the sanitised public config (no secrets / system prompt)."""
        cfg = self._cfg
        ctx = self._ctx
        public_cfg = {
            "app":     cfg["app"],
            "bot":     {k: v for k, v in cfg["bot"].items() if k != "system_prompt"},
            "theme":   cfg["theme"],
            "evaluation": cfg.get("evaluation", {}),
            "protocols":  cfg.get("protocols", {}),
            "formulary":  cfg.get("formulary", {}),
            "i18n":       cfg.get("i18n", {}),
            "provider": {
                "name":          ctx.provider_name,
                "model":         ctx.model_id,
                "provider_type": ctx.provider.get("provider_type", "openai") if ctx.provider else "demo",
            },
            "protocol_version": PROTOCOL_VERSION,
            "build_hash":       ctx.build_hash,
            "built_at":         ctx.built_at.isoformat(),
        }
        (ctx.output_dir / "config.json").write_text(
            json.dumps(public_cfg, indent=2, ensure_ascii=False), encoding="utf-8"
        )
