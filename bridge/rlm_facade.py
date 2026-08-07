"""RLM ergonomic facade bound to Hermes' subagent machinery.

Hermes owns the real recursion engine (``agent/subagent_lifecycle.py`` ->
``SubagentLifecycleService``). Rather than shipping a second backend, the bridge
exposes Prime Agent's *call shape* (``await rlm("goal") -> handle``,
``rlm_list``, ``rlm_get``, ``rlm_delete``) as thin wrappers over that service,
keeping the transport swappable.

Hermes' service API (verified against the installed agent v0.20.0):
    launch(request: SubagentLaunchRequest) -> SubagentHandle      # sync
    status(handle) -> SubagentStatus
    wait(handle, *, timeout_seconds) -> SubagentTerminalState
    cancel(handle, *, reason) -> SubagentCancelResult
    result(handle) -> SubagentResult
    reconnect(handle) -> SubagentReconnectResult

``launch`` returns a handle immediately (the child runs on its own executor);
``SubagentHandle`` exposes ``subagent_id/provider/model/role/depth``.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class RLMHandle:
    """Mirror of prime-agent's ``RLMSpawnHandle`` shape."""

    child_id: str
    name: str
    model: str
    status: str = "running"
    agent: Any = None
    session_key: Optional[str] = None


class SubagentBackend:
    """Adapter over Hermes' ``SubagentLifecycleService``.

    Backend-agnostic: the plugin's ``register(ctx)`` injects
    ``ctx.subagent_lifecycle`` when available; all model-visible ergonomics live
    here. When no lifecycle is present (e.g. a bare/mock context), it degrades
    to an in-memory handle registry so tool calls still return a stable shape.
    """

    def __init__(self, lifecycle: Any = None) -> None:
        self._lifecycle = lifecycle
        self._by_id: dict[str, RLMHandle] = {}

    def is_available(self) -> bool:
        return self._lifecycle is not None

    # ---- resolve a Hermes handle to our RLMHandle mirror ----
    def _mirror(self, hermes_handle: Any, *, name: str = "", model: str = "") -> RLMHandle:
        child_id = str(getattr(hermes_handle, "subagent_id", "") or "")
        if not child_id:
            child_id = f"loc-{len(self._by_id) + 1}"
        status = "running"
        try:
            st = self._lifecycle.status(hermes_handle)
            state = getattr(st, "state", None)
            status = str(getattr(state, "value", state) or "running")
        except Exception as exc:
            logger.debug("rlm status: %s", exc)
        return RLMHandle(
            child_id=child_id,
            name=name or str(getattr(hermes_handle, "role", "") or "child"),
            model=model or str(getattr(hermes_handle, "model", "") or ""),
            status=status,
            agent=hermes_handle,
        )

    async def spawn(self, goal: str, **kw: Any) -> RLMHandle:
        """Spawn a child via the Hermes lifecycle, returning the handle immediately."""
        name = kw.get("name", "") or ""
        model = kw.get("model", "") or ""
        if not self.is_available():
            h = RLMHandle(child_id=f"loc-{len(self._by_id) + 1}", name=kw.get("name", "child"),
                          model=model, status="recorded")
            self._by_id[h.child_id] = h
            return h
        try:
            from agent.subagent_lifecycle import SubagentLaunchRequest
            req = SubagentLaunchRequest(
                goal=goal,
                role=kw.get("role", "leaf"),
                model=(model or None),
                metadata={"source": "hermes-prime-bridge", "name": name} if name else {"source": "hermes-prime-bridge"},
            )
            hermes_handle = self._lifecycle.launch(req)
        except Exception as exc:  # surface a stable handle on failure
            logger.warning("rlm_facade spawn: %s", exc)
            h = RLMHandle(child_id=f"loc-{len(self._by_id) + 1}", name=name, model=model, status="pending")
            self._by_id[h.child_id] = h
            return h
        h = self._mirror(hermes_handle, name=name, model=model)
        self._by_id[h.child_id] = h
        return h

    def list(self) -> list[RLMHandle]:
        return list(self._by_id.values())

    def get(self, child_id: str) -> Optional[RLMHandle]:
        return self._by_id.get(child_id)

    def delete(self, child_id: str) -> bool:
        h = self._by_id.pop(child_id, None)
        if h is None:
            return False
        if self.is_available() and h.agent is not None:
            try:
                self._lifecycle.cancel(h.agent, reason="deleted via rlm_delete")
            except Exception as exc:
                logger.warning("rlm delete: %s", exc)
        return True
