"""
cdst/builder.py — CDSTBuilder: top-level orchestrator for the build pipeline.

Exposes one method per CLI command:
    init()   — write default config.yaml
    verify() — check API keys
    build()  — full static-site generation
    auto()   — init + build + verify
"""

from __future__ import annotations

import logging
from typing import Any

from .config import AppConfig
from .context import BuildContext
from .html_writer import HtmlWriter
from .js_writer import JavaScriptWriter
from .output_verifier import OutputVerifier
from .static_writer import StaticFileWriter
from .verifier import ProviderVerifier

log = logging.getLogger(__name__)


class CDSTBuilder:
    """
    Top-level orchestrator. Exposes one method per CLI command.
    """

    def init(self) -> None:
        """Write default config.yaml (no-op if it already exists)."""
        AppConfig.save_defaults()

    def verify(self) -> dict[str, Any] | None:
        """Check which provider API keys are present and log results."""
        cfg = AppConfig.load()
        return ProviderVerifier(cfg).verify()

    def build(self) -> None:
        """Full static-site generation pipeline."""
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
        """Full pipeline: init → build (which includes verify)."""
        self.init()
        self.build()
