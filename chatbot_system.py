#!/usr/bin/env python3
"""
chatbot_system.py — EVAH-Aligned Health CDST Chatbot Builder  v1.0
Production-ready Clinical Decision Support Tool for community health workers
in LMICs. Aligned with J-PAL EVAH Pathway A/B RFP.

Commands:
    python chatbot_system.py init     # Create config.yaml from defaults
    python chatbot_system.py build    # Build static site → _site/ or docs/
    python chatbot_system.py auto     # Full pipeline: init → build → verify
    python chatbot_system.py verify   # Check secrets and config only
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PROTOCOL_VERSION = "1.0.0"   # Bump whenever clinical content changes
ROOT = Path(__file__).parent
CONFIG_FILE = ROOT / "config.yaml"


# ===========================================================================
# AppConfig — default configuration + YAML loading
# ===========================================================================

class AppConfig:
    """Holds the default configuration tree and exposes a load() factory."""

    DEFAULTS: dict[str, Any] = {
        "app": {
            "name":          "HealthAssist CDST",
            "tagline":       "AI-Powered Clinical Decision Support",
            "icon":          "🏥",
            "locale":        "en",
            "region":        "Sub-Saharan Africa",
            "facility_type": "Primary Health Centre",
            "facility_id":   "FACILITY-001",
            "emergency_contacts": {
                "ambulance":              "999",
                "referral_hospital":      "+254 000 000 000",
                "district_health_officer": "+254 000 000 001",
            },
        },
        "bot": {
            "name":     "HealthAssist",
            "role":     "Community Health Worker Support",
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
            "accent_color":  "#00A878",
            "warning_color": "#E85D04",
            "danger_color":  "#D62828",
            "surface":       "#FFFFFF",
            "bg":            "#F0F4F8",
        },
        "evaluation": {
            "enabled":            True,
            "pathway":            "A",
            "log_sessions":       True,
            "capture_ratings":    True,
            "anonymize":          True,
            "study_id":           "EVAH-CDST-001",
            "arm":                "intervention",
            "randomisation_unit": "facility",
            "server_log_url":     "",
            "consent_required":   True,
            "consent_text": (
                "This tool is part of a research evaluation. Your de-identified "
                "interactions may be used to assess AI clinical decision support quality. "
                "No patient names or identifiers are recorded. You may withdraw at any time."
            ),
        },
        "formulary": {
            "medicines": [
                {
                    "name":   "Amoxicillin",
                    "forms":  ["250mg/5ml syrup", "500mg tablet"],
                    "dosing": "40mg/kg/day divided 3x daily, 5 days",
                },
                {
                    "name":   "Paracetamol",
                    "forms":  ["120mg/5ml syrup", "500mg tablet"],
                    "dosing": "15mg/kg/dose every 4-6h, max 4 doses/day",
                },
                {
                    "name":   "ORS",
                    "forms":  ["1L sachets"],
                    "dosing": "50-100ml/kg over 3-4h for moderate dehydration",
                },
                {
                    "name":   "Zinc sulfate",
                    "forms":  ["20mg dispersible tablet"],
                    "dosing": "<6mo: 10mg/day 10 days; ≥6mo: 20mg/day 10 days",
                },
                {
                    "name":   "Vitamin A",
                    "forms":  ["100,000IU capsule", "200,000IU capsule"],
                    "dosing": "<12mo: 100,000IU once; ≥12mo: 200,000IU once",
                },
                {
                    "name":   "Artesunate rectal",
                    "forms":  ["200mg suppository"],
                    "dosing": "10mg/kg single pre-referral dose for severe malaria",
                },
                {
                    "name":   "Iron-folate",
                    "forms":  ["60mg/0.4mg tablet"],
                    "dosing": "1 tablet daily (pregnancy), 3mo postpartum",
                },
                {
                    "name":   "Misoprostol",
                    "forms":  ["200mcg tablet"],
                    "dosing": "600mcg oral single dose for PPH prevention",
                },
            ]
        },
        "models": {
            "providers": [
                {
                    "name":          "anthropic",
                    "env_key":       "ANTHROPIC_API_KEY",
                    "endpoint":      "https://api.anthropic.com/v1/messages",
                    "model":         "claude-sonnet-4-20250514",
                    "auth_header":   "x-api-key",
                    "api_version":   "2023-06-01",
                    "provider_type": "anthropic",
                },
                {
                    "name":          "openai",
                    "env_key":       "OPENAI_API_KEY",
                    "endpoint":      "https://api.openai.com/v1/chat/completions",
                    "model":         "gpt-4o",
                    "auth_header":   "Bearer",
                    "provider_type": "openai",
                },
                {
                    "name":          "github",
                    "env_key":       "GIT_TOKEN",
                    "endpoint":      "https://models.github.ai/inference/chat/completions",
                    "model":         "gpt-4o",
                    "auth_header":   "Bearer",
                    "provider_type": "openai",
                },
                {
                    "name":          "groq",
                    "env_key":       "GROQ_API_KEY",
                    "endpoint":      "https://api.groq.com/openai/v1/chat/completions",
                    "model":         "llama-3.3-70b-versatile",
                    "auth_header":   "Bearer",
                    "provider_type": "openai",
                },
                {
                    "name":          "mistral",
                    "env_key":       "MISTRAL_API_KEY",
                    "endpoint":      "https://api.mistral.ai/v1/chat/completions",
                    "model":         "mistral-small-latest",
                    "auth_header":   "Bearer",
                    "provider_type": "openai",
                },
            ]
        },
        "protocols": {
            "imci_enabled":        True,
            "safe_motherhood":     True,
            "malaria_rdt_guidance": True,
            "muac_screening":      True,
        },
        "i18n": {
            "default_locale":    "en",
            "supported_locales": ["en", "sw"],
            "strings": {
                "en": {
                    "greeting_label": "Hello",
                    "send":           "Send",
                    "emergency":      "Emergency",
                    "new_session":    "New session",
                    "export":         "Export session data",
                    "consent_title":  "Research Consent",
                    "consent_agree":  "I agree and continue",
                    "consent_decline": "Decline (demo mode only)",
                    "placeholder":    "Describe the patient's symptoms…",
                },
                "sw": {
                    "greeting_label": "Habari",
                    "send":           "Tuma",
                    "emergency":      "Dharura",
                    "new_session":    "Kikao kipya",
                    "export":         "Hamisha data ya kikao",
                    "consent_title":  "Idhini ya Utafiti",
                    "consent_agree":  "Nakubaliana na kuendelea",
                    "consent_decline": "Kataa (hali ya maonyesho tu)",
                    "placeholder":    "Elezea dalili za mgonjwa…",
                },
            },
        },
        "deploy": {"output_dir": "docs"},
    }

    @classmethod
    def load(cls) -> dict[str, Any]:
        """Load config.yaml if present, else return defaults."""
        if not CONFIG_FILE.exists():
            log.warning("config.yaml not found — using defaults")
            return cls.DEFAULTS
        with open(CONFIG_FILE) as fh:
            return yaml.safe_load(fh)

    @classmethod
    def save_defaults(cls) -> None:
        """Write DEFAULTS to config.yaml (only if file does not exist)."""
        if CONFIG_FILE.exists():
            log.info("config.yaml already exists — skipping init")
            return
        with open(CONFIG_FILE, "w") as fh:
            yaml.dump(
                cls.DEFAULTS, fh,
                default_flow_style=False,
                allow_unicode=True,
                sort_keys=False,
            )
        log.info("✅ config.yaml created")


# ===========================================================================
# BuildContext — resolved paths, hashes, and active provider
# ===========================================================================

class BuildContext:
    """
    Immutable value object produced once per build.
    Encapsulates the output directory, content hash, active provider, and
    the resolved API token so nothing else has to call os.getenv directly.
    """

    def __init__(self, cfg: dict[str, Any]) -> None:
        self.cfg = cfg
        self.output_dir = ROOT / os.getenv("BUILD_OUTPUT_DIR", "docs")
        self.build_hash = self._compute_hash()
        self.provider = self._resolve_provider()
        self.token = self._resolve_token()
        self.built_at = datetime.now(timezone.utc)

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------

    @property
    def built_at_str(self) -> str:
        return self.built_at.strftime("%Y-%m-%d %H:%M UTC")

    @property
    def provider_name(self) -> str:
        return self.provider["name"] if self.provider else "demo"

    @property
    def model_id(self) -> str:
        return self.provider["model"] if self.provider else "demo"

    def ensure_dirs(self) -> None:
        """Create all required subdirectories under output_dir."""
        for sub in ("", "static/js", "static/css", "static/data"):
            (self.output_dir / sub).mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _compute_hash(self) -> str:
        seed = (PROTOCOL_VERSION +
                datetime.now(timezone.utc).date().isoformat()).encode()
        return hashlib.sha256(seed).hexdigest()[:8]

    def _resolve_provider(self) -> dict[str, Any] | None:
        for p in self.cfg["models"]["providers"]:
            if os.getenv(p["env_key"], ""):
                return p
        return None

    def _resolve_token(self) -> str:
        if not self.provider:
            return ""
        return os.getenv(self.provider["env_key"], "")


# ===========================================================================
# ProviderVerifier — API key discovery and reporting
# ===========================================================================

class ProviderVerifier:
    """Checks which provider API keys are present and logs the results."""

    def __init__(self, cfg: dict[str, Any]) -> None:
        self._providers = cfg["models"]["providers"]

    def verify(self) -> dict[str, Any] | None:
        """
        Log found/missing keys and return the first active provider dict,
        or None if no keys are configured.
        """
        found, missing = [], []

        for p in self._providers:
            if os.getenv(p["env_key"], ""):
                found.append(p)
                log.info("OK      %-28s (%s / %s)",
                         p["env_key"], p["name"], p["model"])
            else:
                missing.append(p)
                log.warning("MISSING %-28s (%s)", p["env_key"], p["name"])

        if not found:
            log.warning(
                "No API keys found — CDST will run in demo/offline mode")
            return None

        winner = found[0]
        log.info("✅ Active provider → %s  model=%s",
                 winner["name"], winner["model"])
        return winner


# ===========================================================================
# ProtocolsData — clinical protocol definitions
# ===========================================================================

class ProtocolsData:
    """
    Owns the structured IMCI/MUAC/Malaria/Maternal/Newborn protocol data
    and serialises it to JSON.
    """

    def build(self) -> dict[str, Any]:
        return {
            "version": PROTOCOL_VERSION,
            "imci":    self._imci(),
            "muac":    self._muac(),
            "malaria_rdt":    self._malaria_rdt(),
            "maternal":       self._maternal(),
            "referral_levels": self._referral_levels(),
            "newborn":        self._newborn(),
        }

    # ------------------------------------------------------------------

    def _imci(self) -> dict:
        return {
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
                "high_risk":    "Temp ≥38.5°C + any danger sign → REFER URGENTLY",
                "malaria_risk": "Temp ≥37.5°C in malaria-endemic area → RDT if available",
                "low_risk":     "Temp 37.5–38.4°C, no danger signs → Treat & monitor",
            },
            "respiratory_rate_thresholds": {
                "2_to_11_months":  "≥50 breaths/min = fast breathing",
                "12_to_59_months": "≥40 breaths/min = fast breathing",
            },
        }

    def _muac(self) -> dict:
        return {
            "title": "MUAC Screening (6–59 months)",
            "thresholds": {
                "green":  "≥125mm — Well nourished",
                "yellow": "115–124mm — Moderate acute malnutrition (MAM)",
                "red":    "<115mm — Severe acute malnutrition (SAM) → REFER",
            },
            "bilateral_oedema": (
                "Any pitting oedema → SAM regardless of MUAC → REFER"
            ),
            "appetite_test": (
                "RUTF appetite test: pass = eligible for OTP; fail = inpatient care"
            ),
        }

    def _malaria_rdt(self) -> dict:
        return {
            "title":            "Malaria RDT Protocol",
            "positive":         "RDT+ → Confirm species, treat with ACT per national protocol",
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
        }

    def _maternal(self) -> dict:
        return {
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
            "anc_schedule": (
                "8 contacts: booking (<12wk), 20wk, 26wk, 30wk, 34wk, 36wk, 38wk, 40wk"
            ),
        }

    def _referral_levels(self) -> dict:
        return {
            "immediate": "Life-threatening — call ambulance / refer NOW",
            "urgent":    "Refer within 2–4 hours",
            "routine":   "Refer at next available transport",
            "monitor":   "Manage at facility, review in 24–48h",
        }

    def _newborn(self) -> dict:
        return {
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
        }


# ===========================================================================
# StaticFileWriter — CSS, SW, manifest, protocols, formulary, i18n
# ===========================================================================

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
.consent-study  {{ font-size: 12px; font-family: var(--font-mono); color: var(--muted); margin-bottom: 1.5rem; }}
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
  position: fixed; right: 0; top: 64px; bottom: 0; width: 320px;
  background: var(--surface); border-left: 1px solid var(--border-light);
  z-index: 150; display: none; flex-direction: column;
  box-shadow: -4px 0 20px rgba(15,76,129,.10);
  transform: translateX(100%); transition: transform .25s ease;
}}
#dose-panel.open {{ display: flex; transform: translateX(0); }}
.dose-header {{
  padding: 14px 16px; border-bottom: 1px solid var(--border-light);
  font-size: 13px; font-weight: 600;
  display: flex; align-items: center; justify-content: space-between;
  background: var(--primary); color: white;
}}
.dose-body   {{ flex: 1; overflow-y: auto; padding: 16px; }}
.dose-field  {{ margin-bottom: 14px; }}
.dose-label  {{ font-size: 11px; font-weight: 600; color: var(--muted); letter-spacing: .06em; text-transform: uppercase; margin-bottom: 5px; display: block; }}
.dose-input  {{ width: 100%; border: 1.5px solid var(--border); border-radius: var(--radius-sm); padding: 8px 10px; font-size: 14px; font-family: var(--font-body); outline: none; background: var(--bg); transition: border-color var(--transition); }}
.dose-input:focus {{ border-color: var(--primary); background: var(--surface); }}
.dose-select {{ width: 100%; border: 1.5px solid var(--border); border-radius: var(--radius-sm); padding: 8px 10px; font-size: 13.5px; font-family: var(--font-body); background: var(--bg); outline: none; cursor: pointer; }}
.dose-result {{ background: var(--primary-light); border: 1px solid var(--primary-mid); border-radius: var(--radius); padding: 12px 14px; margin-top: 12px; font-size: 13.5px; line-height: 1.6; }}
.dose-result .dose-qty {{ font-size: 20px; font-weight: 600; color: var(--primary); font-family: var(--font-mono); display: block; margin-bottom: 4px; }}
.dose-warning {{ background: var(--warning-light); border: 1px solid color-mix(in srgb, var(--warning) 30%, white); border-radius: var(--radius-sm); padding: 8px 10px; font-size: 12px; color: color-mix(in srgb, var(--warning) 80%, black); margin-top: 8px; }}

/* ── HEADER ────────────────────────────────── */
header {{
  background: var(--primary); color: white;
  padding: 0 1.25rem; height: 64px;
  display: flex; align-items: center; justify-content: space-between;
  position: sticky; top: 0; z-index: 200;
  box-shadow: 0 2px 12px rgba(0,0,0,.20);
}}
.header-brand   {{ display: flex; align-items: center; gap: 12px; min-width: 0; }}
.header-logo    {{ width: 38px; height: 38px; background: rgba(255,255,255,.15); border: 1.5px solid rgba(255,255,255,.30); border-radius: var(--radius); display: flex; align-items: center; justify-content: center; font-size: 18px; flex-shrink: 0; }}
.header-text    {{ min-width: 0; }}
.header-name    {{ font-size: 15px; font-weight: 600; letter-spacing: -.01em; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
.header-tagline {{ font-size: 11px; color: rgba(255,255,255,.55); }}
.header-controls {{ display: flex; align-items: center; gap: 8px; flex-shrink: 0; }}
.status-pill {{ display: flex; align-items: center; gap: 5px; background: rgba(255,255,255,.10); border: 1px solid rgba(255,255,255,.18); padding: 4px 10px; border-radius: 20px; font-size: 11.5px; color: rgba(255,255,255,.85); white-space: nowrap; }}
.status-dot  {{ width: 6px; height: 6px; background: #4ADE80; border-radius: 50%; animation: pulse-dot 2.5s ease-in-out infinite; }}
.status-dot.offline {{ background: #FCA5A5; animation: none; }}
@keyframes pulse-dot {{ 0%, 100% {{ opacity: 1; transform: scale(1); }} 50% {{ opacity: .5; transform: scale(.8); }} }}
.model-chip {{ font-size: 11px; font-family: var(--font-mono); background: rgba(255,255,255,.12); border: 1px solid rgba(255,255,255,.18); color: rgba(255,255,255,.80); padding: 3px 8px; border-radius: 4px; }}
.icon-btn   {{ background: rgba(255,255,255,.08); border: 1px solid rgba(255,255,255,.15); color: rgba(255,255,255,.80); width: 34px; height: 34px; border-radius: var(--radius-sm); cursor: pointer; display: flex; align-items: center; justify-content: center; transition: background var(--transition); }}
.icon-btn:hover {{ background: rgba(255,255,255,.18); }}

/* ── SAFETY BANNER ─────────────────────────── */
#safety-banner {{ padding: 7px 1.25rem; font-size: 12px; display: flex; align-items: center; gap: 8px; border-bottom: 1px solid; font-weight: 500; }}
#safety-banner.status-live      {{ background: var(--accent-light);   border-color: color-mix(in srgb, var(--accent) 30%, white);  color: color-mix(in srgb, var(--accent) 80%, black); }}
#safety-banner.status-demo      {{ background: var(--warning-light);  border-color: color-mix(in srgb, var(--warning) 30%, white); color: color-mix(in srgb, var(--warning) 80%, black); }}
#safety-banner.status-emergency {{ background: var(--danger-light);   border-color: color-mix(in srgb, var(--danger) 40%, white);  color: var(--danger); animation: blink-border 1s ease-in-out infinite; }}
@keyframes blink-border {{ 0%, 100% {{ background: var(--danger-light); }} 50% {{ background: color-mix(in srgb, var(--danger) 18%, white); }} }}

/* ── LAYOUT ────────────────────────────────── */
.app-body {{ display: flex; flex: 1; overflow: hidden; height: calc(100vh - 64px - 37px); }}

#sidebar {{ width: 260px; background: var(--surface); border-right: 1px solid var(--border-light); display: flex; flex-direction: column; overflow: hidden; transition: width var(--transition); flex-shrink: 0; }}
#sidebar.collapsed {{ width: 0; }}
.sidebar-header  {{ padding: 14px 16px; border-bottom: 1px solid var(--border-light); font-size: 11px; font-weight: 600; color: var(--muted); letter-spacing: .08em; text-transform: uppercase; display: flex; align-items: center; justify-content: space-between; }}
.protocol-list   {{ overflow-y: auto; flex: 1; padding: 8px; }}
.protocol-item   {{ padding: 10px 12px; border-radius: var(--radius-sm); cursor: pointer; margin-bottom: 2px; transition: background var(--transition); border: 1px solid transparent; }}
.protocol-item:hover {{ background: var(--primary-light); border-color: var(--primary-mid); }}
.protocol-title  {{ font-size: 13px; font-weight: 500; color: var(--text); display: flex; align-items: center; gap: 7px; }}
.protocol-badge  {{ font-size: 10px; background: var(--danger); color: white; padding: 1px 6px; border-radius: 10px; font-weight: 600; }}
.protocol-badge.green  {{ background: var(--accent); }}
.protocol-badge.orange {{ background: var(--warning); }}
.protocol-sub    {{ font-size: 11.5px; color: var(--muted); margin-top: 2px; }}
.sidebar-divider {{ height: 1px; background: var(--border-light); margin: 6px 8px; }}

/* ── CHAT COLUMN ───────────────────────────── */
#chat-col        {{ flex: 1; display: flex; flex-direction: column; overflow: hidden; min-width: 0; }}
#chat-container  {{ flex: 1; overflow-y: auto; padding: 1.25rem 1rem; display: flex; flex-direction: column; gap: 1rem; scroll-behavior: smooth; }}

/* ── MESSAGES ──────────────────────────────── */
.message {{ display: flex; gap: 10px; max-width: 86%; animation: msg-in .2s ease; }}
@keyframes msg-in {{ from {{ opacity: 0; transform: translateY(6px); }} to {{ opacity: 1; transform: translateY(0); }} }}
.message.user   {{ align-self: flex-end;   flex-direction: row-reverse; }}
.message.bot    {{ align-self: flex-start; }}
.message.system {{ align-self: center;     max-width: 100%; }}
.msg-avatar {{ width: 32px; height: 32px; border-radius: 8px; flex-shrink: 0; display: flex; align-items: center; justify-content: center; font-size: 14px; font-weight: 600; margin-top: 2px; }}
.message.bot  .msg-avatar {{ background: var(--primary); color: white; }}
.message.user .msg-avatar {{ background: var(--accent);  color: white; font-size: 11px; }}
.msg-body   {{ display: flex; flex-direction: column; min-width: 0; }}
.msg-bubble {{ padding: 11px 14px; border-radius: var(--radius); font-size: 14px; line-height: 1.65; word-break: break-word; }}
.message.bot    .msg-bubble {{ background: var(--surface); color: var(--text); border: 1px solid var(--border-light); border-bottom-left-radius: 3px; box-shadow: var(--shadow-sm); }}
.message.user   .msg-bubble {{ background: var(--primary); color: white; border-bottom-right-radius: 3px; }}
.message.system .msg-bubble {{ background: transparent; border: 1px dashed var(--border); color: var(--muted); font-size: 12.5px; text-align: center; border-radius: var(--radius); padding: 7px 14px; box-shadow: none; }}
.message.emergency .msg-bubble {{ background: var(--danger-light); border: 1.5px solid var(--danger); color: var(--text); }}
.message.emergency .msg-avatar {{ background: var(--danger); }}

/* ── CLINICAL CARD ─────────────────────────── */
.clinical-card {{ background: var(--surface); border: 1px solid var(--border-light); border-radius: var(--radius); overflow: hidden; box-shadow: var(--shadow-sm); }}
.clinical-section {{ padding: 10px 14px; border-bottom: 1px solid var(--border-light); }}
.clinical-section:last-child {{ border-bottom: none; }}
.clinical-section-label {{ font-size: 10.5px; font-weight: 600; letter-spacing: .07em; text-transform: uppercase; color: var(--muted); margin-bottom: 5px; display: flex; align-items: center; gap: 5px; }}
.clinical-section-label.danger  {{ color: var(--danger); }}
.clinical-section-label.warning {{ color: var(--warning); }}
.clinical-section-label.success {{ color: var(--accent); }}
.clinical-content {{ font-size: 13.5px; line-height: 1.6; }}
.tag-list {{ display: flex; flex-wrap: wrap; gap: 5px; margin-top: 5px; }}
.tag {{ font-size: 12px; padding: 3px 9px; border-radius: 20px; font-weight: 500; }}
.tag.red    {{ background: var(--danger-light);  color: var(--danger);  border: 1px solid color-mix(in srgb, var(--danger) 25%, white); }}
.tag.green  {{ background: var(--accent-light);  color: color-mix(in srgb, var(--accent) 80%, black); border: 1px solid color-mix(in srgb, var(--accent) 25%, white); }}
.tag.blue   {{ background: var(--primary-light); color: var(--primary); border: 1px solid var(--primary-mid); }}
.tag.orange {{ background: var(--warning-light); color: var(--warning); border: 1px solid color-mix(in srgb, var(--warning) 25%, white); }}
.referral-badge {{ display: inline-flex; align-items: center; gap: 6px; padding: 6px 12px; border-radius: var(--radius-sm); font-size: 13px; font-weight: 600; margin-top: 6px; }}
.referral-badge.immediate {{ background: var(--danger);  color: white; }}
.referral-badge.urgent    {{ background: var(--warning); color: white; }}
.referral-badge.routine   {{ background: var(--accent);  color: white; }}
.referral-badge.monitor   {{ background: var(--primary-light); color: var(--primary); }}

/* ── FOLLOW-UP ─────────────────────────────── */
.followup-form  {{ background: var(--bg); border: 1px solid var(--border-light); border-radius: var(--radius-sm); padding: 10px 12px; margin-top: 8px; font-size: 12.5px; }}
.followup-row   {{ display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }}
.followup-input {{ border: 1px solid var(--border); border-radius: 4px; padding: 5px 8px; font-size: 12px; font-family: var(--font-body); background: var(--surface); outline: none; flex: 1; min-width: 100px; }}
.followup-btn   {{ background: var(--primary); color: white; border: none; border-radius: 4px; padding: 5px 10px; font-size: 12px; font-family: var(--font-body); cursor: pointer; }}

/* ── FEEDBACK ──────────────────────────────── */
.msg-feedback    {{ display: flex; align-items: center; gap: 6px; margin-top: 6px; font-size: 11.5px; color: var(--muted); }}
.feedback-btn    {{ background: none; border: 1px solid var(--border); border-radius: 4px; padding: 2px 7px; cursor: pointer; font-size: 12px; color: var(--muted); transition: all var(--transition); font-family: var(--font-body); }}
.feedback-btn:hover  {{ border-color: var(--primary); color: var(--primary); }}
.feedback-btn.active {{ background: var(--primary-light); border-color: var(--primary); color: var(--primary); }}
.confidence-chip {{ font-family: var(--font-mono); font-size: 10.5px; padding: 2px 6px; border-radius: 3px; border: 1px solid var(--border); color: var(--muted); }}
.confidence-chip.HIGH   {{ border-color: var(--accent);   color: var(--accent); }}
.confidence-chip.MEDIUM {{ border-color: var(--warning);  color: var(--warning); }}
.confidence-chip.LOW    {{ border-color: var(--danger);   color: var(--danger); }}

/* ── TYPING INDICATOR ──────────────────────── */
.typing-indicator {{ display: flex; align-items: center; gap: 4px; padding: 12px 14px; background: var(--surface); border: 1px solid var(--border-light); border-radius: var(--radius); border-bottom-left-radius: 3px; width: fit-content; }}
.typing-dot {{ width: 6px; height: 6px; background: var(--muted); border-radius: 50%; animation: typing-bounce 1.2s ease-in-out infinite; }}
.typing-dot:nth-child(2) {{ animation-delay: .2s; }}
.typing-dot:nth-child(3) {{ animation-delay: .4s; }}
@keyframes typing-bounce {{ 0%, 80%, 100% {{ transform: translateY(0); opacity: .5; }} 40% {{ transform: translateY(-5px); opacity: 1; }} }}

/* ── QUICK REPLIES ─────────────────────────── */
.quick-replies {{ display: flex; flex-wrap: wrap; gap: 7px; padding: 2px 0 8px 42px; animation: msg-in .25s ease; }}
.quick-btn {{ background: var(--surface); border: 1.5px solid var(--border); color: var(--primary); padding: 6px 12px; border-radius: 20px; font-size: 12.5px; font-family: var(--font-body); font-weight: 500; cursor: pointer; transition: all var(--transition); white-space: nowrap; }}
.quick-btn:hover {{ background: var(--primary-light); border-color: var(--primary); }}

/* ── META / BADGES ─────────────────────────── */
.msg-meta {{ font-size: 10.5px; color: var(--muted); margin-top: 4px; display: flex; align-items: center; gap: 6px; }}
.message.user .msg-meta {{ justify-content: flex-end; }}
.offline-badge {{ display: inline-flex; align-items: center; gap: 5px; font-size: 11.5px; background: var(--warning-light); color: color-mix(in srgb, var(--warning) 80%, black); border: 1px solid color-mix(in srgb, var(--warning) 30%, white); padding: 3px 8px; border-radius: 20px; margin-top: 4px; }}

/* ── INPUT BAR ─────────────────────────────── */
#input-bar {{ background: var(--surface); border-top: 1px solid var(--border-light); padding: .75rem 1rem; box-shadow: 0 -2px 12px rgba(15,76,129,.06); }}
.input-inner {{ display: flex; gap: 8px; align-items: flex-end; max-width: 900px; margin: 0 auto; }}
#user-input {{ flex: 1; border: 1.5px solid var(--border); border-radius: var(--radius); padding: 9px 14px; font-size: 14px; font-family: var(--font-body); outline: none; background: var(--bg); color: var(--text); resize: none; max-height: 120px; line-height: 1.5; transition: border-color var(--transition), box-shadow var(--transition); }}
#user-input:focus {{ border-color: var(--primary); box-shadow: 0 0 0 3px var(--primary-light); background: var(--surface); }}
#user-input::placeholder {{ color: var(--muted); }}
.input-actions {{ display: flex; gap: 6px; }}
#send-btn {{ width: 40px; height: 40px; border-radius: var(--radius-sm); background: var(--primary); border: none; color: white; cursor: pointer; display: flex; align-items: center; justify-content: center; transition: background var(--transition), transform var(--transition); flex-shrink: 0; box-shadow: 0 2px 6px rgba(15,76,129,.30); }}
#send-btn:hover    {{ background: color-mix(in srgb, var(--primary) 85%, black); }}
#send-btn:active   {{ transform: scale(.94); }}
#send-btn:disabled {{ background: var(--border); cursor: not-allowed; box-shadow: none; }}
#emergency-btn {{ height: 40px; padding: 0 12px; border-radius: var(--radius-sm); background: var(--danger); border: none; color: white; cursor: pointer; font-size: 12px; font-weight: 600; font-family: var(--font-body); display: flex; align-items: center; gap: 5px; transition: background var(--transition); white-space: nowrap; }}
#emergency-btn:hover {{ background: color-mix(in srgb, var(--danger) 85%, black); }}
#dose-btn {{ height: 40px; padding: 0 10px; border-radius: var(--radius-sm); background: var(--surface); border: 1.5px solid var(--border); color: var(--text-2); cursor: pointer; font-size: 12px; font-family: var(--font-body); display: flex; align-items: center; gap: 5px; transition: all var(--transition); white-space: nowrap; }}
#dose-btn:hover {{ border-color: var(--primary); color: var(--primary); }}

/* ── MODAL ─────────────────────────────────── */
#modal-overlay {{ display: none; position: fixed; inset: 0; background: rgba(0,0,0,.35); z-index: 300; align-items: center; justify-content: center; padding: 1rem; backdrop-filter: blur(3px); }}
#modal-overlay.open {{ display: flex; }}
.modal {{ background: var(--surface); border-radius: var(--radius-lg); box-shadow: var(--shadow-lg); max-width: 520px; width: 100%; max-height: 80vh; overflow-y: auto; animation: modal-in .2s ease; }}
@keyframes modal-in {{ from {{ opacity: 0; transform: scale(.96) translateY(10px); }} to {{ opacity: 1; transform: scale(1) translateY(0); }} }}
.modal-header {{ padding: 18px 20px 14px; border-bottom: 1px solid var(--border-light); display: flex; align-items: center; justify-content: space-between; position: sticky; top: 0; background: var(--surface); }}
.modal-title  {{ font-size: 16px; font-weight: 600; }}
.modal-close  {{ background: none; border: none; color: var(--muted); cursor: pointer; font-size: 20px; padding: 2px 6px; border-radius: 4px; transition: color var(--transition); }}
.modal-close:hover {{ color: var(--text); }}
.modal-body   {{ padding: 16px 20px 20px; }}
.protocol-section       {{ margin-bottom: 18px; }}
.protocol-section-title {{ font-size: 12px; font-weight: 600; color: var(--muted); letter-spacing: .06em; text-transform: uppercase; margin-bottom: 8px; }}
.protocol-list-item {{ display: flex; align-items: flex-start; gap: 8px; padding: 6px 0; border-bottom: 1px solid var(--border-light); font-size: 13.5px; }}
.protocol-list-item:last-child {{ border-bottom: none; }}
.protocol-bullet        {{ width: 7px; height: 7px; border-radius: 50%; background: var(--danger); flex-shrink: 0; margin-top: 6px; }}
.protocol-bullet.green  {{ background: var(--accent); }}
.protocol-bullet.orange {{ background: var(--warning); }}

/* ── EVALUATION PANEL ──────────────────────── */
#eval-panel {{ width: 280px; background: var(--surface); border-left: 1px solid var(--border-light); overflow-y: auto; flex-shrink: 0; padding: 14px; display: none; flex-direction: column; gap: 14px; }}
#eval-panel.open {{ display: flex; }}
.eval-title    {{ font-size: 11px; font-weight: 600; color: var(--muted); letter-spacing: .08em; text-transform: uppercase; padding-bottom: 10px; border-bottom: 1px solid var(--border-light); }}
.eval-stat     {{ display: flex; justify-content: space-between; align-items: center; padding: 6px 0; font-size: 13px; border-bottom: 1px solid var(--border-light); }}
.eval-stat-val {{ font-family: var(--font-mono); font-size: 13px; font-weight: 600; color: var(--primary); }}
.eval-tag      {{ display: inline-flex; align-items: center; gap: 4px; background: var(--primary-light); border: 1px solid var(--primary-mid); color: var(--primary); padding: 4px 9px; border-radius: 4px; font-size: 11.5px; font-weight: 500; margin-bottom: 4px; margin-right: 4px; }}

/* ── EMERGENCY OVERLAY ─────────────────────── */
#emergency-overlay {{ display: none; position: fixed; inset: 0; background: rgba(214,40,40,.08); z-index: 100; pointer-events: none; border: 4px solid var(--danger); animation: emergency-pulse 1s ease-in-out infinite; }}
#emergency-overlay.active {{ display: block; }}
@keyframes emergency-pulse {{ 0%, 100% {{ opacity: 1; }} 50% {{ opacity: .4; }} }}

/* ── SCROLLBAR ─────────────────────────────── */
::-webkit-scrollbar       {{ width: 5px; }}
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
            "app":              cfg["app"],
            "bot":              {k: v for k, v in cfg["bot"].items() if k != "system_prompt"},
            "theme":            cfg["theme"],
            "evaluation":       cfg.get("evaluation", {}),
            "protocols":        cfg.get("protocols", {}),
            "formulary":        cfg.get("formulary", {}),
            "i18n":             cfg.get("i18n", {}),
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


# ===========================================================================
# JavaScriptWriter — generates chat.js
# ===========================================================================

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
  EVAL.consentGiven    = true;
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
  const el        = document.getElementById('safety-banner');
  const dot       = document.getElementById('status-dot');
  const modelChip = document.getElementById('model-chip');
  if (!el) return;
  if (modelChip) modelChip.textContent = PROVIDER.model;

  if (!PROVIDER.token || PROVIDER.name === 'demo') {{
    el.className  = 'status-demo';
    el.innerHTML  = '⚠️ &nbsp;Demo mode — set <strong>ANTHROPIC_API_KEY</strong> or another API key in GitHub Secrets.';
    if (dot) dot.className = 'status-dot offline';
  }} else {{
    el.className  = 'status-live';
    const labels  = {{ anthropic: 'Anthropic Claude', openai: 'OpenAI', github: 'GitHub Models', groq: 'Groq', mistral: 'Mistral' }};
    const label   = labels[PROVIDER.name] || PROVIDER.name;
    el.innerHTML  = `✅ &nbsp;Live — <strong>${{label}}</strong> · ${{PROVIDER.model}} · ${{EVAL.facilityId}} · Session: <code style="font-size:10px">${{EVAL.sessionId.slice(0,8)}}</code>`;
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

  const flagsHtml = (data.red_flags    || []).map(f => `<span class="tag red">${{esc(f)}}</span>`).join('');
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

  const clinicalData  = (role === 'bot' && !opts.noFeedback) ? parseClinicalJSON(text) : null;
  const isEmergency   = role === 'bot' && (
    clinicalData?.referral === 'IMMEDIATE' ||
    text.includes('EMERGENCY REFERRAL') ||
    text.includes('REFER URGENTLY') ||
    opts.emergency === true
  );

  if (isEmergency) setEmergencyMode(true);

  el.id        = id;
  el.className = 'message ' + role + (isEmergency ? ' emergency' : '');

  const avatar      = role === 'bot' ? '🏥' : (role === 'user' ? 'CHW' : '');
  const bubbleHtml  = clinicalData
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
  if (/confidence.*HIGH|HIGH.*confidence/i.test(text))   return 'HIGH';
  if (/confidence.*MEDIUM|MEDIUM.*confidence/i.test(text)) return 'MEDIUM';
  if (/confidence.*LOW|LOW.*confidence/i.test(text))    return 'LOW';
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
    const btn    = document.createElement('button');
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
    const opt = document.createElement('option');
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
      doseText = weight < 5
        ? '10 mg daily (½ tablet × 10 days — under 6 months)'
        : '20 mg daily (1 tablet × 10 days)';
      doseText += '<br><small style="font-size:12px;color:var(--muted)">Give with ORS for diarrhoea</small>';
      break;
    case 'Vitamin A':
      doseText = weight < 8 ? '100,000 IU once (under 12 months)' : '200,000 IU once (12 months and above)';
      doseText += '<br><small style="font-size:12px;color:var(--muted)">Do not repeat within 4–6 weeks</small>';
      break;
    case 'Artesunate rectal': {{
      const dose = (weight * 10).toFixed(0);
      doseText    = `${{dose}} mg single pre-referral dose<br><small style="font-size:12px;color:var(--text-2)">= ${{Math.ceil(weight * 10 / 200)}} × 200mg suppository</small>`;
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
    {{ key: 'imci',            icon: '👶', label: 'IMCI Danger Signs',    badge: 'Emergency', color: 'red'    }},
    {{ key: 'muac',            icon: '📏', label: 'MUAC Screening',        badge: 'Nutrition',  color: 'orange' }},
    {{ key: 'malaria_rdt',     icon: '🦟', label: 'Malaria RDT Protocol',  badge: 'Malaria',    color: 'orange' }},
    {{ key: 'maternal',        icon: '🤱', label: 'Safe Motherhood',        badge: 'Maternal',   color: 'green'  }},
    {{ key: 'newborn',         icon: '🍼', label: 'Newborn Danger Signs',   badge: '0–28d',      color: 'red'    }},
    {{ key: 'referral_levels', icon: '🚑', label: 'Referral Levels',        badge: 'Guide',      color: 'green'  }},
  ];
  list.innerHTML = items.map(item => `
    <div class="protocol-item" onclick="showProtocol('${{item.key}}')" role="button" tabindex="0">
      <div class="protocol-title">${{item.icon}} ${{item.label}} <span class="protocol-badge ${{item.color}}">${{item.badge}}</span></div>
      <div class="protocol-sub">Tap for quick reference</div>
    </div>`).join('');
}}

function showProtocol(key) {{
  if (!protocolData?.[key]) return;
  const p      = protocolData[key];
  const modal  = document.getElementById('modal-overlay');
  const title  = document.getElementById('modal-title');
  const body   = document.getElementById('modal-body');
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


# ===========================================================================
# HtmlWriter — generates index.html
# ===========================================================================

class HtmlWriter:
    """Generates the main index.html entry point."""

    def __init__(self, ctx: BuildContext) -> None:
        self._ctx = ctx
        self._cfg = ctx.cfg

    def write(self) -> None:
        content = self._render()
        (self._ctx.output_dir / "index.html").write_text(content, encoding="utf-8")

    # ------------------------------------------------------------------

    def _render(self) -> str:
        ctx = self._ctx
        cfg = self._cfg
        app = cfg["app"]
        eval_cfg = cfg.get("evaluation", {})
        i18n = cfg.get("i18n", AppConfig.DEFAULTS["i18n"])

        study_id = eval_cfg.get("study_id", "EVAH-CDST-001")
        facility_id = app.get("facility_id", "FACILITY-001")
        pathway = eval_cfg.get("pathway", "A")
        arm = eval_cfg.get("arm", "intervention")
        locale = i18n.get("default_locale", "en")
        locale_btns = self._locale_buttons(
            i18n.get("supported_locales", ["en"]))

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

  <!-- CONSENT SCREEN -->
  <div id="consent-overlay" role="dialog" aria-modal="true" aria-labelledby="consent-title">
    <div class="consent-card">
      <div class="consent-icon" aria-hidden="true">🔒</div>
      <h2 class="consent-title" id="consent-title">Research Consent</h2>
      <p class="consent-body" id="consent-body-text">Loading consent text…</p>
      <p class="consent-study" id="consent-study-id">{study_id} · Pathway {pathway} · {facility_id}</p>
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
      <span class="model-chip" id="model-chip">{ctx.model_id}</span>
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
      <div class="sidebar-divider"></div>
      <div style="padding:10px 12px">
        <div style="font-size:11px;color:var(--muted);line-height:1.7">
          Study: <code style="font-size:10px">{study_id}</code><br>
          Facility: <code style="font-size:10px">{facility_id}</code><br>
          Pathway: <code style="font-size:10px">{pathway}</code> · Arm: <code style="font-size:10px">{arm}</code><br>
          Provider: <code style="font-size:10px">{ctx.provider_name}</code>
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
        <div class="eval-stat"><span>Bot responses</span>      <span class="eval-stat-val" id="eval-total">0</span></div>
        <div class="eval-stat"><span>Marked accurate</span>    <span class="eval-stat-val" id="eval-accurate">0</span></div>
        <div class="eval-stat"><span>Escalated for review</span><span class="eval-stat-val" id="eval-reviewed">0</span></div>
        <div class="eval-stat"><span>Emergency alerts</span>   <span class="eval-stat-val" id="eval-emergency">0</span></div>
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

  <!-- Built: {ctx.built_at_str} | Provider: {ctx.provider_name} | Model: {ctx.model_id} | Study: {study_id} | Proto: {PROTOCOL_VERSION} | Hash: {ctx.build_hash} -->
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


# ===========================================================================
# OutputVerifier — post-build sanity check
# ===========================================================================

class OutputVerifier:
    """Checks that all required output files exist and logs their sizes."""

    REQUIRED_FILES = [
        "index.html",
        "static/js/chat.js",
        "static/css/chat.css",
        "config.json",
        "static/data/protocols.json",
        "sw.js",
        "manifest.json",
    ]

    def __init__(self, output_dir: Path) -> None:
        self._output_dir = output_dir

    def verify(self) -> None:
        ok = True
        for rel in self.REQUIRED_FILES:
            path = self._output_dir / rel
            if path.exists():
                log.info("OK    %s (%d bytes)", rel, path.stat().st_size)
            else:
                log.error("MISSING  %s", rel)
                ok = False
        if not ok:
            sys.exit(1)


# ===========================================================================
# CDSTBuilder — orchestrates the full build pipeline
# ===========================================================================

class CDSTBuilder:
    """
    Top-level orchestrator.  Exposes one method per CLI command:
        init()   — write default config.yaml
        verify() — check API keys
        build()  — full static-site generation
        auto()   — init + build + verify
    """

    def init(self) -> None:
        AppConfig.save_defaults()

    def verify(self) -> dict[str, Any] | None:
        cfg = AppConfig.load()
        return ProviderVerifier(cfg).verify()

    def build(self) -> None:
        cfg = AppConfig.load()
        ctx = BuildContext(cfg)

        # Always run a verify so missing keys are visible in CI logs.
        ProviderVerifier(cfg).verify()

        ctx.ensure_dirs()

        StaticFileWriter(ctx).write_all()
        JavaScriptWriter(ctx).write()
        HtmlWriter(ctx).write()

        log.info("✅ Build complete → %s/  [hash=%s]",
                 ctx.output_dir, ctx.build_hash)
        OutputVerifier(ctx.output_dir).verify()

    def auto(self) -> None:
        self.init()
        self.build()


# ===========================================================================
# CLI — argument parsing & dispatch
# ===========================================================================

class CLI:
    """Parses command-line arguments and dispatches to CDSTBuilder."""

    COMMANDS = ("init", "build", "auto", "verify")

    def run(self) -> None:
        parser = argparse.ArgumentParser(
            description="HealthAssist CDST Builder v1")
        parser.add_argument(
            "command",
            choices=self.COMMANDS,
            help="Command to run",
        )
        args = parser.parse_args()
        builder = CDSTBuilder()
        getattr(builder, args.command)()


# ===========================================================================
# Entry point
# ===========================================================================

if __name__ == "__main__":
    CLI().run()
