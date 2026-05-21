#!/usr/bin/env python3
"""
chatbot_system.py — EVAH-Aligned Health CDST Chatbot Builder  v1.0
Production-ready Clinical Decision Support Tool for community health workers
in LMICs. Aligned with J-PAL EVAH Pathway A/B RFP.

Commands:
    python chatbot_system.py init     # Create config.yaml from defaults
    python chatbot_system.py build    # Build static site → docs/
    python chatbot_system.py auto     # Full pipeline: init → build → verify
    python chatbot_system.py verify   # Check secrets and config only
"""

from __future__ import annotations

import argparse
import logging

from cdst.builder import CDSTBuilder

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


# ===========================================================================
# CLI — argument parsing & dispatch
# ===========================================================================

class CLI:
    """Parses command-line arguments and dispatches to CDSTBuilder."""

    COMMANDS = ("init", "build", "auto", "verify")

    def run(self) -> None:
        parser = argparse.ArgumentParser(
            description="HealthAssist CDST Builder v1",
        )
        parser.add_argument(
            "command",
            choices=self.COMMANDS,
            help="Command to run",
        )
        args = parser.parse_args()
        builder = CDSTBuilder()
        getattr(builder, args.command)()


# ===========================================================================
# Entry point
# ===========================================================================

if __name__ == "__main__":
    CLI().run()
