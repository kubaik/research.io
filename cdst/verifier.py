"""
cdst/verifier.py — ProviderVerifier: API key discovery and reporting.
"""

from __future__ import annotations

import logging
import os
from typing import Any

log = logging.getLogger(__name__)


class ProviderVerifier:
    """
    Checks which provider API keys are present locally and logs the results.

    At build time this is informational only — the JavaScript bundle now embeds
    ALL providers with named placeholders (e.g. __GIT_TOKEN__).  GitHub Actions
    injects each real secret into its own placeholder at deploy time, so every
    provider whose secret is set in GitHub will be available in the browser.

    The returned provider (if any) is used only to set ctx.model_id /
    ctx.provider_name in the build metadata comment at the top of chat.js.
    It does NOT restrict which providers the browser can use.
    """

    def __init__(self, cfg: dict[str, Any]) -> None:
        self._providers = cfg["models"]["providers"]

    def verify(self) -> dict[str, Any] | None:
        """
        Log found/missing keys and return the first active provider dict,
        or None if no keys are configured locally.

        Notes
        -----
        • Priority order follows the providers list in config.yaml.
          GIT_TOKEN (GitHub Models) is expected to be listed first.
        • A missing key locally is NOT a build error — GitHub Actions injects
          keys at deploy time via per-provider __ENV_KEY__ placeholders.
        • All providers with keys set in GitHub Secrets will be active in the
          deployed app regardless of what is found here locally.
        """
        found, missing = [], []

        for p in self._providers:
            key_value = os.getenv(p["env_key"], "")
            if key_value:
                found.append(p)
                log.info(
                    "OK      %-28s  provider=%-12s  model=%s",
                    p["env_key"], p["name"], p["model"],
                )
            else:
                missing.append(p)
                log.info(
                    "MISSING %-28s  provider=%-12s  (placeholder __%-s__ will be in chat.js)",
                    p["env_key"], p["name"], p["env_key"],
                )

        if missing:
            log.info(
                "%d provider(s) have no local key — their __PLACEHOLDER__ tokens "
                "will be injected by GitHub Actions at deploy time: %s",
                len(missing),
                ", ".join(p["name"] for p in missing),
            )

        if not found:
            log.info(
                "No API keys found in local environment. "
                "The browser will skip providers whose placeholder is not replaced. "
                "Set secrets in GitHub → Settings → Secrets → Actions to activate them."
            )
            return None

        winner = found[0]
        log.info(
            "✅ Primary local provider → %s  model=%s  "
            "(all %d provider(s) will be embedded in chat.js)",
            winner["name"], winner["model"], len(self._providers),
        )
        return winner
