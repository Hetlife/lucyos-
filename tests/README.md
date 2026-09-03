# tests/

Run everything: `python3 -m unittest discover -s tests -t . -q`

Every test builds a throwaway shared brain in a temp directory via
`tests/base.AionTest`, so tests never touch the real state and can run in any
order.

| File | Proves |
|---|---|
| `test_security.py` | Real credential shapes are caught, ordinary owner messages are not, redaction removes the value |
| `test_tasks.py` | Value ranking, exclusive claims, dependency gating, retry-then-block, the evidence gate |
| `test_approvals.py` | One approval holds one task, approve resumes the prepared step, a duplicate reply is not re-applied |
| `test_router.py` | Every command answers without a model, casual talk never approves, secrets are refused, unknown text becomes a triage task |
| `test_packets.py` | Packet parsing, dedup by content, conflict flagging, inbox file handling |
| `test_routing_and_state.py` | Model routing and escalation, budget governor thresholds, failure classification, checkpoint and bottleneck logic |
| `test_notebook_sessions.py` | Notebook entries become state, resync is a no-op, session logs record and compact |
| `test_bridge.py` | Redacted replies, size limits, file round trip, duplicate delivery, crash containment |
| `test_end_to_end.py` | The full pipeline: external packet → ingest → task → routing → execution → validation → owner status → approval → backup |

## Rules for new tests

- Assert on behaviour the directives require, not on wording.
- A test that needs a credential-shaped string must have its file listed in
  `.secretscanignore`, so the exemption is visible in review.
- If a test needs the real filesystem, use the temp brain, never `AION_HOME`
  from the environment.
