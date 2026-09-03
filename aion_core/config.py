"""Central configuration and path resolution for AION.

The canonical operational state lives on the owner's machine under AION_HOME
(default ~/openclaw/shared_brain).  Nothing in this module ever holds secrets;
secrets live only in the OS keyring / .env file referenced by SECRETS_FILE and
are never read into shared-brain markdown, git or WhatsApp payloads.
"""
from __future__ import annotations

import os
from pathlib import Path

APP_NAME = "AION"
SCHEMA_VERSION = 1
PROMPT_VERSION = "1.0.0"


def home() -> Path:
    """Root of the canonical shared brain."""
    return Path(os.environ.get("AION_HOME", Path.home() / "openclaw" / "shared_brain")).expanduser()


def db_path() -> Path:
    return Path(os.environ.get("AION_DB", home() / "state" / "aion.sqlite3")).expanduser()


def secrets_file() -> Path:
    """Path to the protected secret store (never committed, 0600)."""
    return Path(os.environ.get("AION_SECRETS", home() / "private_state" / "secrets.env")).expanduser()


# Directory layout.  Every entry has an operational purpose; nothing decorative.
DIRS = [
    "state",
    "private_state",
    "PROJECTS",
    "TASKS",
    "AGENTS/prompts",
    "AGENTS/work_orders",
    "AGENTS/results",
    "APPROVALS",
    "MEMORY/facts",
    "MEMORY/decisions",
    "MEMORY/lessons",
    "MEMORY/preferences",
    "RESEARCH",
    "EXPERIMENTS",
    "HANDOFFS",
    "INBOX/pending",
    "INBOX/processed",
    "INBOX/failed",
    "OUTBOX",
    "METRICS",
    "FINANCE",
    "LOGS",
    "BACKUPS",
    "CONFIG",
    "SCHEMAS",
    "INDEX",
]

# Markdown surfaces the owner (or another AI) reads directly.
DOCS = [
    "README.md",
    "SYSTEM_STATE.md",
    "GLOBAL_TASKS.md",
    "DECISIONS.md",
    "BLOCKERS.md",
    "APPROVALS.md",
    "OWNER_SETUP_REQUIRED.md",
    "RESUME.md",
    "CHANGELOG.md",
]

# Budget failsafes.  Zero real money is spent without an approval; these caps
# bound model spend that is already inside an authorised budget.
DEFAULT_DAILY_COST_CAP_INR = float(os.environ.get("AION_DAILY_COST_CAP_INR", "200"))
DEFAULT_MONTHLY_COST_CAP_INR = float(os.environ.get("AION_MONTHLY_COST_CAP_INR", "2000"))

# Loop failsafes.
MAX_TASK_RETRIES = 3
STALE_CLAIM_SECONDS = 60 * 45
MAX_CONSECUTIVE_ERRORS = 5
