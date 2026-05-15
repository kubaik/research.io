#!/usr/bin/env python3
"""
chatbot_system.py — EVAH-Aligned Health CDST Chatbot Builder  v1.0
Production-ready Clinical Decision Support Tool for community health workers
in LMICs. Aligned with J-PAL EVAH Pathway A/B RFP.

V1 additions over baseline:
  • Structured clinical output (SOAP-aligned system prompt + JS parser)
  • Weight-based dosing calculator (offline, CHW formulary-constrained)
  • Browser-side network resilience (retry, timeout, offline queue)
  • Pathway B fields (facility_id, arm, patient_hash, randomisation seed)
  • Consent / data-governance screen (IRB requirement)
  • Facility config (emergency contacts, formulary list, region, language)
  • PWA service worker + manifest (offline protocol access)
  • Multi-language scaffold (i18n keys, Swahili starter pack)
  • Immutable audit trail (protocol_version pin, session hash chain)
  • Follow-up capture in eval log

Commands:
    python chatbot_system.py init     # Create config.yaml from defaults
    python chatbot_system.py build    # Build static site → _site/ or docs/
    python chatbot_system.py auto     # Full pipeline: init → build → verify
    python chatbot_system.py verify   # Check secrets and config only
"""

import os
import sys
import json
import hashlib
import logging
import argparse
from pathlib import Path
from datetime import datetime, timezone

import yaml

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

ROOT = Path(__file__).parent
DOCS_DIR = ROOT / os.getenv("BUILD_OUTPUT_DIR", "docs")
CONFIG_FILE = ROOT / "config.yaml"

# Protocol version — bump whenever clinical content changes
PROTOCOL_VERSION = "1.0.0"

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
        "facility_id": "FACILITY-001",
        "emergency_contacts": {
            "ambulance": "999",
            "referral_hospital": "+254 000 000 000",
            "district_health_officer": "+254 000 000 001",
        },
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
        # V1: structured SOAP-aligned system prompt with formulary guard
        "system_prompt": (
            "You are HealthAssist, a clinical decision support tool for community "
            "health workers (CHWs) at primary health centres in Sub-Saharan Africa, "
            "South Asia, and Southeast Asia. Your role is to assist frontline workers "
            "with evidence-based guidance on triage, diagnosis, referral, and treatment "
            "within WHO and national protocol standards.\n\n"
            "CORE PRINCIPLES:\n"
            "1. SAFETY FIRST: Always flag red flag symptoms requiring immediate referral.\n"
            "2. EVIDENCE-BASED: Ground all guidance in WHO IMCI, national formularies, "
            "and established clinical protocols.\n"
            "3. APPROPRIATE SCOPE: You support CHWs — not replace physician judgment. "
            "Recommend escalation when beyond CHW scope.\n"
            "4. STRUCTURED OUTPUT: For every clinical query respond ONLY in this exact "
            "JSON structure (no prose outside the JSON):\n"
            "{\n"
            '  "assessment": "2-3 sentence summary of the clinical picture",\n'
            '  "differentials": ["Differential 1", "Differential 2"],\n'
            '  "actions": ["Action 1 — specific and numbered", "Action 2"],\n'
            '  "red_flags": ["Red flag 1", "Red flag 2"],\n'
            '  "referral": "IMMEDIATE|URGENT|ROUTINE|MONITOR",\n'
            '  "referral_reason": "One sentence explaining referral urgency",\n'
            '  "confidence": "HIGH|MEDIUM|LOW",\n'
            '  "confidence_reason": "One sentence explaining confidence level",\n'
            '  "formulary_note": "null or short note if prescription beyond CHW scope"\n'
            "}\n"
            "5. LANGUAGE: Use clear, simple language appropriate for CHW literacy.\n\n"
            "SAFETY RULES:\n"
            "- Altered consciousness, severe breathing difficulty, signs of shock, "
            "severe malnutrition, convulsions, severe dehydration → "
            "referral: IMMEDIATE in every case.\n"
            "- Never recommend prescription medications beyond the CHW formulary "
            "(amoxicillin, ORS, zinc, paracetamol, artesunate pre-referral, "
            "vitamin A, iron-folate, misoprostol). Flag in formulary_note.\n"
            "- Always include weight-based dosing for paediatric cases.\n"
            "- For maternal health, apply SAFE MOTHERHOOD protocols.\n\n"
            "EVALUATION CONTEXT:\n"
            "This is an EVAH-aligned evaluation tool. The confidence field is used "
            "for Pathway A/B accuracy measurement — calibrate it honestly."
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
            "yellow eyes", "swollen face", "not waking", "limp", "floppy",
        ],
    },
    "theme": {
        "primary_color": "#0F4C81",
        "accent_color": "#00A878",
        "warning_color": "#E85D04",
        "danger_color": "#D62828",
        "surface": "#FFFFFF",
        "bg": "#F0F4F8",
    },
    "evaluation": {
        "enabled": True,
        "pathway": "A",
        "log_sessions": True,
        "capture_ratings": True,
        "anonymize": True,
        "study_id": "EVAH-CDST-001",
        # V1: Pathway B fields
        "arm": "intervention",        # "intervention" | "control"
        "randomisation_unit": "facility",  # "facility" | "worker" | "patient"
        "server_log_url": "",         # POST endpoint — blank = client-side only
        "consent_required": True,
        "consent_text": (
            "This tool is part of a research evaluation. Your de-identified "
            "interactions may be used to assess AI clinical decision support quality. "
            "No patient names or identifiers are recorded. You may withdraw at any time."
        ),
    },
    # V1: CHW formulary (enforced in system prompt + calculator)
    "formulary": {
        "medicines": [
            {"name": "Amoxicillin", "forms": ["250mg/5ml syrup", "500mg tablet"],
             "dosing": "40mg/kg/day divided 3x daily, 5 days"},
            {"name": "Paracetamol", "forms": ["120mg/5ml syrup", "500mg tablet"],
             "dosing": "15mg/kg/dose every 4-6h, max 4 doses/day"},
            {"name": "ORS", "forms": ["1L sachets"],
             "dosing": "50-100ml/kg over 3-4h for moderate dehydration"},
            {"name": "Zinc sulfate", "forms": ["20mg dispersible tablet"],
             "dosing": "<6mo: 10mg/day 10 days; ≥6mo: 20mg/day 10 days"},
            {"name": "Vitamin A", "forms": ["100,000IU capsule", "200,000IU capsule"],
             "dosing": "<12mo: 100,000IU once; ≥12mo: 200,000IU once"},
            {"name": "Artesunate rectal", "forms": ["200mg suppository"],
             "dosing": "10mg/kg single pre-referral dose for severe malaria"},
            {"name": "Iron-folate", "forms": ["60mg/0.4mg tablet"],
             "dosing": "1 tablet daily (pregnancy), 3mo postpartum"},
            {"name": "Misoprostol", "forms": ["200mcg tablet"],
             "dosing": "600mcg oral single dose for PPH prevention"},
        ]
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
    # V1: i18n scaffold
    "i18n": {
        "default_locale": "en",
        "supported_locales": ["en", "sw"],
        "strings": {
            "en": {
                "greeting_label": "Hello",
                "send": "Send",
                "emergency": "Emergency",
                "new_session": "New session",
                "export": "Export session data",
                "consent_title": "Research Consent",
                "consent_agree": "I agree and continue",
                "consent_decline": "Decline (demo mode only)",
                "placeholder": "Describe the patient's symptoms…",
            },
            "sw": {
                "greeting_label": "Habari",
                "send": "Tuma",
                "emergency": "Dharura",
                "new_session": "Kikao kipya",
                "export": "Hamisha data ya kikao",
                "consent_title": "Idhini ya Utafiti",
                "consent_agree": "Nakubaliana na kuendelea",
                "consent_decline": "Kataa (hali ya maonyesho tu)",
                "placeholder": "Elezea dalili za mgonjwa…",
            },
        },
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
        return None
    winner = found[0]
    log.info("✅ Active provider → %s  model=%s",
             winner["name"], winner["model"])
    return winner


def cmd_build():
    cfg = load_config()
    provider = cmd_verify()

    for sub in ["", "static/js", "static/css", "static/data"]:
        (DOCS_DIR / sub).mkdir(parents=True, exist_ok=True)

    # Compute a content hash for cache-busting
    build_hash = hashlib.sha256(
        (PROTOCOL_VERSION + datetime.now(timezone.utc).date().isoformat()).encode()
    ).hexdigest()[:8]

    public_cfg = {
        "app": cfg["app"],
        "bot": {k: v for k, v in cfg["bot"].items() if k != "system_prompt"},
        "theme": cfg["theme"],
        "evaluation": cfg.get("evaluation", {}),
        "protocols": cfg.get("protocols", {}),
        "formulary": cfg.get("formulary", {}),
        "i18n": cfg.get("i18n", {}),
        "provider": {
            "name": provider["name"] if provider else "demo",
            "model": provider["model"] if provider else "none",
            "provider_type": provider.get("provider_type", "openai") if provider else "demo",
        },
        "protocol_version": PROTOCOL_VERSION,
        "build_hash": build_hash,
        "built_at": datetime.now(timezone.utc).isoformat(),
    }
    (DOCS_DIR / "config.json").write_text(
        json.dumps(public_cfg, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    write_protocols_data()
    write_formulary_data(cfg)
    write_i18n_data(cfg)

    token = os.getenv(provider["env_key"], "") if provider else ""
    write_css(cfg)
    write_js(cfg, provider, token, build_hash)
    write_html(cfg, provider, build_hash)
    write_sw(build_hash)
    write_manifest(cfg)

    log.info("✅ Build complete → %s/  [hash=%s]", DOCS_DIR, build_hash)
    for f in ["index.html", "static/js/chat.js", "static/css/chat.css",
              "config.json", "static/data/protocols.json",
              "static/data/formulary.json", "sw.js", "manifest.json"]:
        path = DOCS_DIR / f
        if path.exists():
            log.info("   %s  ✓  (%d bytes)", f, path.stat().st_size)


def cmd_auto():
    cmd_init()
    cmd_build()
    verify_output()


def verify_output():
    required = [
        "index.html", "static/js/chat.js", "static/css/chat.css",
        "config.json", "static/data/protocols.json", "sw.js", "manifest.json",
    ]
    ok = True
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


# ─────────────────────────────────────────────
#  DATA FILES
# ─────────────────────────────────────────────

def write_protocols_data():
    protocols = {
        "version": PROTOCOL_VERSION,
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
            "respiratory_rate_thresholds": {
                "2_to_11_months": "≥50 breaths/min = fast breathing",
                "12_to_59_months": "≥40 breaths/min = fast breathing",
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
            "appetite_test": "RUTF appetite test: pass = eligible for OTP; fail = inpatient care",
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
                "Prostration (cannot sit/stand)",
                "Abnormal bleeding",
            ],
            "severe_action": (
                "Any severe sign → EMERGENCY REFERRAL, "
                "pre-referral artesunate rectal 10mg/kg if available"
            ),
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
                "Prolonged labour (>12h active phase)",
                "Abnormal fetal position at term",
            ],
            "anc_schedule": "8 contacts: booking (<12wk), 20wk, 26wk, 30wk, 34wk, 36wk, 38wk, 40wk",
        },
        "referral_levels": {
            "immediate": "Life-threatening — call ambulance / refer NOW",
            "urgent": "Refer within 2–4 hours",
            "routine": "Refer at next available transport",
            "monitor": "Manage at facility, review in 24–48h",
        },
        "newborn": {
            "title": "Newborn Danger Signs (0–28 days)",
            "danger_signs": [
                "Not feeding well / stopped feeding",
                "Convulsions",
                "Fast breathing (≥60/min)",
                "Severe chest indrawing",
                "Temp <35.5°C or >37.5°C (axillary)",
                "Yellow skin/eyes in first 24h or persisting >2 weeks",
                "Umbilicus red, swollen, or draining pus",
                "Many or severe skin pustules",
            ],
        },
    }
    (DOCS_DIR / "static" / "data" / "protocols.json").write_text(
        json.dumps(protocols, indent=2), encoding="utf-8"
    )


def write_formulary_data(cfg: dict):
    """Write CHW formulary with dosing calculator data."""
    formulary = cfg.get("formulary", DEFAULT_CONFIG["formulary"])
    # Add dosing calculator metadata
    formulary["calculator_note"] = (
        "All doses are for guidance only. Apply clinical judgment. "
        "Refer to national formulary for definitive dosing."
    )
    formulary["version"] = PROTOCOL_VERSION
    (DOCS_DIR / "static" / "data" / "formulary.json").write_text(
        json.dumps(formulary, indent=2), encoding="utf-8"
    )


def write_i18n_data(cfg: dict):
    """Write i18n string bundles."""
    i18n = cfg.get("i18n", DEFAULT_CONFIG["i18n"])
    (DOCS_DIR / "static" / "data" / "i18n.json").write_text(
        json.dumps(i18n, indent=2), encoding="utf-8"
    )


# ─────────────────────────────────────────────
#  SERVICE WORKER  (V1 — PWA offline support)
# ─────────────────────────────────────────────

def write_sw(build_hash: str):
    sw = f"""/* HealthAssist CDST — Service Worker v1  hash={build_hash} */
'use strict';

const CACHE = 'cdst-v{build_hash}';
const OFFLINE_ASSETS = [
  './',
  './index.html',
  './static/css/chat.css',
  './static/js/chat.js',
  './static/data/protocols.json',
  './static/data/formulary.json',
  './static/data/i18n.json',
  './config.json',
  './manifest.json',
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
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
}});

self.addEventListener('fetch', e => {{
  /* Network-first for API calls; cache-first for assets */
  const url = new URL(e.request.url);
  const isAPI = url.hostname !== self.location.hostname;

  if (isAPI) {{
    /* API: network with 10s timeout, no cache fallback */
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

  /* Static assets: cache-first */
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
    (DOCS_DIR / "sw.js").write_text(sw, encoding="utf-8")


def write_manifest(cfg: dict):
    app = cfg["app"]
    t = cfg["theme"]
    manifest = {
        "name": app["name"],
        "short_name": "HealthAssist",
        "description": app["tagline"],
        "start_url": "./",
        "display": "standalone",
        "background_color": t["bg"],
        "theme_color": t["primary_color"],
        "icons": [
            {"src": "static/images/icon-192.png",
                "sizes": "192x192", "type": "image/png"},
            {"src": "static/images/icon-512.png",
                "sizes": "512x512", "type": "image/png"},
        ],
        "categories": ["medical", "health"],
        "lang": cfg.get("i18n", {}).get("default_locale", "en"),
    }
    (DOCS_DIR / "manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )


# ─────────────────────────────────────────────
#  CSS  (unchanged from baseline, minor additions)
# ─────────────────────────────────────────────

def write_css(cfg: dict):
    t = cfg["theme"]
    primary = t["primary_color"]
    accent = t["accent_color"]
    warning = t.get("warning_color", "#E85D04")
    danger = t.get("danger_color", "#D62828")

    css = f"""/* HealthAssist CDST v1 — Auto-generated */
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

/* ── CONSENT OVERLAY (V1) ──────────────────── */
#consent-overlay {{
  position: fixed;
  inset: 0;
  background: rgba(15,76,129,.85);
  z-index: 500;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 1.5rem;
  backdrop-filter: blur(4px);
}}

