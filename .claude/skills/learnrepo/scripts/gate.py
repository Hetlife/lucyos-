#!/usr/bin/env python3
"""Deterministic merge-eligibility gate for a learnrepo capability.

Why this is code and not a judgement call: a model asked whether 88 is "close
enough" to a 90 threshold, or whether one open high-severity finding is
"probably fine", will sometimes say yes.  Arithmetic and vetoes do not
negotiate.  The gate decides eligibility; a human decides the merge.

`eligible` means only "eligible to ASK the owner for approval".  It never
means approved, merged, or safe in any absolute sense.

Usage:
    python3 gate.py <manifest.json> [--json] [--write <gate.json>]

Exit codes: 0 eligible · 1 not eligible · 2 error (including invalid manifest)
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from learnrepo_paths import now, read_json, write_json  # noqa: E402
from validate_manifest import validate  # noqa: E402

# Thresholds from the master specification.  LucyOS policy may raise these but
# must not lower them without an explicit, recorded owner decision.
THRESHOLDS = {
    "lucyos_compatibility": 90,
    "security": 90,
    "license": 90,
    "test": 95,
    "overall": 90,
}

BLOCKING_SEVERITIES = ("critical", "high")
UNRESOLVED_DISPOSITIONS = ("open",)
ACCEPTABLE_TEST_RESULTS = ("pass",)


def evaluate(manifest: dict) -> dict:
    """Return the gate decision: blocking reasons, warnings, and eligibility."""
    blocking = []
    warnings = []

    structural = validate(manifest)
    if structural:
        # A manifest that does not parse cannot be reasoned about at all.
        return {
            "checked_at": now(),
            "capability_id": manifest.get("capability_id", "(unknown)"),
            "eligible_for_approval_request": False,
            "blocking": [f"manifest is structurally invalid: {p}" for p in structural],
            "warnings": [],
            "thresholds": THRESHOLDS,
        }

    src = manifest["source"]
    lic = manifest["license"]
    sec = manifest["security"]
    tests = manifest["tests"]
    conf = manifest["confidence"]
    rollback = manifest["rollback"]
    ext = manifest["external_services"]

    # --- provenance -------------------------------------------------------
    if not src.get("provenance_verified"):
        blocking.append(
            "provenance is not verified — the exact owner/URL/revision must be "
            "confirmed before anything downstream can be trusted")
    if src.get("kind") not in ("none", "unknown") and not (
            src.get("commit") or src.get("version") or src.get("tag")):
        blocking.append(
            "no exact commit, tag or version recorded — every other finding is a "
            "claim about a specific revision, not about a project in general")

    # --- security veto ----------------------------------------------------
    for finding in sec.get("findings", []):
        if (finding.get("severity") in BLOCKING_SEVERITIES
                and finding.get("disposition") in UNRESOLVED_DISPOSITIONS):
            blocking.append(
                f"unresolved {finding['severity']} security finding: "
                f"{finding.get('title', '(untitled)')}")
    if not sec.get("screened_at"):
        blocking.append("security screening has not been recorded (security.screened_at empty)")
    if sec.get("execution_performed") and str(sec.get("sandbox", "none")).lower() in (
            "", "none", "unknown", "false"):
        blocking.append(
            "candidate code was executed without a recorded containment method — "
            "record the sandbox confirmed by sandbox_probe.py, or do not execute")

    # --- licence veto -----------------------------------------------------
    if not lic.get("spdx"):
        blocking.append("license not identified — do not copy, vendor or derive from it")
    if lic.get("compatible_with_lucyos") is not True:
        blocking.append(
            "license is not recorded as compatible with LucyOS "
            f"(compatible_with_lucyos={lic.get('compatible_with_lucyos')!r})")
    if not lic.get("source_of_truth"):
        blocking.append(
            "license conclusion has no source of truth — read the LICENSE file at "
            "the evaluated revision, not the repository's metadata label")
    if lic.get("requires_legal_review"):
        blocking.append(
            "license requires specialist legal review; that review is an owner "
            "decision and cannot be self-certified here")

    # --- tests ------------------------------------------------------------
    suites = tests.get("suites", [])
    if not suites:
        blocking.append("no tests recorded for this change")
    for suite in suites:
        if suite.get("result") not in ACCEPTABLE_TEST_RESULTS:
            blocking.append(
                f"test suite {suite.get('name', '(unnamed)')!r} is "
                f"{suite.get('result')!r}, not 'pass' — skipped, mocked and flaky "
                "results are not passes")
    if not tests.get("regression_suite_run"):
        blocking.append("the existing LucyOS regression suite was not run")
    elif tests.get("regression_result") != "pass":
        blocking.append(
            f"LucyOS regression suite result is {tests.get('regression_result')!r}, not 'pass'")

    # --- rollback ---------------------------------------------------------
    if not rollback.get("steps"):
        blocking.append("no rollback steps recorded")
    if not rollback.get("tested"):
        blocking.append(
            "rollback has not been tested or credibly verified — an untested "
            "rollback is an assumption, not a recovery path")

    # --- confidence thresholds -------------------------------------------
    for key, minimum in THRESHOLDS.items():
        value = conf.get(key)
        if value is None:
            blocking.append(f"confidence.{key} is unknown; it must be scored with a reason")
        elif value < minimum:
            blocking.append(f"confidence.{key} is {value}, below the required {minimum}")

    reasons = manifest.get("confidence_reasons", {})
    for key in THRESHOLDS:
        if conf.get(key) is not None and not reasons.get(key):
            warnings.append(f"confidence.{key} has no recorded reason")

    # --- external services ------------------------------------------------
    if ext.get("required"):
        if not ext.get("activation_is_separate_approval"):
            blocking.append(
                "an external service is required but activation is not marked as a "
                "separate approval — account creation and activation are never "
                "bundled into a code merge")
        warnings.append(
            "external services are required: accounts, privacy review and cost "
            "review are separate owner decisions from this merge")
        if ext.get("privacy_review_required"):
            warnings.append("a privacy review is outstanding for the external service")
        if ext.get("cost_review_required"):
            warnings.append("a cost review is outstanding for the external service")

    # --- non-blocking hygiene --------------------------------------------
    deps = manifest["dependencies"]
    if deps.get("direct") and not deps.get("pinned"):
        warnings.append("dependencies are not pinned")
    if manifest["runtime"].get("telemetry") in ("unknown", ""):
        warnings.append("telemetry behaviour is unknown; confirm and disable by default")
    if not manifest["feature_flag"].get("name"):
        warnings.append("no feature flag recorded; prefer a flag that defaults to off")
    if len(manifest.get("evidence", [])) < 3:
        warnings.append("thin evidence base (fewer than three recorded items)")
    if not manifest.get("residual_risks"):
        warnings.append("no residual risks recorded — a truly zero-risk change is rare")

    return {
        "checked_at": now(),
        "capability_id": manifest.get("capability_id"),
        "eligible_for_approval_request": not blocking,
        "blocking": blocking,
        "warnings": warnings,
        "thresholds": THRESHOLDS,
        "note": ("Eligible means eligible to ASK for approval. It does not mean "
                 "approved, merged, or safe in any absolute sense."),
    }


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Deterministic learnrepo merge gate")
    p.add_argument("manifest")
    p.add_argument("--json", action="store_true")
    p.add_argument("--write", metavar="PATH", help="also write the result to this path")
    args = p.parse_args(argv)

    try:
        manifest = read_json(Path(args.manifest))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"could not read manifest: {exc}", file=sys.stderr)
        return 2

    result = evaluate(manifest)

    if args.write:
        write_json(Path(args.write), result)

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        verdict = "ELIGIBLE TO REQUEST APPROVAL" if result["eligible_for_approval_request"] \
            else "NOT ELIGIBLE"
        print(f"{verdict} — {result['capability_id']}")
        if result["blocking"]:
            print(f"\nBlocking ({len(result['blocking'])}):")
            for item in result["blocking"]:
                print(f"  ✗ {item}")
        if result["warnings"]:
            print(f"\nWarnings ({len(result['warnings'])}):")
            for item in result["warnings"]:
                print(f"  ! {item}")
        print(f"\n{result['note']}")

    return 0 if result["eligible_for_approval_request"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
