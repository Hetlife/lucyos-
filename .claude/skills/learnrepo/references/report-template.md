# Decision report

Generate it rather than writing it by hand:

```bash
python3 .claude/skills/learnrepo/scripts/render_report.py <investigation-dir>
```

Rendering from the manifest means a section cannot quietly go missing, the
confidence table always matches the recorded scores, and the approval question
always names the real branch and commit.

## The sixteen sections

1. **Request understood** — the ask restated in LucyOS terms.
2. **Candidates considered** — everything seriously evaluated, with verdicts.
3. **Best candidate or approach** — with the exact revision evaluated.
4. **What it adds to LucyOS** — and which projects benefit.
5. **Evidence and real-user feedback** — typed: fact, maintainer claim, user
   report, tool finding, inference.
6. **Architecture and integration approach** — pattern, flag, permissions,
   network, secrets.
7. **Security findings** — including patched ones, with dispositions.
8. **License status and obligations** — in plain language, plus the record.
9. **Tests performed and results** — with honest result values.
10. **Costs and resource impact** — compute, latency, tokens, money.
11. **Confidence** — the eight scores with reasons.
12. **Risks and limitations** — including residual risk after merge.
13. **Exact files and components prepared** — added, changed, removed.
14. **Rollback plan** — steps, and whether they were tested.
15. **Recommendation** — plus any blocking items from the gate.
16. **Approval required** — one precise question, or a refusal to ask.

## Tone

Write for an owner deciding whether to spend risk, not for a reviewer
checking your homework.

- **Summarise; link to evidence.** Never paste raw logs into the report. Point
  at the artifact path.
- **Lead with the decision.** The gate verdict appears at the top for a
  reason.
- **State uncertainty plainly.** "Not tested on the deployment host" is more
  useful than a confident number.
- **No secrets.** No tokens, keys, credentials, private data, customer
  identifiers or internal hostnames. Reports get forwarded.
- **No absolutes.** Never "works 100%", "fully safe", or "guaranteed
  compatible". Say what was tested, where, and what remains unknown.

## The approval question

When the gate passes, ask exactly one precise question naming the capability,
branch, target and tested commit, and stating explicitly what is *not*
included:

> Approve merging capability `live-agent-activity-view` from branch
> `feature/learnrepo-live-view` into `main` at tested commit `abc1234`?
> This adds a read-only activity panel behind the flag
> `LUCY_LIVE_VIEW` (default off). No production deployment, no external
> account activation, and nothing enabled by default.

A vague question ("shall I proceed?") produces a vague answer and no audit
trail. Silence is not approval.

When the gate does not pass, section 16 refuses to ask, and that refusal is
the correct output. Presenting a blocked change as merge-ready is the one
failure mode that makes every future report worthless.

Optionally record the request in AION so it survives the conversation:

```bash
./aion approval-add "merge capability <id> into main at <commit>" \
  --why "<one line>" --cost "none" \
  --reversibility "easy: git revert, flag defaults off" \
  --prepared "branch tested, gate PASS, rollback tested" \
  --resumes "merge and optionally enable the flag"
```
