# LucyOS — Full Codebase Review

**Date:** 2026-09-24 · **Reviewed:** `origin/main` @ `81d25a1` · **Reviewer:** Opus full-code pass
**Method:** every number below was produced by running the command, not estimated.

---

## Verdict

**The code is in good health. The repository is not.**

The Python is genuinely well built: 666 tests pass, every security gate is clean, and I found
no `eval`, no `exec`, no `shell=True`, no `pickle.loads`, no bare `except:`, and no `TODO`
or `FIXME` debt anywhere in production code. That is unusual and worth saying plainly.

The problem is **branch sprawl**, and it got substantially worse this week: **103 branches,
45 of them unmerged**, up from 30 branches with 7 unmerged on 2026-09-17. That is the single
largest risk to this project right now, and it is an operational problem, not a code problem.

---

## 1. Scale

| Metric | Value |
|---|---|
| Python files | 142 |
| Python lines | 23,322 |
| `aion_core/` modules | 49 files, 11,282 lines |
| `tests/` | 64 files, 7,733 lines |
| `bridges/` | 6 files, 1,453 lines |
| `scripts/` | 15 files, 1,290 lines |
| Commits since 2026-09-17 | 73 |

Test-to-source ratio is roughly **1 : 1.5**, which is healthy for a system whose core claim is
"evidence, not assertion".

Largest modules: `fable.py` (678), `learnrepo.py` (669), `db.py` (633), `cli.py` (625),
`tasks.py` (617), `worker.py` (615), `health.py` (488). Nothing is pathologically large.

---

## 2. Health and gates — all verified by execution

| Check | Result |
|---|---|
| `compileall aion_core bridges tests scripts` | clean |
| Full suite | **666 tests, OK, 2 skipped** (72s) |
| `./aion scan .` | clean, no credential-shaped content |
| `check_portability.py` | 0 violations, 3 known exceptions, **0 stale**, 58 files, portable |
| `verify_authority.py anti-dup` | **0 violations** |
| `verify_authority.py self` | hash drift on `config.py`, `db.py`, `router.py` — informational |

The `self` drift is the known, expected lag between the freeze SHA and merged work. Commit
`b45f73c` ("keep informational authority drift from failing CI") already stops it failing CI.
**Not a defect.** Re-freeze when the owner next ratifies a state.

---

## 3. Security review — strong

I looked specifically for the things that actually cause incidents.

**Nothing dangerous found:**
- No `eval()`, `exec()`, `os.system()`, `shell=True`, or `pickle.loads` in any production file.
- No bare `except:` and no `except Exception: pass` anywhere in `aion_core/` or `bridges/`.
- Secret scan clean across the whole tree.

**TaskCheck public surface (`aion_core/taskcheck.py`, `bridges/taskcheck_server.py`)** — this is
the newest externally-reachable code, so it got the closest reading. It is well designed:

- Access tokens are `secrets.token_urlsafe(32)` — 256 bits, cryptographically strong.
- Tokens are stored **hashed** (SHA-256), never in plaintext. A database copy does not leak
  live links.
- `security.redact()` is applied to title, description, requester, assignee and location on
  the way in, so operator text cannot carry a credential into a shared page.
- Expiry is enforced on read: `_run_for_token()` calls `expire_due()` before the lookup, so an
  expired link cannot be used even if the sweeper has not run. Revocation is supported.
- Full Content-Security-Policy: `default-src 'self'`, `object-src 'none'`, `base-uri 'none'`,
  `frame-ancestors 'none'`. Plus `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`,
  `Referrer-Policy: no-referrer`, and a `Permissions-Policy` that allows camera only to self
  and denies microphone and geolocation.
- Static asset serving has a **correct path-traversal guard**: `path.relative_to(WEB.resolve())`
  inside a `try/except ValueError`. This is the right way to do it.
- Report downloads set `Cache-Control: private, no-store`.
- Server binds `127.0.0.1` by default.

**`aion_core/model_gateway.py`** routes to three external inference providers. It is default-deny:
`DATA_POLICY` permits only `PUBLIC`, and `tasks.data_class` defaults to `INTERNAL`, so nothing
leaves the machine unless explicitly reclassified. It is auxiliary to the existing
DET → Ollama → `cloud_command` hierarchy, not a replacement for it.

---

## 4. Findings

