"""Secret detection, redaction and outbound-message guarding.

Two hard rules from the constitution are enforced here mechanically rather
than by agent good intentions:

  * No literal secret is ever written into shared-brain markdown, git, logs
    or an outbound WhatsApp message.
  * An inbound WhatsApp message that contains something that looks like a
    credential is refused and scrubbed before it reaches any state file.
"""
from __future__ import annotations

import re
from pathlib import Path

REDACTION = "[REDACTED]"

# Ordered most-specific first.  Each entry is (name, compiled pattern).
_PATTERNS = [
    ("aws_access_key", re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b")),
    ("github_token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b")),
    ("slack_token", re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}\b")),
    ("anthropic_key", re.compile(r"\bsk-ant-[A-Za-z0-9_\-]{20,}\b")),
    ("openai_key", re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_\-]{20,}\b")),
    ("google_api_key", re.compile(r"\bAIza[0-9A-Za-z_\-]{35}\b")),
    ("razorpay_key", re.compile(r"\brzp_(?:live|test)_[A-Za-z0-9]{10,}\b")),
    ("stripe_key", re.compile(r"\b[sr]k_(?:live|test)_[A-Za-z0-9]{20,}\b")),
    ("private_key_block", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("jwt", re.compile(r"\beyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\b")),
    ("bearer_header", re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._\-]{20,}")),
    # Assignments such as API_KEY=..., password: ..., secret = "..."
    ("assigned_secret", re.compile(
        r"(?i)\b([a-z0-9_.\-]*(?:passwd|password|secret|token|api[_-]?key|access[_-]?key|"
        r"private[_-]?key|client[_-]?secret|otp|recovery[_-]?code)[a-z0-9_.\-]*)[ \t]*[:=][ \t]*"
        r"['\"]?([^\s'\"]{6,})['\"]?")),
    ("card_number", re.compile(r"\b(?:\d[ -]?){13,19}\b")),
    ("otp_phrase", re.compile(r"(?i)\b(?:otp|one[ -]time (?:password|code)|verification code)\b[^\d]{0,20}\d{4,8}\b")),
]

# Values that look secret-shaped but are placeholders, not real credentials.
_PLACEHOLDERS = re.compile(
    r"(?i)^(?:x{3,}|\*{3,}|\.{3,}|<[^>]+>|\{\{.*\}\}|change[_-]?me|your[_-].*|"
    r"placeholder|example|redacted|dummy|todo|none|null|unset|\[redacted\])$")


# An assignment whose right-hand side is itself an identifier is naming a key,
# not carrying one: `secret="GITHUB_TOKEN"`, `input_tokens=args.in_tokens`.
# The exemption deliberately requires an underscore or dot, so an all-caps
# value with neither (a plausible real secret) is still reported.
_IDENTIFIER = re.compile(r"^(?:[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)+|[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)+)$")


def _is_placeholder(value: str) -> bool:
    value = value.strip().strip(",;\"')")
    if not value:
        return True
    if value.startswith("-"):          # a CLI flag, not a value
        return True
    if _IDENTIFIER.match(value):       # a key name or code reference
        return True
    if any(ch in value for ch in "(){}<>[]$`"):  # a code expression, not a literal
        return True
    return bool(_PLACEHOLDERS.match(value))


def scan_text(text: str) -> list[dict]:
    """Return a list of findings.  Never returns the secret value itself."""
    findings: list[dict] = []
    if not text:
        return findings
    for name, pattern in _PATTERNS:
        for match in pattern.finditer(text):
            value = match.group(2) if (name == "assigned_secret" and match.lastindex and match.lastindex >= 2) else match.group(0)
            if _is_placeholder(value):
                continue
            if name == "card_number" and not _luhn(re.sub(r"[ -]", "", match.group(0))):
                continue
            line = text.count("\n", 0, match.start()) + 1
            findings.append({
                "kind": name,
                "line": line,
                "preview": _mask(match.group(0)),
            })
    return findings


def _luhn(digits: str) -> bool:
    """Reduce card-number false positives (order ids, timestamps)."""
    if not digits.isdigit() or not 13 <= len(digits) <= 19:
        return False
    total, alt = 0, False
    for ch in reversed(digits):
        d = int(ch)
        if alt:
            d *= 2
            if d > 9:
                d -= 9
        total += d
        alt = not alt
    return total % 10 == 0


def _mask(value: str) -> str:
    value = value.strip()
    if len(value) <= 8:
        return REDACTION
    return f"{value[:4]}…{REDACTION}"


def redact(text: str) -> str:
    """Replace every detected secret with a redaction marker."""
    if not text:
        return text
    out = text
    for name, pattern in _PATTERNS:
        def _sub(m, _name=name):
            if _name == "assigned_secret" and m.lastindex and m.lastindex >= 2:
                if _is_placeholder(m.group(2)):
                    return m.group(0)
                return f"{m.group(1)}={REDACTION}"
            if _is_placeholder(m.group(0)):
                return m.group(0)
            if _name == "card_number" and not _luhn(re.sub(r"[ -]", "", m.group(0))):
                return m.group(0)
            return REDACTION
        out = pattern.sub(_sub, out)
    return out


def assert_clean(text: str, where: str) -> None:
    """Raise before anything secret-bearing is persisted or transmitted."""
    findings = scan_text(text)
    if findings:
        kinds = ", ".join(sorted({f["kind"] for f in findings}))
        raise SecretLeak(f"refusing to write/send {where}: possible secrets ({kinds})")


class SecretLeak(Exception):
    """Raised when secret-shaped content reaches a channel that forbids it."""


SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", "BACKUPS", "private_state"}
SKIP_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".pdf", ".zip", ".sqlite3", ".db", ".ico", ".woff2"}


IGNORE_FILE = ".secretscanignore"


def _ignore_globs(root: Path) -> list[str]:
    """Explicit, reviewable allowlist for files that hold deliberate fixtures.

    Keeping this in a file (rather than softening the patterns) means every
    exemption is visible in the diff.
    """
    f = root / IGNORE_FILE
    if not f.is_file():
        return []
    return [line.strip() for line in f.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.strip().startswith("#")]


def scan_paths(root: Path) -> list[dict]:
    """Scan a tree for committed secrets.  Used by the pre-commit guard."""
    root = Path(root)
    ignores = _ignore_globs(root)
    results: list[dict] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if path.suffix.lower() in SKIP_SUFFIXES:
            continue
        try:
            rel = path.relative_to(root)
        except ValueError:
            rel = path
        if any(rel.match(pattern) for pattern in ignores):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for finding in scan_text(text):
            results.append({"file": str(path), **finding})
    return results
