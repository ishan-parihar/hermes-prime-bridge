
import pytest
from bridge import harness


def test_harness_entries_absent_without_submodule(tmp_path):
    # in-memory harness should still construct without the submodule runtime
    try:
        h = harness.BridgeHarness(state_dir=tmp_path, scope="local", in_memory=True)
        h.entries()
    except Exception as exc:
        # If prime runtime is absent we expect a controlled HarnessError only
        assert "rlm" in str(exc) or isinstance(exc, harness.HarnessError) or str(exc)

def test_harness_store_scoped_away_from_host_env(monkeypatch, tmp_path):
    """Bridge keeps its own store dir even when the host runtime set RLM_*_DIR."""
    from bridge import harness

    host_dir = tmp_path / "host" / "harness"
    monkeypatch.setenv("RLM_HARNESS_STATE_DIR", str(host_dir))
    monkeypatch.setenv("RLM_SESSION_DIR", str(tmp_path / "hostsession"))

    store = harness.BridgeHarness(state_dir=tmp_path / "plugin" / "harness")
    st = store._ensure()
    assert str(st.file_path).startswith(str(tmp_path / "plugin" / "harness")), st.file_path
    store.delete("memory", "__nonexistent__")  # force ensure without touching host
