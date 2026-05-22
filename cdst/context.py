"""
cdst/context.py — BuildContext: resolved paths, hashes, and active provider.
"""

from __future__ import annotations

import hashlib
import os
from datetime import datetime, timezone
from typing import Any

from .constants import PROTOCOL_VERSION, ROOT, TOKEN_PLACEHOLDER


class BuildContext:
    """
    Immutable value object produced once per build.

    token is always TOKEN_PLACEHOLDER ("__API_TOKEN__") — the real secret
    is injected by GitHub Actions at deploy time via sed, so no key is
    ever committed to the repository.
    """

    def __init__(self, cfg: dict[str, Any]) -> None:
        self.cfg = cfg
        self.output_dir = ROOT / "docs"
        self.build_hash = self._compute_hash()
        self.provider = self._resolve_provider()
        # Always write the placeholder — CI replaces it with the real key.
        self.token = TOKEN_PLACEHOLDER
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
        """
        Determine which provider config to embed in chat.js.
        Checks env vars to find the first configured provider so the
        correct endpoint/model/auth settings are written — but the
        actual token value is always TOKEN_PLACEHOLDER.
        """
        for p in self.cfg["models"]["providers"]:
            if os.getenv(p["env_key"], ""):
                return p
        # No key set locally — default to anthropic config so the
        # generated JS has the right endpoint/headers ready for CI injection.
        return self.cfg["models"]["providers"][0]