#consent-overlay.hidden {{ display: none; }}

.consent-card {{
  background: var(--surface);
  border-radius: var(--radius-lg);
  max-width: 520px;
  width: 100%;
  padding: 2rem;
  box-shadow: 0 20px 60px rgba(0,0,0,.35);
}}

.consent-icon {{
  font-size: 2.5rem;
  margin-bottom: 1rem;
}}

.consent-title {{
  font-size: 18px;
  font-weight: 600;
  color: var(--text);
  margin-bottom: .75rem;
}}

.consent-body {{
  font-size: 13.5px;
  color: var(--text-2);
  line-height: 1.7;
  margin-bottom: 1.5rem;
  border-left: 3px solid var(--primary-mid);
  padding-left: 12px;
}}

.consent-study {{
  font-size: 12px;
  font-family: var(--font-mono);
  color: var(--muted);
  margin-bottom: 1.5rem;
}}

.consent-actions {{ display: flex; flex-direction: column; gap: 8px; }}

.consent-btn-primary {{
  width: 100%;
  padding: 12px;
  background: var(--primary);
  color: white;
  border: none;
  border-radius: var(--radius);
  font-size: 14px;
  font-weight: 600;
  font-family: var(--font-body);
  cursor: pointer;
  transition: background var(--transition);
}}

.consent-btn-primary:hover {{ background: color-mix(in srgb, var(--primary) 85%, black); }}

.consent-btn-secondary {{
  width: 100%;
  padding: 10px;
  background: transparent;
  color: var(--muted);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  font-size: 13px;
  font-family: var(--font-body);
  cursor: pointer;
  transition: all var(--transition);
}}

.consent-btn-secondary:hover {{ border-color: var(--primary); color: var(--primary); }}

/* ── DOSING CALCULATOR (V1) ────────────────── */
#dose-panel {{
  position: fixed;
  right: 0;
  top: 64px;
  bottom: 0;
  width: 320px;
  background: var(--surface);
  border-left: 1px solid var(--border-light);
  z-index: 150;
  display: none;
  flex-direction: column;
  box-shadow: -4px 0 20px rgba(15,76,129,.10);
  transform: translateX(100%);
  transition: transform .25s ease;
}}

#dose-panel.open {{
  display: flex;
  transform: translateX(0);
}}

.dose-header {{
  padding: 14px 16px;
  border-bottom: 1px solid var(--border-light);
  font-size: 13px;
  font-weight: 600;
  color: var(--text);
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: var(--primary);
  color: white;
}}

.dose-body {{ flex: 1; overflow-y: auto; padding: 16px; }}

.dose-field {{ margin-bottom: 14px; }}

.dose-label {{
  font-size: 11px;
  font-weight: 600;
  color: var(--muted);
  letter-spacing: .06em;
  text-transform: uppercase;
  margin-bottom: 5px;
  display: block;
}}

.dose-input {{
  width: 100%;
  border: 1.5px solid var(--border);
  border-radius: var(--radius-sm);
  padding: 8px 10px;
  font-size: 14px;
  font-family: var(--font-body);
  outline: none;
  background: var(--bg);
  transition: border-color var(--transition);
}}

.dose-input:focus {{ border-color: var(--primary); background: var(--surface); }}

.dose-select {{
  width: 100%;
  border: 1.5px solid var(--border);
  border-radius: var(--radius-sm);
  padding: 8px 10px;
  font-size: 13.5px;
  font-family: var(--font-body);
  background: var(--bg);
  outline: none;
  cursor: pointer;
}}

.dose-result {{
  background: var(--primary-light);
  border: 1px solid var(--primary-mid);
  border-radius: var(--radius);
  padding: 12px 14px;
  margin-top: 12px;
  font-size: 13.5px;
  line-height: 1.6;
}}

.dose-result .dose-qty {{
  font-size: 20px;
  font-weight: 600;
  color: var(--primary);
  font-family: var(--font-mono);
  display: block;
  margin-bottom: 4px;
}}

.dose-warning {{
  background: var(--warning-light);
  border: 1px solid color-mix(in srgb, var(--warning) 30%, white);
  border-radius: var(--radius-sm);
  padding: 8px 10px;
  font-size: 12px;
  color: color-mix(in srgb, var(--warning) 80%, black);
  margin-top: 8px;
}}

/* ── HEADER ────────────────────────────────── */
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
  width: 38px; height: 38px;
  background: rgba(255,255,255,.15);
  border: 1.5px solid rgba(255,255,255,.30);
  border-radius: var(--radius);
  display: flex; align-items: center; justify-content: center;
  font-size: 18px; flex-shrink: 0;
}}

.header-text {{ min-width: 0; }}

.header-name {{
  font-size: 15px; font-weight: 600; letter-spacing: -.01em;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}}

.header-tagline {{ font-size: 11px; color: rgba(255,255,255,.55); }}

.header-controls {{ display: flex; align-items: center; gap: 8px; flex-shrink: 0; }}

.status-pill {{
  display: flex; align-items: center; gap: 5px;
  background: rgba(255,255,255,.10);
  border: 1px solid rgba(255,255,255,.18);
  padding: 4px 10px; border-radius: 20px;
  font-size: 11.5px; color: rgba(255,255,255,.85); white-space: nowrap;
}}

