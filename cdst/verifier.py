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

        Priority order is defined by the providers list in config.yaml.
        GIT_TOKEN (GitHub Models) is expected to be listed first.
        """
        found, missing = [], []

        for p in self._providers:
            if os.getenv(p["env_key"], ""):
                found.append(p)
                log.info("OK      %-28s (%s / %s)",
                         p["env_key"], p["name"], p["model"])
            else:
                missing.append(p)
                log.info("MISSING %-28s (%s)", p["env_key"], p["name"])

        if not found:
            # Not a warning — GitHub Actions injects the key at deploy time.
            log.info(
                "No API keys found locally — GitHub Actions will inject "
                "the real key at deploy time via __API_TOKEN__ placeholder."
            )
            return None

        winner = found[0]
        log.info("✅ Active provider → %s  model=%s",
                 winner["name"], winner["model"])
        return winner
