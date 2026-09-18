# LucyOS Prompt Work Orders

This folder is a transport/provenance layer for owner-supplied prompts that an AI agent must explicitly read and execute.

It is NOT a second task queue, memory system, approval system, or source of operational truth.
LucyOS tasks/sessions/state remain canonical.

## Lifecycle

`00_PENDING -> 01_PROCESSING -> 02_ARCHIVE`

- `00_PENDING`: unread/unclaimed work orders.
- `01_PROCESSING`: claimed by one execution session.
- `02_ARCHIVE`: used prompts with execution receipts.

## Core rule

Every execution must link the prompt to an existing LucyOS `SES-*` session.
A prompt is moved to PROCESSING before execution so two agents do not work it at once.
Live repo/runtime evidence outranks prompt text if they conflict.

Never store secrets, credentials, private keys, cookies, passwords, raw sensitive logs, or account recovery data here.
