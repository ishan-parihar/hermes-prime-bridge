
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
