<p align="center">
  <img src="./assets/readme/hero.svg" width="100%" alt="hermes-prime-bridge — Prime Agent's persistent kernel, continual harness, and lean subagent calls, live-sourced straight off Prime Agent into Hermes. Replaces, not duplicates.">
</p>

**hermes-prime-bridge** is a [Hermes Agent](https://github.com/primeintellect-ai/hermes-agent) plugin that ports the strengths of [Prime Agent](https://github.com/PrimeIntellect-ai/prime-agent) — a stateful kernel, a continual-refinement harness, and ergonomic subagent calls — directly from **live upstream Prime source**. Rather than forking or copy-pasting, the plugin pulls Prime Agent as a pinned submodule at `vendor/prime-agent` and imports its real `rlm` runtime, so upgrades propagate on their own.

The guiding directive is **replace, never duplicate**: every capability the bridge brings either *replaces* a redundant Hermes path or is an *adapter* over a Hermes-owned backend. It never plants a second, competing engine side-by-side with the thing it touches.

---

## Why it exists

Hermes is a narrow-waisted, stateless agent: each Python call is a fresh subprocess, tool schemas stay lean, and the "prompt-contract" (PTC) pipeline rebuilds context per message. Prime Agent grew different strengths: a **persistent kernel**, a **continual harness** of versioned prompt / memory / skill / subagent records, and an **`await rlm(...)`** ergonomics for recursive calls.

This plugin keeps Hermes' architecture intact while importing those strengths as *one* integration surface — a **live** one, so nothing ships as a frozen copy.

---

## What it brings

| Prime feature | Hermes today | The bridge replaces it with |
|---|---|---|
| **Persistent stateful kernel** | `code_execution_tool` (stateless script-per-call) | `pk_kernel_exec` — kernel state persists across turns |
| **Continual harness** (`memory/prompt/skill/subagent`) | curator + memory_manager | `pk_harness_*` + `/harness` — versioned, scoped, refinement-ready |
| **RLM call ergonomics** (`await rlm()`) | verbose delegate/async calls | `rlm` / `rlm_list` / `rlm_get` / `rlm_delete` facade over `subagent_lifecycle` |
| **Python-executable skills** | markdown-first SKILL.md | `pyskill` loader (roadmap) |

Full tour of the code: [`docs/REPLACES.md`](docs/REPLACES.md) records the exact replace-vs-reuse-vs-untouched decision for every surface.

---

## The replaces-not-duplicates contract


<p align="center">
  <img src="./assets/readme/mechanism.svg" width="100%" alt="Diagram: Hermes Agent connects over a bridge facade to the live Prime Agent submodule. Three contracts follow — REPLACES the stateless PTC with the persistent kernel; REUSES the subagent_lifecycle backend via the rlm facade; UNTOUCHED MCP/cron/gateway/daemons.">
</p>

The rule, per layer:

- **One recursion, not two.** The `rlm` facade is a *call-shape adapter* over Hermes' `subagent_lifecycle` — it launches, lists, inspects, and removes through Hermes' own backend. There is never a second subagent engine.
- **One kernel authority.** The stateful kernel is *the* Python execution path; the stateless script path is considered redundant for interactive work.
- **Separate memory lanes.** The harness store reads/writes its own scoped JSON; it never mutates Hermes' memory-provider records.
- **Live upstream.** Every Python import of the Prime runtime resolves through `vendor/prime-agent/.../rlm` — a real pinned checkout, not a snapshot — so `git submodule update --remote` pulls new Prime behavior into the bridge.

---

## Quick start (native Hermes, any host)

**One command** — install from any machine that has `curl` and `git`:

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/ishan-parihar/hermes-prime-bridge/main/scripts/install.sh) \
  https://github.com/ishan-parihar/hermes-prime-bridge.git
```

The installer finds Hermes home, clones the bridge — **with its live submodule** — into `~/.hermes/plugins/hermes-prime-bridge/`, enables it, and confirms with `hermes doctor`. No repo checkout required on the target host.

Prefer the source over the script? Clone with the submodule and run the installer from it:

```bash
git clone --recurse-submodules https://github.com/ishan-parihar/hermes-prime-bridge.git
cd hermes-prime-bridge
./scripts/install.sh
```

Verify it is live:

```bash
hermes plugins list | grep hermes-prime-bridge   # enabled, source: git
hermes tools list                               # prime_kernel toolset (Prime Kernel)
hermes doctor                                   # prime_kernel under Tool Availability
```

From inside an Hermes session the toolset is available to the model:

- `pk_kernel_exec(code)` — run Python in the persistent kernel; state persists across turns.
- `pk_harness_get` — read back continual-harness entries (memory, prompts, skills, subagents).
- `pk_refine` — record a small, evidence-backed harness refinement.
- `rlm` — spawn a subagent; `rlm_list` / `rlm_get` / `rlm_delete` manage handles.
- Slash commands: `/harness`, `/kernel`.

---

## Roadmap

- [x] **Bridge + installer** — native install via `scripts/install.sh`, live-submodule vendor.
- [x] **Persistent kernel + harness tools** — state and continual records end-to-end.
- [x] **rlm facade** — bound to Hermes `subagent_lifecycle`, no second engine.
- [x] **Replacements documented** — `docs/REPLACES.md` contract.
- [ ] **`pyskill` executor** — run Python-backed skills through the existing Hermes skill surface.
- [ ] **Live-update workflow** — verify `hermes plugins update hermes-prime-bridge` pulls new Prime submodule pin.

---

## Development

This repo is a Python package plus an Hermes directory-plugin wrapper. Tests run in the repo-local venv:

```bash
uv sync
uv run pytest -q      # 12 tests
```

The root `__init__.py` satisfies both **Hermes' directory-plugin loader** (relative import) and **pytest** (module import) through a single dual-path entry — see `pyproject.toml` for the `--import-mode=importlib` note.

### Layout

```
pyproject.toml        # pip-installable; hermes_agent.plugins entry group
plugin.yaml           # Hermes directory-plugin manifest (provides_tools / provides_hooks)
bridge/
  __init__.py         # register(ctx) re-export
  plugin.py           # register(ctx): tools, hooks, slash commands
  vendor.py           # import Prime rlm live from vendor submodule
  kernel.py           # persistent per-session kernel
  harness.py          # continual-harness store adapter
  rlm_facade.py       # RLM call shape over Hermes subagent_lifecycle
  schemas.py          # LLM tool schemas
  pyskill.py          # Python-executable skill support (roadmap)
tests/                # pytest suite (12 contract + integration)
vendor/prime-agent    # submodule (pinned)
scripts/install.sh    # native installer (clone --recurse-submodules)
scripts/update.sh     # advance the vendored pin
docs/REPLACES.md      # replaces / reuses / untouched contract
```

---

## License

MIT