### F-1 (P1) — Branch sprawl has roughly tripled in a week
**103 branches, 45 unmerged.** On 2026-09-17 it was 30 and 7.

Unmerged work is spread across at least nine naming conventions: `task/`, `repair/`,
`feature/`, `candidate/`, `research/`, `design/`, `diagnostic/`, `review/`, `fable/`.
Several carry large deltas (`integration/lucyos-autonomous-wave-20260919` +41,
`repair/worker-empty-session-churn-20260920` +41, `claude/fable-deploy-setup-mc5nr6` +39).

**Why this matters more than it looks.** Every unmerged branch is work that was paid for and is
not running. Some of these will conflict with each other. Some are almost certainly superseded
and nobody knows which. The cost of reconciling grows superlinearly with branch count, and it
is currently growing faster than it is being paid down.

**Recommendation:** freeze new branch creation until the count is under 20. Triage in three
buckets, do not review them one by one: (a) fully contained in `main` → delete; (b) unique work
that merges clean → merge in a batch; (c) genuine conflicts → schedule individually. The
existing `docs/internal/REPO_CLEANUP_AND_MERGE_PLAN.md` already demonstrates this method on the
earlier, smaller set.

### F-2 (P2) — The newest, most security-sensitive code is the least readable
`bridges/taskcheck_server.py` averages **76 characters per line** against **34** for `db.py`.
`aion_core/taskcheck.py` has **43 lines over 120 characters** and 16 multi-statement lines
(`a=1; b=2; c=3`). Example, a single line handling HTTP response construction:

```
body=json.dumps(payload,ensure_ascii=False).encode(); self.send_response(code); self.send_header(...); ... self.wfile.write(body)
```

The code is *correct* — I checked the security-relevant paths individually. But this is the
public-facing attack surface written in the style hardest to review, in a project whose entire
governance model depends on humans and models being able to review diffs. A subtle change here
is much easier to miss than the same change in `db.py`.

**Recommendation:** reformat these two files to the house style used by the rest of `aion_core`.
Pure formatting, no behaviour change, tests unchanged. This is cheap and high-leverage.

### F-3 (P3) — No rate limiting or access logging on the public token endpoint
`bridges/taskcheck_server.py` has zero matches for rate/limit/throttle/attempt, and
`log_message` is overridden to `pass`, so requests are not logged.

Brute force is **not** a practical threat against a 256-bit token, so this is genuinely low
severity. The real gap is **detection**: if a link were leaked or scraped, there would be no
record of it being accessed. Consider logging token-hash prefix, timestamp and status (never
the token itself) to the existing `events` table.

### F-4 (P3) — `aion_core` is at 49 modules and still growing
Six new modules landed this week alone (`model_gateway`, `owner_actions`, `platform_resolver`,
`semantic_recall`, `taskcheck`, `usage_telemetry`). Each individually justified; the trend is
worth watching. The `anti-dup` allowlist is doing its job as a speed bump, but a speed bump is
not a design review. No action now, just do not let this reach 70 without a deliberate look at
whether some of these belong behind a smaller number of interfaces.

---

## 5. What is working well — stated so it does not get "fixed"

- **Evidence discipline is real, not decorative.** `worker._validate()` independently reruns
  `validation_command`, falls back to `output_location` existence, and returns `needs_review`
  rather than DONE for class A/B work with no independent validation.
- **Singleton execution locking** (`worker._execution_lock`) is intact.
- **Schema migrations** remain additive via `_ADDED_COLUMNS`; no destructive migration exists.
- **Backups are restore-tested**, not merely created.
- **The authority gates work, including against their own authors.** `strict` correctly refuses
  any `.lucy/authority/**` change regardless of task ID, and `anti-dup` mechanically catches new
  core modules and second state stores. During this session those gates blocked me, which is
  the point.
- **Cross-platform ratchet holds:** 0 violations, 0 stale exceptions across 58 files.

---

## 6. Priority order

1. **F-1 branch sprawl** — the only finding that is actively getting worse. Start here.
2. **F-2 readability of the public surface** — cheap, mechanical, reduces real review risk.
3. **F-3 access logging** — small, improves incident response.
4. **F-4 module growth** — monitor, no action yet.

Nothing here is a P0. Nothing is broken. There is no data-loss or security emergency.
The work is to stop the repository outgrowing the ability to reason about it.
