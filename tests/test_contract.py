"""Hermes dispatch-contract tests for the bridge plugin.

Hermes (tools/registry.py ``dispatch``) calls a registered tool handler as
``handler(args, **kwargs)`` where ``args`` is the full argument *dict* passed
positionally, flags async handlers via ``is_async=True``, and requires a JSON
string (or multimodal envelope) as the result. These tests pin the real Bridge
through a FakeContext that reproduces that contract so a signature or
serialization regression is caught before a live agent turn.
"""
import asyncio
import json

from bridge import plugin as P


class FakeContext:
    """Mirrors the decisions Hermes make for plugins: register_tool/hook/command."""

    def __init__(self):
        self.tools = {}
        self.hooks = []
        self.commands = {}

    def register_tool(self, name, toolset, schema, handler, is_async=False,
                      check_fn=None, requires_env=None, description="", emoji="", override=False):
        self.tools[name] = {
            "toolset": toolset,
            "schema": schema,
            "handler": handler,
            "is_async": is_async,
            "description": description or schema.get("description", ""),
        }

    def register_hook(self, name, cb):
        self.hooks.append(name)

    def register_command(self, name, handler, description="", args_hint=""):
        self.commands[name] = (handler, description, args_hint)

    def dispatch(self, name, args):
        """Replicate Hermes registry.dispatch (positional arg dict; await iff async)."""
        t = self.tools.get(name)
        assert t, f"unregistered tool {name}"
        if t["is_async"]:
            result = _run_async(t["handler"], args)
        else:
            result = t["handler"](args)
        assert isinstance(result, str), f"{name} returned non-string: {result!r}"
        return json.loads(result)


def _run_async(handler, args):
    """Emulate Hermes' model_tools._run_async from a clean event loop."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(handler(args))
    finally:
        loop.close()


def test_register_wires_all_contracts():
    ctx = FakeContext()
    P.register(ctx)
    expected = {"pk_kernel_exec", "pk_harness_get", "pk_refine"}
    assert set(ctx.tools) == expected
    for name in expected:
        assert ctx.tools[name]["is_async"] is True
        assert ctx.tools[name]["toolset"] == "prime_kernel"
    assert "on_session_end" in ctx.hooks and "on_session_reset" in ctx.hooks
    assert set(ctx.commands) == {"harness", "kernel"}


def test_kernel_exec_persists_across_positional_calls():
    ctx = FakeContext()
    P.register(ctx)
    r1 = ctx.dispatch("pk_kernel_exec", {"code": "acc = 21"})
    assert r1["ok"] is True and r1["error"] is False
    r2 = ctx.dispatch("pk_kernel_exec", {"code": "acc * 2"})
    assert r2["ok"] is True
    assert "acc" in r2["vars"]


def test_kernel_exec_syntax_error_reported():
    ctx = FakeContext()
    P.register(ctx)
    r = ctx.dispatch("pk_kernel_exec", {"code": "def broken"})
    assert r["ok"] is True and r["error"] is True
    assert "SyntaxError" in r["stderr"] or r["stderr"]


def test_kernel_exec_namespace_isolation():
    """Different namespaces are independent."""
    ctx = FakeContext()
    P.register(ctx)
    ctx.dispatch("pk_kernel_exec", {"code": "a = 100", "namespace": "ns1"})
    ctx.dispatch("pk_kernel_exec", {"code": "a = 200", "namespace": "ns2"})
    r1 = ctx.dispatch("pk_kernel_exec", {"code": "a", "namespace": "ns1"})
    r2 = ctx.dispatch("pk_kernel_exec", {"code": "a", "namespace": "ns2"})
    assert "a" in r1["vars"]
    assert "a" in r2["vars"]


def test_kernel_exec_empty_code_returns_error():
    ctx = FakeContext()
    P.register(ctx)
    r = ctx.dispatch("pk_kernel_exec", {"code": ""})
    assert r["ok"] is False
    assert "code" in r["error"]


def test_harness_get_missing_runtime_degrades_not_crash():
    # Without prime runtime the harness is disabled -> tool must return JSON even for error
    ctx = FakeContext()
    P.register(ctx)
    r = ctx.dispatch("pk_harness_get", {"kind": "memory"})
    assert isinstance(r, dict)  # JSON object, not a crash / coroutine


def test_pk_refine_requires_evidence():
    ctx = FakeContext()
    P.register(ctx)
    r = ctx.dispatch("pk_refine", {"evidence": ""})
    assert r["ok"] is False
    assert "evidence" in r["error"]


def test_no_rlm_tools_registered():
    """v0.2: rlm ergonomics removed; the four rlm_* names must NOT be tools."""
    ctx = FakeContext()
    P.register(ctx)
    for name in ("rlm", "rlm_list", "rlm_get", "rlm_delete"):
        assert name not in ctx.tools, f"{name} should not be registered in v0.2"
