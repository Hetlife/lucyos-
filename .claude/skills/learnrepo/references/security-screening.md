# Security screening

Treat every external repository, package and dependency as untrusted until you
have evidence otherwise. The goal is not to prove a project is malicious — it
is to understand what it can do, decide whether LucyOS can contain that, and
record the reasoning so a future reader can check it.

## Order of work

Provenance first. Everything else is a claim about a specific revision, and a
finding about the wrong revision is worthless.

1. **Provenance** — canonical owner, canonical URL, exact commit/tag/release,
   package registry entry. Record the retrieval date.
2. **Identity risk** — is this the project it appears to be? Look for recent
   transfer of ownership, a new maintainer with few commits merging large
   changes, a name one character away from a popular package, a fork
   presenting itself as the original, or a registry entry whose repository
   link does not match.
3. **History** — does the commit history show a sudden behaviour change, a
   large unexplained binary or minified blob, or a force-push near a release?
4. **Dependencies** — direct and transitive. Count them. A small library with
   80 transitive dependencies is not a small library.
5. **Known vulnerabilities** — advisories for the exact version, not the
   project generally.
6. **Code review of the risky surface** — the areas below.
7. **Execution, only if genuinely needed, only with confirmed containment.**

## Run the screen, then read the code

```bash
python3 .claude/skills/learnrepo/scripts/static_screen.py <quarantine-dir> --json
```

The script flags leads. It cannot tell intent. Confirm every material finding
by reading the surrounding code — and remember the inverse: a clean screen is
not evidence of safety, because obfuscated, compiled, generated or
fetched-at-runtime code hides from static reading entirely.

## What actually matters, by category

**Runs on install or build.** `postinstall`/`preinstall`/`prepare` scripts,
`setup.py`, `binding.gyp`, Makefile targets, Dockerfiles, CI workflows, git
hooks. These execute before anyone has decided to trust the code, which is why
`pip install` and `npm install` of an unscreened package is itself the risk.

**Loads code at runtime.** Downloading a script and piping it to a shell,
fetching and `eval`-ing, plugin auto-download, auto-updaters. This defeats
every review you have done, because the code you reviewed is not the code that
runs. Treat as critical.

**Dynamic evaluation and unsafe deserialization.** `eval`, `exec`,
`new Function`, `pickle.loads`, `yaml.load` without a safe loader. Often
legitimate in template engines and serializers; the question is whether
untrusted input can reach it.

**Credential and secret access.** Reading `~/.ssh`, `~/.aws/credentials`,
`.netrc`, browser profiles, keychains, wallet files, or environment variables
matching token/secret/password shapes. A library that needs your SSH key to
format text has a problem. Weight this heavily.

**Network behaviour.** Where does it connect, when, and is it optional?
Distinguish a documented API client from silent telemetry. LucyOS requires
telemetry off by default; if it cannot be disabled, that is a finding.

**Persistence and privilege.** Cron entries, systemd units, launch agents,
shell rc modification, `sudo`, setuid, `--privileged`, `chmod 777`,
`CAP_SYS_ADMIN`. A library should not want to survive a reboot.

**Disabled security controls.** `verify=False`, `rejectUnauthorized: false`,
`InsecureSkipVerify`, unverified SSL contexts. Sometimes a test fixture,
sometimes shipped in the default path — check which.

**Opaque artifacts.** Committed binaries, minified bundles, vendored blobs,
archives. You cannot review what you cannot read. Prefer building from source;
if that is not possible, say so and lower the security confidence score.

**Container and service posture** (if applicable). Privileged containers, host
network mode, mounted `/var/run/docker.sock`, mounted host root, default
credentials, unauthenticated ports, permissive CORS, unvalidated webhooks,
missing input validation, path traversal, SSRF, command injection.

## Execution policy

**Default: do not execute.** Static analysis, documentation and history answer
most questions at zero risk.

If you conclude execution is necessary:

```bash
python3 .claude/skills/learnrepo/scripts/sandbox_probe.py
```

- If it reports **no usable containment**, do not execute. Complete the
  assessment statically and state in the report that dynamic behaviour was not
  observed. This is an honest limitation, not a failure.
- If containment exists, use it with: no network egress, synthetic data only,
  no real credentials, a non-root user, a read-only root filesystem where
  supported, CPU/memory/time limits, and a disposable working directory.
- Record the exact containment used in `security.sandbox`. The gate blocks a
  manifest that reports execution with no recorded containment, because an
  unverifiable claim of sandboxing is worse than none.

Containment reduces blast radius. It does not make untrusted code safe, and
user namespaces in particular are not a hardened boundary.

## When you find something

1. Stop any execution.
2. Preserve the evidence — file, line, commit — without copying secrets into
   notes or reports.
3. Describe the behaviour, its trigger, plausible impact, exploitability and
   which trust boundary it crosses.
4. Assign severity (critical/high/medium/low/info) **and** your confidence in
   the finding. A high-severity guess and a high-severity certainty call for
   different responses.
5. Choose a disposition: `open`, `patched`, `mitigated`, `accepted`,
   `rejected`, `false_positive`.
6. If you patch it: keep the patch separate, add a regression test, note
   whether it should be reported upstream, and record the maintenance cost of
   carrying a divergence from upstream.
7. Keep the finding in the manifest and the report even after patching. A
   report that hides fixed findings teaches the reader nothing about the
   project's overall quality.

## Reject by default when you see

Credible malicious behaviour · unexplained access to credentials or wallets ·
remote code loading without a documented, bounded purpose · dangerous
persistence · provenance you cannot establish · an unresolved critical or high
finding · a maintainer who has responded to a security report by deleting it.

Rejecting is a normal, successful outcome. The cost of rejecting a useful
library is a few days of work; the cost of adopting a compromised one is every
credential LucyOS holds.
