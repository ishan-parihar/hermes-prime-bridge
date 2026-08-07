"""hermes-prime-bridge - Hermes plugin directory entry point.

Hermes loads directory plugins as ``hermes_plugins.<slug>`` via
``spec_from_file_location`` with the plugin dir as the package path, so the
relative re-export below works there. Pytest, by contrast, imports this root
``__init__.py`` as a bare top-level module; the relative import would then
fail. Hence: try relative first, fall back to an absolute import with the
plugin dir on sys.path (same module, no duplicate implementation).
"""

from __future__ import annotations

try:  # Hermes directory-plugin loader path
    from .bridge import register
    from .bridge._version import __version__
except ImportError:  # pytest / direct-file import context
    import os as _os
    import sys as _sys

    _here = _os.path.dirname(_os.path.abspath(__file__))
    if _here not in _sys.path:
        _sys.path.insert(0, _here)
    from bridge import register
    from bridge._version import __version__

__all__ = ["register", "__version__"]
