
"""Adapter binding prime-agent's live HarnessState to a Hermes plugin store.

prime-agent's submodule exposes ``rlm.get_harness_state`` / ``HarnessState``
(continual-harness CRUD over ``prompt``/``memory``/``skill``/``subagent``
entries plus refinement snapshots). The Hermes bridge keeps one harness store
per profile/session inside ``~/.hermes/plugins/hermes-prime-bridge/`` and
re-exports the same CRUD surface to the model as a tool and slash command.

Separation vs Hermes curator: Hermes' curator *creates skills from experience*;
the harness stores *supplemental prompt/memory/subagent-spec records with
small, evidence-backed, rollable refinement*. They are complementary, and the
bridge never mutates Hermes' memory provider records.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any, Optional

from . import vendor

logger = logging.getLogger(__name__)


class HarnessError(RuntimeError):
    pass


def _default_state_dir() -> Path:
    base = Path(os.environ.get("HERMES_PLUGIN_DATA_DIR", Path.home() / ".hermes" / "plugins"))
    return base / "hermes-prime-bridge" / "harness"


class BridgeHarness:
    """Thin stateful wrapper over the vendored prime HarnessState."""

    def __init__(
        self,
        state_dir: str | Path | None = None,
        scope: str = "local",
        in_memory: bool = False,
    ) -> None:
        self._state_dir = Path(state_dir) if state_dir else _default_state_dir()
        self._scope = scope
        self._in_memory = in_memory
        self._store = None  # lazily bound to prime's HarnessState on first use

    def _ensure(self):
        if self._store is not None:
            return self._store
        if not vendor._HAS_PRIME_RUNTIME:
            raise HarnessError("prime-agent rlm unavailable; harness store disabled.")
        rlm = vendor.require_rlm()
        # Pass state_dir explicitly instead of relying on ambient RLM_HARNESS_STATE_DIR /
        # RLM_SESSION_DIR, which may already be set by the hosting runtime (e.g. a prime
        # kernel). Explicit state_dir keeps the plugin store scoped to its own directory
        # and immune to host-path aliasing.
        try:
            self._store = rlm.get_harness_state(
                state_dir=str(self._state_dir),
                global_=(self._scope == "global"),
            )
        except Exception as exc:
            if self._in_memory:
                self._store = rlm.get_harness_state(
                    state_dir=str(self._state_dir),
                    global_=(self._scope == "global"),
                )
            else:
                raise HarnessError(f"harness init: {exc}") from exc
        return self._store

    def entries(self, kind: str | None = None) -> dict[str, Any]:
        """Return entries as JSON-safe dicts (id -> {fields})."""
        from dataclasses import asdict
        s = self._ensure()
        if kind is None:
            return {k: [asdict(e) for e in v.values()] for k, v in s.entries.items()}
        if kind not in s.entries:
            return {}
        return {eid: asdict(e) for eid, e in s.entries[kind].items()}

    def upsert(self, kind: str, title: str, content: str, **kw: Any) -> Any:
        s = self._ensure()
        return s.upsert(kind=kind, title=title, content=content, **kw)

    def get(self, kind: str, entry_id: str) -> Optional[Any]:
        s = self._ensure()
        return s.entries.get(kind, {}).get(entry_id)

    def delete(self, kind: str, entry_id: str) -> bool:
        s = self._ensure()
        if entry_id not in s.entries.get(kind, {}):
            return False
        s.delete(kind=kind, id=entry_id)
        return True

    def save(self) -> None:
        if self._store is not None:
            self._store.save()

    def overview(self) -> dict[str, Any]:
        s = self._ensure()
        try:
            return s.overview()
        except Exception:
            return {"entries": self.entries()}
