"""
cdst/constants.py — Shared constants for the CDST builder.
"""

from pathlib import Path

PROTOCOL_VERSION = "1.0.0"   # Bump whenever clinical content changes
ROOT = Path(__file__).parent.parent
CONFIG_FILE = ROOT / "config.yaml"

# Placeholder written into chat.js at build time.
# The real API key is injected by GitHub Actions at deploy time via sed,
# so secrets are NEVER stored in the repository.
TOKEN_PLACEHOLDER = "__API_TOKEN__"
