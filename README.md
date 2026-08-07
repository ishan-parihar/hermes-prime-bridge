
# hermes-prime-bridge

A **bridge plugin** that ports Prime Agent's distinctive strengths into Hermes
Agent, sourcing live upstream code from Prime Agent so upgrades integrate
directly — while **replacing** overlapping Hermes capability instead of leaving
it redundantly duplicated.

## What it brings

| Prime-Agent feature | How Hermes currently does it | Bridge replaces it with |
|---|---|---|
| **Stateful IPython control plane** | `code_execution_tool.py` (stateless script-per-call) | `pk_kernel_exec` — persistent per-session kernel state across turns |
| **Continual Harness** (`prompt/memory/skill/subagent`) | Hermes memory + curator (skill creation) | `pk_harness_*` + `/harness` — versioned, scoped, refinement-ready store |
| **RLM call ergonomics** (`await rlm()` -> handle) | `delegate_tool` / `async_delegation` / `subagent_lifecycle` (powerful, verbose) | `rlm`/`rlm_list`/`rlm_get`/`rlm_delete` thin facade over Hermes `subagent_lifecycle` |
| **Skills as executable Python packages** | markdown-first SKILL.md | `pyskill` loader (see roadmap) |

## How "replaces, not duplicates" is enforced

- **Single recursion backend:** the RLM facade is a *call-shaped adapter* over
  Hermes' own `subagent_lifecycle`; it never spins up a second subagent engine.
- **Single kernel authority:** the stateful kernel is *the* Python execution
  path; the stateless PTC path is flagged for removal in favor of this.
- **Separate memory lanes:** the harness store reads/writes only its own scoped
  JSON; it never mutates Hermes' memory-provider records (avoids clone between
  curator and harness).

## Live upstream integration

Prime Agent is pulled as a **git submodule** at `vendor/prime-agent`. The
control-plane `rlm` package (harness, mcp_base, skill) is imported directly
from that pinned checkout via `bridge/vendor.py`. To absorb newer Prime Agent:

```bash
git submodule update --remote  # pull upstream main into vendor/
# review, then:  bridge picks it up on next import
```

## Layout

```
pyproject.toml        # pip-installable; hermes_agent.plugins entry group
plugin.yaml           # Hermes directory-plugin manifest
bridge/
  __init__.py         # register(ctx) re-export
  plugin.py           # register(ctx): tools, hooks, slash commands
  vendor.py           # import prime-agent rlm live from submodule
  kernel.py           # persistent per-session kernel
  harness.py          # continual-harness store adapter
  rlm_facade.py       # RLM call shape over Hermes subagent_lifecycle
  schemas.py          # LLM tool schemas
  pyskill.py          # python-executable skill support (WIP)
tests/
vendor/prime-agent    # submodule (pinned)
```


## Install (native Hermes, any host)

The repo ships a ready installer at `scripts/install.sh`. It:

- discovers Hermes Home (default `~/.hermes`) and the plugins dir,
- clones the bridge **with its prime-agent submodule** into
  `~/.hermes/plugins/hermes-prime-bridge/` (git clone --recurse-submodules so the
  vendored upstream is an independent, pinned checkout),
- enables the plugin via `hermes plugins enable`,
- runs `hermes doctor` and lists the plugin to confirm integration.

```bash
# from a clone of this repo (defaults to the current working tree)
./scripts/install.sh

# or from a git remote, on any host native Hermes
./scripts/install.sh https://github.com/YOU/hermes-prime-bridge.git
```

After install verify with:

```bash
hermes plugins list | grep hermes-prime-bridge   # -> enabled, source: git
hermes tools list                                # -> prime_kernel toolset (🔌 Prime Kernel)
hermes doctor                                    # -> prime_kernel under Tool Availability
```

To pull newer Prime Agent at runtime (bridged live-upstream):

```bash
hermes plugins update hermes-prime-bridge        # updates bridge (git pull)
cd ~/.hermes/plugins/hermes-prime-bridge && git submodule update --init --recursive
```

> Reproduces/replaces: the stateless script PTC path and the verbose delegate
> call, via the stateful kernel and RLM facade — no redundant backend is kept.

## Ensure live-upstream integration

Prime Agent is pulled as a **git submodule** at `vendor/prime-agent`. The
bridge imports prime-agent's `rlm` package directly from that pinned checkout
via `bridge/vendor.py`, so new upstream code integrates at install/update time.



```bash
git clone git@github.com:/YOU/hermes-prime-bridge.git
git submodule update --init --recursive
uv pip install -e .            # or: python -m pip install -e .
hermes plugins list            # should show hermes-prime-bridge
hermes tools                   # prime_kernel toolset
```

## Roadmap
1. `pk_kernel_exec` stateful kernel (done - basic)
2. harness store + `/harness` (done - basic)
3. `rlm_*` facade over subagent_lifecycle (done - backend-injectable)
4. `pyskill` executable skills (WIP)
5. `/refine` evidence-backed auto-update (stub)
