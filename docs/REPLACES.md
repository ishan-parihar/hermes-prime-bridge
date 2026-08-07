
# What the bridge replaces (and what it deliberately reuses)

This file records the "replaces, not duplicates" contract. The rule: if Hermes
already owns a capability, the bridge **adapts** its call surface or extends
it — it never plants a second, competing backend.

| # | Hermes capability | Bridge action |
|---|---|---|
| 1 | `tools/code_execution_tool.py` (stateless PTC) | **Replaced** by the persistent kernel for interactive/exploratory stateful Python. PTC stays only for batch/RPC tool-calling scripts where isolation is wanted. |
| 2 | `delegate_tool.py` / `async_delegation.py` / `subagent_lifecycle.py` | **Reused as the RLM backend.** Bridge only adds prime call ergonomics (`rlm`->handle). No new recursion engine. |
| 3 | `curator.py` + `memory_manager.py` | **Complemented, not duplicated.** Harness store is scoped supplemental records with refinement/rollback; never writes Hermes memory-provider records. |
| 4 | `skills/` + `skill_commands.py` | **Extended** with Python-executable entries via `pyskill`, folding into the existing /skill surface. |
| 5 | MCP tool, cron, gateway, daemons | **Untouched.** Out of scope; prime-agent duplicates would add no value. |

Definition of done for a bridge component: it must *interoperate with* the
Hermes surface it touches (register through `ctx`, hook into lifecycle, read
only its own state) and it must make the Hermes way of doing that thing
redundant wherever that is sensible.