.status-dot {{
  width: 6px; height: 6px; background: #4ADE80;
  border-radius: 50%; animation: pulse-dot 2.5s ease-in-out infinite;
}}

.status-dot.offline {{ background: #FCA5A5; animation: none; }}

@keyframes pulse-dot {{
  0%, 100% {{ opacity: 1; transform: scale(1); }}
  50% {{ opacity: .5; transform: scale(.8); }}
}}

.model-chip {{
  font-size: 11px; font-family: var(--font-mono);
  background: rgba(255,255,255,.12); border: 1px solid rgba(255,255,255,.18);
  color: rgba(255,255,255,.80); padding: 3px 8px; border-radius: 4px;
}}

.icon-btn {{
  background: rgba(255,255,255,.08); border: 1px solid rgba(255,255,255,.15);
  color: rgba(255,255,255,.80); width: 34px; height: 34px;
  border-radius: var(--radius-sm); cursor: pointer;
  display: flex; align-items: center; justify-content: center;
  transition: background var(--transition);
}}

.icon-btn:hover {{ background: rgba(255,255,255,.18); }}

/* ── SAFETY BANNER ─────────────────────────── */
#safety-banner {{
  padding: 7px 1.25rem; font-size: 12px;
  display: flex; align-items: center; gap: 8px;
  border-bottom: 1px solid; font-weight: 500;
}}

#safety-banner.status-live {{ background: var(--accent-light); border-color: color-mix(in srgb, var(--accent) 30%, white); color: color-mix(in srgb, var(--accent) 80%, black); }}
#safety-banner.status-demo {{ background: var(--warning-light); border-color: color-mix(in srgb, var(--warning) 30%, white); color: color-mix(in srgb, var(--warning) 80%, black); }}
#safety-banner.status-emergency {{ background: var(--danger-light); border-color: color-mix(in srgb, var(--danger) 40%, white); color: var(--danger); animation: blink-border 1s ease-in-out infinite; }}

@keyframes blink-border {{
  0%, 100% {{ background: var(--danger-light); }}
  50% {{ background: color-mix(in srgb, var(--danger) 18%, white); }}
}}

/* ── LAYOUT ────────────────────────────────── */
.app-body {{
  display: flex; flex: 1; overflow: hidden;
  height: calc(100vh - 64px - 37px);
}}

#sidebar {{
  width: 260px; background: var(--surface);
  border-right: 1px solid var(--border-light);
  display: flex; flex-direction: column; overflow: hidden;
  transition: width var(--transition); flex-shrink: 0;
}}

#sidebar.collapsed {{ width: 0; }}

.sidebar-header {{
  padding: 14px 16px; border-bottom: 1px solid var(--border-light);
  font-size: 11px; font-weight: 600; color: var(--muted);
  letter-spacing: .08em; text-transform: uppercase;
  display: flex; align-items: center; justify-content: space-between;
}}

.protocol-list {{ overflow-y: auto; flex: 1; padding: 8px; }}

.protocol-item {{
  padding: 10px 12px; border-radius: var(--radius-sm);
  cursor: pointer; margin-bottom: 2px;
  transition: background var(--transition);
  border: 1px solid transparent;
}}

.protocol-item:hover {{ background: var(--primary-light); border-color: var(--primary-mid); }}

.protocol-title {{ font-size: 13px; font-weight: 500; color: var(--text); display: flex; align-items: center; gap: 7px; }}

.protocol-badge {{ font-size: 10px; background: var(--danger); color: white; padding: 1px 6px; border-radius: 10px; font-weight: 600; }}
.protocol-badge.green {{ background: var(--accent); }}
.protocol-badge.orange {{ background: var(--warning); }}

.protocol-sub {{ font-size: 11.5px; color: var(--muted); margin-top: 2px; }}
.sidebar-divider {{ height: 1px; background: var(--border-light); margin: 6px 8px; }}

/* ── CHAT COLUMN ───────────────────────────── */
#chat-col {{ flex: 1; display: flex; flex-direction: column; overflow: hidden; min-width: 0; }}

#chat-container {{
  flex: 1; overflow-y: auto; padding: 1.25rem 1rem;
  display: flex; flex-direction: column; gap: 1rem; scroll-behavior: smooth;
}}

/* ── MESSAGES ──────────────────────────────── */
.message {{ display: flex; gap: 10px; max-width: 86%; animation: msg-in .2s ease; }}

@keyframes msg-in {{ from {{ opacity: 0; transform: translateY(6px); }} to {{ opacity: 1; transform: translateY(0); }} }}

.message.user {{ align-self: flex-end; flex-direction: row-reverse; }}
.message.bot {{ align-self: flex-start; }}
.message.system {{ align-self: center; max-width: 100%; }}

.msg-avatar {{
  width: 32px; height: 32px; border-radius: 8px; flex-shrink: 0;
  display: flex; align-items: center; justify-content: center;
  font-size: 14px; font-weight: 600; margin-top: 2px;
}}

.message.bot  .msg-avatar {{ background: var(--primary); color: white; }}
.message.user .msg-avatar {{ background: var(--accent);  color: white; font-size: 11px; }}

.msg-body {{ display: flex; flex-direction: column; min-width: 0; }}

.msg-bubble {{
  padding: 11px 14px; border-radius: var(--radius);
  font-size: 14px; line-height: 1.65; word-break: break-word;
}}

.message.bot .msg-bubble {{ background: var(--surface); color: var(--text); border: 1px solid var(--border-light); border-bottom-left-radius: 3px; box-shadow: var(--shadow-sm); }}
.message.user .msg-bubble {{ background: var(--primary); color: white; border-bottom-right-radius: 3px; }}
.message.system .msg-bubble {{ background: transparent; border: 1px dashed var(--border); color: var(--muted); font-size: 12.5px; text-align: center; border-radius: var(--radius); padding: 7px 14px; box-shadow: none; }}
.message.emergency .msg-bubble {{ background: var(--danger-light); border: 1.5px solid var(--danger); color: var(--text); }}
.message.emergency .msg-avatar {{ background: var(--danger); }}

/* ── STRUCTURED CLINICAL CARD (V1) ─────────── */
.clinical-card {{
  background: var(--surface); border: 1px solid var(--border-light);
  border-radius: var(--radius); overflow: hidden; margin-top: 0;
  box-shadow: var(--shadow-sm);
}}

.clinical-section {{ padding: 10px 14px; border-bottom: 1px solid var(--border-light); }}
.clinical-section:last-child {{ border-bottom: none; }}

.clinical-section-label {{
  font-size: 10.5px; font-weight: 600; letter-spacing: .07em;
  text-transform: uppercase; color: var(--muted); margin-bottom: 5px;
  display: flex; align-items: center; gap: 5px;
}}

.clinical-section-label.danger {{ color: var(--danger); }}
.clinical-section-label.warning {{ color: var(--warning); }}
.clinical-section-label.success {{ color: var(--accent); }}

.clinical-content {{ font-size: 13.5px; line-height: 1.6; }}
.tag-list {{ display: flex; flex-wrap: wrap; gap: 5px; margin-top: 5px; }}
.tag {{ font-size: 12px; padding: 3px 9px; border-radius: 20px; font-weight: 500; }}
.tag.red {{ background: var(--danger-light); color: var(--danger); border: 1px solid color-mix(in srgb, var(--danger) 25%, white); }}
.tag.green {{ background: var(--accent-light); color: color-mix(in srgb, var(--accent) 80%, black); border: 1px solid color-mix(in srgb, var(--accent) 25%, white); }}
.tag.blue {{ background: var(--primary-light); color: var(--primary); border: 1px solid var(--primary-mid); }}
.tag.orange {{ background: var(--warning-light); color: var(--warning); border: 1px solid color-mix(in srgb, var(--warning) 25%, white); }}

.referral-badge {{
  display: inline-flex; align-items: center; gap: 6px;
  padding: 6px 12px; border-radius: var(--radius-sm);
  font-size: 13px; font-weight: 600; margin-top: 6px;
}}

.referral-badge.immediate {{ background: var(--danger); color: white; }}
.referral-badge.urgent {{ background: var(--warning); color: white; }}
.referral-badge.routine {{ background: var(--accent); color: white; }}
.referral-badge.monitor {{ background: var(--primary-light); color: var(--primary); }}

/* ── FOLLOW-UP CAPTURE (V1) ────────────────── */
.followup-form {{
  background: var(--bg); border: 1px solid var(--border-light);
  border-radius: var(--radius-sm); padding: 10px 12px; margin-top: 8px;
  font-size: 12.5px;
}}

.followup-row {{ display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }}

.followup-input {{
  border: 1px solid var(--border); border-radius: 4px; padding: 5px 8px;
  font-size: 12px; font-family: var(--font-body); background: var(--surface);
  outline: none; flex: 1; min-width: 100px;
}}

.followup-btn {{
  background: var(--primary); color: white; border: none; border-radius: 4px;
  padding: 5px 10px; font-size: 12px; font-family: var(--font-body); cursor: pointer;
}}

/* ── FEEDBACK WIDGET ───────────────────────── */
.msg-feedback {{
  display: flex; align-items: center; gap: 6px;
  margin-top: 6px; font-size: 11.5px; color: var(--muted);
}}

.feedback-btn {{
  background: none; border: 1px solid var(--border); border-radius: 4px;
  padding: 2px 7px; cursor: pointer; font-size: 12px; color: var(--muted);
  transition: all var(--transition); font-family: var(--font-body);
}}

.feedback-btn:hover {{ border-color: var(--primary); color: var(--primary); }}
.feedback-btn.active {{ background: var(--primary-light); border-color: var(--primary); color: var(--primary); }}

.confidence-chip {{
  font-family: var(--font-mono); font-size: 10.5px; padding: 2px 6px;
  border-radius: 3px; border: 1px solid var(--border); color: var(--muted);
}}

.confidence-chip.HIGH {{ border-color: var(--accent); color: var(--accent); }}
.confidence-chip.MEDIUM {{ border-color: var(--warning); color: var(--warning); }}
.confidence-chip.LOW {{ border-color: var(--danger); color: var(--danger); }}

/* ── TYPING ────────────────────────────────── */
.typing-indicator {{
  display: flex; align-items: center; gap: 4px; padding: 12px 14px;
  background: var(--surface); border: 1px solid var(--border-light);
  border-radius: var(--radius); border-bottom-left-radius: 3px; width: fit-content;
}}

