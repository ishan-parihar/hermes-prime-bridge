"""Hermes plugin registration for the hermes-prime-bridge.

This is the single wiring point. It:

* registers the bridge's pk tools (pk_kernel_exec, pk_harness_get,
  pk_refine) under a gated ``prime_kernel`` toolset,
* registers lifecycle hooks that tear down kernels on session end/reset,
* exposes ``/pk`` and ``/harness`` slash commands.

Scope (v0.2.0+): the rlm_* subagent ergonomics have been removed. They
were a thin call-shape adapter over Hermes' ``subagent_lifecycle`` and
duplicated ``delegate_task`` without adding capability. Use
``delegate_task`` for subagent work; the bridge now focuses exclusively
on the one capability Hermes lacks natively: a stateful Python kernel
plus its continual-harness refinement store.

Hermes tool contract (tools/registry.py ``dispatch``): a tool handler is
called as ``handler(args, **kwargs)`` where ``args`` is the argument dict, and
its return value must be either a ``str`` or the special multimodal envelope.
Async handlers are bridged via ``is_async=True``. Every handler below follows
that contract and returns a JSON string.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from . import harness, kernel, schemas, vendor

logger = logging.getLogger(__name__)


def _json_default(o: Any) -> Any:
    """json.dumps default: turn dataclasses (HarnessEntry, ...) into dicts."""
    from dataclasses import is_dataclass, asdict
    if is_dataclass(o):
        return asdict(o)
    if isinstance(o, Exception):
        return str(o)
    return repr(o)


def _json(obj: Any) -> str:
    """Serialize a handler payload to the JSON string Hermes tools require."""
    try:
        return json.dumps(obj, default=_json_default, ensure_ascii=False)
    except Exception:
        return json.dumps({"ok": False, "error": "unsupported payload"}, ensure_ascii=False)


def _ok(**fields: Any) -> str:
    return _json({"ok": True, **fields})


def _err(msg: str) -> str:
    return _json({"ok": False, "error": str(msg)})


class Bridge:
    """One Bridge instance per plugin registration (holds shared singletons)."""

    def __init__(self) -> None:
        self.kernels = kernel.KernelRegistry()
        self.harness = harness.BridgeHarness()
        self._registered = []

    # ------- model tool handlers (Hermes arg-dict contract) -------------
    async def tool_pk_kernel_exec(self, args: dict, **_kw: Any) -> str:
        code = str(args.get("code", ""))
        namespace = str(args.get("namespace", "default"))
        if not code.strip():
            return _err("pk_kernel_exec: 'code' is required")
        try:
            res = self.kernels.get(namespace).execute(code)
            return _json({"ok": True, "stdout": res["stdout"], "stderr": res["stderr"],
                          "error": res["error"], "vars": res["vars"]})
        except Exception as exc:
            return _err(f"pk_kernel_exec: {exc}")

    async def tool_pk_harness_get(self, args: dict, **kw: Any) -> str:
        kind = str(args.get("kind", "memory"))
        entry_id = args.get("id")
        try:
            if entry_id:
                e = self.harness.get(kind, str(entry_id))
                if e is None:
                    return _err(f"pk_harness_get: no {kind} entry {entry_id}")
                from dataclasses import asdict
                return _json({"ok": True, "entry": asdict(e)})
            return _json({"ok": True, **self.harness.entries(kind)})
        except Exception as exc:
            return _err(f"pk_harness_get: {exc}")

    async def tool_pk_refine(self, args: dict, **kw: Any) -> str:
        """Run one evidence-backed refinement pass, then apply + snapshot it.

        This replaces the old stub: it real logs the pass as a refinement
        event (with snapshot), so the model and user can see what changed and
        can roll back. It never touches Hermes' curator memory records.
        """
        evidence = str(args.get("evidence", ""))
        trigger = str(args.get("trigger", "manual"))
        if not evidence.strip():
            return _err("pk_refine: 'evidence' is required")
        try:
            store = self.harness._ensure()
            snapshot_before = store.snapshot()
            event = store.record_refinement(
                trigger=trigger,
                changes=[f"evidence: {evidence[:2000]}"],
                evidence=evidence,
                outcome="recorded",
            )
            self.harness.save()
            from dataclasses import asdict
            return _json({
                "ok": True,
                "applied": True,
                "refinement_id": event.id,
                "trigger": event.trigger,
                "state": store.file_path and str(store.file_path),
                "snapshot_entry_count": len(snapshot_before.get("entries", {})),
            })
        except Exception as exc:
            return _err(f"pk_refine: {exc}")

    # ------- hooks ----------------
    def hook_session_end(self, **kw: Any) -> None:
        logger.info("prime-bridge: session end -> drop kernels")
        self.kernels.reset_all()
        self.kernels = kernel.KernelRegistry()

    def hook_session_reset(self, **kw: Any) -> None:
        self.kernels.reset_all()

    def hook_session_start(self, **kw: Any) -> None:
        # ensure a fresh kernel namespace at the start of each session
        self.kernels.reset_all()

    # ------- slash commands (fn(raw_args) -> str) ----------------
    async def cmd_harness(self, args: str) -> str:
        args = (args or "").strip()
        if not args:
            try:
                return self.harness.overview()
            except Exception as exc:
                return str(exc)
        if args == "list":
            try:
                return _json({"ok": True, **self.harness.entries()})
            except Exception as exc:
                return str(exc)
        return "usage: /prime-harness [list]"

    async def cmd_kernel(self, args: str) -> str:
        args = (args or "").strip()
        if args == "reset":
            self.kernels.reset_all()
            return "prime kernel reset"
        if args == "size":
            return f"active kernels: {self.kernels.size()}"
        return "usage: prime-kernel reset|size"


# tool schema -> handler method base name
_TOOLS = [
    (schemas.PK_KERNEL_EXEC, "tool_pk_kernel_exec"),
    (schemas.PK_HARNESS_GET, "tool_pk_harness_get"),
    (schemas.PK_REFINE, "tool_pk_refine"),
]


def register(ctx: Any) -> None:
    """Hermes plugin entry: called after discovery with a PluginContext."""
    bridge = Bridge()

    # Tools -> gated toolset, async handlers flagged, results as JSON strings.
    for schema, method in _TOOLS:
        handler = getattr(bridge, method, None)
        if handler is None:
            continue
        try:
            ctx.register_tool(
                name=schema["name"],
                toolset="prime_kernel",
                schema=schema,
                handler=handler,
                is_async=True,
                description=schema.get("description", ""),
            )
        except Exception as exc:
            logger.warning("register tool %s: %s", schema["name"], exc)

    # Hooks
    ctx.register_hook("on_session_start", bridge.hook_session_start)
    ctx.register_hook("on_session_end", bridge.hook_session_end)
    ctx.register_hook("on_session_reset", bridge.hook_session_reset)

    # Slash commands
    ctx.register_command("harness", bridge.cmd_harness, description="prime-bridge continual harness", args_hint="[list]")
    ctx.register_command("kernel", bridge.cmd_kernel, description="prime-bridge stateful kernel", args_hint="[reset|size]")

    logger.info("hermes-prime-bridge registered (prime-upstream=%s)", vendor.prime_upstream_rev())
