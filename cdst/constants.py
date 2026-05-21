"""
cdst/constants.py — Shared constants for the CDST builder.
"""

from pathlib import Path

PROTOCOL_VERSION = "1.0.0"   # Bump whenever clinical content changes
ROOT = Path(__file__).parent.parent
CONFIG_FILE = ROOT / "config.yaml"