.typing-dot {{ width: 6px; height: 6px; background: var(--muted); border-radius: 50%; animation: typing-bounce 1.2s ease-in-out infinite; }}
.typing-dot:nth-child(2) {{ animation-delay: .2s; }}
.typing-dot:nth-child(3) {{ animation-delay: .4s; }}

@keyframes typing-bounce {{ 0%, 80%, 100% {{ transform: translateY(0); opacity: .5; }} 40% {{ transform: translateY(-5px); opacity: 1; }} }}

/* ── QUICK REPLIES ─────────────────────────── */
.quick-replies {{ display: flex; flex-wrap: wrap; gap: 7px; padding: 2px 0 8px 42px; animation: msg-in .25s ease; }}

.quick-btn {{
  background: var(--surface); border: 1.5px solid var(--border); color: var(--primary);
  padding: 6px 12px; border-radius: 20px; font-size: 12.5px;
  font-family: var(--font-body); font-weight: 500; cursor: pointer;
  transition: all var(--transition); white-space: nowrap;
}}

.quick-btn:hover {{ background: var(--primary-light); border-color: var(--primary); }}

/* ── META ──────────────────────────────────── */
.msg-meta {{ font-size: 10.5px; color: var(--muted); margin-top: 4px; display: flex; align-items: center; gap: 6px; }}
.message.user .msg-meta {{ justify-content: flex-end; }}

/* ── OFFLINE QUEUE BADGE (V1) ──────────────── */
.offline-badge {{
  display: inline-flex; align-items: center; gap: 5px; font-size: 11.5px;
  background: var(--warning-light); color: color-mix(in srgb, var(--warning) 80%, black);
  border: 1px solid color-mix(in srgb, var(--warning) 30%, white);
  padding: 3px 8px; border-radius: 20px; margin-top: 4px;
}}

/* ── INPUT BAR ─────────────────────────────── */
#input-bar {{ background: var(--surface); border-top: 1px solid var(--border-light); padding: .75rem 1rem; box-shadow: 0 -2px 12px rgba(15,76,129,.06); }}

.input-inner {{ display: flex; gap: 8px; align-items: flex-end; max-width: 900px; margin: 0 auto; }}

#user-input {{
  flex: 1; border: 1.5px solid var(--border); border-radius: var(--radius);
  padding: 9px 14px; font-size: 14px; font-family: var(--font-body); outline: none;
  background: var(--bg); color: var(--text); resize: none; max-height: 120px; line-height: 1.5;
  transition: border-color var(--transition), box-shadow var(--transition);
}}

#user-input:focus {{ border-color: var(--primary); box-shadow: 0 0 0 3px var(--primary-light); background: var(--surface); }}
#user-input::placeholder {{ color: var(--muted); }}

.input-actions {{ display: flex; gap: 6px; }}

#send-btn {{
  width: 40px; height: 40px; border-radius: var(--radius-sm); background: var(--primary);
  border: none; color: white; cursor: pointer; display: flex; align-items: center;
  justify-content: center; transition: background var(--transition), transform var(--transition);
  flex-shrink: 0; box-shadow: 0 2px 6px rgba(15,76,129,.30);
}}

#send-btn:hover {{ background: color-mix(in srgb, var(--primary) 85%, black); }}
#send-btn:active {{ transform: scale(.94); }}
#send-btn:disabled {{ background: var(--border); cursor: not-allowed; box-shadow: none; }}

#emergency-btn {{
  height: 40px; padding: 0 12px; border-radius: var(--radius-sm);
  background: var(--danger); border: none; color: white; cursor: pointer;
  font-size: 12px; font-weight: 600; font-family: var(--font-body);
  display: flex; align-items: center; gap: 5px; transition: background var(--transition);
  white-space: nowrap;
}}

#emergency-btn:hover {{ background: color-mix(in srgb, var(--danger) 85%, black); }}

#dose-btn {{
  height: 40px; padding: 0 10px; border-radius: var(--radius-sm);
  background: var(--surface); border: 1.5px solid var(--border); color: var(--text-2);
  cursor: pointer; font-size: 12px; font-family: var(--font-body);
  display: flex; align-items: center; gap: 5px; transition: all var(--transition);
  white-space: nowrap;
}}

#dose-btn:hover {{ border-color: var(--primary); color: var(--primary); }}

/* ── MODAL ─────────────────────────────────── */
#modal-overlay {{
  display: none; position: fixed; inset: 0;
  background: rgba(0,0,0,.35); z-index: 300;
  align-items: center; justify-content: center;
  padding: 1rem; backdrop-filter: blur(3px);
}}

#modal-overlay.open {{ display: flex; }}

.modal {{
  background: var(--surface); border-radius: var(--radius-lg);
  box-shadow: var(--shadow-lg); max-width: 520px; width: 100%;
  max-height: 80vh; overflow-y: auto; animation: modal-in .2s ease;
}}

@keyframes modal-in {{ from {{ opacity: 0; transform: scale(.96) translateY(10px); }} to {{ opacity: 1; transform: scale(1) translateY(0); }} }}

.modal-header {{
  padding: 18px 20px 14px; border-bottom: 1px solid var(--border-light);
  display: flex; align-items: center; justify-content: space-between;
  position: sticky; top: 0; background: var(--surface);
}}

.modal-title {{ font-size: 16px; font-weight: 600; }}
.modal-close {{ background: none; border: none; color: var(--muted); cursor: pointer; font-size: 20px; padding: 2px 6px; border-radius: 4px; transition: color var(--transition); }}
.modal-close:hover {{ color: var(--text); }}
.modal-body {{ padding: 16px 20px 20px; }}
.protocol-section {{ margin-bottom: 18px; }}
.protocol-section-title {{ font-size: 12px; font-weight: 600; color: var(--muted); letter-spacing: .06em; text-transform: uppercase; margin-bottom: 8px; }}
.protocol-list-item {{ display: flex; align-items: flex-start; gap: 8px; padding: 6px 0; border-bottom: 1px solid var(--border-light); font-size: 13.5px; }}
.protocol-list-item:last-child {{ border-bottom: none; }}
.protocol-bullet {{ width: 7px; height: 7px; border-radius: 50%; background: var(--danger); flex-shrink: 0; margin-top: 6px; }}
.protocol-bullet.green {{ background: var(--accent); }}
.protocol-bullet.orange {{ background: var(--warning); }}

/* ── EVALUATION PANEL ──────────────────────── */
#eval-panel {{
  width: 280px; background: var(--surface);
  border-left: 1px solid var(--border-light);
  overflow-y: auto; flex-shrink: 0; padding: 14px;
  display: none; flex-direction: column; gap: 14px;
}}

#eval-panel.open {{ display: flex; }}

.eval-title {{ font-size: 11px; font-weight: 600; color: var(--muted); letter-spacing: .08em; text-transform: uppercase; padding-bottom: 10px; border-bottom: 1px solid var(--border-light); }}
.eval-stat {{ display: flex; justify-content: space-between; align-items: center; padding: 6px 0; font-size: 13px; border-bottom: 1px solid var(--border-light); }}
.eval-stat-val {{ font-family: var(--font-mono); font-size: 13px; font-weight: 600; color: var(--primary); }}
.eval-tag {{ display: inline-flex; align-items: center; gap: 4px; background: var(--primary-light); border: 1px solid var(--primary-mid); color: var(--primary); padding: 4px 9px; border-radius: 4px; font-size: 11.5px; font-weight: 500; margin-bottom: 4px; margin-right: 4px; }}

/* ── EMERGENCY OVERLAY ─────────────────────── */
#emergency-overlay {{
  display: none; position: fixed; inset: 0;
  background: rgba(214,40,40,.08); z-index: 100; pointer-events: none;
  border: 4px solid var(--danger); animation: emergency-pulse 1s ease-in-out infinite;
}}

#emergency-overlay.active {{ display: block; }}

@keyframes emergency-pulse {{ 0%, 100% {{ opacity: 1; }} 50% {{ opacity: .4; }} }}

/* ── SCROLLBAR ─────────────────────────────── */
::-webkit-scrollbar {{ width: 5px; }}
::-webkit-scrollbar-track {{ background: transparent; }}
::-webkit-scrollbar-thumb {{ background: var(--border); border-radius: 10px; }}
::-webkit-scrollbar-thumb:hover {{ background: var(--muted); }}

/* ── RESPONSIVE ────────────────────────────── */
@media (max-width: 768px) {{
  #sidebar {{ display: none; }}
  #eval-panel {{ display: none !important; }}
  .model-chip {{ display: none; }}
  .message {{ max-width: 95%; }}
  #dose-panel {{ width: 100%; }}
}}

