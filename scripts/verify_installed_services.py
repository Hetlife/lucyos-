#!/usr/bin/env python3
"""Verify installed AION systemd user units against rendered repository templates."""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path

UNITS = (
    "aion-bridge.service",
    "aion-interface.service",
    "aion-maintenance.service",
    "aion-maintenance.timer",
    "aion-work.service",
    "aion-work.timer",
)

def render(template: str, *, repo: Path, aion_home: Path) -> str:
    return template.replace("@REPO@", str(repo)).replace("@AION_HOME@", str(aion_home))

def verify(template_repo: Path, render_repo: Path, aion_home: Path, units_dir: Path) -> dict:
    results = []
    for name in UNITS:
        template_path = template_repo / "systemd" / name
        installed_path = units_dir / name
        if not template_path.is_file():
            results.append({"unit": name, "status": "missing-template"})
            continue
        if not installed_path.is_file():
            results.append({"unit": name, "status": "missing-installed"})
            continue
        expected = render(template_path.read_text(), repo=render_repo, aion_home=aion_home)
        actual = installed_path.read_text()
        results.append({"unit": name, "status": "match" if actual == expected else "different"})
    return {
        "ok": all(item["status"] == "match" for item in results),
        "template_repo": str(template_repo),
        "render_repo": str(render_repo),
        "aion_home": str(aion_home),
        "units_dir": str(units_dir),
        "results": results,
    }

def main() -> int:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=root,
                        help="repository checkout containing the systemd templates")
    parser.add_argument("--render-repo", type=Path,
                        help="repo path expected inside installed units; defaults to --repo")
    parser.add_argument("--aion-home", type=Path,
                        default=Path(os.environ.get("AION_HOME", Path.home() / "openclaw" / "shared_brain")))
    parser.add_argument("--units-dir", type=Path, default=Path.home() / ".config" / "systemd" / "user")
    args = parser.parse_args()
    template_repo = args.repo.resolve()
    render_repo = (args.render_repo or args.repo).resolve()
    report = verify(template_repo, render_repo, args.aion_home.resolve(), args.units_dir.resolve())
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["ok"] else 1

if __name__ == "__main__":
    raise SystemExit(main())
