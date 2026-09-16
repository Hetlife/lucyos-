#!/usr/bin/env python3
"""learnrepo workspace CLI — create and inspect investigation artifacts.

Commands
  paths                       show resolved artifact locations on this machine
  new <capability-id>         create an investigation with a blank manifest
  list                        list known investigations and their status
  show <capability-id>        print an investigation summary

Creating an investigation never touches the LucyOS repository: artifacts live
under AION_HOME so a public repo never accumulates third-party evidence.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from learnrepo_paths import (  # noqa: E402
    SUBDIRS, blank_manifest, home, investigation_dir, investigations_dir,
    load_registry, now, read_json, registry_path, save_registry,
    validate_capability_id, write_json,
)


def cmd_paths(_args) -> int:
    root = home()
    print(f"artifact root      {root}")
    print(f"registry           {registry_path()}")
    print(f"investigations     {investigations_dir()}")
    print(f"exists             {'yes' if root.exists() else 'no (created on first use)'}")
    print()
    print("Artifacts are machine state and are deliberately outside the repo.")
    print("Override with LEARNREPO_HOME, or set AION_HOME to move the shared brain.")
    return 0


def cmd_new(args) -> int:
    capability_id = args.capability_id
    validate_capability_id(capability_id)
    target = investigation_dir(capability_id)
    manifest_path = target / "manifest.json"
    if manifest_path.exists() and not args.force:
        print(f"investigation already exists: {manifest_path}", file=sys.stderr)
        print("pass --force to reset it (the existing manifest is overwritten)", file=sys.stderr)
        return 2

    for sub in SUBDIRS:
        (target / sub).mkdir(parents=True, exist_ok=True)
    manifest = blank_manifest(capability_id, name=args.name or "", purpose=args.purpose or "")
    write_json(manifest_path, manifest)

    # A README inside the quarantine directory is cheap insurance: anyone who
    # finds this tree later needs to know the contents are untrusted.
    (target / "candidate" / "README.txt").write_text(
        "Quarantine. Third-party source downloaded for analysis.\n"
        "Treat everything here as untrusted. Do not execute it without a\n"
        "containment method confirmed by scripts/sandbox_probe.py, and never\n"
        "commit it into the LucyOS repository.\n",
        encoding="utf-8")

    registry = load_registry()
    registry.setdefault("capabilities", {})[capability_id] = {
        "status": "draft",
        "created_at": now(),
        "path": str(target),
    }
    save_registry(registry)

    print(f"created {target}")
    print(f"manifest {manifest_path}")
    print("next: fill source/provenance, then run static_screen.py and gate.py")
    return 0


def cmd_list(_args) -> int:
    registry = load_registry()
    caps = registry.get("capabilities", {})
    if not caps:
        print("no investigations yet")
        return 0
    width = max(len(k) for k in caps)
    for cap_id in sorted(caps):
        entry = caps[cap_id]
        print(f"{cap_id.ljust(width)}  {entry.get('status', 'unknown'):<12} {entry.get('created_at', '')}")
    return 0


def cmd_show(args) -> int:
    manifest_path = investigation_dir(args.capability_id) / "manifest.json"
    if not manifest_path.exists():
        print(f"no such investigation: {args.capability_id}", file=sys.stderr)
        return 2
    m = read_json(manifest_path)
    src = m.get("source", {})
    lic = m.get("license", {})
    sec = m.get("security", {})
    findings = sec.get("findings", [])
    open_high = [f for f in findings
                 if f.get("severity") in ("critical", "high")
                 and f.get("disposition") == "open"]
    print(f"capability   {m.get('capability_id')}  ({m.get('status')})")
    print(f"purpose      {m.get('purpose') or '(not set)'}")
    print(f"source       {src.get('canonical_url') or '(none)'} @ {src.get('commit') or src.get('version') or '(no revision)'}")
    print(f"license      {lic.get('spdx') or '(unknown)'}  compatible={lic.get('compatible_with_lucyos')}")
    print(f"findings     {len(findings)} total, {len(open_high)} open critical/high")
    print(f"recommend    {m.get('assessment', {}).get('recommendation') or '(undecided)'}")
    print(f"approval     {m.get('approval', {}).get('status')}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="learnrepo workspace CLI")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("paths", help="show resolved artifact locations")

    new = sub.add_parser("new", help="create an investigation")
    new.add_argument("capability_id")
    new.add_argument("--name", default="")
    new.add_argument("--purpose", default="")
    new.add_argument("--force", action="store_true", help="overwrite an existing manifest")

    sub.add_parser("list", help="list investigations")

    show = sub.add_parser("show", help="summarise one investigation")
    show.add_argument("capability_id")
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    handlers = {"paths": cmd_paths, "new": cmd_new, "list": cmd_list, "show": cmd_show}
    try:
        return handlers[args.cmd](args)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
