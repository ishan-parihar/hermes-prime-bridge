
"""Hermes plugin entry point.

The instantiating contract is the Hermes plugin system: this module must expose
a top-level ``register(ctx)`` that is called by ``hermes_cli/plugins.py`` after
discovery. Docstring of the bridge lives in :mod:`bridge`.
"""

from __future__ import annotations

from typing import Any

from .plugin import register

__all__ = ["register"]


def _version() -> str:
    try:
        from . import _version as v
        return v.__version__
    except Exception:
        return "0.1.0"


if __name__ == "__main__":
    print(f"hermes-prime-bridge {_version()} (entry loaded)")
