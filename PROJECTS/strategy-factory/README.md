# strategy-factory — the Capital Engine, as a LucyOS project

This folder is the **definition** LucyOS needs (06_PROJECT_COMPANY_APP_MODEL):
`project.json` (objective, policy, integrations), `money_path.json` (the owner's
phone-visible path to real money, evidenced by files in `evidence/`), and
`plans/plan-ce-phase0.json` (the first `aion plan apply` graph). It deliberately
contains **no plan prose** — the design, research and 21 mechanical work orders
live in the strategy-factory repository:

- `docs/capital_engine/00_DESIGN.md` — why and shape (three classes, gates, the
  exact owner authorization sentences in §8)
- `docs/capital_engine/research/R1_*.md`, `R2_*.md` — evidence records
- `.autonomous/capital_engine/WORK_ORDERS.md` — the queue any model can execute
  with the repo's `/ce-workorder` skill
- `CLAUDE.md` — that repo's constitution (Three Laws, hard rules)

Authority here: contract **C9** in `.lucy/authority/LUCYOS_PLATFORM_AND_DATA_CONTRACTS.md`
(research/paper allowed; real capital, crypto purchases, derivatives, broker
execution need fresh owner authorization). Routing: `.lucy/planning/lucyos-total-recovery/09_AGENT_ROUTING.md`.
Registration into the DB waits for TR-5-02..07; `money_path.py` already reads
this folder today. Work order: TR-8-04 (and strategy-factory CE-5-02 for the
nightly evidence sync).

`evidence/` is written by syncs, never by hand.
