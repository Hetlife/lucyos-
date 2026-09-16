# LucyOS LearnRepo maintenance pilot

This directory is the repository-side surface for the native LearnRepo queue/health pilot.
Canonical runtime state remains in the existing AION SQLite database; this directory holds
contracts and concise reference-learning notes only.

The pilot deliberately does **not** install APScheduler or Healthchecks.io. Linux uses the
existing AION systemd maintenance timer as the wake-up trigger. The queue, leases, grace
handling, health results, deduplicated escalations and contracts are LucyOS-native.

Routine nightly/daily/weekly checks are deterministic. A healthy run must record `AI_CALLS=0`.
Only a failing deterministic check that requires reasoning or code repair creates an
`API_WORK_REQUIRED` task in the existing LucyOS task/control plane.
