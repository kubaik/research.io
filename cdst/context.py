"""
cdst/context.py — BuildContext: resolved paths, hashes, and active provider.
"""

from __future__ import annotations

import hashlib
import os
from datetime import datetime, timezone
from typing import Any

from .constants import PROTOCOL_VERSION, ROOT


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
