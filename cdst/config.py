"""
cdst/config.py — AppConfig: default configuration tree and YAML loading.
"""

from __future__ import annotations

import logging
from typing import Any

import yaml

from .constants import CONFIG_FILE

log = logging.getLogger(__name__)


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
                "ambulance":               "911",
                "referral_hospital":       "+254 000 000 000",
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
            # ── CHANGE 1: consent screen disabled by default ──────────────
            "consent_required":   False,
            # ─────────────────────────────────────────────────────────────
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
            "imci_enabled":         True,
            "safe_motherhood":      True,
            "malaria_rdt_guidance": True,
            "muac_screening":       True,
        },
        "i18n": {
            "default_locale":    "en",
            "supported_locales": ["en", "sw"],
            "strings": {
                "en": {
                    "greeting_label":  "Hello",
                    "send":            "Send",
                    "emergency":       "Emergency",
                    "new_session":     "New session",
                    "export":          "Export session data",
                    "consent_title":   "Research Consent",
                    "consent_agree":   "I agree and continue",
                    "consent_decline": "Decline (demo mode only)",
                    "placeholder":     "Describe the patient's symptoms…",
                },
                "sw": {
                    "greeting_label":  "Habari",
                    "send":            "Tuma",
                    "emergency":       "Dharura",
                    "new_session":     "Kikao kipya",
                    "export":          "Hamisha data ya kikao",
                    "consent_title":   "Idhini ya Utafiti",
                    "consent_agree":   "Nakubaliana na kuendelea",
                    "consent_decline": "Kataa (hali ya maonyesho tu)",
                    "placeholder":     "Elezea dalili za mgonjwa…",
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
