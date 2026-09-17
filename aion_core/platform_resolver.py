"""Deterministic platform/capability resolver for LucyOS bootstrap planning.

This planner never installs software. It answers what the current or target
machine can use, what is already active, and which catalog skills still need
LearnRepo/lifecycle work. Installation remains behind the existing approval and
skill-lifecycle gates.
"""
from __future__ import annotations

import os
import platform

from . import skills

ALIASES = {
    "darwin": "macos", "mac": "macos", "macos": "macos",
    "linux": "linux", "windows": "windows", "win32": "windows",
}
PRIORITY_ORDER = {"P0": 0, "P1": 1, "P2": 2}


def machine_profile(*, system: str | None = None, machine: str | None = None,
                    ram_gb: float | None = None) -> dict:
    raw_system = (system or platform.system()).strip().lower()
    os_name = ALIASES.get(raw_system, raw_system)
    arch = (machine or platform.machine()).strip().lower()
    if ram_gb is None:
        try:
            pages = os.sysconf("SC_PHYS_PAGES")
            page_size = os.sysconf("SC_PAGE_SIZE")
            ram_gb = round((pages * page_size) / (1024 ** 3), 1)
        except (AttributeError, OSError, ValueError):
            ram_gb = None
    return {
        "os": os_name,
        "arch": arch,
        "ram_gb": ram_gb,
        "apple_silicon": os_name == "macos" and arch in {"arm64", "aarch64"},
    }


def _platform_fit(platforms: list[str], target: str) -> bool:
    normalized = {ALIASES.get(str(x).lower(), str(x).lower()) for x in platforms}
    return "any" in normalized or target in normalized


def resolve(*, profile: dict | None = None) -> dict:
    profile = profile or machine_profile()
    rows = {r["skill_id"]: r for r in skills.all_skills()}
    items = []
    for path in skills.catalog_manifests():
        data = skills.load_manifest(path)
        sid = data["skill_id"]
        row = rows.get(sid)
        compatible = _platform_fit(data.get("platforms", ["any"]), profile["os"])
        lifecycle = row["lifecycle_state"] if row else data.get("lifecycle_state", "DISCOVERED")
        enabled = bool(row["enabled"]) if row else False
        if not compatible:
            action = "INCOMPATIBLE"
        elif lifecycle == "ACTIVE" and enabled:
            action = "ALREADY_ACTIVE"
        elif lifecycle == "TESTED":
            action = "READY_TO_ACTIVATE"
        elif lifecycle in {"OWNER_APPROVED", "ARCHITECTURE_APPROVED", "INSTALLED_DISABLED"}:
            action = "READY_FOR_CONTROLLED_INSTALL_OR_TEST"
        else:
            action = "CONTINUE_LEARNREPO_REVIEW"
        items.append({
            "skill_id": sid,
            "name": data["name"],
            "priority": data["priority"],
            "platforms": data["platforms"],
            "compatible": compatible,
            "lifecycle": lifecycle,
            "enabled": enabled,
            "action": action,
            "cost_class": data["cost_class"],
            "risk_class": data["risk_class"],
        })
    items.sort(key=lambda x: (PRIORITY_ORDER.get(x["priority"], 9), x["skill_id"]))
    return {
        "profile": profile,
        "compatible": sum(1 for x in items if x["compatible"]),
        "incompatible": sum(1 for x in items if not x["compatible"]),
        "items": items,
    }
