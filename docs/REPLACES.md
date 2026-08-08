# What the bridge replaces (and what it deliberately reuses)

This file records the "replaces, not duplicates" contract. The rule: if Hermes
already owns a capability, the bridge **adapts** its call surface or extends
it — it never plants a second, competing backend.

## v0.2 scope correction

In v0.1 the bridge also exposed `rlm` / `rlm_list` / `rlm_get` / `rlm_delete`
subagent ergonomics as a thin call-shape adapter over Hermes'
`subagent_lifecycle`. **These have been removed.** They duplicated Hermes'
native `delegate_task` (which already supports batches, roles, background
execution, and model selection) without adding capability. For subagent work,
use `delegate_task`.

The bridge now ships only the one capability Hermes lacks natively: a
**stateful Python kernel** plus its **continual-harness refinement store**.

## v0.2 surface

| # | Hermes capability | Bridge action |
|---|---|---|
| 1 | `tools/code_execution_tool.py` (stateless PTC) | **Replaced for interactive work** by `pk_kernel_exec` — the persistent kernel where variables and imports survive across turns. `execute_code` stays for batch/RPC tool-calling scripts where isolation is wanted. |
| 2 | `curator.py` + `memory_manager.py` | **Complemented, not duplicated.** Harness store is scoped supplemental records with refinement/rollback; never writes Hermes memory-provider records. |
| 3 | `skills/` + `skill_commands.py` | **Extended** with Python-executable entries via `pyskill`, folding into the existing /skill surface. |
| 4 | `delegate_task` (subagent spawn) | **Untouched.** Use `delegate_task` for subagent work. v0.2 removed the redundant `rlm*` ergonomics. |
| 5 | MCP tool, cron, gateway, daemons | **Untouched.** Out of scope. |

Definition of done for a bridge component: it must *interoperate with* the
Hermes surface it touches (register through `ctx`, hook into lifecycle, read
only its own state) and it must make the Hermes way of doing that thing
redundant wherever that is sensible.
