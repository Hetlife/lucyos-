"""NOTEBOOK.md — the one file anyone is meant to edit by hand.

Every other markdown file in the shared brain is generated and will be
overwritten.  This one is the opposite: the owner, ChatGPT, Claude, a local
model or OpenClaw can all append to it to report a bug, leave a note, correct a
fact or hand over work.  `sync()` reads it, turns each new entry into real state
(a task, an error, a memory), and stamps the entry as processed so the same
entry is never applied twice.

Token discipline: `sync()` skips anything already stamped, so a long notebook
costs almost nothing to re-sync, and processed entries are moved to
NOTEBOOK_ARCHIVE.md once the live file grows past ARCHIVE_AFTER entries.
"""
from __future__ import annotations

import re
from pathlib import Path

from . import config, db, errors, memory, security, tasks, util

ARCHIVE_AFTER = 40
STAMP = re.compile(r"<!--\s*aion:processed\s+(?P<meta>[^>]*?)-->")
HEADER = re.compile(r"^##\s*\[(?P<kind>[A-Za-z_]+)\]\s*(?P<title>.+?)\s*$")
FROM = re.compile(r"(?i)^from:\s*(?P<who>.+?)\s*$")

KIND_ACTIONS = {
    "BUG": "creates a task and an error row",
    "TASK": "creates a task in the queue",
    "FIX": "records the fix as a lesson in memory",
    "NOTE": "stores a durable note in memory",
    "FACT": "stores a fact in memory (flagged if it contradicts one)",
    "QUESTION": "creates a task so the question is answered, not lost",
    "HANDOFF": "records the handoff and its resume point",
}

TEMPLATE = """# NOTEBOOK — the file you are meant to edit

Everything else in this shared brain is generated and gets overwritten. **This
file is yours.** Owner, ChatGPT, Claude, a local model or OpenClaw can all
append to it. Run `aion notebook sync` (or just `aion boot`) and each new entry
becomes real state.

## How to add an entry

Append a block at the bottom. Nothing above is ever rewritten except by adding a
processed stamp.

```
## [BUG] Short title on one line
from: your name or model name
Describe what happened, what you expected, and how to reproduce it.
Keep it to a few lines — this is a message, not a document.
```

Kinds and what each one does:

| Kind | Effect |
|---|---|
| `[BUG]` | Creates a task and an error row so it is tracked and root-caused |
| `[TASK]` | Creates a task in the queue, ranked with everything else |
| `[FIX]` | Records what fixed something as a reusable lesson |
| `[NOTE]` | Stores a durable note in searchable memory |
| `[FACT]` | Stores a fact; a contradiction with existing memory is flagged, not overwritten |
| `[QUESTION]` | Creates a task so the question is answered rather than lost |
| `[HANDOFF]` | Records what you were doing and the exact resume point |

## Rules

- **Never write a credential here.** Keys, passwords, OTPs and card numbers are
  detected and stripped before storage; put real values in the secret store with
  `aion secrets set <NAME>`.
- Do not delete the `<!-- aion:processed ... -->` stamps. They are what stops an
  entry being applied twice.
- Processed entries are archived to `NOTEBOOK_ARCHIVE.md` automatically once this
  file gets long, so it stays cheap to read.

---

<!-- Append new entries below this line -->
"""


def path() -> Path:
    return config.home() / "NOTEBOOK.md"


def archive_path() -> Path:
    return config.home() / "NOTEBOOK_ARCHIVE.md"


def ensure() -> Path:
    p = path()
    if not p.exists():
        util.atomic_write(p, TEMPLATE)
    return p


def _split_entries(text: str) -> list[dict]:
    """Split the file into entry blocks, keeping their exact source text."""
    lines = text.splitlines()
    # Headers inside a fenced block are documentation examples, not entries.
    in_fence = False
    starts = []
    for i, line in enumerate(lines):
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            continue
        if not in_fence and HEADER.match(line):
            starts.append(i)
    entries = []
    for n, start in enumerate(starts):
        end = starts[n + 1] if n + 1 < len(starts) else len(lines)
        block = lines[start:end]
        m = HEADER.match(block[0])
        author = "unknown"
        body_lines = []
        for line in block[1:]:
            fm = FROM.match(line.strip())
            if fm and author == "unknown":
                author = fm.group("who")[:64]
                continue
            body_lines.append(line)
        entries.append({
            "kind": m.group("kind").upper(),
            "title": m.group("title").strip(),
            "author": author,
            "body": "\n".join(body_lines).strip(),
            "processed": bool(STAMP.search("\n".join(block))),
            "start": start,
            "end": end,
        })
    return entries


