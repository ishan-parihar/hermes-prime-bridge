
import pytest
from bridge import vendor


def test_vendor_resolves_to_submodule():
    assert vendor.VENDOR_RUNTIME_SRC.is_dir()


def test_require_rlm():
    try:
        rlm = vendor.require_rlm()
        assert hasattr(rlm, "get_harness_state") or hasattr(rlm, "run")
    except ImportError as e:
        pytest.skip(f"prime runtime not importable: {e}")