@media print {{
  header, #input-bar, #sidebar, #eval-panel, .quick-replies,
  .feedback-btn, #safety-banner, #consent-overlay {{ display: none !important; }}
  .msg-bubble {{ border: 1px solid #ccc !important; box-shadow: none !important; }}
  body {{ background: white; }}
}}

.sr-only {{ position: absolute; width: 1px; height: 1px; padding: 0; margin: -1px; overflow: hidden; clip: rect(0,0,0,0); white-space: nowrap; border: 0; }}
strong {{ font-weight: 600; }}
"""
    (DOCS_DIR / "static" / "css" / "chat.css").write_text(css, encoding="utf-8")


# ─────────────────────────────────────────────
#  JAVASCRIPT  — Full V1 CDST Logic
# ─────────────────────────────────────────────

def write_js(cfg: dict, provider: dict | None, token: str, build_hash: str):
    bot = cfg["bot"]
    app = cfg["app"]
    eval_cfg = cfg.get("evaluation", {})
    formulary = cfg.get("formulary", DEFAULT_CONFIG["formulary"])
    i18n_cfg = cfg.get("i18n", DEFAULT_CONFIG["i18n"])
    emergency_contacts = app.get("emergency_contacts", {})

    quick_json = json.dumps(bot["quick_replies"], ensure_ascii=False)
    safety_kw_json = json.dumps(
        bot.get("safety_keywords", []), ensure_ascii=False)
    system = (bot["system_prompt"]
              .replace("\\", "\\\\")
              .replace("`", "\\`")
              .replace("\n", "\\n"))
    greeting = (bot["greeting"]
                .replace("\\", "\\\\")
                .replace("`", "\\`")
                .replace("\n", "\\n"))

    provider_type = provider.get(
        "provider_type", "openai") if provider else "demo"
    endpoint = provider["endpoint"] if provider else ""
    model_id = provider["model"] if provider else "demo"
    provider_name = provider["name"] if provider else "demo"
    auth_header = provider.get(
        "auth_header", "Bearer") if provider else "Bearer"
    api_version = provider.get("api_version", "") if provider else ""
    safe_token = token.replace("\\", "\\\\").replace(
        "`", "\\`") if token else ""

    study_id = eval_cfg.get("study_id", "EVAH-CDST-001")
    eval_enabled = str(eval_cfg.get("enabled", True)).lower()
    consent_required = str(eval_cfg.get("consent_required", True)).lower()
    consent_text = (eval_cfg.get("consent_text", "")
                    .replace("\\", "\\\\").replace("`", "\\`"))
    server_log_url = eval_cfg.get("server_log_url", "")
    pathway = eval_cfg.get("pathway", "A")
    arm = eval_cfg.get("arm", "intervention")
    facility_id = app.get("facility_id", "FACILITY-001")
    formulary_json = json.dumps(formulary.get(
        "medicines", []), ensure_ascii=False)
    i18n_json = json.dumps(i18n_cfg.get("strings", {}), ensure_ascii=False)
    default_locale = i18n_cfg.get("default_locale", "en")
    emergency_json = json.dumps(emergency_contacts, ensure_ascii=False)
    built = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    protocol_version = PROTOCOL_VERSION

    js = f"""/* HealthAssist CDST v1 — Auto-generated */
/* EVAH-Aligned Clinical Decision Support Tool */
/* Provider: {provider_name} | Model: {model_id} | Built: {built} | Hash: {build_hash} */

'use strict';

// ─── PROVIDER CONFIG ─────────────────────────────────────────────────────
const PROVIDER = {{
  token:      `{safe_token}`,
  endpoint:   `{endpoint}`,
  model:      `{model_id}`,
  name:       `{provider_name}`,
  authHeader: `{auth_header}`,
  apiVersion: `{api_version}`,
  type:       `{provider_type}`,
}};

// ─── BOT CONFIG ──────────────────────────────────────────────────────────
const BOT_CONFIG = {{
  system:          `{system}`,
  greeting:        `{greeting}`,
  quickReplies:    {quick_json},
  safetyKeywords:  {safety_kw_json},
}};

// ─── EVALUATION CONFIG ───────────────────────────────────────────────────
const EVAL = {{
  enabled:          {eval_enabled},
  studyId:          '{study_id}',
  pathway:          '{pathway}',
  arm:              '{arm}',
  facilityId:       '{facility_id}',
  protocolVersion:  '{protocol_version}',
  buildHash:        '{build_hash}',
  consentRequired:  {consent_required},
  consentText:      `{consent_text}`,
  serverLogUrl:     `{server_log_url}`,
  sessionId:        _genSessionId(),
  consentGiven:     false,
  log:              [],
}};

// ─── FORMULARY ───────────────────────────────────────────────────────────
const FORMULARY = {formulary_json};

// ─── I18N ────────────────────────────────────────────────────────────────
const I18N_STRINGS = {i18n_json};
let LOCALE = navigator.language?.startsWith('sw') ? 'sw' : '{default_locale}';
function t(key) {{ return (I18N_STRINGS[LOCALE] || I18N_STRINGS['{default_locale}'] || {{}})[key] || key; }}

// ─── EMERGENCY CONTACTS ──────────────────────────────────────────────────
const EMERGENCY_CONTACTS = {emergency_json};

// ─── OFFLINE QUEUE (V1) ──────────────────────────────────────────────────
let offlineQueue = [];
let isOnline = navigator.onLine;

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
    offlineQueue = [...batch, ...offlineQueue]; // re-queue
  }}
}}

// ─── STATE ───────────────────────────────────────────────────────────────
let history      = [];
let busy         = false;
let msgCounter   = 0;
let emergencyMode = false;
let protocolData = null;

// ─── HELPERS ─────────────────────────────────────────────────────────────
function _genSessionId() {{
  const raw = (crypto.randomUUID ? crypto.randomUUID() : Math.random().toString(36).slice(2));
  // Chain hash for audit trail integrity
  return raw;
}}

function _hashChain(prev, data) {{
  // Simple client-side hash chain — not cryptographic, but provides audit trail
  return btoa(prev.slice(-8) + JSON.stringify(data)).slice(0, 16);
}}

// ─── INIT ────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', async () => {{
  // Register service worker (PWA)
  if ('serviceWorker' in navigator) {{
    navigator.serviceWorker.register('./sw.js').catch(e => console.warn('SW:', e));
  }}

  if (EVAL.consentRequired) {{
    showConsentScreen();
  }} else {{
    initApp();
  }}
}});

function initApp() {{
  renderProviderBanner();
  showGreeting();
  loadProtocols();
  setupEvalPanel();
  updateEvalStats();
  updateConnectionStatus();
  loadLocaleFromStorage();

  const inp = document.getElementById('user-input');
  inp?.addEventListener('keydown', e => {{
    if (e.key === 'Enter' && !e.shiftKey) {{ e.preventDefault(); send(); }}
  }});
  inp?.addEventListener('input', autoResize);
}};

function autoResize() {{
  const el = document.getElementById('user-input');
  el.style.height = 'auto';
  el.style.height = Math.min(el.scrollHeight, 120) + 'px';
}};

// ─── CONSENT SCREEN (V1) ─────────────────────────────────────────────────
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
  EVAL.consentGiven = true;
  EVAL.consentTimestamp = new Date().toISOString();
  document.getElementById('consent-overlay')?.classList.add('hidden');
  initApp();
  logEvalEvent({{ type: 'consent', given: true, ts: EVAL.consentTimestamp }});
}}

function declineConsent() {{
  EVAL.consentGiven = false;
  document.getElementById('consent-overlay')?.classList.add('hidden');
  initApp();
  // Demo mode — disable eval logging
  EVAL.enabled = false;
  logEvalEvent({{ type: 'consent', given: false }});
}}

// ─── BANNER ──────────────────────────────────────────────────────────────
function renderProviderBanner() {{
  const el = document.getElementById('safety-banner');
  if (!el) return;
  const dot = document.getElementById('status-dot');
  const modelChip = document.getElementById('model-chip');
  if (modelChip) modelChip.textContent = PROVIDER.model;

  if (!PROVIDER.token || PROVIDER.name === 'demo') {{
    el.className = 'status-demo';
    el.innerHTML = '⚠️ &nbsp;Demo mode — set <strong>ANTHROPIC_API_KEY</strong> or another API key in GitHub Secrets.';
    if (dot) dot.className = 'status-dot offline';
  }} else {{
    el.className = 'status-live';
    const labels = {{ anthropic: 'Anthropic Claude', openai: 'OpenAI', github: 'GitHub Models', groq: 'Groq', mistral: 'Mistral' }};
    const label = labels[PROVIDER.name] || PROVIDER.name;
    el.innerHTML = `✅ &nbsp;Live — <strong>${{label}}</strong> · ${{PROVIDER.model}} · ${{EVAL.facilityId}} · Session: <code style="font-size:10px">${{EVAL.sessionId.slice(0,8)}}</code>`;
  }}
}};

// ─── GREETING ────────────────────────────────────────────────────────────
function showGreeting() {{
  addMsg('bot', BOT_CONFIG.greeting, {{ noFeedback: true }});
  setTimeout(renderQuickReplies, 400);
}}

// ─── SAFETY DETECTOR ─────────────────────────────────────────────────────
function detectEmergency(text) {{
  const lower = text.toLowerCase();
  return BOT_CONFIG.safetyKeywords.some(kw => lower.includes(kw));
}}