def sync() -> dict:
    """Apply every unprocessed entry.  Idempotent and safe to run constantly."""
    p = ensure()
    text = p.read_text(encoding="utf-8")
    entries = _split_entries(text)
    todo = [e for e in entries if not e["processed"]]
    result = {"scanned": len(entries), "applied": 0, "skipped_duplicates": 0,
              "redacted": 0, "created": []}
    if not todo:
        return result

    lines = text.splitlines()
    inserts: dict[int, str] = {}
    for entry in todo:
        clean_body = security.redact(entry["body"])
        clean_title = security.redact(entry["title"])
        if clean_body != entry["body"] or clean_title != entry["title"]:
            result["redacted"] += 1
        digest = util.sha256_text(f"{entry['kind']}|{clean_title}|{clean_body}")
        existing = db.connect().execute(
            "SELECT entry_id, created_ref FROM notebook WHERE hash=?", (digest,)).fetchone()
        if existing:
            result["skipped_duplicates"] += 1
            inserts[entry["end"]] = _stamp(existing["entry_id"], existing["created_ref"],
                                           duplicate=True)
            continue
        entry_id = f"NB-{digest[:8].upper()}"
        ref = _apply(entry["kind"], clean_title, clean_body, entry["author"], entry_id)
        conn = db.connect()
        conn.execute(
            "INSERT INTO notebook(entry_id, at, author, kind, title, body, hash, created_ref) "
            "VALUES(?,?,?,?,?,?,?,?)",
            (entry_id, util.now(), entry["author"], entry["kind"], clean_title,
             clean_body, digest, ref))
        conn.commit()
        result["applied"] += 1
        result["created"].append({"entry_id": entry_id, "kind": entry["kind"], "ref": ref})
        inserts[entry["end"]] = _stamp(entry_id, ref)

    for at in sorted(inserts, reverse=True):
        lines.insert(at, inserts[at])
    body = "\n".join(lines)
    if body != text:
        # Redact the live file too, so a pasted secret does not sit on disk.
        util.atomic_write(p, security.redact(body) + ("\n" if not body.endswith("\n") else ""))
    _archive_if_long()
    db.log_event("aion", "notebook.sync", "", f"{result['applied']} applied")
    return result


def _stamp(entry_id: str, ref: str, duplicate: bool = False) -> str:
    tag = "duplicate of an earlier entry" if duplicate else f"created {ref or 'nothing'}"
    return f"<!-- aion:processed {entry_id} at={util.now()} — {tag} -->"


def _apply(kind: str, title: str, body: str, author: str, entry_id: str) -> str:
    """Turn one entry into real state and return the id it created."""
    source = f"notebook {entry_id} from {author}"
    if kind == "BUG":
        eid = errors.record("notebook", title, body)
        tid = tasks.create(f"Fix: {title}", description=f"{body}\n\nReported by {author} ({entry_id}).",
                           impact=4, priority=2, success_criteria="reproduced, fixed, test added",
                           model_class="B")
        return f"{tid},{eid}"
    if kind == "TASK":
        return tasks.create(title, description=f"{body}\n\nRequested by {author} ({entry_id}).",
                            priority=2)
    if kind == "QUESTION":
        return tasks.create(f"Answer: {title}",
                            description=f"{body}\n\nAsked by {author} ({entry_id}).",
                            priority=2, success_criteria="a recorded answer with evidence")
    if kind == "FIX":
        return memory.remember("lesson", title, body, confidence="SUPPORTED_FACT", source=source)
    if kind == "FACT":
        return memory.remember("fact", title, body, confidence="SUPPORTED_FACT", source=source)
    if kind == "HANDOFF":
        db.set_meta("notebook_handoff", f"{title}: {body}"[:2000])
        return memory.remember("fact", f"handoff: {title}", body, source=source)
    return memory.remember("preference" if kind == "PREFERENCE" else "fact", title, body,
                           source=source)


def _archive_if_long() -> int:
    """Move processed entries out of the live file once it grows."""
    p = ensure()
    text = p.read_text(encoding="utf-8")
    entries = _split_entries(text)
    processed = [e for e in entries if e["processed"]]
    if len(processed) <= ARCHIVE_AFTER:
        return 0
    lines = text.splitlines()
    move = processed[:len(processed) - ARCHIVE_AFTER // 2]
    moved_text = []
    for entry in move:
        moved_text.extend(lines[entry["start"]:entry["end"]])
    keep = [l for i, l in enumerate(lines)
            if not any(e["start"] <= i < e["end"] for e in move)]
    ap = archive_path()
    header = "" if ap.exists() else "# NOTEBOOK ARCHIVE\n\nProcessed entries, kept for history.\n\n"
    with open(ap, "a", encoding="utf-8") as fh:
        fh.write(header + "\n".join(moved_text) + "\n")
    util.atomic_write(p, "\n".join(keep) + "\n")
    return len(move)


def recent(limit: int = 10) -> list:
    return db.connect().execute(
        "SELECT * FROM notebook ORDER BY at DESC LIMIT ?", (limit,)).fetchall()
