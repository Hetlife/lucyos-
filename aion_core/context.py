"""Task-specific context packets.

A worker gets only what its task needs: the objective, the current state, the
relevant files, the recent failures and the success criteria — never the whole
repository or the whole chat history.  This is the main token-waste control.
"""
from __future__ import annotations

import ast
import json
from pathlib import Path
import re
import shlex
import subprocess

from . import agents, db, errors, memory, resume, security, tasks, util


def build(task_id: str, *, module: str | None = None,
          budget_bytes: int | None = None, since: str | None = None,
          json_output: bool = False) -> str:
    if budget_bytes is not None and budget_bytes < 0:
        raise ValueError("context budget must be non-negative")
    if module is None and (budget_bytes is not None or since is not None):
        raise ValueError("--budget-bytes and --since require --module")
    row = tasks.get(task_id)
    if row is None:
        return _output(security.redact(f"no such task {task_id}"), json_output)
    r = resume.load()
    related = memory.search(row["title"], limit=5)
    recent_errs = db.connect().execute(
        "SELECT error_id, kind, message FROM errors WHERE task_id=? OR component=? "
        "ORDER BY created_at DESC LIMIT 3", (task_id, row["project"])).fetchall()
    route = agents.route(row["model_class"].lower() if row["model_class"] else "code",
                         complexity=min(5, row["priority"] + 1))
    lines = [
        f"# WORK ORDER {task_id}",
        "",
        f"TASK_ID: {task_id}",
        f"OBJECTIVE: {row['title']}",
        f"WHY IT MATTERS: {row['description'] or 'not recorded'}",
        f"PROJECT: {row['project']}",
        f"STATUS: {row['status']}   PRIORITY: {row['priority']}   VALUE: {tasks.value(row)}",
        f"ASSIGNED CLASS: {row['model_class']} (router suggests {route['model_class']}: {route['reason']})",
        "",
        "## CURRENT STATE",
        r.get("current_state", "not recorded"),
        f"Bottleneck: {r.get('bottleneck', 'not identified')}",
        "",
        "## FILES",
        row["output_location"] or "not specified",
        "",
        "## SUCCESS CRITERIA",
        row["success_criteria"] or "not recorded — define before claiming DONE",
        "",
        "## VALIDATION METHOD",
        row["validation_method"] or "run the repo test suite and record the command + result",
        "",
        "## CONSTRAINTS",
        "- Do not mark DONE without evidence (a command run, a measurement, an observation).",
        "- Never write a credential into shared state, git, logs or WhatsApp.",
        "- Tier-3 actions (spend, contracts, credentials, irreversible changes) need an approval id.",
        "- Escalate after two materially different failures instead of looping.",
        "",
        "## RELEVANT MEMORY",
    ]
    lines += [f"- {m['memory_id']} [{m['confidence']}] {m['title']}" for m in related] or ["- none"]
    lines += ["", "## RECENT FAILURES"]
    lines += [f"- {e['error_id']} ({e['kind']}) {e['message'][:120]}" for e in recent_errs] or ["- none"]
    lines += ["", "## RETURN THIS RESULT PACKET", "",
              "STATUS / ACTIONS / FILES_CHANGED / TESTS / RESULTS / BLOCKERS / NEXT_ACTION",
              "Use these seven field names exactly. Put unresolved failures in BLOCKERS; "
              "put the exact resume step in NEXT_ACTION. Do not add alternate field names.", ""]
    if module is not None:
        sections = _repo_sections(module, budget_bytes, since)
        offset = lines.index("## SUCCESS CRITERIA")
        lines[offset:offset] = sections
    return _output(security.redact("\n".join(lines)), json_output)


def _output(packet: str, json_output: bool) -> str:
    # Redact before JSON encoding so escaping cannot hide credentials.
    return json.dumps({"context": packet}, ensure_ascii=False) if json_output else packet


def _git(repo: Path, *args: str) -> str:
    try:
        result = subprocess.run(["git", *args], cwd=repo, text=True,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                timeout=10, check=False)
    except (OSError, subprocess.TimeoutExpired):
        raise ValueError("context git query unavailable or timed out") from None
    if result.returncode:
        raise ValueError("context git query failed (repository or revision unavailable)")
    return result.stdout