function setEmergencyMode(on) {{
  emergencyMode = on;
  const overlay = document.getElementById('emergency-overlay');
  const banner  = document.getElementById('safety-banner');
  const amb = EMERGENCY_CONTACTS.ambulance || '999';
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

// ─── STRUCTURED CLINICAL RESPONSE PARSER (V1) ────────────────────────────
function parseClinicalJSON(text) {{
  // Try to extract JSON from the response
  const jsonMatch = text.match(/\\{{[\\s\\S]*\\}}/);
  if (!jsonMatch) return null;
  try {{
    return JSON.parse(jsonMatch[0]);
  }} catch (e) {{
    return null;
  }}
}}

function renderClinicalCard(data) {{
  const refClass = {{
    IMMEDIATE: 'immediate', URGENT: 'urgent',
    ROUTINE: 'routine', MONITOR: 'monitor',
  }}[data.referral] || 'monitor';

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

  const flagsHtml = (data.red_flags || []).map(f =>
    `<span class="tag red">${{esc(f)}}</span>`
  ).join('');

  const diffsHtml = (data.differentials || []).map(d =>
    `<span class="tag blue">${{esc(d)}}</span>`
  ).join('');

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
    ${{flagsHtml ? `<div class="clinical-section"><div class="clinical-section-label danger">⚠ Red flags</div><div class="tag-list">${{flagsHtml}}</div></div>` : ''}}
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

// ─── MESSAGE RENDERING ───────────────────────────────────────────────────
function addMsg(role, text, opts = {{}}) {{
  const c = document.getElementById('chat-container');
  if (!c) return;

  const id  = 'msg-' + (++msgCounter);
  const w   = document.createElement('div');
  const ts  = new Date().toLocaleTimeString([], {{ hour: '2-digit', minute: '2-digit' }});

  // Try structured clinical JSON parse first (V1)
  let bubbleContent;
  let clinicalData = null;
  if (role === 'bot' && !opts.noFeedback) {{
    clinicalData = parseClinicalJSON(text);
  }}

  const isEmergency = role === 'bot' && (
    clinicalData?.referral === 'IMMEDIATE' ||
    text.includes('EMERGENCY REFERRAL') ||
    text.includes('REFER URGENTLY') ||
    opts.emergency === true
  );

  if (isEmergency) setEmergencyMode(true);

  w.id = id;
  w.className = 'message ' + role + (isEmergency ? ' emergency' : '');

  const avatar = role === 'bot' ? '🏥' : (role === 'user' ? 'CHW' : '');

  if (clinicalData) {{
    bubbleContent = renderClinicalCard(clinicalData);
  }} else {{
    bubbleContent = role === 'bot'
      ? formatBotText(text)
      : esc(text).replace(/\\n/g, '<br>');
  }}

  const confidence = clinicalData?.confidence || extractConfidence(text);

  let feedbackHtml = '';
  if (role === 'bot' && !opts.noFeedback) {{
    feedbackHtml = `
      <div class="msg-feedback">
        <button class="feedback-btn" onclick="rateMsgAccuracy('${{id}}', 'accurate')" title="Mark as accurate">✓ Accurate</button>
        <button class="feedback-btn" onclick="rateMsgAccuracy('${{id}}', 'inaccurate')" title="Mark as inaccurate">✗ Inaccurate</button>
        <button class="feedback-btn" onclick="rateMsgAccuracy('${{id}}', 'escalate')" title="Escalate for specialist review">⬆ Review</button>
        ${{confidence ? `<span class="confidence-chip ${{confidence}}">${{confidence}}</span>` : ''}}
      </div>
      <div class="followup-form">
        <div style="font-size:11px;color:var(--muted);margin-bottom:6px;font-weight:600">Schedule follow-up</div>
        <div class="followup-row">
          <input type="date" class="followup-input" id="fu-date-${{id}}" min="${{new Date().toISOString().split('T')[0]}}">
          <input type="text" class="followup-input" id="fu-reason-${{id}}" placeholder="Reason…" style="flex:2">
          <button class="followup-btn" onclick="saveFollowUp('${{id}}')">Save</button>
        </div>
      </div>`;
  }}

  w.innerHTML = `
    <div class="msg-avatar">${{avatar}}</div>
    <div class="msg-body">
      <div class="msg-bubble">${{bubbleContent}}</div>
      <div class="msg-meta">
        <span>${{ts}}</span>
        ${{isEmergency ? '<span class="text-danger" style="font-weight:600;color:var(--danger)">⚠ EMERGENCY</span>' : ''}}
        ${{!isOnline ? '<span class="offline-badge">📡 Offline</span>' : ''}}
      </div>
      ${{feedbackHtml}}
    </div>`;

  c.appendChild(w);
  c.scrollTop = c.scrollHeight;

  if (EVAL.enabled) {{
    const entry = {{
      t: Date.now(),
      role,
      len: text.length,
      emergency: isEmergency,
      referral: clinicalData?.referral || null,
      confidence: clinicalData?.confidence || confidence || null,
      feedback: null,
      followUp: null,
      msgId: id,
      chainHash: null,
    }};
    // Hash chain for audit trail integrity
    const prev = EVAL.log.length ? EVAL.log[EVAL.log.length - 1].chainHash || '' : '';
    entry.chainHash = _hashChain(prev, entry);
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
  const entry  = EVAL.log.find(e => e.msgId === msgId);
  if (entry) entry.followUp = {{ date, reason, savedAt: new Date().toISOString() }};
  const btn = document.querySelector(`#${{msgId}} .followup-btn`);
  if (btn) {{ btn.textContent = '✓'; btn.style.background = 'var(--accent)'; btn.disabled = true; }}
  updateEvalStats();
}}

function extractConfidence(text) {{
  if (/confidence.*HIGH|HIGH.*confidence/i.test(text)) return 'HIGH';
  if (/confidence.*MEDIUM|MEDIUM.*confidence/i.test(text)) return 'MEDIUM';
  if (/confidence.*LOW|LOW.*confidence/i.test(text)) return 'LOW';
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
             '<span style="color:var(--danger);font-weight:700">⚠ $1</span>');
}}

// ─── SEND WITH RETRY (V1) ────────────────────────────────────────────────
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
      // Queue for when back online, use demo
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
    addMsg('bot',
      `⚠️ Connection error: ${{esc(err.message || 'Unknown error')}}\\n\\n` +
      `Please check your connection. For emergencies call directly: ${{amb}}`
    );
    console.error('[HealthAssist CDST]', err);
  }}

  busy = false;
  if (sendBtn) sendBtn.disabled = false;
  inp?.focus();
}}

// ─── API WITH RETRY + TIMEOUT (V1) ──────────────────────────────────────
async function callAIWithRetry(maxRetries = 2, timeoutMs = 15000) {{
  let lastErr;
  for (let attempt = 0; attempt <= maxRetries; attempt++) {{
    try {{
      const controller = new AbortController();
      const timer = setTimeout(() => controller.abort(), timeoutMs);
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
        await sleep(1000 * (attempt + 1)); // exponential back-off
        console.warn(`[CDST] Retry ${{attempt + 1}}/${{maxRetries}}`);
      }}
    }}
  }}
  throw lastErr;
}}

async function callAI(signal) {{
  if (PROVIDER.type === 'anthropic') return callAnthropic(signal);
  return callOpenAICompat(signal);
}}

