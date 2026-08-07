
"""Stateful per-session Python kernel service.

Prime Agent's hallmark is turn-to-turn persistent kernel state. Hermes'
``code_execution_tool`` is script-per-call (stateless). The bridge adds a
lightweight, thread-safe, stateful executor: a per-session persistent globals
namespace that survives cancellation / resets, with a safe codec that avoids
crashing on weird objects. No subprocess kernel is required by default — a
process-scoped namespace is cheap and portable; a real ``ipykernel`` subprocess
(native) is a future opt-in backend.
"""

from __future__ import annotations

import io
import logging
import traceback
import threading
from contextlib import redirect_stderr, redirect_stdout
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

_MAX_OUTPUT_BYTES = 200_000


class KernelLock(RuntimeError):
    pass


class SessionKernel:
    """One persistent namespace per session_key (a thread is not shared)."""

    def __init__(self, session_key: str = "default") -> None:
        self.session_key = session_key
        self._globals: Dict[str, Any] = {"__name__": "__pk_kernel__"}
        self._lock = threading.RLock()
        self._counter = 0
        _b = __builtins__ if isinstance(__builtins__, dict) else vars(__builtins__)
        self._safe_builtins = {
            name: _b[name]
            for name in ("print", "len", "range", "list", "dict", "set", "str", "int",
                         "float", "bool", "sorted", "min", "max", "sum", "abs", "round",
                         "isinstance", "getattr", "hasattr", "enumerate", "Exception")
            if name in _b
        }
        self._safe_builtins["__import__"] = __import__
        self._globals["__builtins__"] = self._safe_builtins

    def reset(self) -> None:
        with self._lock:
            self._globals = {"__name__": "__pk_kernel__"}
            self._globals["__builtins__"] = self._safe_builtins
            self._counter = 0

    def execute(self, code: str) -> dict[str, Any]:
        """Execute one code block, returning marshalled result."""
        with self._lock:
            out = io.StringIO()
            err = io.StringIO()
            result: Optional[Any] = None
            error: Optional[str] = None
            try:
                with redirect_stdout(out), redirect_stderr(err):
                    self._counter += 1
                    compiled = compile(code, f"<kernel:{self.session_key}>", "exec")
                    exec(compiled, self._globals)
            except Exception:
                error = traceback.format_exc()
            stdout = out.getvalue()
            stderr = err.getvalue()
            return {
                "stdout": stdout[:_MAX_OUTPUT_BYTES],
                "stderr": (stderr or error or "")[:_MAX_OUTPUT_BYTES],
                "error": error is not None,
                "vars": list(self._globals.keys()),
            }


class KernelRegistry:
    """Per-session kernel registry."""

    def __init__(self) -> None:
        self._kernels: Dict[str, SessionKernel] = {}
        self._lock = threading.Lock()

    def get(self, session_key: str | None = None) -> SessionKernel:
        key = session_key or "default"
        with self._lock:
            k = self._kernels.get(key)
            if k is None:
                k = SessionKernel(key)
                self._kernels[key] = k
            return k

    def drop(self, session_key: str | None = None) -> None:
        key = session_key or "default"
        with self._lock:
            self._kernels.pop(key, None)

    def reset_all(self) -> None:
        with self._lock:
            for k in self._kernels.values():
                k.reset()

    def size(self) -> int:
        with self._lock:
            return len(self._kernels)
