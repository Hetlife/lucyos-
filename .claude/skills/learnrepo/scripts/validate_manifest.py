#!/usr/bin/env python3
"""Validate a learnrepo capability manifest against schema v1.

Hand-written rather than jsonschema-based because LucyOS runs on the standard
library only.  The checks are deliberately structural (shape, types, enums,
ranges); judging whether the *content* is honest is a human and model job.

Usage:
    python3 validate_manifest.py <manifest.json> [--json]

Exit codes: 0 valid · 1 invalid · 2 usage/IO error
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from learnrepo_paths import SCHEMA_VERSION, CAPABILITY_ID, read_json  # noqa: E402

SEVERITIES = {"critical", "high", "medium", "low", "info"}
DISPOSITIONS = {"open", "patched", "mitigated", "accepted", "rejected", "false_positive"}
TEST_RESULTS = {"pass", "fail", "skipped", "mocked", "flaky", "not_run", "error"}
EVIDENCE_TYPES = {"fact", "maintainer_claim", "user_report", "tool_finding", "inference"}
STATUSES = {"draft", "research", "assessed", "prepared", "approved",
            "integrated", "rejected", "postponed"}
RECOMMENDATIONS = {"reject", "research_only", "reimplement_pattern", "wrap_dependency",
                   "prototype", "prepare_integration", "postpone",
                   "ready_for_merge_approval", ""}
PATTERNS = {"adapter", "plugin", "sidecar", "vendored", "core", ""}
APPROVAL_STATES = {"not_requested", "requested", "approved", "denied"}

SCORE_KEYS = ("evidence", "functional_fit", "lucyos_compatibility", "security",
              "license", "test", "maintainability", "overall")

TOP_LEVEL = (
    "schema_version", "capability_id", "name", "purpose", "request", "candidates",
    "consumers", "status",
    "created_at", "updated_at", "source", "license", "evidence", "learned",
    "disposition", "dependencies", "runtime", "security", "changes", "tests",
    "resources", "confidence", "confidence_reasons", "assessment", "limitations",
    "residual_risks", "feature_flag", "rollback", "integration",
    "external_services", "monitoring", "approval",
)


def _is_list_of_str(value) -> bool:
    return isinstance(value, list) and all(isinstance(v, str) for v in value)


def validate(manifest: dict) -> list:
    """Return a list of human-readable problems.  Empty means structurally valid."""
    problems = []

    if not isinstance(manifest, dict):
        return ["manifest must be a JSON object"]

    for key in TOP_LEVEL:
        if key not in manifest:
            problems.append(f"missing top-level key: {key}")
    if problems:
        return problems

    if manifest["schema_version"] != SCHEMA_VERSION:
        problems.append(
            f"schema_version is {manifest['schema_version']!r}, this validator "
            f"handles {SCHEMA_VERSION}; run a migration rather than editing in place")

    if not CAPABILITY_ID.match(str(manifest.get("capability_id", ""))):
        problems.append("capability_id must be lowercase words joined by single dashes")

    if manifest["status"] not in STATUSES:
        problems.append(f"status must be one of {sorted(STATUSES)}")

    if not _is_list_of_str(manifest["consumers"]):
        problems.append("consumers must be a list of strings")

    if not isinstance(manifest["candidates"], list):
        problems.append("candidates must be a list")
    else:
        for i, cand in enumerate(manifest["candidates"]):
            if not isinstance(cand, dict):
                problems.append(f"candidates[{i}] must be an object")
            elif not cand.get("name"):
                problems.append(f"candidates[{i}].name must be non-empty")

    src = manifest["source"]
    if not isinstance(src, dict):
        problems.append("source must be an object")
    else:
        for key in ("kind", "canonical_url", "owner", "commit", "tag", "version",
                    "release_date", "retrieved_at", "provenance_notes"):
            if not isinstance(src.get(key, ""), str):
                problems.append(f"source.{key} must be a string")
        if not isinstance(src.get("provenance_verified"), bool):
            problems.append("source.provenance_verified must be true or false")

    lic = manifest["license"]
    if not isinstance(lic, dict):
        problems.append("license must be an object")
    else:
        if not isinstance(lic.get("spdx", ""), str):
            problems.append("license.spdx must be a string")
        if not _is_list_of_str(lic.get("obligations", [])):
            problems.append("license.obligations must be a list of strings")
        if lic.get("compatible_with_lucyos") not in (True, False, None):
            problems.append("license.compatible_with_lucyos must be true, false or null")
        if not isinstance(lic.get("requires_legal_review"), bool):
            problems.append("license.requires_legal_review must be true or false")

    if not isinstance(manifest["evidence"], list):
        problems.append("evidence must be a list")
    else:
        for i, item in enumerate(manifest["evidence"]):
            if not isinstance(item, dict):
                problems.append(f"evidence[{i}] must be an object")
                continue
            if item.get("type") not in EVIDENCE_TYPES:
                problems.append(
                    f"evidence[{i}].type must be one of {sorted(EVIDENCE_TYPES)} — "
                    "keeping facts, claims, reports and inference separate is the point")
            if not item.get("claim"):
                problems.append(f"evidence[{i}].claim must be non-empty")

    sec = manifest["security"]
    if not isinstance(sec, dict):
        problems.append("security must be an object")
    else:
        if not isinstance(sec.get("execution_performed"), bool):
            problems.append("security.execution_performed must be true or false")
        findings = sec.get("findings", [])
        if not isinstance(findings, list):
            problems.append("security.findings must be a list")
        else:
            for i, f in enumerate(findings):
                if not isinstance(f, dict):
                    problems.append(f"security.findings[{i}] must be an object")
                    continue
                if f.get("severity") not in SEVERITIES:
                    problems.append(
                        f"security.findings[{i}].severity must be one of {sorted(SEVERITIES)}")
                if f.get("disposition") not in DISPOSITIONS:
                    problems.append(
                        f"security.findings[{i}].disposition must be one of {sorted(DISPOSITIONS)}")
                if not f.get("title"):
                    problems.append(f"security.findings[{i}].title must be non-empty")

    tests = manifest["tests"]
    if not isinstance(tests, dict):
        problems.append("tests must be an object")
    else:
        if not isinstance(tests.get("regression_suite_run"), bool):
            problems.append("tests.regression_suite_run must be true or false")
        suites = tests.get("suites", [])
        if not isinstance(suites, list):
            problems.append("tests.suites must be a list")
        else:
            for i, s in enumerate(suites):
                if not isinstance(s, dict):
                    problems.append(f"tests.suites[{i}] must be an object")
                    continue
                if s.get("result") not in TEST_RESULTS:
                    problems.append(
                        f"tests.suites[{i}].result must be one of {sorted(TEST_RESULTS)}")
                if not s.get("name"):
                    problems.append(f"tests.suites[{i}].name must be non-empty")

    conf = manifest["confidence"]
    if not isinstance(conf, dict):
        problems.append("confidence must be an object")
    else:
        for key in SCORE_KEYS:
            if key not in conf:
                problems.append(f"confidence.{key} is missing")
                continue
            value = conf[key]
            if value is None:
                continue  # explicitly unknown is allowed; the gate treats it as blocking
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                problems.append(f"confidence.{key} must be a number 0-100 or null")
            elif not 0 <= value <= 100:
                problems.append(f"confidence.{key} must be within 0-100, got {value}")

    assessment = manifest["assessment"]
    if not isinstance(assessment, dict):
        problems.append("assessment must be an object")
    elif assessment.get("recommendation") not in RECOMMENDATIONS:
        problems.append(f"assessment.recommendation must be one of {sorted(RECOMMENDATIONS)}")

    rollback = manifest["rollback"]
    if not isinstance(rollback, dict):
        problems.append("rollback must be an object")
    else:
        if not isinstance(rollback.get("tested"), bool):
            problems.append("rollback.tested must be true or false")
        if not _is_list_of_str(rollback.get("steps", [])):
            problems.append("rollback.steps must be a list of strings")

    integration = manifest["integration"]
    if isinstance(integration, dict):
        if integration.get("pattern") not in PATTERNS:
            problems.append(f"integration.pattern must be one of {sorted(PATTERNS)}")
    else:
        problems.append("integration must be an object")

    ext = manifest["external_services"]
    if not isinstance(ext, dict):
        problems.append("external_services must be an object")
    else:
        for key in ("required", "privacy_review_required", "cost_review_required",
                    "activation_is_separate_approval"):
            if not isinstance(ext.get(key), bool):
                problems.append(f"external_services.{key} must be true or false")

    approval = manifest["approval"]
    if not isinstance(approval, dict):
        problems.append("approval must be an object")
    elif approval.get("status") not in APPROVAL_STATES:
        problems.append(f"approval.status must be one of {sorted(APPROVAL_STATES)}")

    return problems


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Validate a learnrepo manifest (schema v1)")
    p.add_argument("manifest")
    p.add_argument("--json", action="store_true", help="emit machine-readable output")
    args = p.parse_args(argv)

    try:
        manifest = read_json(Path(args.manifest))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"could not read manifest: {exc}", file=sys.stderr)
        return 2

    problems = validate(manifest)
    if args.json:
        print(json.dumps({"valid": not problems, "problems": problems}, indent=2))
    elif problems:
        print(f"INVALID — {len(problems)} problem(s):")
        for problem in problems:
            print(f"  - {problem}")
    else:
        print("VALID — manifest matches schema v1")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