async function callAnthropic(signal) {{
  const messages = history.map(m => ({{
    role: m.role === 'assistant' ? 'assistant' : 'user',
    content: m.content,
  }}));

  const res = await fetch(PROVIDER.endpoint, {{
    method: 'POST',
    signal,
    headers: {{
      'Content-Type':          'application/json',
      'x-api-key':             PROVIDER.token,
      'anthropic-version':     PROVIDER.apiVersion || '2023-06-01',
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

async function callOpenAICompat(signal) {{
  const res = await fetch(PROVIDER.endpoint, {{
    method: 'POST',
    signal,
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
      temperature: 0.2,  // Lower for clinical accuracy
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
  await sleep(700 + Math.random() * 400);
  const t = text.toLowerCase();

  if (t.includes('fever') || t.includes('malaria') || t.includes('temperature')) {{
    return JSON.stringify({{
      assessment: "Child presenting with fever in a malaria-endemic setting. Systematic IMCI assessment required before treatment.",
      differentials: ["Uncomplicated malaria", "Bacterial infection (pneumonia, UTI)", "Viral illness", "Meningitis (if stiff neck)"],
      actions: [
        "Measure temperature (axillary) — document reading",
        "Check ALL IMCI danger signs: drinking ability, vomiting, convulsions, lethargy",
        "Perform malaria RDT if available and child in endemic zone",
        "Assess respiratory rate vs age-specific threshold",
        "Check for stiff neck and bulging fontanelle",
        "Document weight for weight-based dosing"
      ],
      red_flags: ["Cannot drink or breastfeed", "Had convulsions", "Lethargic or unconscious", "Stiff neck", "Severe respiratory distress"],
      referral: "URGENT",
      referral_reason: "Fever with any danger sign requires urgent facility assessment within 2–4h.",
      confidence: "MEDIUM",
      confidence_reason: "Demo mode — limited patient context. Confidence would be higher with full symptom history.",
      formulary_note: "If RDT positive: ACT per national protocol (artemether-lumefantrine). Paracetamol 15mg/kg/dose for fever ≥38.5°C."
    }});
  }}

  if (t.includes('malnutrition') || t.includes('muac') || t.includes('wasting')) {{
    return JSON.stringify({{
      assessment: "Child presenting for nutritional assessment. MUAC measurement is the primary screening tool for acute malnutrition in 6–59 month age group.",
      differentials: ["Severe acute malnutrition (SAM)", "Moderate acute malnutrition (MAM)", "Well-nourished (adequate MUAC)"],
      actions: [
        "Measure MUAC on left mid-upper arm — document in mm",
        "Check for bilateral pitting oedema (press both feet 3 seconds)",
        "Conduct RUTF appetite test if MUAC <115mm",
        "Weigh and plot on growth chart",
        "Assess for medical complications (infection, dehydration)"
      ],
      red_flags: ["MUAC <115mm", "Bilateral pitting oedema", "Failed appetite test", "Unconscious or lethargic", "Severe oedema"],
      referral: "IMMEDIATE",
      referral_reason: "SAM (MUAC <115mm or bilateral oedema) with any medical complication requires inpatient stabilisation.",
      confidence: "HIGH",
      confidence_reason: "MUAC thresholds are evidence-based WHO standards — high confidence in classification criteria.",
      formulary_note: "RUTF for OTP (uncomplicated SAM). Amoxicillin 40mg/kg/day 5 days. Vitamin A 200,000IU once if not given in last 6 months."
    }});
  }}

  if (t.includes('maternal') || t.includes('pregnant') || t.includes('antenatal')) {{
    return JSON.stringify({{
      assessment: "Maternal health query — applying Safe Motherhood protocol. Full obstetric assessment required including BP measurement.",
      differentials: ["Normal pregnancy requiring routine ANC", "Pre-eclampsia", "Antepartum haemorrhage", "Preterm labour"],
      actions: [
        "Measure BP immediately — target <140/90",
        "Check for headache, visual disturbance, epigastric pain",
        "Assess fetal movement (after quickening)",
        "Check for vaginal bleeding or watery discharge",
        "Document gestational age and ANC contact number"
      ],
      red_flags: ["BP ≥140/90", "Severe headache + visual disturbance", "Heavy vaginal bleeding", "Convulsions", "No fetal movement >12h", "Labour <37 weeks"],
      referral: "URGENT",
      referral_reason: "Any danger sign in pregnancy requires urgent obstetric assessment — do not delay.",
      confidence: "HIGH",
      confidence_reason: "Safe Motherhood red flags are evidence-based WHO criteria.",
      formulary_note: "Misoprostol 600mcg for PPH prevention (facility delivery). Iron-folate 60mg/0.4mg daily throughout pregnancy."
    }});
  }}

  return JSON.stringify({{
    assessment: "Clinical query received in demo mode. A full response requires an active API key. The structured output format shown here is the production response format used by HealthAssist v1.",
    differentials: ["Diagnosis requires full clinical context", "Please describe specific symptoms for guidance"],
    actions: [
      "Provide patient age, weight, and chief complaint for specific guidance",
      "Use the protocol sidebar (left panel) for quick offline reference",
      "Use the dosing calculator (💊 button) for weight-based medication doses"
    ],
    red_flags: ["Any altered consciousness", "Severe breathing difficulty", "Signs of shock"],
    referral: "MONITOR",
    referral_reason: "Insufficient information to determine referral urgency. Provide clinical details for assessment.",
    confidence: "LOW",
    confidence_reason: "Demo mode with no patient information — confidence in this response is low.",
    formulary_note: "null"
  }});
}}

// ─── DOSING CALCULATOR (V1) ──────────────────────────────────────────────
function toggleDosePanel() {{
  const panel = document.getElementById('dose-panel');
  panel?.classList.toggle('open');
  if (panel?.classList.contains('open')) renderFormulary();
}}

function renderFormulary() {{
  const sel = document.getElementById('dose-medicine');
  if (!sel || sel.options.length > 1) return;
  FORMULARY.forEach((med, i) => {{
    const opt = document.createElement('option');
    opt.value = i;
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

  // Built-in dosing logic for common CHW medicines
  let doseText = '', warningText = '';

  switch (med.name) {{
    case 'Paracetamol': {{
      const dose = (weight * 15).toFixed(0);
      const syrupMl = ((weight * 15) / (120/5)).toFixed(1);
      const tabQty  = (weight * 15 / 500).toFixed(2);
      doseText = `${{dose}} mg per dose`;
      doseText += `<br><small style="font-size:12px;color:var(--text-2)">= ${{syrupMl}} ml syrup (120mg/5ml) or ${{parseFloat(tabQty).toFixed(1)}} × 500mg tab</small>`;
      doseText += `<br><small style="font-size:12px;color:var(--muted)">Every 4–6h, max 4 doses/day</small>`;
      if (weight * 15 * 4 > 60 * weight) warningText = 'Max dose: do not exceed 60mg/kg/day';
      break;
    }}
    case 'Amoxicillin': {{
      const dose = (weight * 40 / 3).toFixed(0);
      const syrupMl = ((weight * 40 / 3) / (250/5)).toFixed(1);
      doseText = `${{dose}} mg per dose (3x daily)`;
      doseText += `<br><small style="font-size:12px;color:var(--text-2)">= ${{syrupMl}} ml syrup (250mg/5ml)</small>`;
      doseText += `<br><small style="font-size:12px;color:var(--muted)">Duration: 5 days</small>`;
      break;
    }}
    case 'ORS': {{
      const modVol = (weight * 75).toFixed(0);
      const sevVol = (weight * 100).toFixed(0);
      doseText = `Moderate dehydration: ${{modVol}} ml over 3–4h`;
      doseText += `<br><small style="font-size:12px;color:var(--text-2)">Severe (with IV access): ${{sevVol}} ml over 3h</small>`;
      break;
    }}
    case 'Zinc sulfate': {{
      if (weight < 5) {{
        doseText = '10 mg daily (½ tablet × 10 days — under 6 months)';
      }} else {{
        doseText = '20 mg daily (1 tablet × 10 days)';
      }}
      doseText += '<br><small style="font-size:12px;color:var(--muted)">Give with ORS for diarrhoea</small>';
      break;
    }}
    case 'Vitamin A': {{
      if (weight < 8) {{
        doseText = '100,000 IU once (under 12 months)';
      }} else {{
        doseText = '200,000 IU once (12 months and above)';
      }}
      doseText += '<br><small style="font-size:12px;color:var(--muted)">Do not repeat within 4–6 weeks</small>';
      break;
    }}
    case 'Artesunate rectal': {{
      const dose = (weight * 10).toFixed(0);
      doseText = `${{dose}} mg single pre-referral dose`;
      doseText += `<br><small style="font-size:12px;color:var(--text-2)">= ${{Math.ceil(weight * 10 / 200)}} × 200mg suppository</small>`;
      warningText = 'PRE-REFERRAL ONLY — patient must be transferred to facility immediately after';
      break;
    }}
    default:
      doseText = esc(med.dosing);
  }}

  result.innerHTML = `
    <span class="dose-qty">${{doseText}}</span>
    <span style="font-size:12px;color:var(--muted)">Based on ${{weight}} kg body weight · ${{med.name}}</span>
    ${{warningText ? `<div class="dose-warning">⚠ ${{warningText}}</div>` : ''}}
    <div style="font-size:11px;color:var(--muted);margin-top:8px">Confirm with national formulary. This tool supports — does not replace — clinical judgment.</div>
  `;
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
    {{ key: 'imci',            icon: '👶', label: 'IMCI Danger Signs',     badge: 'Emergency', color: 'red'    }},
    {{ key: 'muac',            icon: '📏', label: 'MUAC Screening',         badge: 'Nutrition',  color: 'orange' }},
    {{ key: 'malaria_rdt',     icon: '🦟', label: 'Malaria RDT Protocol',   badge: 'Malaria',    color: 'orange' }},
    {{ key: 'maternal',        icon: '🤱', label: 'Safe Motherhood',         badge: 'Maternal',   color: 'green'  }},
    {{ key: 'newborn',         icon: '🍼', label: 'Newborn Danger Signs',    badge: '0–28d',      color: 'red'    }},
    {{ key: 'referral_levels', icon: '🚑', label: 'Referral Levels',         badge: 'Guide',      color: 'green'  }},
  ];
  list.innerHTML = items.map(item => `
    <div class="protocol-item" onclick="showProtocol('${{item.key}}')" role="button" tabindex="0">
      <div class="protocol-title">${{item.icon}} ${{item.label}} <span class="protocol-badge ${{item.color}}">${{item.badge}}</span></div>
      <div class="protocol-sub">Tap for quick reference</div>
    </div>
  `).join('');
}}

function showProtocol(key) {{
  if (!protocolData || !protocolData[key]) return;
  const p = protocolData[key];
  const modal = document.getElementById('modal-overlay');
  const title = document.getElementById('modal-title');
  const body  = document.getElementById('modal-body');
  if (!modal) return;
  title.textContent = p.title || key;
  body.innerHTML = buildProtocolHTML(key, p);
  modal.classList.add('open');
}}

function buildProtocolHTML(key, p) {{
  const listItems = (arr) => (arr || []).map(s => `
    <div class="protocol-list-item">
      <div class="protocol-bullet"></div>
      <span>${{esc(s)}}</span>
    </div>`).join('');

  if (key === 'imci') return `
    <div class="protocol-section">
      <div class="protocol-section-title" style="color:var(--danger)">⚠ Emergency signs — refer immediately</div>
      ${{listItems(p.emergency_signs)}}
    </div>
    <div class="protocol-section">
      <div class="protocol-section-title">Fever classification</div>
      ${{Object.entries(p.classify_fever || {{}}).map(([k,v]) => `
        <div class="protocol-list-item"><div class="protocol-bullet orange"></div><span><strong>${{k.replace('_',' ')}}:</strong> ${{esc(v)}}</span></div>
      `).join('')}}
    </div>
    <div class="protocol-section">
      <div class="protocol-section-title">Respiratory rate thresholds</div>
      ${{Object.entries(p.respiratory_rate_thresholds || {{}}).map(([k,v]) => `
        <div class="protocol-list-item"><div class="protocol-bullet orange"></div><span><strong>${{k.replace(/_/g,' ')}}:</strong> ${{esc(v)}}</span></div>
      `).join('')}}
    </div>`;

  if (key === 'muac') return `
    <div class="protocol-section">
      <div class="protocol-section-title">MUAC thresholds (6–59 months)</div>
      ${{Object.entries(p.thresholds || {{}}).map(([k,v]) => `
        <div class="protocol-list-item">
          <div class="protocol-bullet ${{k === 'green' ? 'green' : k === 'yellow' ? 'orange' : ''}}"></div>
          <span><strong>${{k.toUpperCase()}}:</strong> ${{esc(v)}}</span>
        </div>`).join('')}}
    </div>
    <div class="protocol-section">
      <div class="protocol-section-title" style="color:var(--danger)">Bilateral oedema</div>
      <p style="font-size:13.5px">${{esc(p.bilateral_oedema || '')}}</p>
    </div>
    ${{p.appetite_test ? `<div class="protocol-section"><div class="protocol-section-title">Appetite test</div><p style="font-size:13.5px">${{esc(p.appetite_test)}}</p></div>` : ''}}`;

  if (key === 'malaria_rdt') return `
    <div class="protocol-section">
      <div class="protocol-section-title">RDT results</div>
      <p style="font-size:13.5px;margin-bottom:8px"><strong>Positive:</strong> ${{esc(p.positive || '')}}</p>
      <p style="font-size:13.5px"><strong>Negative (clinical suspicion):</strong> ${{esc(p.negative_clinical || '')}}</p>
    </div>
    <div class="protocol-section">
      <div class="protocol-section-title" style="color:var(--danger)">⚠ Severe malaria — emergency referral</div>
      ${{listItems(p.severe_signs)}}
      <p style="font-size:13px;margin-top:8px;color:var(--danger)">${{esc(p.severe_action || '')}}</p>
    </div>`;

  if (key === 'maternal') return `
    <div class="protocol-section">
      <div class="protocol-section-title" style="color:var(--danger)">⚠ Refer immediately</div>
      ${{listItems(p.refer_immediately)}}
    </div>
    ${{p.anc_schedule ? `<div class="protocol-section"><div class="protocol-section-title">ANC schedule</div><p style="font-size:13px">${{esc(p.anc_schedule)}}</p></div>` : ''}}`;

  if (key === 'newborn') return `
    <div class="protocol-section">
      <div class="protocol-section-title" style="color:var(--danger)">⚠ Newborn danger signs</div>
      ${{listItems(p.danger_signs)}}
    </div>`;

  if (key === 'referral_levels') {{
    const icons = {{ immediate: '🔴', urgent: '🟠', routine: '🟡', monitor: '🟢' }};
    return `<div class="protocol-section">${{
      Object.entries(p).map(([k,v]) => `
        <div class="protocol-list-item">
          <span style="font-size:16px">${{icons[k] || '•'}}</span>
          <span><strong style="text-transform:capitalize">${{k}}:</strong> ${{esc(v)}}</span>
        </div>`).join('')
    }}</div>`;
  }}

  return `<p style="font-size:13.5px">${{esc(JSON.stringify(p, null, 2))}}</p>`;
}}

function closeModal() {{ document.getElementById('modal-overlay')?.classList.remove('open'); }}

// ─── EVALUATION & FEEDBACK ───────────────────────────────────────────────
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

function setupEvalPanel() {{}}

function updateEvalStats() {{
  const total      = EVAL.log.filter(e => e.role === 'bot').length;
  const accurate   = EVAL.log.filter(e => e.feedback === 'accurate').length;
  const reviewed   = EVAL.log.filter(e => e.feedback === 'escalate').length;
  const emergencies = EVAL.log.filter(e => e.emergency).length;
  const followUps  = EVAL.log.filter(e => e.followUp).length;
  const immediates = EVAL.log.filter(e => e.referral === 'IMMEDIATE').length;

  const els = {{
    'eval-total': total, 'eval-accurate': accurate,
    'eval-reviewed': reviewed, 'eval-emergency': emergencies,
    'eval-followups': followUps, 'eval-immediates': immediates,
  }};
  Object.entries(els).forEach(([id, val]) => {{
    const el = document.getElementById(id);
    if (el) el.textContent = val;
  }});
}}

function toggleEvalPanel() {{ document.getElementById('eval-panel')?.classList.toggle('open'); }}

function logEvalEvent(data) {{
  if (!EVAL.enabled) return;
  const payload = {{
    ...data,
    sessionId:       EVAL.sessionId,
    studyId:         EVAL.studyId,
    pathway:         EVAL.pathway,
    arm:             EVAL.arm,
    facilityId:      EVAL.facilityId,
    protocolVersion: EVAL.protocolVersion,
    ts:              data.ts || Date.now(),
  }};

  if (EVAL.serverLogUrl && isOnline) {{
    fetch(EVAL.serverLogUrl, {{
      method: 'POST',
      headers: {{'Content-Type': 'application/json'}},
      body: JSON.stringify(payload),
      keepalive: true,
    }}).catch(() => offlineQueue.push(payload));
  }} else if (EVAL.serverLogUrl) {{
    offlineQueue.push(payload);
  }}
}}

function serverLog(entry) {{ logEvalEvent({{ type: 'message', ...entry }}); }}

function exportSession() {{
  const botMsgs   = EVAL.log.filter(e => e.role === 'bot');
  const data = {{
    studyId:          EVAL.studyId,
    pathway:          EVAL.pathway,
    arm:              EVAL.arm,
    facilityId:       EVAL.facilityId,
    protocolVersion:  EVAL.protocolVersion,
    buildHash:        EVAL.buildHash,
    sessionId:        EVAL.sessionId,
    exportedAt:       new Date().toISOString(),
    consentGiven:     EVAL.consentGiven,
    consentTimestamp: EVAL.consentTimestamp || null,
    summary: {{
      totalBotMessages:   botMsgs.length,
      userMessages:       EVAL.log.filter(e => e.role === 'user').length,
      accurateRatings:    EVAL.log.filter(e => e.feedback === 'accurate').length,
      inaccurateRatings:  EVAL.log.filter(e => e.feedback === 'inaccurate').length,
      escalations:        EVAL.log.filter(e => e.feedback === 'escalate').length,
      emergencyAlerts:    EVAL.log.filter(e => e.emergency).length,
      immediateReferrals: EVAL.log.filter(e => e.referral === 'IMMEDIATE').length,
      followUpsScheduled: EVAL.log.filter(e => e.followUp).length,
      highConfidence:     botMsgs.filter(e => e.confidence === 'HIGH').length,
      mediumConfidence:   botMsgs.filter(e => e.confidence === 'MEDIUM').length,
      lowConfidence:      botMsgs.filter(e => e.confidence === 'LOW').length,
    }},
    auditChain: EVAL.log.map(e => ({{ msgId: e.msgId, chainHash: e.chainHash }})),
    conversationHistory: history,
    evalLog: EVAL.log,
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

// ─── SIDEBAR / LOCALE / SESSION ──────────────────────────────────────────
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
  history = [];
  EVAL.log = [];
  EVAL.sessionId = _genSessionId();
  EVAL.consentGiven = false;
  emergencyMode = false;
  setEmergencyMode(false);
  document.getElementById('chat-container').innerHTML = '';
  renderProviderBanner();
  if (EVAL.consentRequired) {{ showConsentScreen(); }} else {{ showGreeting(); }}
  updateEvalStats();
}}

// ─── UTILS ───────────────────────────────────────────────────────────────
function esc(t) {{
  return String(t||'')
    .replace(/&/g,'&amp;').replace(/</g,'&lt;')
    .replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}}

function sleep(ms) {{ return new Promise(r => setTimeout(r, ms)); }}
"""
    (DOCS_DIR / "static" / "js" / "chat.js").write_text(js, encoding="utf-8")


# ─────────────────────────────────────────────
#  HTML — Production V1 Interface
# ─────────────────────────────────────────────

def write_html(cfg: dict, provider: dict | None, build_hash: str):
    app = cfg["app"]
    bot = cfg["bot"]
    eval_cfg = cfg.get("evaluation", {})
    name = app["name"]
    tagline = app["tagline"]
    icon = app["icon"]
    model = provider["model"] if provider else "demo"
    provider_name = provider["name"] if provider else "demo"
    built = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    study_id = eval_cfg.get("study_id", "EVAH-CDST-001")
    facility_id = app.get("facility_id", "FACILITY-001")
    pathway = eval_cfg.get("pathway", "A")
    arm = eval_cfg.get("arm", "intervention")
    i18n = cfg.get("i18n", DEFAULT_CONFIG["i18n"])
    default_locale = i18n.get("default_locale", "en")
    supported_locales = i18n.get("supported_locales", ["en"])

    locale_buttons = " ".join(
        f'<button onclick="switchLocale(\'{loc}\')" '
        f'style="font-size:11px;background:rgba(255,255,255,.12);border:1px solid rgba(255,255,255,.20);'
        f'color:rgba(255,255,255,.80);padding:3px 7px;border-radius:4px;cursor:pointer;font-family:var(--font-body)">'
        f'{loc.upper()}</button>'
        for loc in supported_locales
    )

    html = f"""<!DOCTYPE html>
<html lang="{default_locale}">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta name="description" content="{name} — {tagline}. EVAH-aligned AI clinical decision support for community health workers.">
  <meta name="theme-color" content="#0F4C81">
  <link rel="manifest" href="manifest.json">
  <title>{name} — {tagline}</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@300;400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="static/css/chat.css?v={build_hash}">
</head>
<body>

  <div id="emergency-overlay" aria-hidden="true"></div>

  <!-- CONSENT SCREEN (V1) -->
  <div id="consent-overlay" role="dialog" aria-modal="true" aria-labelledby="consent-title">
    <div class="consent-card">
      <div class="consent-icon" aria-hidden="true">🔒</div>
      <h2 class="consent-title" id="consent-title">Research Consent</h2>
      <p class="consent-body" id="consent-body-text">Loading consent text…</p>
      <p class="consent-study" id="consent-study-id">{study_id} · Pathway {pathway} · {facility_id}</p>
      <div class="consent-actions">
        <button class="consent-btn-primary" onclick="giveConsent()">I agree and continue</button>
        <button class="consent-btn-secondary" onclick="declineConsent()">Decline (demo mode only)</button>
      </div>
    </div>
  </div>

  <!-- DOSING CALCULATOR PANEL (V1) -->
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
      <div class="header-logo" aria-hidden="true">{icon}</div>
      <div class="header-text">
        <div class="header-name">{name}</div>
        <div class="header-tagline">{tagline}</div>
      </div>
    </div>
    <div class="header-controls">
      {locale_buttons}
      <span class="model-chip" id="model-chip">{model}</span>
      <div class="status-pill">
        <div class="status-dot" id="status-dot"></div>
        <span>Online</span>
      </div>
      <button class="icon-btn" onclick="toggleDosePanel()" aria-label="Dosing calculator" title="Dosing calculator">💊</button>
      <button class="icon-btn" onclick="toggleEvalPanel()" aria-label="Evaluation panel" title="EVAH Evaluation">
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
      <div class="sidebar-divider"></div>
      <div style="padding:10px 12px">
        <div style="font-size:11px;color:var(--muted);line-height:1.7">
          Study: <code style="font-size:10px">{study_id}</code><br>
          Facility: <code style="font-size:10px">{facility_id}</code><br>
          Pathway: <code style="font-size:10px">{pathway}</code> · Arm: <code style="font-size:10px">{arm}</code><br>
          Provider: <code style="font-size:10px">{provider_name}</code>
        </div>
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
            <button id="emergency-btn" onclick="triggerEmergency()" aria-label="Emergency protocol" title="Emergency protocol">
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
      <div class="eval-title">📊 EVAH Evaluation — {study_id}</div>
      <div>
        <div class="eval-stat"><span>Bot responses</span><span class="eval-stat-val" id="eval-total">0</span></div>
        <div class="eval-stat"><span>Marked accurate</span><span class="eval-stat-val" id="eval-accurate">0</span></div>
        <div class="eval-stat"><span>Escalated for review</span><span class="eval-stat-val" id="eval-reviewed">0</span></div>
        <div class="eval-stat"><span>Emergency alerts</span><span class="eval-stat-val" id="eval-emergency">0</span></div>
        <div class="eval-stat"><span>Immediate referrals</span><span class="eval-stat-val" id="eval-immediates">0</span></div>
        <div class="eval-stat"><span>Follow-ups scheduled</span><span class="eval-stat-val" id="eval-followups">0</span></div>
      </div>
      <div>
        <div style="font-size:11px;font-weight:600;color:var(--muted);letter-spacing:.06em;text-transform:uppercase;margin-bottom:8px">Tags</div>
        <div>
          <span class="eval-tag">Pathway {pathway}</span>
          <span class="eval-tag">{arm}</span>
          <span class="eval-tag">IMCI</span>
          <span class="eval-tag">{app.get("region", "SSA")}</span>
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
        Protocol v{PROTOCOL_VERSION} · Build {build_hash}
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

  <!-- Built: {built} | Provider: {provider_name} | Model: {model} | Study: {study_id} | Proto: {PROTOCOL_VERSION} | Hash: {build_hash} -->
  <script src="static/js/chat.js?v={build_hash}"></script>
</body>
</html>
"""
    (DOCS_DIR / "index.html").write_text(html, encoding="utf-8")


# ─────────────────────────────────────────────
#  ENTRY POINT
# ─────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="HealthAssist CDST Builder v1")
    parser.add_argument(
        "command",
        choices=["init", "build", "auto", "verify"],
        help="Command to run",
    )
    args = parser.parse_args()
    {"init": cmd_init, "build": cmd_build, "auto": cmd_auto,
        "verify": cmd_verify}[args.command]()
