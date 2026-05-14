#!/usr/bin/env python3
"""
chatbot_system.py — EVAH-Aligned Health CDST Chatbot Builder
Production-ready Clinical Decision Support Tool for community health workers
in LMICs (Sub-Saharan Africa focus). Aligned with J-PAL EVAH Pathway A/B.

Commands:
    python chatbot_system.py init     # Create config.yaml from defaults
    python chatbot_system.py build    # Build static site → _site/ or docs/
    python chatbot_system.py auto     # Full pipeline: init → build → verify
    python chatbot_system.py verify   # Check secrets and config only
"""

import os
import sys
import json
import logging
import argparse
from pathlib import Path
from datetime import datetime, timezone

import yaml

# ─────────────────────────────────────────────
#  LOGGING
# ─────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

# ─────────────────────────────────────────────
#  PATHS
# ─────────────────────────────────────────────
ROOT = Path(__file__).parent
DOCS_DIR = ROOT / os.getenv("BUILD_OUTPUT_DIR", "docs")
CONFIG_FILE = ROOT / "config.yaml"

# ─────────────────────────────────────────────
#  DEFAULT CONFIG
# ─────────────────────────────────────────────
DEFAULT_CONFIG = {
    "app": {
        "name": "HealthAssist CDST",
        "tagline": "AI-Powered Clinical Decision Support",
        "icon": "🏥",
        "locale": "en",
        "region": "Sub-Saharan Africa",
        "facility_type": "Primary Health Centre",
    },
    "bot": {
        "name": "HealthAssist",
        "role": "Community Health Worker Support",
        "greeting": (
            "Hello, I'm HealthAssist — your AI clinical decision support tool.\n\n"
            "I can help you with:\n"
            "• Symptom assessment & triage guidance\n"
            "• Treatment protocol references\n"
            "• Referral decision support\n"
            "• Medication dosage guidance\n\n"
            "⚠️ This tool supports clinical decision-making. Always apply your "
            "clinical judgment and follow your facility's protocols.\n\n"
            "How can I assist you today?"
        ),
        "system_prompt": (
            "You are HealthAssist, a clinical decision support tool for community "
            "health workers (CHWs) at primary health centres in Sub-Saharan Africa. "
            "Your role is to assist frontline workers with evidence-based guidance on "
            "triage, diagnosis, referral, and treatment within WHO and national "
            "protocol standards.\n\n"
            "CORE PRINCIPLES:\n"
            "1. SAFETY FIRST: Always flag red flag symptoms that require immediate "
            "referral or emergency action.\n"
            "2. EVIDENCE-BASED: Ground all guidance in WHO IMCI guidelines, "
            "national formularies, and established clinical protocols.\n"
            "3. APPROPRIATE SCOPE: You support CHWs — not replace physician judgment. "
            "Recommend escalation when beyond CHW scope.\n"
            "4. STRUCTURED OUTPUT: For clinical queries, always provide: "
            "(a) Assessment summary, (b) Key differentials to consider, "
            "(c) Recommended actions, (d) Red flags to watch for, "
            "(e) Referral criteria.\n"
            "5. LANGUAGE: Use clear, simple language appropriate for CHW literacy "
            "levels. Avoid excessive jargon.\n\n"
            "SAFETY RULES:\n"
            "- If you identify ANY of these: altered consciousness, severe breathing "
            "difficulty, signs of shock, severe malnutrition, convulsions, or severe "
            "dehydration — immediately flag as EMERGENCY REFERRAL REQUIRED.\n"
            "- Never recommend prescription medications beyond the CHW formulary.\n"
            "- Always include dosing weight-based guidance for paediatric cases.\n"
            "- For maternal health queries, apply SAFE MOTHERHOOD protocols.\n\n"
            "EVALUATION CONTEXT:\n"
            "This tool is part of an EVAH-aligned evaluation. Log your confidence "
            "level (HIGH/MEDIUM/LOW) and indicate if this case would benefit from "
            "specialist review for quality assurance."
        ),
        "quick_replies": [
            "Child fever & symptoms",
            "Malaria assessment",
            "Respiratory illness",
            "Maternal health",
            "Malnutrition screening",
            "Referral criteria",
            "Medication dosages",
            "View protocols",
        ],
        "safety_keywords": [
            "unconscious", "not breathing", "fitting", "convulsion", "severe",
            "emergency", "shock", "collapsed", "unresponsive", "bleeding heavily",
            "difficulty breathing", "chest pain", "cannot walk", "very pale",
            "yellow eyes", "swollen face",
        ],
    },
    "theme": {
        "primary_color": "#0F4C81",    # Deep medical blue
        "accent_color": "#00A878",     # Health green
        "warning_color": "#E85D04",    # Alert orange
        "danger_color": "#D62828",     # Emergency red
        "surface": "#FFFFFF",
        "bg": "#F0F4F8",
    },
    "evaluation": {
        "enabled": True,
        "pathway": "A",                # EVAH Pathway A (deployment evaluation)
        "log_sessions": True,
        "capture_ratings": True,
        "anonymize": True,
        "study_id": "EVAH-CDST-001",
    },
    "models": {
        "providers": [
            {
                "name": "anthropic",
                "env_key": "ANTHROPIC_API_KEY",
                "endpoint": "https://api.anthropic.com/v1/messages",
                "model": "claude-sonnet-4-20250514",
                "auth_header": "x-api-key",
                "api_version": "2023-06-01",
                "provider_type": "anthropic",
            },
            {
                "name": "openai",
                "env_key": "OPENAI_API_KEY",
                "endpoint": "https://api.openai.com/v1/chat/completions",
                "model": "gpt-4o",
                "auth_header": "Bearer",
                "provider_type": "openai",
            },
            {
                "name": "github",
                "env_key": "GIT_TOKEN",
                "endpoint": "https://models.github.ai/inference/chat/completions",
                "model": "gpt-4o",
                "auth_header": "Bearer",
                "provider_type": "openai",
            },
            {
                "name": "groq",
                "env_key": "GROQ_API_KEY",
                "endpoint": "https://api.groq.com/openai/v1/chat/completions",
                "model": "llama-3.3-70b-versatile",
                "auth_header": "Bearer",
                "provider_type": "openai",
            },
            {
                "name": "mistral",
                "env_key": "MISTRAL_API_KEY",
                "endpoint": "https://api.mistral.ai/v1/chat/completions",
                "model": "mistral-small-latest",
                "auth_header": "Bearer",
                "provider_type": "openai",
            },
        ]
    },
    "protocols": {
        "imci_enabled": True,
        "safe_motherhood": True,
        "malaria_rdt_guidance": True,
        "muac_screening": True,
    },
    "deploy": {"output_dir": "docs"},
}

# ─────────────────────────────────────────────
#  COMMANDS
# ─────────────────────────────────────────────


def cmd_init():
    if CONFIG_FILE.exists():
        log.info("config.yaml already exists — skipping init")
        return
    with open(CONFIG_FILE, "w") as f:
        yaml.dump(DEFAULT_CONFIG, f, default_flow_style=False,
                  allow_unicode=True, sort_keys=False)
    log.info("✅ config.yaml created")
    log.info("   Priority: ANTHROPIC_API_KEY → OPENAI_API_KEY → GIT_TOKEN → GROQ_API_KEY → MISTRAL_API_KEY")


def cmd_verify():
    cfg = load_config()
    providers = cfg["models"]["providers"]
    found, missing = [], []

    for p in providers:
        if os.getenv(p["env_key"], ""):
            found.append(p)
            log.info("OK      %-28s (%s / %s)",
                     p["env_key"], p["name"], p["model"])
        else:
            missing.append(p)
            log.warning("MISSING %-28s (%s)", p["env_key"], p["name"])

    if not found:
        log.warning("No API keys found — CDST will run in demo/offline mode")
        log.warning(
            "  ANTHROPIC_API_KEY  → Claude claude-sonnet-4-20250514 (recommended for clinical)")
        log.warning("  OPENAI_API_KEY     → GPT-4o (alternative)")
        log.warning("  GIT_TOKEN          → GitHub Models / gpt-4o (free tier)")
        log.warning("  GROQ_API_KEY       → Llama 3.3 70B (fast/free)")
        log.warning("  MISTRAL_API_KEY    → Mistral Small (fallback)")
        return None

    winner = found[0]
    log.info("✅ Active provider → %s  model=%s  type=%s",
             winner["name"], winner["model"], winner.get("provider_type", "openai"))
    return winner


