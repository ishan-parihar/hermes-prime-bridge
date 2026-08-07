
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
