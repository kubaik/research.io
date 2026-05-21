"""
cdst/verifier.py — ProviderVerifier: API key discovery and reporting.
"""

from __future__ import annotations

import logging
import os
from typing import Any

log = logging.getLogger(__name__)


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
