
"""Python-executable skill support (WIP).

Mirrors prime-agent's "skills are executable Python packages": a skill folder
may carry ``SKILL.md`` plus an importable Python module exposing ``run(...)``.
This loader bridges that onto Hermes' existing markdown skill surface, so a
markdown skill can optionally `g the python backend without a second skill
registry.
"""

from __future__ import annotations

import importlib
import logging
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

_MARKERS = ("run.py", "__init__.py", "main.py")


def find_python_entry(skill_dir: Path) -> Optional[Path]:
    """Return the python module path for a skill dir, or None."""
    for marker in _MARKERS:
        p = skill_dir / marker
        if p.exists():
            return p
    return None


def load_skill_entry(skill_dir: Path):
    """Import the python runner module and return its ``run`` callable if present."""
    entry = find_python_entry(skill_dir)
    if entry is None:
        return None
    import importlib.util
    spec = importlib.util.spec_from_file_location(skill_dir.name + "_impl", entry)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return getattr(mod, "run", None)
