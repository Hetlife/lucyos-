#!/usr/bin/env python3
"""Render the 16-section learnrepo decision report from a manifest + gate result.

Rendering from structured data rather than free-writing each report means a
section cannot quietly go missing, the confidence table always matches the
manifest, and the approval question always states the real branch and commit.

Usage:
    python3 render_report.py <investigation-dir> [--out report.md] [--stdout]
    python3 render_report.py --manifest m.json [--gate g.json] [--stdout]

Exit codes: 0 rendered · 2 error
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from learnrepo_paths import now, read_json  # noqa: E402
from gate import evaluate  # noqa: E402

SECTIONS = (
    "Request understood",
    "Candidates considered",
    "Best candidate or approach",
    "What it adds to LucyOS and which projects benefit",
    "Evidence and real-user feedback",
    "Architecture and integration approach",
    "Security findings",
    "License status and obligations",
    "Tests performed and results",
    "Costs and resource impact",
    "Confidence",
    "Risks and limitations",
    "Exact files and components prepared",
    "Rollback plan",
    "Recommendation",
    "Approval required",
)

SCORE_LABELS = (
    ("evidence", "Evidence"),
    ("functional_fit", "Functional fit"),
    ("lucyos_compatibility", "LucyOS compatibility"),
    ("security", "Security"),
    ("license", "License"),
    ("test", "Test"),
    ("maintainability", "Maintainability"),
    ("overall", "Overall integration"),
)


def _or_none(value, empty: str = "_not recorded_") -> str:
    if value is None or value == "" or value == []:
        return empty
    return str(value)


def _bullets(items, empty: str = "_none recorded_") -> str:
    if not items:
        return empty
    return "\n".join(f"- {item}" for item in items)


def render(manifest: dict, gate: dict) -> str:
    cap = manifest.get("capability_id", "(unknown)")
    src = manifest.get("source", {})
    lic = manifest.get("license", {})
    sec = manifest.get("security", {})
    tests = manifest.get("tests", {})
    conf = manifest.get("confidence", {})
    reasons = manifest.get("confidence_reasons", {})
    assess = manifest.get("assessment", {})
    integ = manifest.get("integration", {})
    changes = manifest.get("changes", {})
    rollback = manifest.get("rollback", {})
    ext = manifest.get("external_services", {})
    eligible = gate.get("eligible_for_approval_request", False)

    out = []
    add = out.append

    add(f"# learnrepo decision report — `{cap}`")
    add("")
    add(f"Generated {now()} · manifest schema v{manifest.get('schema_version')} · "
        f"status **{manifest.get('status', 'unknown')}**")
    add("")
    verdict = "ELIGIBLE TO REQUEST APPROVAL" if eligible else "NOT ELIGIBLE"
    add(f"**Gate: {verdict}** — {len(gate.get('blocking', []))} blocking, "
        f"{len(gate.get('warnings', []))} warnings.")
    add("")

    add(f"## 1. {SECTIONS[0]}")
    add("")
    add(_or_none(manifest.get("request")))
    add("")
    add(f"Purpose: {_or_none(manifest.get('purpose'))}")
    add("")

    add(f"## 2. {SECTIONS[1]}")
    add("")
    candidates = manifest.get("candidates", [])
    if candidates:
        add("| Candidate | Source | Verdict | Why |")
        add("|---|---|---|---|")
        for c in candidates:
            add(f"| {c.get('name', '?')} | {c.get('url', '')} | "
                f"{c.get('verdict', '')} | {c.get('why', '')} |")
    else:
        add("_No alternatives recorded. If only one candidate was considered, say why "
            "that was sufficient — a single-candidate comparison is a weak comparison._")
    add("")

    add(f"## 3. {SECTIONS[2]}")
    add("")
    add(f"- Source: {_or_none(src.get('canonical_url'))}")
    add(f"- Owner: {_or_none(src.get('owner'))}")
    revision = src.get("commit") or src.get("tag") or src.get("version")
    add(f"- Evaluated revision: `{_or_none(revision, 'NOT RECORDED')}`")
    add(f"- Retrieved: {_or_none(src.get('retrieved_at'))}")
    add(f"- Provenance verified: **{bool(src.get('provenance_verified'))}** "
        f"{src.get('provenance_notes', '')}")
    add("")
    add("Everything below is a claim about that exact revision, not about the "
        "project in general.")
    add("")

    add(f"## 4. {SECTIONS[3]}")
    add("")
    add(_or_none(manifest.get("learned")))
    add("")
    add(f"Consumers: {', '.join(manifest.get('consumers', [])) or '_none recorded_'}")
    add("")

    add(f"## 5. {SECTIONS[4]}")
    add("")
    evidence = manifest.get("evidence", [])
    if evidence:
        add("| Type | Claim | Source | Date |")
        add("|---|---|---|---|")
        for e in evidence:
            add(f"| {e.get('type', '?')} | {e.get('claim', '')} | "
                f"{e.get('source', '')} | {e.get('date', '')} |")
        add("")
        add("Types are kept separate deliberately: a maintainer claim and an "
            "independently observed fact are not the same evidence.")
    else:
        add("_No evidence recorded._")
    add("")

    add(f"## 6. {SECTIONS[5]}")
    add("")
    add(f"- Integration pattern: **{_or_none(integ.get('pattern'))}**")
    add(f"- Branch: `{_or_none(integ.get('branch'))}`")
    add(f"- Baseline LucyOS commit: `{_or_none(integ.get('baseline_commit'))}`")
    add(f"- Target branch: `{_or_none(integ.get('target_branch'))}`")
    flag = manifest.get("feature_flag", {})
    add(f"- Feature flag: `{_or_none(flag.get('name'))}` (default {flag.get('default', 'off')})")
    runtime = manifest.get("runtime", {})
    add(f"- Permissions: {', '.join(runtime.get('permissions', [])) or 'none'}")
    add(f"- Network: {', '.join(runtime.get('network', [])) or 'none'}")
    add(f"- Secrets required: {', '.join(runtime.get('secrets', [])) or 'none'}")
    add(f"- Telemetry: {runtime.get('telemetry', 'unknown')}")
    add("")

    add(f"## 7. {SECTIONS[6]}")
    add("")
    add(f"Screened: {_or_none(sec.get('screened_at'))} · method: "
        f"{_or_none(sec.get('screening_method'))}")
    add(f"Candidate code executed: **{bool(sec.get('execution_performed'))}** "
        f"(containment: {sec.get('sandbox', 'none')})")
    add("")
    findings = sec.get("findings", [])
    if findings:
        add("| Severity | Finding | Disposition | Confidence |")
        add("|---|---|---|---|")
        for f in findings:
            add(f"| {f.get('severity', '?')} | {f.get('title', '')} | "
                f"{f.get('disposition', '?')} | {f.get('confidence', '')} |")
        add("")
        add("Patched findings remain listed. Fixing one issue does not make the "
            "rest of a codebase safe.")
    else:
        add("_No findings recorded. Note that a clean screen is not proof of safety._")
    add("")

    add(f"## 8. {SECTIONS[7]}")
    add("")
    add(f"- SPDX: **{_or_none(lic.get('spdx'), 'UNKNOWN')}**")
    add(f"- Read from: {_or_none(lic.get('source_of_truth'))}")
    add(f"- Commercial use: {lic.get('commercial_use', 'unclear')} · "
        f"redistribution: {lic.get('redistribution', 'unclear')} · "
        f"network/SaaS use: {lic.get('network_use', 'unclear')}")
    add(f"- Compatible with LucyOS: **{lic.get('compatible_with_lucyos')}**")
    add(f"- Specialist legal review advised: **{bool(lic.get('requires_legal_review'))}**")
    add("")
    add("Obligations:")
    add(_bullets(lic.get("obligations", []), "_none identified_"))
    add("")
    add("This is an engineering reading of the license text, not legal advice.")
    add("")

    add(f"## 9. {SECTIONS[8]}")
    add("")
    suites = tests.get("suites", [])
    if suites:
        add("| Suite | Command | Result | Notes |")
        add("|---|---|---|---|")
        for s in suites:
            add(f"| {s.get('name', '')} | `{s.get('command', '')}` | "
                f"**{s.get('result', '?')}** | {s.get('notes', '')} |")
    else:
        add("_No test suites recorded._")
    add("")
    add(f"LucyOS regression suite run: **{bool(tests.get('regression_suite_run'))}** → "
        f"{tests.get('regression_result', 'not_run')}")
    add("")

    add(f"## 10. {SECTIONS[9]}")
    add("")
    res = manifest.get("resources", {})
    for key in ("cpu", "memory", "disk", "network", "latency", "token_cost", "monetary_cost"):
        add(f"- {key.replace('_', ' ').title()}: {_or_none(res.get(key))}")
    add("")

    add(f"## 11. {SECTIONS[10]}")
    add("")
    add("| Dimension | Score | Reason |")
    add("|---|---:|---|")
    for key, label in SCORE_LABELS:
        value = conf.get(key)
        shown = "—" if value is None else str(value)
        add(f"| {label} | {shown} | {reasons.get(key, '_no reason recorded_')} |")
    add("")
    add(f"- Expected value: {_or_none(assess.get('expected_value'))}")
    add(f"- Integration effort: {_or_none(assess.get('integration_effort'))}")
    add(f"- Failure impact: {_or_none(assess.get('failure_impact'))}")
    add(f"- Reversibility: {_or_none(assess.get('reversibility'))}")
    add("")

    add(f"## 12. {SECTIONS[11]}")
    add("")
    add("Limitations:")
    add(_bullets(manifest.get("limitations", [])))
    add("")
    add("Residual risks:")
    add(_bullets(manifest.get("residual_risks", [])))
    add("")
    if ext.get("required"):
        add("**External services required.** Accounts, privacy review, cost review and "
            "activation are separate owner decisions and are NOT included in this merge.")
        add(_bullets(ext.get("services", [])))
        add("")

    add(f"## 13. {SECTIONS[12]}")
    add("")
    for label, key in (("Added", "files_added"), ("Changed", "files_changed"),
                       ("Removed", "files_removed")):
        files = changes.get(key, [])
        add(f"{label} ({len(files)}):")
        add(_bullets(files, "_none_"))
        add("")

    add(f"## 14. {SECTIONS[13]}")
    add("")
    add(_bullets(rollback.get("steps"), "_no rollback steps recorded_"))
    add("")
    add(f"Rollback tested: **{bool(rollback.get('tested'))}** — "
        f"{_or_none(rollback.get('tested_evidence'))}")
    add("")

    add(f"## 15. {SECTIONS[14]}")
    add("")
    add(f"**{_or_none(assess.get('recommendation'), 'undecided')}**")
    add("")
    if gate.get("blocking"):
        add("Blocking items from the deterministic gate:")
        add(_bullets(gate["blocking"]))
        add("")
    if gate.get("warnings"):
        add("Warnings:")
        add(_bullets(gate["warnings"]))
        add("")

    add(f"## 16. {SECTIONS[15]}")
    add("")
    if eligible:
        revision_note = integ.get("baseline_commit") or "(commit not recorded)"
        add(f"> Approve merging capability `{cap}` from branch "
            f"`{_or_none(integ.get('branch'), '(branch not recorded)')}` into "
            f"`{integ.get('target_branch', 'main')}` at tested commit `{revision_note}`?")
        add(">")
        add(f"> This adds: {_or_none(manifest.get('purpose'))}")
        add(">")
        add("> No production deployment, no external account activation, and no "
            "capability enabled by default are included in this approval.")
        add("")
        add("Reply with an explicit approval. Silence is not approval.")
    else:
        add("**Not ready to request merge approval.** Resolve the blocking items in "
            "section 15 first. Presenting this as merge-ready would misrepresent it.")
    add("")
    add("---")
    add("")
    add("_Scores and gate results are engineering judgements recorded against evidence, "
        "not guarantees. Software behaviour cannot be guaranteed across all future "
        "states; this report states what was tested and what was not._")
    add("")
    return "\n".join(out)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Render the learnrepo decision report")
    p.add_argument("investigation_dir", nargs="?")
    p.add_argument("--manifest")
    p.add_argument("--gate")
    p.add_argument("--out")
    p.add_argument("--stdout", action="store_true")
    args = p.parse_args(argv)

    if args.manifest:
        manifest_path = Path(args.manifest)
        gate_path = Path(args.gate) if args.gate else None
        out_path = Path(args.out) if args.out else None
    elif args.investigation_dir:
        base = Path(args.investigation_dir)
        manifest_path = base / "manifest.json"
        gate_path = base / "gate.json"
        out_path = Path(args.out) if args.out else base / "report.md"
    else:
        print("give an investigation directory or --manifest", file=sys.stderr)
        return 2

    try:
        manifest = read_json(manifest_path)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"could not read manifest: {exc}", file=sys.stderr)
        return 2

    if gate_path and gate_path.exists():
        gate = read_json(gate_path)
    else:
        gate = evaluate(manifest)

    text = render(manifest, gate)

    if out_path:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(text, encoding="utf-8")
        print(f"wrote {out_path}")
    if args.stdout or not out_path:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
