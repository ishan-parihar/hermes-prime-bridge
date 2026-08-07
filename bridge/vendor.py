
"""Live-vendor loader for Prime Agent's ``rlm`` control-plane package.

The whole point of the bridge is that upstream Prime Agent code is imported
*as-is* from the pinned submodule (``vendor/prime-agent``) rather than copied,
so new Prime Agent releases integrate here via ``git submodule update``. This
module locates ``prime-agent-runtime/src`` inside the submodule and exposes the
``rlm`` package to the rest of the bridge.

Vendored layout::

    vendor/prime-agent/
      prime-agent-runtime/src/rlm/{__init__,harness,mcp_base,skill}.py

If the submodule is missing we degrade with a diagnosable error instead of
crashing Hermes.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

_BRIDGE_ROOT = Path(__file__).resolve().parent.parent
VENDOR_DIR = _BRIDGE_ROOT / "vendor" / "prime-agent"
VENDOR_RUNTIME_SRC = VENDOR_DIR / "prime-agent-runtime" / "src"

_HAS_PRIME_RUNTIME = False
_VENDOR_IMPORT_ERROR: Exception | None = None

if VENDOR_RUNTIME_SRC.is_dir():
    if str(VENDOR_RUNTIME_SRC) not in sys.path:
        sys.path.insert(0, str(VENDOR_RUNTIME_SRC))
    try:
        import rlm  # noqa: F401  (installs into sys.modules)
        _HAS_PRIME_RUNTIME = True
    except Exception as exc:  # pragma: no cover - env dependent
        _VENDOR_IMPORT_ERROR = exc
else:
    _VENDOR_IMPORT_ERROR = FileNotFoundError(
        f"prime-agent submodule runtime not found at {VENDOR_RUNTIME_SRC}. "
        "Run:  git submodule update --init --recursive"
    )


def require_rlm():
    """Return the live prime-agent ``rlm`` module or raise a useful error."""
    if not _HAS_PRIME_RUNTIME:
        raise ImportError(
            f"prime-agent bridge: rlm unavailable. "
            f"{getattr(_VENDOR_IMPORT_ERROR, 'strerror', '') or _VENDOR_IMPORT_ERROR}"
        )
    return sys.modules.get("rlm") or __import__("rlm")


def prime_upstream_rev() -> str | None:
    """Return the pinned submodule commit short-hash (best-effort)."""
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=str(VENDOR_DIR), capture_output=True, text=True, timeout=5,
        )
        return out.stdout.strip() or None
    except Exception:
        return None
