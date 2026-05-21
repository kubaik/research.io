"""
cdst/output_verifier.py — OutputVerifier: post-build sanity check that all
required output files exist.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

log = logging.getLogger(__name__)


class OutputVerifier:
    """Checks that all required output files exist and logs their sizes."""

    REQUIRED_FILES = [
        "index.html",
        "static/js/chat.js",
        "static/css/chat.css",
        "config.json",
        "static/data/protocols.json",
        "sw.js",
        "manifest.json",
    ]

    def __init__(self, output_dir: Path) -> None:
        self._output_dir = output_dir

    def verify(self) -> None:
        ok = True
        for rel in self.REQUIRED_FILES:
            path = self._output_dir / rel
            if path.exists():
                log.info("OK    %s (%d bytes)", rel, path.stat().st_size)
            else:
                log.error("MISSING  %s", rel)
                ok = False
        if not ok:
            sys.exit(1)
