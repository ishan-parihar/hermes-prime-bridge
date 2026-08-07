import pytest

from bridge.kernel import KernelRegistry


def test_stateful_kernel_persists_across_exec():
    kr = KernelRegistry()
    k = kr.get("s1")
    r1 = k.execute("x = 41")
    assert r1["error"] is False
    # state persists across turns: 'x' remains in the namespace and mutates
    r2 = k.execute("x = x + 1")
    assert r2["error"] is False
    assert "x" in r2["vars"]


def test_kernel_reset():
    kr = KernelRegistry()
    k = kr.get("s2")
    k.execute("y = 10")
    k.reset()
    assert "y" not in k._globals
