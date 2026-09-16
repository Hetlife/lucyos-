# Worked scenarios

These are **illustrative walkthroughs of the workflow**, not records of real
investigations. Repository names are deliberately generic placeholders and the
findings are examples of shape, not claims about any real project. Never copy
a finding from here into a manifest — every manifest records what *you*
actually observed, at a revision you actually checked.

---

## 1. The user supplies a repository

> "Add this to LucyOS: `https://github.com/example-org/task-scheduler`"

Do not clone-and-import. Run the pipeline:

1. **UNDERSTAND** — what would LucyOS do afterwards that it cannot now?
   LucyOS already has a task queue and a systemd timer. Is this replacing a
   working subsystem? Often the honest answer at this stage is "we do not need
   this", and the investigation ends in twenty minutes.
2. **VERIFY** — resolve owner, canonical URL, and the exact tag you would use.
3. **DISCOVER anyway** — find one or two alternatives. Even when the user
   names a repository, a comparison is what makes the recommendation credible.
4. **INSPECT** — `static_screen.py` on a quarantined copy, then read the
   flagged code.
5. **DECIDE** — record scores, run `gate.py`, write the report.

The common outcome here is not a merge. It is: "LucyOS already does this; the
gap is X; here is a 40-line adapter that closes X."

---

## 2. The user asks the skill to find the best option

> "Find the best way to give LucyOS a live view of what agents are doing."

No repository given, so DISCOVER does real work. Find several candidates plus
the build-it-ourselves option, which is a legitimate candidate and often wins
for a small surface.

Do not rank by stars. Build the comparison table and record it in
`candidates[]`:

| Candidate | Fit | Maintenance | Deps | License | Verdict |
|---|---|---|---|---|---|
| A: full dashboard framework | high | active | 40+ transitive | permissive | rejected — dependency weight vs. LucyOS stdlib-only policy |
| B: small SSE log viewer | medium | single maintainer, quiet 14 months | 2 | permissive | prototype — small enough to vendor or reimplement |
| C: build native | exact | ours | 0 | n/a | recommended — the needed surface is small |

Recommending "build a small native thing" after researching alternatives is a
real result, and the research is what justifies it.

---

## 3. Useful capability, unsafe to integrate directly

The candidate does the job, but the screen shows it shells out to a system
binary with user-controlled arguments and reads broad filesystem paths.

The capability is still worth having. The integration is not.

Options in order of preference: reimplement the narrow piece you need behind
a LucyOS interface; run it as a sidecar with no credentials and no host
access; or reject.

Record the security findings with `disposition: open` — they remain true of
the upstream project even though you routed around them. The gate will refuse
merge approval while an open high finding exists, which is why the chosen path
is "reimplement", with `disposition.rewritten` naming what you wrote yourself.

---

## 4. The license is incompatible or unclear

Two distinct cases:

**No license file.** No grant of rights. You may read the documentation and
public API and write an independent implementation; you may not copy, vendor
or derive from the source. Set `license.spdx: ""`,
`compatible_with_lucyos: false`, and say in the report that the capability can
still be obtained by independent implementation.

**Source-available or strong copyleft** (BSL, SSPL, Commons Clause, AGPL).
Explain the specific obligation in plain language — for AGPL, that serving
users over a network can trigger source disclosure; for BSL, that the grant
may exclude commercial use. Set `requires_legal_review: true` where the terms
are unusual. The gate blocks, and correctly so: accepting a license obligation
is the owner's decision, not the skill's.

Either way the report states the license, the obligation, the consequence for
LucyOS, and the alternative path — not just "incompatible".

---

## 5. Suspicious code found, safe patch prepared

The screen flags a `postinstall` script that fetches a remote URL. Reading it
confirms it downloads a platform binary with no checksum verification.

1. Stop. Do not install the package.
2. Record the finding: `severity: high`, evidence = file and line at the
   evaluated commit, your confidence in the reading.
3. Decide: reject, isolate, replace, or patch. If patching (for example,
   pinning the artifact and verifying a checksum), keep the patch separate,
   add a regression test proving the unverified path is gone, and record the
   maintenance burden of carrying a divergence.
4. Set `disposition: patched` — and **leave the finding in the report**. The
   project still ships that behaviour upstream; you have protected this
   deployment, not fixed the ecosystem.
5. Note whether it was reported upstream.

Never let "we patched it" become "it is safe". You fixed the one thing you
found in the part you read.

---

## 6. Adapting a visual agent artifact

> "This dashboard looks great — can LucyOS have it?"

Visual artifacts carry risk that is easy to miss: bundled minified JavaScript,
remote font and script loads, telemetry, and a CSP the existing LucyOS
interface does not have.

LucyOS already serves a loopback-bound UI with a strict Content-Security-Policy
and bearer auth (`bridges/http_server.py`). An imported artifact must fit that,
not weaken it. Check specifically for: remote `<script>`/`@font-face` sources,
inline event handlers that a strict CSP forbids, analytics, and any build step
that pulls a large dependency tree.

Usually the right outcome is to take the **design idea** and render it with
LucyOS's existing stack, adding a feature flag defaulting to off. Record in
`disposition.rewritten` that the layout was reimplemented and no bundle was
imported.

Also ask the honest question in section 6 of the report: does this make an
operator decision clearer, or is it visual noise?

---

## 7. A capability needing external accounts (WhatsApp-style)

> "Add WhatsApp voice calling so Lucy can call customers."

This is where several non-technical gates apply at once, and the skill's job
is to name them rather than route around them:

- **Accounts** — a business account, a verified number, a provider contract.
  Creating accounts is an owner action, never autonomous.
- **Consent and privacy** — contacting customers, and recording calls, is
  regulated. Whether it is lawful in the relevant jurisdiction is not an
  engineering question, and the report must say so instead of guessing.
- **Cost** — per-message and per-minute pricing, plus provider markup. Set
  `cost_review_required: true`.
- **Security** — the credential lives in the LucyOS secret store, never in the
  repo, the artifact tree, or a report.
- **Blast radius** — an automated outbound channel that misfires contacts real
  customers. This is `failure_impact: critical` even if the code is trivial.

Set `external_services.required: true`, list the services and accounts,
set `activation_is_separate_approval: true`.

The code merge and the activation are **two separate approvals**. It is
legitimate to merge a fully-tested, flag-off integration while the account,
privacy review and cost approval remain open — and the report must make that
split explicit so nobody reads a merge approval as permission to start calling
customers.

LucyOS already treats real-capital and customer-contact actions as RED
(`docs/architect/03_THREAT_MODEL_AND_SECURITY.md` §3). Nothing here overrides
that.
