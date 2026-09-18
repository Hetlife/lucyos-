# 22 — Google Drive Archive Plan

## Layers (11 §6, restated as rules)

- **GitHub is authored truth** for code, contracts, manifests, this package, evidence measurements.
- **Drive is the human-readable mirror**: `LucyOS/Architecture_Research/Codebase_Reduction_2026-09/`
  (exists; owner `scs.admin01@gmail.com`; contains `01_CURRENT_STATE_BASELINE`, 2026-09-18) with a new
  subfolder `Fable_Execution_Architecture/` for this package.
- **Mark-2** holds runtime state; **Lucy-den** holds nothing canonical.
- **Never in Drive**: secrets, private logs, Mark-2 DB dumps, anything not also in the (public) repo.
- **Never authored in Drive**: a document is written once in git and exported; an owner comment in Drive
  is transcribed into `CHECKPOINT.md` with the Drive link as provenance.

## What goes up, when

| Event | Files | Format |
|---|---|---|
| Package published (now) | all `NN_*.md/.json/.txt` from this folder | Google Docs (converted from Markdown/text) or plain text where conversion loses structure (`.json`, `.txt` prompts) |
| Each milestone gate | `evidence/M<n>_GATE.md`, `evidence/SCORECARD.md` | Google Doc |
| Owner decision recorded | the `CHECKPOINT.md` block that records it | appended to a running `DECISIONS_LOG` doc |
| M3 pilot | `evidence/context_pilot_results.md` | Google Doc |
| Program end (M9 entry) | `23_FINAL_HANDOFF.md` refreshed + final scorecard | Google Doc |

Mechanics: the controller uploads via the Drive connector available to it (or the owner's), naming files
exactly as in git with the git SHA in the first line ("Mirror of `<path>` @ `<sha>`"). Because Drive
writes from Mark-2 are BROKEN (FABLE_PROGRESS, unchanged), **no LucyOS code path is involved and nothing
blocks on Drive** (C2). If the upload fails, the checkpoint says so and work continues.

Do not create `Metrics_Task1/`, `Context_Pack_Pilot/` or other ad-hoc folders from the Executive Summary;
everything lives under the two folders above with the git path as the title.