def cmd_build():
    cfg = load_config()
    provider = cmd_verify()

    for sub in ["", "static/js", "static/css", "static/data"]:
        (DOCS_DIR / sub).mkdir(parents=True, exist_ok=True)

    # Public config (no secrets)
    public_cfg = {
        "app": cfg["app"],
        "bot": {k: v for k, v in cfg["bot"].items() if k != "system_prompt"},
        "theme": cfg["theme"],
        "evaluation": cfg.get("evaluation", {}),
        "protocols": cfg.get("protocols", {}),
        "provider": {
            "name": provider["name"] if provider else "demo",
            "model": provider["model"] if provider else "none",
            "provider_type": provider.get("provider_type", "openai") if provider else "demo",
        },
        "built_at": datetime.now(timezone.utc).isoformat(),
    }
    (DOCS_DIR / "config.json").write_text(
        json.dumps(public_cfg, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    # Write protocol reference data
    write_protocols_data()

    token = os.getenv(provider["env_key"], "") if provider else ""

    write_css(cfg)
    write_js(cfg, provider, token)
    write_html(cfg, provider)

    log.info("✅ Build complete → %s/", DOCS_DIR)
    for f in ["index.html", "static/js/chat.js", "static/css/chat.css",
              "config.json", "static/data/protocols.json"]:
        path = DOCS_DIR / f
        if path.exists():
            log.info("   %s  ✓  (%d bytes)", f, path.stat().st_size)


def cmd_auto():
    cmd_init()
    cmd_build()
    verify_output()


def verify_output():
    ok = True
    required = ["index.html", "static/js/chat.js",
                "static/css/chat.css", "config.json"]
    for rel in required:
        f = DOCS_DIR / rel
        if f.exists():
            log.info("OK    %s (%d bytes)", rel, f.stat().st_size)
        else:
            log.error("MISSING  %s", rel)
            ok = False
    if not ok:
        sys.exit(1)


def load_config() -> dict:
    if not CONFIG_FILE.exists():
        log.warning("config.yaml not found — using defaults")
        return DEFAULT_CONFIG
    with open(CONFIG_FILE) as f:
        return yaml.safe_load(f)


def write_protocols_data():
    """Write offline protocol reference data (IMCI, malaria, malnutrition)."""
    protocols = {
        "imci": {
            "title": "IMCI Danger Signs (Children <5)",
            "emergency_signs": [
                "Cannot drink or breastfeed",
                "Vomits everything",
                "Had convulsions",
                "Lethargic or unconscious",
                "Stiff neck",
                "Grunting",
                "Severe respiratory distress",
            ],
            "classify_fever": {
                "high_risk": "Temp ≥38.5°C + any danger sign → REFER URGENTLY",
                "malaria_risk": "Temp ≥37.5°C in malaria-endemic area → RDT if available",
                "low_risk": "Temp 37.5–38.4°C, no danger signs → Treat & monitor",
            },
        },
        "muac": {
            "title": "MUAC Screening (6–59 months)",
            "thresholds": {
                "green": "≥125mm — Well nourished",
                "yellow": "115–124mm — Moderate acute malnutrition (MAM)",
                "red": "<115mm — Severe acute malnutrition (SAM) → REFER",
            },
            "bilateral_oedema": "Any pitting oedema → SAM regardless of MUAC → REFER",
        },
        "malaria_rdt": {
            "title": "Malaria RDT Protocol",
            "positive": "RDT+ → Confirm species, treat with ACT per national protocol",
            "negative_clinical": "RDT- but strong clinical suspicion → Repeat in 24h or refer",
            "severe_signs": [
                "Impaired consciousness",
                "Repeated vomiting (cannot take oral meds)",
                "Convulsions",
                "Severe anaemia (Hb <7)",
                "Jaundice + fever",
            ],
            "severe_action": "Any severe sign → EMERGENCY REFERRAL, pre-referral artesunate if available",
        },
        "maternal": {
            "title": "Safe Motherhood Red Flags",
            "refer_immediately": [
                "Severe headache + visual disturbance (pre-eclampsia)",
                "Heavy vaginal bleeding",
                "Fever >38°C in pregnancy",
                "Convulsions",
                "Labour <37 weeks",
                "No fetal movement >12h (after quickening)",
                "BP ≥140/90",
            ],
        },
        "referral_levels": {
            "immediate": "Life-threatening — call ambulance / refer NOW",
            "urgent": "Refer within 2–4 hours",
            "routine": "Refer at next available transport",
            "monitor": "Manage at facility, review in 24–48h",
        },
    }
    (DOCS_DIR / "static" / "data" / "protocols.json").write_text(
        json.dumps(protocols, indent=2), encoding="utf-8"
    )


# ─────────────────────────────────────────────
#  CSS — Clinical, Trusted, Accessible
# ─────────────────────────────────────────────
def write_css(cfg: dict):
    t = cfg["theme"]
    primary = t["primary_color"]
    accent = t["accent_color"]
    warning = t.get("warning_color", "#E85D04")
    danger = t.get("danger_color", "#D62828")

    css = f"""/* HealthAssist CDST — Auto-generated by chatbot_system.py */
/* EVAH-aligned Clinical Decision Support Tool */
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@300;400;500;600&family=IBM+Plex+Mono:wght@400;500&family=Noto+Serif:ital,wght@0,600;1,400&display=swap');

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
  --shadow-lg:     0 8px 32px rgba(15,76,129,.16);
  --font-body:     'IBM Plex Sans', system-ui, sans-serif;
  --font-mono:     'IBM Plex Mono', monospace;
  --font-serif:    'Noto Serif', Georgia, serif;
  --transition:    0.18s ease;
}}

*, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}

html {{ scroll-behavior: smooth; }}

body {{
  font-family: var(--font-body);
  background: var(--bg);
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  color: var(--text);
  font-size: 15px;
  line-height: 1.6;
  -webkit-font-smoothing: antialiased;
}}

/* ─── HEADER ─────────────────────────────────── */
header {{
  background: var(--primary);
  color: white;
  padding: 0 1.25rem;
  height: 64px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  position: sticky;
  top: 0;
  z-index: 200;
  box-shadow: 0 2px 12px rgba(0,0,0,.20);
}}

.header-brand {{
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
}}

.header-logo {{
  width: 38px;
  height: 38px;
  background: rgba(255,255,255,.15);
  border: 1.5px solid rgba(255,255,255,.30);
  border-radius: var(--radius);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  flex-shrink: 0;
}}

.header-text {{ min-width: 0; }}

.header-name {{
  font-family: var(--font-body);
  font-size: 15px;
  font-weight: 600;
  letter-spacing: -.01em;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}}

.header-tagline {{
  font-size: 11px;
  color: rgba(255,255,255,.55);
  font-weight: 400;
  letter-spacing: .02em;
}}

.header-controls {{
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}}

.status-pill {{
  display: flex;
  align-items: center;
  gap: 5px;
  background: rgba(255,255,255,.10);
  border: 1px solid rgba(255,255,255,.18);
  padding: 4px 10px;
  border-radius: 20px;
  font-size: 11.5px;
  color: rgba(255,255,255,.85);
  white-space: nowrap;
}}

.status-dot {{
  width: 6px;
  height: 6px;
  background: #4ADE80;
  border-radius: 50%;
  animation: pulse-dot 2.5s ease-in-out infinite;
}}

.status-dot.offline {{ background: #FCA5A5; animation: none; }}

@keyframes pulse-dot {{
  0%, 100% {{ opacity: 1; transform: scale(1); }}
  50%  {{ opacity: .5; transform: scale(.8); }}
}}

.model-chip {{
  font-size: 11px;
  font-family: var(--font-mono);
  background: rgba(255,255,255,.12);
  border: 1px solid rgba(255,255,255,.18);
  color: rgba(255,255,255,.80);
  padding: 3px 8px;
  border-radius: 4px;
}}

.icon-btn {{
  background: rgba(255,255,255,.08);
  border: 1px solid rgba(255,255,255,.15);
  color: rgba(255,255,255,.80);
  width: 34px;
  height: 34px;
  border-radius: var(--radius-sm);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background var(--transition);
}}

.icon-btn:hover {{ background: rgba(255,255,255,.18); }}

/* ─── SAFETY BANNER ──────────────────────────── */
#safety-banner {{
  padding: 7px 1.25rem;
  font-size: 12px;
  display: flex;
  align-items: center;
  gap: 8px;
  border-bottom: 1px solid;
  font-weight: 500;
  letter-spacing: .01em;
  transition: all var(--transition);
}}

#safety-banner.status-live {{
  background: var(--accent-light);
  border-color: color-mix(in srgb, var(--accent) 30%, white);
  color: color-mix(in srgb, var(--accent) 80%, black);
}}

#safety-banner.status-demo {{
  background: var(--warning-light);
  border-color: color-mix(in srgb, var(--warning) 30%, white);
  color: color-mix(in srgb, var(--warning) 80%, black);
}}

#safety-banner.status-emergency {{
  background: var(--danger-light);
  border-color: color-mix(in srgb, var(--danger) 40%, white);
  color: var(--danger);
  animation: blink-border 1s ease-in-out infinite;
}}

@keyframes blink-border {{
  0%, 100% {{ background: var(--danger-light); }}
  50%       {{ background: color-mix(in srgb, var(--danger) 18%, white); }}
}}

/* ─── MAIN LAYOUT ────────────────────────────── */
.app-body {{
  display: flex;
  flex: 1;
  overflow: hidden;
  height: calc(100vh - 64px - 41px); /* header + banner */
}}

/* ─── SIDEBAR (protocols) ─────────────────────── */
#sidebar {{
  width: 260px;
  background: var(--surface);
  border-right: 1px solid var(--border-light);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  transition: width var(--transition);
  flex-shrink: 0;
}}

#sidebar.collapsed {{ width: 0; }}

.sidebar-header {{
  padding: 14px 16px;
  border-bottom: 1px solid var(--border-light);
  font-size: 11px;
  font-weight: 600;
  color: var(--muted);
  letter-spacing: .08em;
  text-transform: uppercase;
  display: flex;
  align-items: center;
  justify-content: space-between;
}}

.protocol-list {{
  overflow-y: auto;
  flex: 1;
  padding: 8px;
}}

.protocol-item {{
  padding: 10px 12px;
  border-radius: var(--radius-sm);
  cursor: pointer;
  margin-bottom: 2px;
  transition: background var(--transition);
  border: 1px solid transparent;
}}

.protocol-item:hover {{
  background: var(--primary-light);
  border-color: var(--primary-mid);
}}

.protocol-item.active {{
  background: var(--primary-light);
  border-color: var(--primary-mid);
}}

.protocol-title {{
  font-size: 13px;
  font-weight: 500;
  color: var(--text);
  display: flex;
  align-items: center;
  gap: 7px;
}}

.protocol-badge {{
  font-size: 10px;
  background: var(--danger);
  color: white;
  padding: 1px 6px;
  border-radius: 10px;
  font-weight: 600;
  letter-spacing: .02em;
}}

.protocol-badge.green {{ background: var(--accent); }}
.protocol-badge.orange {{ background: var(--warning); }}

.protocol-sub {{
  font-size: 11.5px;
  color: var(--muted);
  margin-top: 2px;
}}

.sidebar-divider {{
  height: 1px;
  background: var(--border-light);
  margin: 6px 8px;
}}

/* ─── CHAT COLUMN ────────────────────────────── */
#chat-col {{
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  min-width: 0;
}}

#chat-container {{
  flex: 1;
  overflow-y: auto;
  padding: 1.25rem 1rem;
  display: flex;
  flex-direction: column;
  gap: 1rem;
  scroll-behavior: smooth;
}}

/* ─── MESSAGES ───────────────────────────────── */
.message {{
  display: flex;
  gap: 10px;
  max-width: 86%;
  animation: msg-in .2s ease;
}}

@keyframes msg-in {{
  from {{ opacity: 0; transform: translateY(6px); }}
  to   {{ opacity: 1; transform: translateY(0); }}
}}

.message.user  {{ align-self: flex-end;  flex-direction: row-reverse; }}
.message.bot   {{ align-self: flex-start; }}
.message.system {{ align-self: center; max-width: 100%; }}

.msg-avatar {{
  width: 32px;
  height: 32px;
  border-radius: 8px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  font-weight: 600;
  margin-top: 2px;
}}

.message.bot  .msg-avatar {{ background: var(--primary); color: white; }}
.message.user .msg-avatar {{ background: var(--accent);  color: white; font-size: 11px; }}

.msg-body {{ display: flex; flex-direction: column; min-width: 0; }}

.msg-bubble {{
  padding: 11px 14px;
  border-radius: var(--radius);
  font-size: 14px;
  line-height: 1.65;
  word-break: break-word;
}}

.message.bot .msg-bubble {{
  background: var(--surface);
  color: var(--text);
  border: 1px solid var(--border-light);
  border-bottom-left-radius: 3px;
  box-shadow: var(--shadow-sm);
}}

.message.user .msg-bubble {{
  background: var(--primary);
  color: white;
  border-bottom-right-radius: 3px;
}}

.message.system .msg-bubble {{
  background: transparent;
  border: 1px dashed var(--border);
  color: var(--muted);
  font-size: 12.5px;
  text-align: center;
  border-radius: var(--radius);
  padding: 7px 14px;
  box-shadow: none;
}}

/* Emergency message style */
.message.emergency .msg-bubble {{
  background: var(--danger-light);
  border: 1.5px solid var(--danger);
  color: var(--text);
}}

.message.emergency .msg-avatar {{ background: var(--danger); }}

/* ─── CLINICAL STRUCTURED OUTPUT ─────────────── */
.clinical-card {{
  background: var(--surface);
  border: 1px solid var(--border-light);
  border-radius: var(--radius);
  overflow: hidden;
  margin-top: 8px;
  box-shadow: var(--shadow-sm);
}}

.clinical-section {{
  padding: 10px 14px;
  border-bottom: 1px solid var(--border-light);
}}

.clinical-section:last-child {{ border-bottom: none; }}

.clinical-section-label {{
  font-size: 10.5px;
  font-weight: 600;
  letter-spacing: .07em;
  text-transform: uppercase;
  color: var(--muted);
  margin-bottom: 5px;
  display: flex;
  align-items: center;
  gap: 5px;
}}

.clinical-section-label.danger {{ color: var(--danger); }}
.clinical-section-label.warning {{ color: var(--warning); }}
.clinical-section-label.success {{ color: var(--accent); }}

.clinical-content {{ font-size: 13.5px; line-height: 1.6; }}

.tag-list {{ display: flex; flex-wrap: wrap; gap: 5px; margin-top: 5px; }}

.tag {{
  font-size: 12px;
  padding: 3px 9px;
  border-radius: 20px;
  font-weight: 500;
}}

.tag.red {{ background: var(--danger-light); color: var(--danger); border: 1px solid color-mix(in srgb, var(--danger) 25%, white); }}
.tag.green {{ background: var(--accent-light); color: color-mix(in srgb, var(--accent) 80%, black); border: 1px solid color-mix(in srgb, var(--accent) 25%, white); }}
.tag.blue {{ background: var(--primary-light); color: var(--primary); border: 1px solid var(--primary-mid); }}
.tag.orange {{ background: var(--warning-light); color: var(--warning); border: 1px solid color-mix(in srgb, var(--warning) 25%, white); }}

.referral-badge {{
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  border-radius: var(--radius-sm);
  font-size: 13px;
  font-weight: 600;
  margin-top: 6px;
}}

.referral-badge.immediate {{ background: var(--danger); color: white; }}
.referral-badge.urgent    {{ background: var(--warning); color: white; }}
.referral-badge.routine   {{ background: var(--accent);  color: white; }}
.referral-badge.monitor   {{ background: var(--primary-light); color: var(--primary); }}

/* ─── FEEDBACK WIDGET ────────────────────────── */
.msg-feedback {{
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 6px;
  font-size: 11.5px;
  color: var(--muted);
}}

.feedback-btn {{
  background: none;
  border: 1px solid var(--border);
  border-radius: 4px;
  padding: 2px 7px;
  cursor: pointer;
  font-size: 12px;
  color: var(--muted);
  transition: all var(--transition);
  font-family: var(--font-body);
}}

.feedback-btn:hover {{ border-color: var(--primary); color: var(--primary); }}
.feedback-btn.active {{ background: var(--primary-light); border-color: var(--primary); color: var(--primary); }}

.confidence-chip {{
  font-family: var(--font-mono);
  font-size: 10.5px;
  padding: 2px 6px;
  border-radius: 3px;
  border: 1px solid var(--border);
  color: var(--muted);
}}

.confidence-chip.HIGH {{ border-color: var(--accent); color: var(--accent); }}
.confidence-chip.MEDIUM {{ border-color: var(--warning); color: var(--warning); }}
.confidence-chip.LOW {{ border-color: var(--danger); color: var(--danger); }}

/* ─── TYPING INDICATOR ───────────────────────── */
.typing-indicator {{
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 12px 14px;
  background: var(--surface);
  border: 1px solid var(--border-light);
  border-radius: var(--radius);
  border-bottom-left-radius: 3px;
  width: fit-content;
}}

.typing-dot {{
  width: 6px;
  height: 6px;
  background: var(--muted);
  border-radius: 50%;
  animation: typing-bounce 1.2s ease-in-out infinite;
}}

.typing-dot:nth-child(2) {{ animation-delay: .2s; }}
.typing-dot:nth-child(3) {{ animation-delay: .4s; }}

@keyframes typing-bounce {{
  0%, 80%, 100% {{ transform: translateY(0); opacity: .5; }}
  40%           {{ transform: translateY(-5px); opacity: 1; }}
}}

/* ─── QUICK REPLIES ──────────────────────────── */
.quick-replies {{
  display: flex;
  flex-wrap: wrap;
  gap: 7px;
  padding: 2px 0 8px 42px;
  animation: msg-in .25s ease;
}}

.quick-btn {{
  background: var(--surface);
  border: 1.5px solid var(--border);
  color: var(--primary);
  padding: 6px 12px;
  border-radius: 20px;
  font-size: 12.5px;
  font-family: var(--font-body);
  font-weight: 500;
  cursor: pointer;
  transition: all var(--transition);
  white-space: nowrap;
}}

.quick-btn:hover {{
  background: var(--primary-light);
  border-color: var(--primary);
}}

/* ─── TIMESTAMP ──────────────────────────────── */
.msg-meta {{
  font-size: 10.5px;
  color: var(--muted);
  margin-top: 4px;
  display: flex;
  align-items: center;
  gap: 6px;
}}

.message.user .msg-meta {{ justify-content: flex-end; }}

/* ─── INPUT BAR ──────────────────────────────── */
#input-bar {{
  background: var(--surface);
  border-top: 1px solid var(--border-light);
  padding: .75rem 1rem;
  box-shadow: 0 -2px 12px rgba(15,76,129,.06);
}}

.input-inner {{
  display: flex;
  gap: 8px;
  align-items: flex-end;
  max-width: 900px;
  margin: 0 auto;
}}

#user-input {{
  flex: 1;
  border: 1.5px solid var(--border);
  border-radius: var(--radius);
  padding: 9px 14px;
  font-size: 14px;
  font-family: var(--font-body);
  outline: none;
  background: var(--bg);
  color: var(--text);
  transition: border-color var(--transition), box-shadow var(--transition);
  resize: none;
  max-height: 120px;
  line-height: 1.5;
}}

#user-input:focus {{
  border-color: var(--primary);
  box-shadow: 0 0 0 3px var(--primary-light);
  background: var(--surface);
}}

#user-input::placeholder {{ color: var(--muted); }}

.input-actions {{ display: flex; gap: 6px; }}

#send-btn {{
  width: 40px;
  height: 40px;
  border-radius: var(--radius-sm);
  background: var(--primary);
  border: none;
  color: white;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background var(--transition), transform var(--transition);
  flex-shrink: 0;
  box-shadow: 0 2px 6px rgba(15,76,129,.30);
}}

#send-btn:hover  {{ background: color-mix(in srgb, var(--primary) 85%, black); }}
#send-btn:active {{ transform: scale(.94); }}
#send-btn:disabled {{ background: var(--border); cursor: not-allowed; box-shadow: none; }}

#emergency-btn {{
  height: 40px;
  padding: 0 12px;
  border-radius: var(--radius-sm);
  background: var(--danger);
  border: none;
  color: white;
  cursor: pointer;
  font-size: 12px;
  font-weight: 600;
  font-family: var(--font-body);
  display: flex;
  align-items: center;
  gap: 5px;
  transition: background var(--transition);
  white-space: nowrap;
}}

#emergency-btn:hover {{ background: color-mix(in srgb, var(--danger) 85%, black); }}

/* ─── PROTOCOL MODAL ─────────────────────────── */
#modal-overlay {{
  display: none;
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,.35);
  z-index: 300;
  align-items: center;
  justify-content: center;
  padding: 1rem;
  backdrop-filter: blur(3px);
}}

#modal-overlay.open {{ display: flex; }}

.modal {{
  background: var(--surface);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-lg);
  max-width: 520px;
  width: 100%;
  max-height: 80vh;
  overflow-y: auto;
  animation: modal-in .2s ease;
}}

@keyframes modal-in {{
  from {{ opacity: 0; transform: scale(.96) translateY(10px); }}
  to   {{ opacity: 1; transform: scale(1) translateY(0); }}
}}

.modal-header {{
  padding: 18px 20px 14px;
  border-bottom: 1px solid var(--border-light);
  display: flex;
  align-items: center;
  justify-content: space-between;
  position: sticky;
  top: 0;
  background: var(--surface);
}}

.modal-title {{
  font-size: 16px;
  font-weight: 600;
  color: var(--text);
}}

.modal-close {{
  background: none;
  border: none;
  color: var(--muted);
  cursor: pointer;
  font-size: 20px;
  padding: 2px 6px;
  border-radius: 4px;
  transition: color var(--transition);
}}

.modal-close:hover {{ color: var(--text); }}

.modal-body {{ padding: 16px 20px 20px; }}

.protocol-section {{ margin-bottom: 18px; }}

.protocol-section-title {{
  font-size: 12px;
  font-weight: 600;
  color: var(--muted);
  letter-spacing: .06em;
  text-transform: uppercase;
  margin-bottom: 8px;
}}

.protocol-list-item {{
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 6px 0;
  border-bottom: 1px solid var(--border-light);
  font-size: 13.5px;
}}

.protocol-list-item:last-child {{ border-bottom: none; }}

.protocol-bullet {{
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--danger);
  flex-shrink: 0;
  margin-top: 6px;
}}

.protocol-bullet.green {{ background: var(--accent); }}
.protocol-bullet.orange {{ background: var(--warning); }}

/* ─── EVALUATION PANEL ───────────────────────── */
#eval-panel {{
  width: 280px;
  background: var(--surface);
  border-left: 1px solid var(--border-light);
  overflow-y: auto;
  flex-shrink: 0;
  padding: 14px;
  display: none;
  flex-direction: column;
  gap: 14px;
}}

#eval-panel.open {{ display: flex; }}

.eval-title {{
  font-size: 11px;
  font-weight: 600;
  color: var(--muted);
  letter-spacing: .08em;
  text-transform: uppercase;
  padding-bottom: 10px;
  border-bottom: 1px solid var(--border-light);
}}

.eval-stat {{
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 6px 0;
  font-size: 13px;
  border-bottom: 1px solid var(--border-light);
}}

.eval-stat-val {{
  font-family: var(--font-mono);
  font-size: 13px;
  font-weight: 600;
  color: var(--primary);
}}

.eval-tag {{
  display: inline-flex;
  align-items: center;
  gap: 4px;
  background: var(--primary-light);
  border: 1px solid var(--primary-mid);
  color: var(--primary);
  padding: 4px 9px;
  border-radius: 4px;
  font-size: 11.5px;
  font-weight: 500;
  margin-bottom: 4px;
  margin-right: 4px;
}}

.session-log-item {{
  background: var(--bg);
  border: 1px solid var(--border-light);
  border-radius: var(--radius-sm);
  padding: 8px 10px;
  font-size: 12px;
  color: var(--text-2);
  margin-bottom: 6px;
}}

.session-log-time {{
  font-family: var(--font-mono);
  font-size: 10.5px;
  color: var(--muted);
  display: block;
  margin-bottom: 2px;
}}

/* ─── SCROLLBAR ──────────────────────────────── */
::-webkit-scrollbar {{ width: 5px; }}
::-webkit-scrollbar-track {{ background: transparent; }}
::-webkit-scrollbar-thumb {{ background: var(--border); border-radius: 10px; }}
::-webkit-scrollbar-thumb:hover {{ background: var(--muted); }}

/* ─── RESPONSIVE ─────────────────────────────── */
@media (max-width: 768px) {{
  #sidebar {{ display: none; }}
  #eval-panel {{ display: none !important; }}
  .model-chip {{ display: none; }}
  .message {{ max-width: 95%; }}
}}

/* ─── PRINT (for clinical records) ──────────────── */
@media print {{
  header, #input-bar, #sidebar, #eval-panel, .quick-replies,
  .feedback-btn, #safety-banner {{ display: none !important; }}
  .msg-bubble {{ border: 1px solid #ccc !important; box-shadow: none !important; }}
  body {{ background: white; }}
}}

/* ─── EMERGENCY OVERLAY ──────────────────────── */
#emergency-overlay {{
  display: none;
  position: fixed;
  inset: 0;
  background: rgba(214,40,40,.08);
  z-index: 100;
  pointer-events: none;
  border: 4px solid var(--danger);
  animation: emergency-pulse 1s ease-in-out infinite;
}}

#emergency-overlay.active {{ display: block; }}

@keyframes emergency-pulse {{
  0%, 100% {{ opacity: 1; }}
  50%      {{ opacity: .4; }}
}}

/* ─── UTILITY ────────────────────────────────── */
.sr-only {{
  position: absolute; width: 1px; height: 1px;
  padding: 0; margin: -1px; overflow: hidden;
  clip: rect(0,0,0,0); white-space: nowrap; border: 0;
}}

strong {{ font-weight: 600; }}
em {{ font-style: italic; }}

.text-danger  {{ color: var(--danger); }}
.text-warning {{ color: var(--warning); }}
.text-success {{ color: var(--accent); }}
"""
    (DOCS_DIR / "static" / "css" / "chat.css").write_text(css, encoding="utf-8")


# ─────────────────────────────────────────────
#  JAVASCRIPT — Full CDST Logic
# ─────────────────────────────────────────────
def write_js(cfg: dict, provider: dict | None, token: str):
    bot = cfg["bot"]
    app = cfg["app"]
    eval_cfg = cfg.get("evaluation", {})

    quick_json = json.dumps(bot["quick_replies"], ensure_ascii=False)
    safety_kw_json = json.dumps(
        bot.get("safety_keywords", []), ensure_ascii=False)
    system = bot["system_prompt"].replace(
        "\\", "\\\\").replace("`", "\\`").replace("\n", "\\n")
    greeting = bot["greeting"].replace("\\", "\\\\").replace(
        "`", "\\`").replace("\n", "\\n")

    provider_type = provider.get(
        "provider_type", "openai") if provider else "demo"
    endpoint = provider["endpoint"] if provider else ""
    model_id = provider["model"] if provider else "demo"
    provider_name = provider["name"] if provider else "demo"
    auth_header = provider["auth_header"] if provider else "Bearer"
    api_version = provider.get("api_version", "") if provider else ""
    safe_token = token.replace("\\", "\\\\").replace(
        "`", "\\`") if token else ""
    study_id = eval_cfg.get("study_id", "EVAH-CDST-001")
    eval_enabled = str(eval_cfg.get("enabled", True)).lower()
    built = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    js = f"""/* HealthAssist CDST — Auto-generated by chatbot_system.py */
/* EVAH-Aligned Clinical Decision Support Tool */
/* Provider: {provider_name} | Model: {model_id} | Built: {built} */

'use strict';

// ─── PROVIDER CONFIG (baked in at build time) ───────────────────────────
const PROVIDER = {{
  token:       `{safe_token}`,
  endpoint:    `{endpoint}`,
  model:       `{model_id}`,
  name:        `{provider_name}`,
  authHeader:  `{auth_header}`,
  apiVersion:  `{api_version}`,
  type:        `{provider_type}`,
}};

// ─── BOT CONFIG ──────────────────────────────────────────────────────────
const BOT_CONFIG = {{
  system:       `{system}`,
  greeting:     `{greeting}`,
  quickReplies:  {quick_json},
  safetyKeywords: {safety_kw_json},
}};

// ─── EVALUATION CONFIG ───────────────────────────────────────────────────
const EVAL = {{
  enabled:   {eval_enabled},
  studyId:   '{study_id}',
  sessionId: crypto.randomUUID ? crypto.randomUUID() : Math.random().toString(36).slice(2),
  log:       [],  // In-session log (exported on demand)
}};

// ─── STATE ───────────────────────────────────────────────────────────────
let history      = [];
let busy         = false;
let msgCounter   = 0;
let emergencyMode = false;
let protocolData = null;

// ─── INIT ────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', async () => {{
  renderProviderBanner();
  showGreeting();
  loadProtocols();
  setupEvalPanel();
  updateEvalStats();

  const inp = document.getElementById('user-input');
  inp.addEventListener('keydown', e => {{
    if (e.key === 'Enter' && !e.shiftKey) {{ e.preventDefault(); send(); }}
  }});
  inp.addEventListener('input', autoResize);
}});

function autoResize() {{
  const el = document.getElementById('user-input');
  el.style.height = 'auto';
  el.style.height = Math.min(el.scrollHeight, 120) + 'px';
}};

// ─── BANNER ──────────────────────────────────────────────────────────────
function renderProviderBanner() {{
  const el = document.getElementById('safety-banner');
  if (!el) return;
  const dot = document.getElementById('status-dot');
  const modelChip = document.getElementById('model-chip');
  if (modelChip) modelChip.textContent = PROVIDER.model;

  if (!PROVIDER.token || PROVIDER.name === 'demo') {{
    el.className = 'status-demo';
    el.innerHTML = '⚠️ &nbsp;Demo mode — set <strong>ANTHROPIC_API_KEY</strong> or another API key in GitHub Secrets for live AI responses.';
    if (dot) dot.className = 'status-dot offline';
  }} else {{
    el.className = 'status-live';
    const labels = {{
      anthropic: 'Anthropic Claude',
      openai: 'OpenAI GPT-4o',
      github: 'GitHub Models',
      groq: 'Groq / Llama 3.3',
      mistral: 'Mistral AI',
    }};
    const label = labels[PROVIDER.name] || PROVIDER.name;
    el.innerHTML = `✅ &nbsp;Live AI &nbsp;·&nbsp; <strong>${{label}}</strong> &nbsp;·&nbsp; ${{PROVIDER.model}} &nbsp;·&nbsp; Session: <code style="font-size:10.5px">${{EVAL.sessionId.slice(0,8)}}</code>`;
  }}
}};

// ─── GREETING ────────────────────────────────────────────────────────────
function showGreeting() {{
  addMsg('bot', BOT_CONFIG.greeting, {{ noFeedback: true }});
  setTimeout(renderQuickReplies, 400);
}}

// ─── SAFETY DETECTOR ────────────────────────────────────────────────────
function detectEmergency(text) {{
  const lower = text.toLowerCase();
  return BOT_CONFIG.safetyKeywords.some(kw => lower.includes(kw));
}}

function setEmergencyMode(on) {{
  emergencyMode = on;
  const overlay = document.getElementById('emergency-overlay');
  const banner  = document.getElementById('safety-banner');
  if (on) {{
    overlay?.classList.add('active');
    if (banner) {{
      banner.className = 'status-emergency';
      banner.innerHTML = '🚨 &nbsp;<strong>EMERGENCY ALERT</strong> — Potential life-threatening situation detected. Refer immediately. Call: <strong>+254 999</strong>';
    }}
  }} else {{
    overlay?.classList.remove('active');
    renderProviderBanner();
  }}
}}

// ─── MESSAGE RENDERING ───────────────────────────────────────────────────
function addMsg(role, text, opts = {{}}) {{
  const c = document.getElementById('chat-container');
  if (!c) return;

  const id = 'msg-' + (++msgCounter);
  const w  = document.createElement('div');
  const ts = new Date().toLocaleTimeString([], {{ hour: '2-digit', minute: '2-digit' }});

  // Detect emergency in bot response
  const isEmergency = role === 'bot' && (
    text.includes('EMERGENCY REFERRAL') ||
    text.includes('REFER URGENTLY') ||
    text.includes('REFER IMMEDIATELY') ||
    (opts.emergency === true)
  );

  if (isEmergency) setEmergencyMode(true);

  w.id = id;
  w.className = 'message ' + role + (isEmergency ? ' emergency' : '');

  const avatar = role === 'bot' ? '🏥' : (role === 'user' ? 'CHW' : '');
  const bubbleContent = role === 'bot' ? formatBotText(text) : esc(text).replace(/\\n/g, '<br>');

  let feedbackHtml = '';
  if (role === 'bot' && !opts.noFeedback) {{
    const confidence = opts.confidence || extractConfidence(text);
    feedbackHtml = `
      <div class="msg-feedback">
        <button class="feedback-btn" onclick="rateMsgAccuracy('${{id}}', 'accurate')" title="Mark as accurate">✓ Accurate</button>
        <button class="feedback-btn" onclick="rateMsgAccuracy('${{id}}', 'inaccurate')" title="Mark as inaccurate">✗ Inaccurate</button>
        <button class="feedback-btn" onclick="rateMsgAccuracy('${{id}}', 'escalate')" title="Escalate for review">⬆ Review</button>
        ${{confidence ? `<span class="confidence-chip ${{confidence}}">${{confidence}}</span>` : ''}}
      </div>`;
  }}

  w.innerHTML = `
    <div class="msg-avatar">${{avatar}}</div>
    <div class="msg-body">
      <div class="msg-bubble">${{bubbleContent}}</div>
      <div class="msg-meta">
        <span>${{ts}}</span>
        ${{isEmergency ? '<span class="text-danger" style="font-weight:600">⚠ EMERGENCY</span>' : ''}}
      </div>
      ${{feedbackHtml}}
    </div>`;

  c.appendChild(w);
  c.scrollTop = c.scrollHeight;

  // Log for evaluation
  if (EVAL.enabled) {{
    EVAL.log.push({{
      t: Date.now(),
      role,
      len: text.length,
      emergency: isEmergency,
      feedback: null,
      confidence: opts.confidence || null,
      msgId: id,
    }});
    updateEvalStats();
  }}

  return id;
}}

function extractConfidence(text) {{
  if (text.includes('confidence: HIGH') || text.includes('Confidence: HIGH')) return 'HIGH';
  if (text.includes('confidence: MEDIUM') || text.includes('Confidence: MEDIUM')) return 'MEDIUM';
  if (text.includes('confidence: LOW') || text.includes('Confidence: LOW')) return 'LOW';
  return null;
}}

function showTyping() {{
  const c  = document.getElementById('chat-container');
  const el = document.createElement('div');
  el.id = 'typing-indicator';
  el.className = 'message bot';
  el.innerHTML = `
    <div class="msg-avatar">🏥</div>
    <div class="msg-body">
      <div class="typing-indicator">
        <div class="typing-dot"></div>
        <div class="typing-dot"></div>
        <div class="typing-dot"></div>
      </div>
    </div>`;
  c.appendChild(el);
  c.scrollTop = c.scrollHeight;
}}

function removeTyping() {{
  document.getElementById('typing-indicator')?.remove();
}}

function renderQuickReplies() {{
  const c = document.getElementById('chat-container');
  const el = document.createElement('div');
  el.className = 'quick-replies';
  el.id = 'quick-replies';
  BOT_CONFIG.quickReplies.forEach(r => {{
    const btn = document.createElement('button');
    btn.className = 'quick-btn';
    btn.textContent = r;
    btn.onclick = () => {{ el.remove(); send(r); }};
    el.appendChild(btn);
  }});
  c.appendChild(el);
  c.scrollTop = c.scrollHeight;
}}

// ─── TEXT FORMATTER ──────────────────────────────────────────────────────
function formatBotText(text) {{
  return esc(text)
    .replace(/\\n\\n/g, '</p><p style="margin-top:8px">')
    .replace(/\\n/g, '<br>')
    .replace(/\\*\\*(.+?)\\*\\*/g, '<strong>$1</strong>')
    .replace(/\\*(.+?)\\*/g, '<em>$1</em>')
    .replace(/`(.+?)`/g, '<code style="font-family:var(--font-mono);font-size:12.5px;background:var(--bg);padding:1px 5px;border-radius:3px">$1</code>')
    .replace(/(EMERGENCY REFERRAL REQUIRED|REFER URGENTLY|REFER IMMEDIATELY)/g,
             '<span class="text-danger" style="font-weight:700">⚠ $1</span>')
    .replace(/(HIGH CONFIDENCE|MEDIUM CONFIDENCE|LOW CONFIDENCE)/g,
             '<span class="confidence-chip $1">$1</span>');
}}

// ─── SEND ────────────────────────────────────────────────────────────────
async function send(override) {{
  if (busy) return;
  const inp  = document.getElementById('user-input');
  const text = (override || inp.value).trim();
  if (!text) return;

  document.getElementById('quick-replies')?.remove();
  inp.value = '';
  inp.style.height = '';

  // Emergency detection on user input
  if (detectEmergency(text)) setEmergencyMode(true);

  addMsg('user', text);
  history.push({{ role: 'user', content: text }});

  busy = true;
  const sendBtn = document.getElementById('send-btn');
  if (sendBtn) sendBtn.disabled = true;
  showTyping();

  try {{
    const reply = PROVIDER.token && PROVIDER.name !== 'demo'
      ? await callAI()
      : await demoReply(text);
    removeTyping();
    addMsg('bot', reply);
    history.push({{ role: 'assistant', content: reply }});
  }} catch (err) {{
    removeTyping();
    addMsg('bot', '⚠️ Connection error: ' + esc(err.message || 'Unknown error') +
           '\\n\\nPlease check your connection. For emergencies, use the emergency button or call directly.');
    console.error('[HealthAssist CDST]', err);
  }}

  busy = false;
  if (sendBtn) sendBtn.disabled = false;
  inp.focus();
}}

// ─── ANTHROPIC API CALL ──────────────────────────────────────────────────
async function callAI() {{
  if (PROVIDER.type === 'anthropic') {{
    return callAnthropic();
  }}
  return callOpenAICompat();
}}

async function callAnthropic() {{
  const messages = history.map(m => ({{
    role:    m.role === 'assistant' ? 'assistant' : 'user',
    content: m.content,
  }}));

  const res = await fetch(PROVIDER.endpoint, {{
    method: 'POST',
    headers: {{
      'Content-Type':         'application/json',
      'x-api-key':            PROVIDER.token,
      'anthropic-version':    PROVIDER.apiVersion || '2023-06-01',
      'anthropic-dangerous-direct-browser-access': 'true',
    }},
    body: JSON.stringify({{
      model:      PROVIDER.model,
      max_tokens: 1024,
      system:     BOT_CONFIG.system,
      messages,
    }}),
  }});

  if (!res.ok) {{
    const err = await res.json().catch(() => ({{}}));
    throw new Error(err.error?.message || `HTTP ${{res.status}} from Anthropic`);
  }}

  const data = await res.json();
  return data.content?.[0]?.text?.trim() || 'No response received.';
}}

async function callOpenAICompat() {{
  const res = await fetch(PROVIDER.endpoint, {{
    method: 'POST',
    headers: {{
      'Content-Type':  'application/json',
      'Authorization': `${{PROVIDER.authHeader}} ${{PROVIDER.token}}`,
    }},
    body: JSON.stringify({{
      model:       PROVIDER.model,
      messages: [
        {{ role: 'system', content: BOT_CONFIG.system }},
        ...history,
      ],
      max_tokens:  1024,
      temperature: 0.3,  // Lower temp for clinical accuracy
    }}),
  }});

  if (!res.ok) {{
    const err = await res.json().catch(() => ({{}}));
    throw new Error(err.error?.message || `HTTP ${{res.status}} from ${{PROVIDER.name}}`);
  }}

  const data = await res.json();
  return data.choices?.[0]?.message?.content?.trim() || 'No response received.';
}}

// ─── DEMO MODE ───────────────────────────────────────────────────────────
async function demoReply(text) {{
  await sleep(800 + Math.random() * 400);
  const t = text.toLowerCase();

  if (t.includes('fever') || t.includes('malaria') || t.includes('temperature')) {{
    return `**Fever Assessment — IMCI Protocol**

**Assessment Summary:**
Child presenting with fever. Systematic assessment required.

**Key Questions to Ask:**
• Duration of fever (days)?
• Any convulsions (now or past)?
• Can the child drink/breastfeed?
• Has the child vomited everything?
• Travel/residence in malaria-endemic area?

**Recommended Actions:**
1. Measure temperature (axillary/rectal)
2. Check for IMCI danger signs (see below)
3. If in malaria zone & RDT available → perform RDT
4. Check for stiff neck, bulging fontanelle
5. Assess hydration status

**IMCI Danger Signs (Refer Urgently if Present):**
• Cannot drink or is unconscious
• Convulsing now or recently
• Stiff neck
• Severe respiratory distress

**Referral Criteria:**
• Any danger sign → REFER URGENTLY
• Temp ≥38.5°C + <2 months → REFER
• Fever >7 days → REFER for investigation

Confidence: MEDIUM (demo mode — limited context)`;
  }}

  if (t.includes('malnutrition') || t.includes('muac') || t.includes('wasting')) {{
    return `**Malnutrition Screening — MUAC Protocol**

**MUAC Thresholds (6–59 months):**
• **≥125mm** → Well nourished ✓
• **115–124mm** → Moderate Acute Malnutrition (MAM) — enrol in SFP
• **<115mm** → Severe Acute Malnutrition (SAM) ⚠ REFER

**Also Check:**
• Bilateral pitting oedema → SAM regardless of MUAC (REFER)
• Weight-for-height Z-score if available
• Recent weight loss, appetite, illness history

**For SAM:**
• REFER to stabilisation centre
• If appetite present & no complications → CMAM/OTP
• Give amoxicillin, vitamin A, measles vaccine if due

**For MAM:**
• Enrol in Supplementary Feeding Programme
• Provide RUTF/high-energy biscuits per protocol
• Follow up weekly

Confidence: HIGH`;
  }}

  if (t.includes('maternal') || t.includes('pregnant') || t.includes('antenatal') || t.includes('labour')) {{
    return `**Maternal Health — Safe Motherhood Protocol**

**Immediate Danger Signs — REFER NOW if Present:**
• Severe headache + visual disturbance → Pre-eclampsia
• Heavy vaginal bleeding → Antepartum/postpartum haemorrhage
• Convulsions → Eclampsia
• BP ≥140/90 mmHg
• Fever ≥38°C in pregnancy
• No fetal movement >12h (after quickening)
• Labour <37 weeks (preterm)

**Routine ANC Checks:**
• BP, weight, fundal height, fetal heart rate
• Urine protein & glucose
• Haemoglobin (anaemia screen)
• Tetanus toxoid status
• PMTCT HIV testing

**Key Messages:**
• Facility delivery — reinforce at every contact
• Birth preparedness plan — transport, blood donor, funds
• Emergency contact: obstetric referral facility

Confidence: HIGH`;
  }}

  if (t.includes('refer') || t.includes('referral')) {{
    return `**Referral Decision Guide**

**Referral Levels:**

🔴 **Immediate (life-threatening):**
Call ambulance / refer NOW
• Altered consciousness / unconscious
• Severe respiratory distress
• Signs of shock (cold clammy skin, rapid weak pulse)
• Active convulsions
• Severe haemorrhage

🟠 **Urgent (within 2–4 hours):**
• High fever + any danger sign
• SAM with complications
• BP ≥140/90 in pregnancy
• Suspected meningitis

🟡 **Routine (next available transport):**
• MAM not responding to treatment
• Chronic illness requiring specialist
• Failed treatment after 48–72h

🟢 **Monitor at facility (24–48h review):**
• Uncomplicated illness responding to treatment
• Post-treatment follow-up

**Before Referring:**
1. Stabilise patient (airway, breathing, circulation)
2. Write referral note (name, age, vitals, treatment given)
3. Inform receiving facility by phone
4. Ensure transport arranged
5. Send treatment records

Confidence: HIGH`;
  }}

  if (t.includes('emergency') || t.includes('unconscious') || t.includes('fitting') || t.includes('convulsion')) {{
    return `⚠ **EMERGENCY REFERRAL REQUIRED**

**Immediate Actions (ABC Protocol):**

**Airway:**
• Position in recovery position if unconscious
• Clear airway — no obstruction
• Do NOT put anything in mouth during convulsion

**Breathing:**
• Count respiratory rate
• Give O₂ if available (>90% SpO₂ target)

**Circulation:**
• IV access if trained
• Check capillary refill, pulse

**For Active Convulsions:**
• Diazepam rectal/IV per weight-based protocol
• Call for help IMMEDIATELY

**REFER URGENTLY:**
Contact receiving facility NOW — provide:
• Patient age, weight
• Duration of symptoms
• Vital signs
• Treatment given

**Emergency contacts:** [Configure in config.yaml]

Confidence: HIGH`;
  }}

  return `**HealthAssist CDST — Demo Mode**

I'm currently running in demo mode (no API key configured).

For a real clinical query, I would provide:
• Structured IMCI/WHO-aligned assessment
• Key differential diagnoses to consider
• Recommended immediate actions
• Red flag symptoms to watch for
• Clear referral criteria with urgency level

**Quick Reference:**
Try asking about: fever assessment, malnutrition screening (MUAC), maternal health, referral criteria, or emergency protocols.

⚠ This tool supports clinical judgment — not replaces it.

To enable live AI: Set **ANTHROPIC_API_KEY** in GitHub Secrets.`;
}}

// ─── PROTOCOLS SIDEBAR ───────────────────────────────────────────────────
async function loadProtocols() {{
  try {{
    const res = await fetch('static/data/protocols.json');
    protocolData = await res.json();
    renderProtocolSidebar();
  }} catch (e) {{
    console.warn('Protocol data not loaded:', e);
  }}
}}

function renderProtocolSidebar() {{
  const list = document.getElementById('protocol-list');
  if (!list || !protocolData) return;

  const items = [
    {{ key: 'imci',     icon: '👶', label: 'IMCI Danger Signs',     badge: 'Emergency', color: 'red'    }},
    {{ key: 'muac',     icon: '📏', label: 'MUAC Screening',         badge: 'Nutrition',  color: 'orange' }},
    {{ key: 'malaria_rdt', icon: '🦟', label: 'Malaria RDT Protocol', badge: 'Malaria',  color: 'orange' }},
    {{ key: 'maternal', icon: '🤱', label: 'Safe Motherhood',         badge: 'Maternal', color: 'green'  }},
    {{ key: 'referral_levels', icon: '🚑', label: 'Referral Levels', badge: 'Guide',    color: 'green'  }},
  ];

  list.innerHTML = items.map(item => `
    <div class="protocol-item" onclick="showProtocol('${{item.key}}')" role="button" tabindex="0">
      <div class="protocol-title">
        ${{item.icon}} ${{item.label}}
        <span class="protocol-badge ${{item.color}}">${{item.badge}}</span>
      </div>
      <div class="protocol-sub">Tap to view quick reference</div>
    </div>
  `).join('');
}}

function showProtocol(key) {{
  if (!protocolData || !protocolData[key]) return;
  const p = protocolData[key];
  const modal = document.getElementById('modal-overlay');
  const title = document.getElementById('modal-title');
  const body  = document.getElementById('modal-body');
  if (!modal || !title || !body) return;

  title.textContent = p.title || key;
  body.innerHTML = buildProtocolHTML(key, p);
  modal.classList.add('open');
}}

function buildProtocolHTML(key, p) {{
  if (key === 'imci') {{
    return `
      <div class="protocol-section">
        <div class="protocol-section-title" style="color:var(--danger)">⚠ Emergency Signs — Refer Immediately</div>
        ${{p.emergency_signs.map(s => `
          <div class="protocol-list-item">
            <div class="protocol-bullet"></div>
            <span>${{esc(s)}}</span>
          </div>`).join('')}}
      </div>
      <div class="protocol-section">
        <div class="protocol-section-title">Fever Classification</div>
        ${{Object.entries(p.classify_fever || {{}}).map(([k, v]) => `
          <div class="protocol-list-item">
            <div class="protocol-bullet orange"></div>
            <span><strong>${{k.replace('_', ' ')}}:</strong> ${{esc(v)}}</span>
          </div>`).join('')}}
      </div>`;
  }}
  if (key === 'muac') {{
    return `
      <div class="protocol-section">
        <div class="protocol-section-title">MUAC Thresholds (6–59 months)</div>
        ${{Object.entries(p.thresholds || {{}}).map(([k, v]) => `
          <div class="protocol-list-item">
            <div class="protocol-bullet ${{k === 'red' ? '' : k === 'yellow' ? 'orange' : 'green'}}"></div>
            <span><strong>${{k.toUpperCase()}}:</strong> ${{esc(v)}}</span>
          </div>`).join('')}}
      </div>
      <div class="protocol-section">
        <div class="protocol-section-title" style="color:var(--danger)">Bilateral Oedema</div>
        <p style="font-size:13.5px">${{esc(p.bilateral_oedema || '')}}</p>
      </div>`;
  }}
  if (key === 'malaria_rdt') {{
    return `
      <div class="protocol-section">
        <div class="protocol-section-title">RDT Results</div>
        <p style="font-size:13.5px;margin-bottom:8px"><strong>Positive:</strong> ${{esc(p.positive || '')}}</p>
        <p style="font-size:13.5px"><strong>Negative (clinical suspicion):</strong> ${{esc(p.negative_clinical || '')}}</p>
      </div>
      <div class="protocol-section">
        <div class="protocol-section-title" style="color:var(--danger)">⚠ Severe Malaria Signs — Emergency Referral</div>
        ${{(p.severe_signs || []).map(s => `
          <div class="protocol-list-item">
            <div class="protocol-bullet"></div>
            <span>${{esc(s)}}</span>
          </div>`).join('')}}
        <p style="font-size:13px;margin-top:8px;color:var(--danger)">${{esc(p.severe_action || '')}}</p>
      </div>`;
  }}
  if (key === 'maternal') {{
    return `
      <div class="protocol-section">
        <div class="protocol-section-title" style="color:var(--danger)">⚠ Refer Immediately</div>
        ${{(p.refer_immediately || []).map(s => `
          <div class="protocol-list-item">
            <div class="protocol-bullet"></div>
            <span>${{esc(s)}}</span>
          </div>`).join('')}}
      </div>`;
  }}
  if (key === 'referral_levels') {{
    const icons = {{ immediate: '🔴', urgent: '🟠', routine: '🟡', monitor: '🟢' }};
    return `
      <div class="protocol-section">
        ${{Object.entries(p).map(([k, v]) => `
          <div class="protocol-list-item">
            <span style="font-size:16px">${{icons[k] || '•'}}</span>
            <span><strong style="text-transform:capitalize">${{k}}:</strong> ${{esc(v)}}</span>
          </div>`).join('')}}
      </div>`;
  }}
  return `<p style="font-size:13.5px">${{esc(JSON.stringify(p, null, 2))}}</p>`;
}}

function closeModal() {{
  document.getElementById('modal-overlay')?.classList.remove('open');
}}

// ─── EVALUATION & FEEDBACK ───────────────────────────────────────────────
function rateMsgAccuracy(msgId, rating) {{
  const logEntry = EVAL.log.find(e => e.msgId === msgId);
  if (logEntry) logEntry.feedback = rating;

  const msg = document.getElementById(msgId);
  if (msg) {{
    msg.querySelectorAll('.feedback-btn').forEach(btn => btn.classList.remove('active'));
    const clicked = msg.querySelector(`[onclick*="${{rating}}"]`);
    if (clicked) clicked.classList.add('active');
  }}

  updateEvalStats();
  console.log(`[EVAL ${{EVAL.studyId}}] Session ${{EVAL.sessionId}} — msg ${{msgId}} rated: ${{rating}}`);
}}

function setupEvalPanel() {{
  // Panel is toggled via header button
}}

function updateEvalStats() {{
  const total    = EVAL.log.filter(e => e.role === 'bot').length;
  const accurate = EVAL.log.filter(e => e.feedback === 'accurate').length;
  const reviewed = EVAL.log.filter(e => e.feedback === 'escalate').length;
  const emergencies = EVAL.log.filter(e => e.emergency).length;

  const els = {{
    'eval-total':      total,
    'eval-accurate':   accurate,
    'eval-reviewed':   reviewed,
    'eval-emergency':  emergencies,
  }};
  Object.entries(els).forEach(([id, val]) => {{
    const el = document.getElementById(id);
    if (el) el.textContent = val;
  }});
}}

function toggleEvalPanel() {{
  document.getElementById('eval-panel')?.classList.toggle('open');
}}

function exportSession() {{
  const data = {{
    studyId:   EVAL.studyId,
    sessionId: EVAL.sessionId,
    exportedAt: new Date().toISOString(),
    summary: {{
      totalBotMessages: EVAL.log.filter(e => e.role === 'bot').length,
      userMessages: EVAL.log.filter(e => e.role === 'user').length,
      accurateRatings: EVAL.log.filter(e => e.feedback === 'accurate').length,
      inaccurateRatings: EVAL.log.filter(e => e.feedback === 'inaccurate').length,
      escalations: EVAL.log.filter(e => e.feedback === 'escalate').length,
      emergencyAlerts: EVAL.log.filter(e => e.emergency).length,
    }},
    conversationHistory: history,
    evalLog: EVAL.log,
  }};

  const blob = new Blob([JSON.stringify(data, null, 2)], {{ type: 'application/json' }});
  const url  = URL.createObjectURL(blob);
  const a    = document.createElement('a');
  a.href     = url;
  a.download = `evah-session-${{EVAL.sessionId.slice(0,8)}}-${{Date.now()}}.json`;
  a.click();
  URL.revokeObjectURL(url);
}}

// ─── EMERGENCY BUTTON ────────────────────────────────────────────────────
function triggerEmergency() {{
  setEmergencyMode(true);
  addMsg('system', '🚨 Emergency protocol activated — Patient requires immediate assessment', {{ noFeedback: true }});
  send('EMERGENCY: Patient presenting with potential life-threatening condition. Provide immediate triage guidance and emergency referral protocol.');
}}

function clearEmergency() {{
  setEmergencyMode(false);
  addMsg('system', 'Emergency mode cleared — Continuing normal assessment', {{ noFeedback: true }});
}}

// ─── SIDEBAR TOGGLE ──────────────────────────────────────────────────────
function toggleSidebar() {{
  document.getElementById('sidebar')?.classList.toggle('collapsed');
}}

// ─── NEW SESSION ─────────────────────────────────────────────────────────
function newSession() {{
  if (emergencyMode && !confirm('Emergency mode is active. Start a new session?')) return;
  history = [];
  EVAL.log = [];
  emergencyMode = false;
  setEmergencyMode(false);
  document.getElementById('chat-container').innerHTML = '';
  EVAL.sessionId = crypto.randomUUID ? crypto.randomUUID() : Math.random().toString(36).slice(2);
  renderProviderBanner();
  showGreeting();
  updateEvalStats();
}}

// ─── UTILS ───────────────────────────────────────────────────────────────
function esc(t) {{
  return String(t)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}}

function sleep(ms) {{ return new Promise(r => setTimeout(r, ms)); }}
"""
    (DOCS_DIR / "static" / "js" / "chat.js").write_text(js, encoding="utf-8")


# ─────────────────────────────────────────────
#  HTML — Production Clinical Interface
# ─────────────────────────────────────────────
def write_html(cfg: dict, provider: dict | None):
    app = cfg["app"]
    bot = cfg["bot"]
    name = app["name"]
    tagline = app["tagline"]
    icon = app["icon"]
    model = provider["model"] if provider else "demo"
    provider_name = provider["name"] if provider else "demo"
    built = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    study_id = cfg.get("evaluation", {}).get("study_id", "EVAH-CDST-001")

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta name="description" content="{name} — {tagline}. EVAH-aligned AI clinical decision support for community health workers.">
  <meta name="theme-color" content="#0F4C81">
  <title>{name} — {tagline}</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@300;400;500;600&family=IBM+Plex+Mono:wght@400;500&family=Noto+Serif:ital,wght@0,600;1,400&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="static/css/chat.css">
</head>
<body>

  <!-- Emergency overlay (activated by safety detection) -->
  <div id="emergency-overlay" aria-hidden="true"></div>

  <!-- Header -->
  <header role="banner">
    <div class="header-brand">
      <button class="icon-btn" onclick="toggleSidebar()" aria-label="Toggle protocol sidebar" title="Toggle protocols">
        <svg width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
          <path d="M3 12h18M3 6h18M3 18h18"/>
        </svg>
      </button>
      <div class="header-logo" aria-hidden="true">{icon}</div>
      <div class="header-text">
        <div class="header-name">{name}</div>
        <div class="header-tagline">{tagline}</div>
      </div>
    </div>

    <div class="header-controls">
      <span class="model-chip" id="model-chip" title="AI model">{model}</span>
      <div class="status-pill">
        <div class="status-dot" id="status-dot"></div>
        <span>Online</span>
      </div>
      <button class="icon-btn" onclick="toggleEvalPanel()" aria-label="Evaluation panel" title="EVAH Evaluation Dashboard">
        <svg width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
          <path d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"/>
        </svg>
      </button>
      <button class="icon-btn" onclick="newSession()" aria-label="New session" title="New session">
        <svg width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
          <path d="M12 5v14m7-7H5"/>
        </svg>
      </button>
    </div>
  </header>

  <!-- Safety / Status Banner -->
  <div id="safety-banner" role="status" aria-live="polite">Initialising…</div>

  <!-- App Body (Sidebar + Chat + Eval Panel) -->
  <div class="app-body">

    <!-- Protocol Sidebar -->
    <aside id="sidebar" aria-label="Clinical protocols">
      <div class="sidebar-header">
        <span>Quick Protocols</span>
        <span style="font-weight:400;font-size:10px;color:var(--border)">WHO / IMCI</span>
      </div>
      <div class="protocol-list" id="protocol-list">
        <!-- Rendered by chat.js -->
        <div style="padding:12px 8px;font-size:12.5px;color:var(--muted)">Loading protocols…</div>
      </div>
      <div class="sidebar-divider"></div>
      <div style="padding:10px 12px">
        <div style="font-size:11px;color:var(--muted);line-height:1.5">
          Study ID: <code style="font-size:10.5px">{study_id}</code><br>
          Provider: <code style="font-size:10.5px">{provider_name}</code>
        </div>
      </div>
    </aside>

    <!-- Chat Column -->
    <main id="chat-col">
      <div id="chat-container" role="log" aria-live="polite" aria-label="Clinical conversation">
        <!-- Messages rendered by chat.js -->
      </div>

      <!-- Input Bar -->
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
            <button id="emergency-btn" onclick="triggerEmergency()" aria-label="Emergency protocol" title="Activate emergency protocol">
              <svg width="14" height="14" fill="currentColor" viewBox="0 0 24 24">
                <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-2h2v2zm0-4h-2V7h2v6z"/>
              </svg>
              Emergency
            </button>
            <button id="send-btn" onclick="send()" aria-label="Send message">
              <svg width="17" height="17" fill="none" stroke="currentColor" stroke-width="2.2" viewBox="0 0 24 24">
                <path d="M22 2L11 13M22 2L15 22l-4-9-9-4 20-7z"/>
              </svg>
            </button>
          </div>
        </div>
      </div>
    </main>

    <!-- Evaluation Panel (EVAH Pathway A/B) -->
    <aside id="eval-panel" aria-label="Evaluation dashboard">
      <div class="eval-title">📊 EVAH Evaluation — {study_id}</div>

      <div>
        <div class="eval-stat">
          <span>Bot responses</span>
          <span class="eval-stat-val" id="eval-total">0</span>
        </div>
        <div class="eval-stat">
          <span>Marked accurate</span>
          <span class="eval-stat-val" id="eval-accurate">0</span>
        </div>
        <div class="eval-stat">
          <span>Escalated for review</span>
          <span class="eval-stat-val" id="eval-reviewed">0</span>
        </div>
        <div class="eval-stat">
          <span>Emergency alerts</span>
          <span class="eval-stat-val" id="eval-emergency">0</span>
        </div>
      </div>

      <div>
        <div style="font-size:11px;font-weight:600;color:var(--muted);letter-spacing:.06em;text-transform:uppercase;margin-bottom:8px">Tags</div>
        <div>
          <span class="eval-tag">Pathway A</span>
          <span class="eval-tag">Real-world eval</span>
          <span class="eval-tag">CHW support</span>
          <span class="eval-tag">IMCI</span>
          <span class="eval-tag">Sub-Saharan Africa</span>
        </div>
      </div>

      <div>
        <div style="font-size:11px;font-weight:600;color:var(--muted);letter-spacing:.06em;text-transform:uppercase;margin-bottom:8px">Actions</div>
        <button onclick="exportSession()" style="width:100%;padding:8px;background:var(--primary);color:white;border:none;border-radius:var(--radius-sm);cursor:pointer;font-size:13px;font-family:var(--font-body);font-weight:500;margin-bottom:6px">
          ⬇ Export Session Data
        </button>
        <button onclick="clearEmergency()" style="width:100%;padding:8px;background:var(--surface);color:var(--danger);border:1.5px solid var(--danger);border-radius:var(--radius-sm);cursor:pointer;font-size:13px;font-family:var(--font-body);font-weight:500">
          Clear Emergency Mode
        </button>
      </div>

      <div style="font-size:11px;color:var(--muted);line-height:1.6;border-top:1px solid var(--border-light);padding-top:12px">
        Session data is stored locally and exported as JSON for research use. No PHI is transmitted.
      </div>
    </aside>

  </div>

  <!-- Protocol Reference Modal -->
  <div id="modal-overlay" role="dialog" aria-modal="true" aria-label="Protocol reference" onclick="if(event.target===this)closeModal()">
    <div class="modal">
      <div class="modal-header">
        <div class="modal-title" id="modal-title">Protocol Reference</div>
        <button class="modal-close" onclick="closeModal()" aria-label="Close">✕</button>
      </div>
      <div class="modal-body" id="modal-body">
        <!-- Populated by showProtocol() -->
      </div>
    </div>
  </div>

  <!-- Built metadata (hidden, for debugging) -->
  <!-- Built: {built} | Provider: {provider_name} | Model: {model} | Study: {study_id} -->

  <script src="static/js/chat.js"></script>
</body>
</html>
"""
    (DOCS_DIR / "index.html").write_text(html, encoding="utf-8")


# ─────────────────────────────────────────────
#  ENTRY POINT
# ─────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="HealthAssist CDST Builder")
    parser.add_argument(
        "command",
        choices=["init", "build", "auto", "verify"],
        help="Command to run"
    )
    args = parser.parse_args()
    {"init": cmd_init, "build": cmd_build,
        "auto": cmd_auto, "verify": cmd_verify}[args.command]()
