
"""Hermes plugin registration for the hermes-prime-bridge.

This is the single wiring point. It:

* registers the bridge's model tools under a gated ``prime_kernel`` toolset,
* registers lifecycle hooks that tear down kernels on session end/reset,
* registers the RLM-facade backend (binding prime's call shape to Hermes'
  ``subagent_lifecycle`` when available),
* exposes ``/pk`` and ``/harness`` slash commands.

Replacement rule: every entry point listed here *replaces* or *extends* an
existing Hermes surface (stateless PTC -> stateful kernel; standalone delegate
-> RLM-facade over subagent_lifecycle) rather than shipping a duplicated
backend next to the Hermes one.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from . import harness, kernel, rlm_facade, schemas, vendor

logger = logging.getLogger(__name__)


def _result(obj: Any) -> dict[str, Any]:
    if isinstance(obj, dict):
        return {"ok": True, **obj}
    return {"ok": True, "data": obj}


def _err(msg: str) -> dict[str, Any]:
    return {"ok": False, "error": str(msg)}


class Bridge:
    """One Bridge instance per plugin registration (holds shared singletons)."""

    def __init__(self) -> None:
        self.kernels = kernel.KernelRegistry()
        self.harness = harness.BridgeHarness()
        self.subagent = rlm_facade.SubagentBackend()   # backend injected at register
        self._registered_tools = []

    # ------- model tool handlers -------
    async def tool_pk_kernel_exec(self, code: str, namespace: str = "default", **_: Any) -> dict[str, Any]:
        sess = self.kernels.get(namespace)
        res = sess.execute(code)
        return _result(res)

    async def tool_pk_harness_get(self, kind: str = "memory", id: str | None = None, **_: Any) -> dict[str, Any]:
        try:
            if id:
                e = self.harness.get(kind, id)
                return _result({"entry": e})
            return _result(self.harness.entries(kind))
        except Exception as exc:
            return _err(str(exc))

    async def tool_pk_refine(self, evidence: str, trigger: str = "manual", **_: Any) -> dict[str, Any]:
        # Stub: real implementation applies small updates with snapshots.
        try:
            return _result({"applied": False, "note": "refine pass recorded", "evidence": evidence})
        except Exception as exc:
            return _err(str(exc))

    async def tool_rlm(self, goal: str, name: str = "", model: str = "", **_: Any) -> dict[str, Any]:
        try:
            h = await self.subagent.spawn(goal, name=name, model=model)
            return _result({"rlm_child_id": h.child_id, "name": h.name, "model": h.model, "status": h.status})
        except Exception as exc:
            return _err(str(exc))

    async def tool_rlm_list(self, **_: Any) -> dict[str, Any]:
        return _result({"subagents": [{"id": h.child_id, "status": h.status, "name": h.name} for h in self.subagent.list()]})

    async def tool_rlm_get(self, id: str, **_: Any) -> dict[str, Any]:
        h = self.subagent.get(id)
        if h is None:
            return _err("unknown child")
        return _result({"id": h.child_id, "name": h.name, "model": h.model, "status": h.status})

    async def tool_rlm_delete(self, id: str, **_: Any) -> dict[str, Any]:
        return _result({"deleted": self.subagent.delete(id)})

    # ------- hooks ----------------
    def hook_session_end(self, **kw: Any) -> None:
        # teardown kernels so we never leak a persistent namespace
        logger.info("prime-bridge: session end -> drop kernels")
        self.kernels.reset_all()
        self.kernels = kernel.KernelRegistry()

    def hook_session_reset(self, **kw: Any) -> None:
        self.kernels.reset_all()

    # ------- slash commands ----------------
    async def cmd_harness(self, args: str) -> str:
        args = (args or "").strip().split()
        if not args:
            return json.dumps(self.harness.overview(), indent=2)
        op = args[0]
        if op == "list":
            return json.dumps(self.harness.entries(), indent=2)
        return "usage: /harness [list]"

    async def cmd_kernel(self, args: str) -> str:
        args = (args or "").strip()
        if args == "reset":
            self.kernels.reset_all()
            return "kernel reset"
        if args == "size":
            return f"active kernels: {self.kernels.size()}"
        return "usage: /kernel reset|size"


# tool schema -> handler mapping
_TOOLS = [
    (schemas.PK_KERNEL_EXEC, "pk_kernel_exec"),
    (schemas.PK_HARNESS_GET, "pk_harness_get"),
    (schemas.PK_REFINE, "pk_refine"),
    (schemas.RLM_SPAWN, "rlm"),
    (schemas.RLM_LIST, "rlm_list"),
    (schemas.RLM_GET, "rlm_get"),
    (schemas.RLM_DELETE, "rlm_delete"),
]


def register(ctx: Any) -> None:
    """Hermes plugin entry: called after discovery with a PluginContext."""
    bridge = Bridge()

    # Bind the prime-rlm facade backend from the Hermes subagent lifecycle.
    lifecycle = getattr(ctx, "subagent_lifecycle", None) or getattr(ctx, "delegation", None)
    if lifecycle is not None:
        try:
            bridge.subagent = rlm_facade.SubagentBackend(lifecycle)
        except Exception as exc:
            logger.warning("bridge: could not bind subagent lifecycle: %s", exc)

    # Register tools into a dedicated gated toolset. Handlers are the
    # ``tool_<name>`` coroutine methods on Bridge.
    for schema, _ in _TOOLS:
        handler = getattr(bridge, "tool_" + schema["name"], None)
        if handler is None:
            continue
        try:
            ctx.register_tool(
                name=schema["name"],
                toolset="prime_kernel",
                schema=schema,
                handler=handler,
                description=schema.get("description", ""),
            )
        except Exception as exc:
            # tool may already be registered (idempotence) — log and continue
            logger.warning("register tool %s: %s", schema["name"], exc)

    # Hooks
    ctx.register_hook("on_session_end", bridge.hook_session_end)
    ctx.register_hook("on_session_reset", bridge.hook_session_reset)

    # Slash commands
    ctx.register_command("harness", bridge.cmd_harness, description="://// bridge harness", args_hint="[list]")
    ctx.register_command("kernel", bridge.cmd_kernel, description="kernel stats", args_hint="[reset|size]")

    # Expose upstream rev for diagnostics
    logger.info("hermes-prime-bridge registered (prime-upstream=%s)", vendor.prime_upstream_rev())
