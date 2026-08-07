"""hermes-prime-bridge — Hermes plugin directory entry point.

Hermes directory plugins must expose a top-level ``register(ctx)`` from the
plugin root ``__init__.py``. The implementation lives in the :mod:`bridge`
subpackage (which also carries the ``hermes_agent.plugins`` entry point for
pip installs); this root module simply re-exports it so both distribution
paths share one implementation and we never maintain a second copy.
"""

from .bridge import register
from .bridge._version import __version__

__all__ = ["register", "__version__"]

if __name__ == "__main__":
    print(f"hermes-prime-bridge v{__version__} (plugin entry loaded)")
