# 17 — Critical path (post-merge)

```
TR-0-04 census ──┐
TR-0-03 refreeze ┼─> TR-1-03 OpenClaw write verb ─> TR-1-05 live E2E ─> TR-3-01 phone ─┐
TR-1-01 CI main ─┘                                                                       │
                                                                                         v
TR-4-01 Ollama ─┬─> TR-4-02 executor registry ─> TR-4-03 compiler live ─> L3 proof ──> TR-5-01..07 projects ─> L4/L5 ─> TR-8-04
TR-1-06 DET decoupling ┘                                                                  │
TR-2-02 backup push ─> TR-2-03 restore drill ─┐                                           │
TR-2-04 no-root defaults ─> TR-6-03/04 update ─┴─> TR-7-01 launchd ─> TR-7-02 Mac ─> TR-7-03 promote (L6)
TR-8-01 SEVAA token ─> TR-8-02 nightly reconcile ─> TR-8-03 morning routine ─> L7 (14 days)
Cleanup lane (parallel, never blocking): TR-C-01 archive batch, TR-C-02 skeleton modules, TR-C-03 skill-system docs, TR-C-04 fable pack (after D-8)
Interface lane (after TR-1-03): TR-I-01 task detail + agents + scoped command, TR-I-02 machines/routing/sessions/search
```

## The three things that unblock everything
1. **Census** (TR-0-04): every live claim becomes observed; phases 1–3 stop guessing.
2. **Governed write verb** (TR-1-03): turns the phone into a real control surface; L2.
3. **Executor registry** (TR-4-02): lets routing policy mean something; L3 and every project policy depend on it.

## What is deliberately not on the path
Meta direct bridge, SCG crypto gateway, LucyNest touch hardware, Framer, new UI stacks, branch deletion (hygiene, owner-timed), fable pack removal (waits for D-8).

## Level gates on the path
L1 closes with TR-0-03 + TR-1-01 + TR-1-02 + TR-2-02. L2 with TR-1-05/TR-3-01. L3 with TR-4-02/03 + the 3-step PLAN proof. L4/L5 with phase 5. L6 with TR-7-03. L7 with 14 days of TR-8-02/03.
