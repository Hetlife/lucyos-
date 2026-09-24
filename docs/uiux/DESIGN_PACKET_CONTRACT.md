# LucyOS Design Packet Contract

Status: research-stage contract. No tool installation or UI semantic change is authorized by this document.

A Design Packet is the portable, cross-model handoff for any LucyOS UI change. It is deliberately tool-neutral so GPT, Claude, local models, Figma, or a human designer can consume the same bounded facts without creating a second source of truth.

## Required fields

```yaml
packet_version: 1
work_id: <task-or-change-id>
surface: <screen/component/flow>
user_goal: <one sentence>
current_evidence:
  screenshots: []
  routes_files: []
  observed_problems: []
platform_targets: [web]
platform_guidance:
  apple_hig_relevant: false
  wcag_target: "2.2 AA"
design_intent:
  information_hierarchy: []
  interaction_states: [default, hover, focus, active, disabled, loading, empty, error]
  responsive_breakpoints: []
  motion_rules: []
  copy_rules: []
tokens:
  source: <canonical token file or none>
  changed_tokens: []
components:
  reuse: []
  new_candidates: []
accessibility:
  keyboard_path: []
  focus_order: []
  labels_names: []
  contrast_or_noncolor_cues: []
  reduced_motion: []
validation:
  deterministic_checks: []
  screenshots: []
  responsive_matrix: []
  manual_checks: []
figma:
  source_file: null
  node_ids: []
  code_connect: []
  drift_notes: []
risks: []
rollback: <exact rollback>
approval_required: false
```

## Invariants

1. Repository/runtime evidence outranks screenshots, Figma, prompts, and prose.
2. Figma is a design/handoff surface, not canonical application state.
3. Existing components/tokens are reused before introducing new primitives.
4. Accessibility and reduced-motion requirements are acceptance criteria, not post-polish.
5. A screenshot is evidence of appearance, not proof of behavior or accessibility.
6. Any external tool remains optional until its LearnRepo lifecycle gates pass.
7. A design packet never contains credentials, private customer data, or raw sensitive logs.