def _repo_sections(module: str, budget_bytes: int | None, since: str | None) -> list[str]:
    repo = Path(__file__).resolve().parents[1]
    if not re.fullmatch(r"[a-z][a-z0-9_.-]*", module):
        raise ValueError("invalid context module name")
    manifest = util.read_json(repo / ".lucy/architecture/modules" / (module + ".json"))
    if not isinstance(manifest, dict) or manifest.get("module") != module:
        raise ValueError("context module manifest unavailable or invalid")
    excluded = [".lucy/planning/**", ".lucy/archive/**", "directives/**",
                "docs/internal/**", ".lucy/handoffs/**"]
    if module.startswith("kernel."):
        excluded.append("business/**")

    def allowed(path: Path) -> bool:
        return (not path.is_symlink() and path.is_file()
                and repo in path.resolve().parents
                and not any(path.relative_to(repo).as_posix().startswith(x[:-2])
                            for x in excluded))

    def expand(patterns: list[str]) -> list[str]:
        found = set()
        for pattern in patterns:
            if Path(pattern).is_absolute() or ".." in Path(pattern).parts:
                raise ValueError("invalid context manifest path")
            found.update(p.relative_to(repo).as_posix() for p in repo.glob(pattern) if allowed(p))
        return sorted(found)

    owned = expand(manifest["owned_files"])
    tests = set(expand(manifest["tests"]))
    modules = {p[:-3].replace("/", ".") for p in owned if p.endswith(".py")}
    for path in sorted((repo / "tests").rglob("test*.py")):
        if not allowed(path):
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except (SyntaxError, UnicodeError):
            continue
        imports = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(a.name for a in node.names)
            elif isinstance(node, ast.ImportFrom):
                base = node.module or ""
                if node.level:
                    package = path.relative_to(repo).parts[:-1]
                    base = ".".join((*package[:len(package) - node.level + 1], base)).strip(".")
                imports.add(base)
                imports.update(base + "." + a.name for a in node.names)
        if modules & imports:
            tests.add(path.relative_to(repo).as_posix())
    budget = min(200 * 1024, budget_bytes if budget_bytes is not None else 200 * 1024)
    listed, deferred, used = [], [], 0
    for name in owned:
        path = repo / name
        size = path.stat().st_size
        if len(listed) >= 10 or used + size > budget:
            deferred.append(name)
            continue
        listed.append(f"- {name} ({size} bytes, sha256 {util.sha256_file(path)[:12]})")
        used += size
    watermark = since if since is not None else db.get_meta("last_high_model_reviewed_commit", "")
    changed = []
    if watermark:
        commit = _git(repo, "rev-parse", "--verify", "--end-of-options",
                      watermark + "^{commit}").strip()
        names = _git(repo, "diff", "--name-only", "-z", commit, "HEAD", "--").split("\0")
        # Match patterns too: deleted owned files no longer appear in glob results.
        changed = sorted(n for n in names if n and any(
            Path(n).match(pattern) for pattern in manifest["owned_files"]))
    canonical = _git(repo, "rev-parse", "--verify", "origin/main").strip()
    branch = _git(repo, "branch", "--show-current").strip() or "(detached)"
    dirty = _git(repo, "status", "--porcelain", "-z", "--no-renames").split("\0")
    test_names = [p[:-3].replace("/", ".") for p in sorted(tests) if p.endswith(".py")]
    lines = [f"## MODULE {module}", manifest["purpose"],
             "Public seam: " + ", ".join(manifest["public_api"]),
             "Invariants: " + "; ".join(manifest["invariants"]),
             "Risk: " + manifest["risk_level"],
             "ADRs: " + (", ".join(manifest["adrs"]) or "none"),
             "", "## OWNED FILES", f"Selected {len(listed)} files / {used} bytes (limit 10 / {budget}).",
             "Index only; file contents are not embedded.", *(listed or ["- none"]),
             "", "## TESTS", *["- " + p for p in sorted(tests)],
             "", "## NEIGHBOURS", ", ".join(manifest["allowed_dependencies"]) or "none",
             "", f"## DELTA SINCE {watermark or '(no watermark)'}",
             *(["- " + p for p in changed] or ["- none"]),
             "", "## EXCLUDED", *["- " + p for p in excluded],
             "- Other modules' files (except test pointers above).",
             *["- " + p + " (budget exceeded; path only, no content)" for p in deferred],
             "", "## CANONICAL", f"origin/main: {canonical}", f"Branch: {branch}",
             f"Dirty count: {sum(bool(p) for p in dirty)}",
             "", "## ROLLBACK / COMMANDS",
             "python3 -m unittest " + " ".join(shlex.quote(t) for t in test_names) + " -v",
             "python3 -m unittest discover -s tests -t . -q", "./aion scan .",
             "python3 scripts/check_portability.py",
             "python3 scripts/verify_authority.py strict --base origin/main --branch " + shlex.quote(branch),
             "python3 scripts/verify_authority.py anti-dup --base origin/main",
             "Rollback: git revert <task-commit-sha> (owner-controlled after merge).", ""]
    return lines
