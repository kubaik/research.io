"""
cdst/protocols.py — ProtocolsData: structured IMCI/MUAC/Malaria/Maternal/Newborn
protocol data and JSON serialisation.
"""

from __future__ import annotations

from typing import Any

from .constants import PROTOCOL_VERSION


class ProtocolsData:
    """
    Owns the structured IMCI/MUAC/Malaria/Maternal/Newborn protocol data
    and serialises it to a dict ready for JSON output.
    """

    def build(self) -> dict[str, Any]:
        return {
            "version":        PROTOCOL_VERSION,
            "imci":           self._imci(),
            "muac":           self._muac(),
            "malaria_rdt":    self._malaria_rdt(),
            "maternal":       self._maternal(),
            "referral_levels": self._referral_levels(),
            "newborn":        self._newborn(),
        }

    # ------------------------------------------------------------------
    # Protocol sections
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
            "title":             "Malaria RDT Protocol",
            "positive":          "RDT+ → Confirm species, treat with ACT per national protocol",
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
