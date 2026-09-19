# BACKLOG EPIC — Secure Capability Gateway + Alternative-Path Engine

**Status:** BACKLOG ONLY — do not implement in the current wave.

Design a secure, user-friendly gateway for WhatsApp and future control
channels, with encrypted payloads, authenticated owner approvals, durable task
creation, capability-gap discovery, LearnRepo research, safe prototyping, and
owner-approved capability evolution.

Future scope: encrypted secret/payload relay; time-bounded approvals bound to
owner and exact action; durable task/session/checkpoint creation through
existing LucyOS state; alternative-path discovery; LearnRepo
NEED→SEARCH→QUEUE→VERIFY→SANDBOX→EXTRACT→TEST; and reviewed capability
manifests with tests, rollback and security evidence.

Non-goals now: implementation, connector installation, public exposure,
credential rotation, unrestricted shell, autonomous approval, or CI/service
changes.

Required future gates: threat model, data-flow and approval review, abuse and
replay/idempotency tests, secret scan, cost/rollback plan, owner approval, and
independent architecture/security review.
