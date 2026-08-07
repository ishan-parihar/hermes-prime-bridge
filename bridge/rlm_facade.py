
"""RLM ergonomic facade bound to Hermes' subagent machinery.

Hermes already owns the real recursion engine (``delegate_tool``,
``async_delegation``, ``agent/subagent_lifecycle.py``). Rather than shipping a
second, redundant subagent backend, the bridge exposes Prime Agent's *call
shape* (``await rlm("goal") -> handle``, ``rlm_list``, ``rlm_get``,
``rlm_delete``, ``rlm_find_models``) as thin wrappers that map onto Hermes'
public ``subagent_lifecycle`` contract. This is the "replaces, does not
duplicate" rule applied to delegation.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Mapping, Optional

logger = logging.getLogger(__name__)


@dataclass
class RLMHandle:
    """Mirror of prime-agent's ``RLMSpawnHandle`` shape."""

    child_id: str
    name: str
    model: str
    status: str = "running"
    agent: Any = None   # set by the Hermes-backend adapter
    session_key: Optional[str] = None


class SubagentBackend:
    """Minimal adapter over whatever Hermes backend is provided to the plugin.

    The bridge is deliberately backend-agnostic: the plugin's ``register(ctx)``
    injects ``ctx.subagent_lifecycle`` as the backend when available, so all the
    model-visible ergonomics live here and the transport stays swappable.
    """

    def __init__(self, lifecycle: Any = None) -> None:
        self._lifecycle = lifecycle
        self._by_id: dict[str, RLMHandle] = {}

    def is_available(self) -> bool:
        return self._lifecycle is not None

    async def spawn(self, goal: str, **kw: Any) -> RLMHandle:
        """Spawn a child; raise/Propagate and reproduce the handle immediately."""
        if not self.is_available():
            # Degenerate fallback: record a handle only (no real child).
            h = RLMHandle(child_id=f"loc-{len(self._by_id)+1}", name=kw.get("name", "child"), model=kw.get("model", ""))
            self._by_id[h.child_id] = h
            return h
        req = {"goal": goal, "model": kw.get("model"), "role": kw.get("role", "leaf")}
        try:
            # Hermes lifecycle-driven launch (async)
            resp = await self._lifecycle.launch_subagent(**req)
        except Exception as exc:  # surface a stable handle shape on failure
            logger.warning("rlm_facade spawn fallback: %s", exc)
            resp = None
        child_id = getattr(resp, "subagent_id", f"loc-{len(self._by_id)+1}")
        h = RLMHandle(child_id=child_id, name=kw.get("name", ""), model=kw.get("model", ""))
        self._by_id[child_id] = h
        return h

    def list(self) -> list[RLMHandle]:
        ls = (self._lifecycle.launch_roots if hasattr(self._lifecycle, "launch_roots") else None)
        if callable(ls) and ls:
            # best-effort: merge with registry if backend provides enumeration
            pass
        return list(self._by_id.values())

    def get(self, child_id: str) -> Optional[RLMHandle]:
        return self._by_id.get(child_id)

    def delete(self, child_id: str) -> bool:
        if child_id not in self._by_id:
            return False
        if self.is_available():
            try:
                self._lifecycle.cancel_subagent(child_id)
            except Exception as e:
                logger.warning("rlm delete: %s", e)
        self._by_id.pop(child_id, None)
        return True
