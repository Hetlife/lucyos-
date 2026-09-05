# PLAN FORMAT

Artifact 3 must match this exactly. `aion plan check` rejects anything that
does not, so treat it as a hostile reviewer — because one runs.

Emit JSON. This template is generated from the real validator's own template,
so it is never out of date:

```json
{
  "plan_id": "PLAN-<short-name>",
  "objective": "the end state this plan reaches, in one sentence",
  "bottleneck": "the single constraint this plan removes",
  "success": "how anyone can tell the whole plan worked",
  "steps": [
    {
      "id": "s1",
      "title": "one concrete step",
      "kind": "classify|extract|format|summarize|code|research|file_write|test_run|git|spend",
      "why": "why this step exists",
      "model_class": "DET|A|B|C|D \u2014 omit to let the router decide",
      "depends_on": [
        "ids of steps that must finish first"
      ],
      "prompt": "for A/B steps: the exact instruction a cheap model executes",
      "exec_command": "for DET steps: the command that performs the work",
      "validation_command": "a command that exits 0 only if the step really worked",
      "success_criteria": "what a human would check",
      "impact": 3,
      "cost": 1,
      "risk": 1,
      "output_location": "path the step writes to"
    }
  ]
}
```

## What the validator enforces

- `objective` must be present and non-empty.
- `steps` must be a non-empty list; every step needs `id`, `title`, `kind`.
- `model_class`, when given, must be one of DET, A, B, C, D.
- A DET step needs `exec_command` — the command that does the work.
- An A or B step needs `prompt` — the exact instruction a cheap model runs.
- Every step needs `validation_command` **or** `success_criteria`. A step no
  one can check is not a step.
- `depends_on` must reference ids that exist, and the graph must be acyclic.

## Writing steps a weaker model can actually execute

Assume a fresh Ubuntu machine with Python 3.11, git, and the repo at `~/lucyos`.
Do not assume Ollama is installed, that any paid API key exists, or that any
credential is present. Reserve `model_class: C` for what genuinely needs strong
reasoning — every C step you write is money spent later.
