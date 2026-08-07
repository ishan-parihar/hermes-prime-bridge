
"""JSON tool schemas — the model-facing contract for bridge-provided tools.

Kept deliberately small and in a dedicated gated toolset so they never
bloat the Hermes core tool schema (the "narrow waist" rule).
"""

PK_KERNEL_EXEC = {
    "name": "pk_kernel_exec",
    "description": (
        "Run Python against the stateful per-session kernel. Variables and imports "
        "persist across turns (prime-agent control-plane behavior) — unlike the "
        "stateless script execution. Use for exploratory math, data munging, and "
        "multi-step computation that must keep intermediates."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "code": {"type": "string", "description": "Python source to execute"},
            "namespace": {"type": "string", "description": "optional named workspace; defaults to default"},
        },
        "required": ["code"],
    },
}

PK_HARNESS_GET = {
    "name": "pk_harness_get",
    "description": "Read records (prompt/memory/skill/subagent) from the continual harness store.",
    "parameters": {
        "type": "object",
        "properties": {
            "kind": {"type": "string", "enum": ["prompt", "memory", "skill", "subagent"]},
            "id": {"type": "string", "description": "entry id (omit for overview)"},
        },
    },
}

PK_REFINE = {
    "name": "pk_refine",
    "description": "Run one evidence-backed refinement pass over the trajectory and apply small harness updates (with snapshot rollback).",
    "parameters": {
        "type": "object",
        "properties": {
            "evidence": {"type": "string", "description": "short summary of what happened"},
            "trigger": {"type": "string", "description": "reason for this refinement"},
        },
        "required": ["evidence"],
    },
}

RLM_SPAWN = {
    "name": "rlm",
    "description": "Spawn a recursive subagent (prime ergonomics) backed by Hermes subagent lifecycle. Returns a handle immediately.",
    "parameters": {
        "type": "object",
        "properties": {
            "goal": {"type": "string", "description": "task for the child agent"},
            "name": {"type": "string", "description": "optional stable child name"},
            "model": {"type": "string", "description": "optional provider/model selector"},
        },
        "required": ["goal"],
    },
}

RLM_LIST = {
    "name": "rlm_list",
    "description": "List live subagent handles.",
    "parameters": {"type": "object", "properties": {}},
}

RLM_GET = {
    "name": "rlm_get",
    "description": "Get a child handle / status.",
    "parameters": {"type": "object", "properties": {"id": {"type": "string"}}, "required": ["id"]},
}

RLM_DELETE = {
    "name": "rlm_delete",
    "description": "Cancel and remove a child handle.",
    "parameters": {"type": "object", "properties": {"id": {"type": "string"}}, "required": ["id"]},
}
