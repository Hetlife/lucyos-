#!/usr/bin/env python3
"""Non-executing static risk screen of a quarantined candidate directory.

This reads files.  It never imports, builds, installs or runs anything from
the candidate, so it is safe to point at untrusted source.

Treat the output as leads, not verdicts.  Every pattern here has legitimate
uses — a package with a postinstall script is not malware, and a project that
opens sockets is usually just a network client.  The value is that it tells
you *where to look* in a repository too large to read line by line.  Confirm
material findings by reading the code in context.

A clean report is not proof of safety: obfuscated, compiled, generated or
downloaded-at-runtime code can hide anything.

Usage:
    python3 static_screen.py <directory> [--json] [--max-bytes N]

Exit codes: 0 screened (findings may exist) · 2 error
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

DEFAULT_MAX_BYTES = 2_000_000          # skip files larger than this
SNIPPET_CHARS = 120
SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", "dist",
             "build", ".mypy_cache", ".pytest_cache", "vendor", ".tox"}
BINARY_SUFFIXES = {".so", ".dll", ".dylib", ".exe", ".bin", ".o", ".a", ".class",
                   ".pyc", ".pyd", ".wasm", ".jar", ".node"}
ARCHIVE_SUFFIXES = {".zip", ".tar", ".gz", ".bz2", ".xz", ".7z", ".rar"}

# Files whose mere presence means "code runs when this is installed or built".
HOOK_FILES = {
    "setup.py": "python build/install script executes at install time",
    "conanfile.py": "package manager script executes at build time",
    "binding.gyp": "native build executed at install time",
    "Makefile": "build targets may run arbitrary commands",
    "makefile": "build targets may run arbitrary commands",
    "install.sh": "install script",
    "setup.sh": "setup script",
    "bootstrap.sh": "bootstrap script",
    "Dockerfile": "container build steps run arbitrary commands",
    ".npmrc": "npm configuration can redirect registries",
    ".pypirc": "package index configuration",
}

HOOK_DIRS = {".github/workflows": "CI runs on push/PR with repository permissions",
             ".gitlab-ci.yml": "CI pipeline definition",
             ".husky": "git hooks run on developer machines"}

# Each rule: (category, severity_hint, compiled pattern, why it matters).
# Patterns use character classes rather than literal example credentials so
# this file does not itself look like a secret to a scanner.
RULES = [
    ("install_hook", "high",
     re.compile(r'"(?:pre|post)?install"\s*:|"prepare"\s*:|"prepublish"\s*:'),
     "npm lifecycle script runs automatically on install"),

    ("dynamic_eval", "high",
     re.compile(r"\beval\s*\(|\bexec\s*\(|new\s+Function\s*\(|\bcompile\s*\("),
     "code built at runtime is invisible to static review"),

    ("deserialization", "high",
     re.compile(r"pickle\.loads|marshal\.loads|yaml\.load\s*\((?![^)]*Safe)|"
                r"cPickle\.loads|unserialize\s*\("),
     "deserializing untrusted data can execute code"),

    # `.*` rather than `[^)]*` on purpose: the shell=True keyword is routinely
    # separated from the call by nested parentheses, e.g.
    # subprocess.run("ls " + os.environ.get("X"), shell=True)
    ("shell_execution", "high",
     re.compile(r"os\.system\s*\(|subprocess\.[A-Za-z_]+\(.*shell\s*=\s*True|"
                r"popen\s*\(|child_process\.(?:exec|execSync)\s*\(|`[^`\n]*\$\{",
                re.IGNORECASE),
     "shell execution turns any injected string into a command"),

    ("remote_code_load", "critical",
     re.compile(r"(?:curl|wget)[^\n|;]{0,80}\|\s*(?:ba)?sh|"
                r"urlopen\([^)]*\)\s*\.read\(\)\s*\)?\s*(?:,|\))?\s*$|"
                r"requests\.get\([^)]*\)\.(?:text|content)\s*\)\s*(?:#.*)?$"),
     "downloading and running code at runtime defeats every prior review"),

    ("network_call", "medium",
     re.compile(r"\b(?:urllib\.request|urlopen|requests\.(?:get|post|put)|httpx\.|"
                r"socket\.socket|fetch\s*\(|axios\.|XMLHttpRequest|net\.connect)\b"),
     "outbound network activity — confirm the destination and whether it is optional"),

    ("hardcoded_endpoint", "low",
     re.compile(r"https?://[A-Za-z0-9.\-]+(?::\d+)?(?:/[^\s\"'<>]*)?"),
     "hardcoded endpoint — check it matches documented behaviour"),

    ("credential_access", "high",
     re.compile(r"\.ssh/|id_[re][sd]sa|\.aws/credentials|\.netrc|\.docker/config|"
                r"keychain|gnome-keyring|Login\s+Data|cookies\.sqlite|"
                r"\.config/gcloud|kube(?:ctl)?/config"),
     "reads credential stores — rarely legitimate in a library"),

    ("env_secret_read", "medium",
     re.compile(r"(?:os\.environ(?:\.get)?\s*\(\s*|process\.env\.)"
                r"['\"]?[A-Za-z_]*(?:TOKEN|SECRET|PASSWORD|API[_-]?KEY|CREDENTIAL)"),
     "reads secret-shaped environment variables"),

    ("wallet_or_finance", "critical",
     re.compile(r"wallet\.dat|electrum|metamask|keystore/|privateKey|mnemonic|seed\s*phrase",
                re.IGNORECASE),
     "financial/crypto credential access"),

    ("persistence", "high",
     re.compile(r"crontab|systemctl\s+enable|LaunchAgents|autostart|"
                r"\.bashrc|\.zshrc|\.profile|rc\.local|Run\\\\CurrentVersion"),
     "attempts to survive reboot or hook a shell startup"),

    ("privilege", "high",
     re.compile(r"\bsudo\b|setuid|chmod\s+[0-7]*777|CAP_SYS_ADMIN|--privileged"),
     "privilege escalation or over-broad permissions"),

    ("security_control_disable", "high",
     re.compile(r"verify\s*=\s*False|rejectUnauthorized\s*:\s*false|"
                r"NODE_TLS_REJECT_UNAUTHORIZED|InsecureSkipVerify\s*:\s*true|"
                r"check_hostname\s*=\s*False|ssl\._create_unverified_context"),
     "disables TLS verification"),

    ("telemetry", "medium",
     re.compile(r"telemetry|analytics|posthog|mixpanel|segment\.io|sentry|"
                r"google-analytics|amplitude", re.IGNORECASE),
     "usage reporting — must be disabled by default in LucyOS"),

    ("obfuscation", "high",
     re.compile(r"(?:atob|b64decode|base64\.b64decode|fromCharCode)\s*\(|"
                r"\\x[0-9a-fA-F]{2}(?:\\x[0-9a-fA-F]{2}){8,}"),
     "encoded payloads hide intent from review"),

    ("committed_secret", "critical",
     re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}\b|"
                r"\b(?:AKI|ASI)A[0-9A-Z]{16}\b|"
                r"\bsk-(?:ant-)?[A-Za-z0-9_\-]{24,}\b|"
                r"-----BEGIN (?:RSA |EC |OPENSSH |PGP )?PRIVATE KEY-----|"
                r"\bxox[abprs]-[A-Za-z0-9-]{12,}\b"),
     "credential committed to the repository"),
]

SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}


def _redact(text: str) -> str:
    """Never echo a matched credential back into a report."""
    for category, _sev, pattern, _why in RULES:
        if category == "committed_secret":
            text = pattern.sub("[REDACTED-CREDENTIAL]", text)
    return text


def _snippet(line: str) -> str:
    cleaned = _redact(line.strip())
    if len(cleaned) > SNIPPET_CHARS:
        cleaned = cleaned[:SNIPPET_CHARS] + "…"
    return cleaned


def _looks_binary(path: Path) -> bool:
    if path.suffix.lower() in BINARY_SUFFIXES:
        return True
    try:
        with path.open("rb") as fh:
            return b"\0" in fh.read(4096)
    except OSError:
        return False


def screen(root: Path, max_bytes: int = DEFAULT_MAX_BYTES) -> dict:
    root = Path(root)
    findings = []
    stats = {"files_read": 0, "files_skipped_binary": 0, "files_skipped_large": 0,
             "archives": 0, "total_files": 0}

    for path in sorted(root.rglob("*")):
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if path.is_dir():
            continue
        stats["total_files"] += 1
        rel = path.relative_to(root)

        if path.name in HOOK_FILES:
            findings.append({
                "category": "install_hook", "severity": "high", "file": str(rel),
                "line": 0, "snippet": path.name,
                "why": HOOK_FILES[path.name],
            })
        if path.suffix.lower() in ARCHIVE_SUFFIXES:
            stats["archives"] += 1
            findings.append({
                "category": "opaque_artifact", "severity": "medium", "file": str(rel),
                "line": 0, "snippet": path.name,
                "why": "archive contents are not reviewed by this screen",
            })
            continue
        if _looks_binary(path):
            stats["files_skipped_binary"] += 1
            findings.append({
                "category": "opaque_artifact", "severity": "medium", "file": str(rel),
                "line": 0, "snippet": path.name,
                "why": "binary artifact — cannot be reviewed as source; prefer building "
                       "from source or reject",
            })
            continue
        try:
            if path.stat().st_size > max_bytes:
                stats["files_skipped_large"] += 1
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        stats["files_read"] += 1

        for lineno, line in enumerate(text.splitlines(), start=1):
            if len(line) > 2000:
                findings.append({
                    "category": "obfuscation", "severity": "medium", "file": str(rel),
                    "line": lineno, "snippet": f"<line of {len(line)} chars>",
                    "why": "very long single line — minified or generated code hides intent",
                })
                continue
            for category, severity, pattern, why in RULES:
                if pattern.search(line):
                    findings.append({
                        "category": category, "severity": severity, "file": str(rel),
                        "line": lineno, "snippet": _snippet(line), "why": why,
                    })

    for hook_dir, why in HOOK_DIRS.items():
        candidate = root / hook_dir
        if candidate.exists():
            findings.append({
                "category": "install_hook", "severity": "medium", "file": hook_dir,
                "line": 0, "snippet": hook_dir, "why": why,
            })

    findings.sort(key=lambda f: (SEVERITY_ORDER.get(f["severity"], 9), f["file"], f["line"]))

    counts = {}
    for finding in findings:
        counts[finding["severity"]] = counts.get(finding["severity"], 0) + 1

    return {
        "root": str(root),
        "stats": stats,
        "counts": counts,
        "findings": findings,
        "disclaimer": ("Leads, not verdicts. Every pattern has legitimate uses — confirm "
                       "each material finding by reading the code in context. A clean "
                       "result is not proof of safety."),
    }


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Static risk screen (never executes candidate code)")
    p.add_argument("directory")
    p.add_argument("--json", action="store_true")
    p.add_argument("--max-bytes", type=int, default=DEFAULT_MAX_BYTES)
    args = p.parse_args(argv)

    root = Path(args.directory)
    if not root.is_dir():
        print(f"not a directory: {root}", file=sys.stderr)
        return 2

    report = screen(root, args.max_bytes)
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        stats = report["stats"]
        print(f"screened {stats['files_read']} files under {report['root']}")
        if report["counts"]:
            summary = ", ".join(f"{v} {k}" for k, v in sorted(
                report["counts"].items(), key=lambda kv: SEVERITY_ORDER.get(kv[0], 9)))
            print(f"findings: {summary}\n")
        else:
            print("findings: none\n")
        for finding in report["findings"][:80]:
            location = f"{finding['file']}:{finding['line']}" if finding["line"] else finding["file"]
            print(f"  [{finding['severity']:<8}] {finding['category']:<24} {location}")
            print(f"             {finding['snippet']}")
            print(f"             why: {finding['why']}")
        if len(report["findings"]) > 80:
            print(f"  … {len(report['findings']) - 80} more (use --json for all)")
        print(f"\n{report['disclaimer']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
