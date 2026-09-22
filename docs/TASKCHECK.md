# LUCY TaskCheck

TaskCheck is LucyOS's token-scoped real-world checklist layer. It reuses canonical AION `tasks`, SQLite, events, security scanning and OpenClaw WhatsApp; it is not a second queue or approval system.

## Create a task

```bash
AION_HOME=~/openclaw/shared_brain ./scripts/taskcheck create \
  --template used_camera_insta360_go2 --title "Used Insta360 GO 2 inspection" \
  --description "Inspect before payment" --requester Het --assignee Aksh \
  --location "Mumbai, India" --item "used Insta360 GO 2" --price "₹8,000" \
  --base-url "$TASKCHECK_PUBLIC_BASE_URL"
```

The command creates a canonical AION task plus TaskCheck domain rows in the same SQLite database. The access token is returned once; only its SHA-256 hash is stored.

## Lifecycle

`ASSIGNED -> OPENED -> STARTED -> COMPLETED -> REVIEWED`. Submission moves the linked AION task to `NEEDS_REVIEW`; requester review closes it as `DONE`. Events use the existing `events` table: `task.created`, `task.assigned`, `task.opened`, `task.started`, `task.check.completed`, `task.completed`, `task.reviewed`.

## Web app and evidence

Run `python3 bridges/taskcheck_server.py --host 127.0.0.1 --port 8790` behind HTTPS. Public task URLs are `/t/<opaque-token>`. Browser code receives no LucyOS/OpenClaw/database credentials. Photos are raw file uploads (JPEG/PNG/WebP/HEIC/HEIF, max 8 MB) stored under `$AION_HOME/TASKCHECK/evidence/<task>/`; metadata lives in SQLite.

## WhatsApp

Use the existing OpenClaw WhatsApp channel. Generate assignment text with `taskcheck.whatsapp_assignment(...)` and send with OpenClaw's deterministic message command. Do not create a second WhatsApp provider when the configured channel is healthy. For automatic requester completion reports, start the public server with `TASKCHECK_NOTIFY_TARGET` set server-side to the requester WhatsApp target and optionally `TASKCHECK_OPENCLAW_BIN`; the browser never receives either value. Transport failure emits `task.notification.failed` but never discards a submitted result.

## Templates

Templates are versioned JSON files under `taskcheck/templates/`. Add a new file with a stable `template_id`, integer `version`, title/description and `checks[]`. Each check has `id`, `title`, `instruction`, `help`, `expected_result`, `required`, `severity`, `evidence_allowed`, `note_allowed`; labels default to PASS/FAIL/SKIP. Load with `taskcheck.load_builtin_templates()`.

## Status logic

Routine status is deterministic. Any HIGH/CRITICAL failure yields `HOLD_PAYMENT`; other FAIL/SKIP/unanswered facts yield `REVIEW_REQUIRED`; a fully passed checklist yields `READY_FOR_REVIEW`. This is not a purchase decision. `WALK_AWAY` is reserved for future templates with explicit critical rules.

## Security / deployment

Configuration: `TASKCHECK_PUBLIC_BASE_URL` is used by the CLI when generating links; `TASKCHECK_NOTIFY_TARGET` and optional `TASKCHECK_OPENCLAW_BIN` configure server-side completion notification. Serve only through HTTPS for external assignees. Tokens are unique, revocable and expiring. The server validates task ownership, file type/size and token scope. Never place provider secrets in frontend assets. A stable production deployment should use the existing Mark-2 host behind a managed HTTPS ingress/domain or a future approved Cloudflare tunnel.

## Expiry and demand-driven hosting

Each TaskCheck has two independent clocks. `expires_at` is the real-world completion deadline. `public_access_until` is the bearer-link exposure deadline. New tasks start with both deadlines equal. If a task is submitted early, public access is shortened to at most 60 minutes after submission so the assignee can download/share the report without leaving the link online for days.

Overdue incomplete TaskChecks transition to `EXPIRED`; their linked AION task transitions to `CANCELLED`, while stored answers/evidence remain in canonical AION storage. `task.expired` is recorded in the existing event log.

On Mark-2, `scripts/taskcheck_host reconcile` starts the loopback TaskCheck server and Cloudflare public ingress only while at least one unexpired public TaskCheck exists. With no public TaskChecks, it stops only those TaskCheck processes; it never shuts down Mark-2 or unrelated LucyOS/OpenClaw services. Mark-2 runs this reconciliation every five minutes through cron.

Create tasks with an explicit deadline using `--expires-hours <N>`. When no `--base-url` is supplied, the CLI can bring up the TaskCheck host and return the current public URL automatically. Completed reports/evidence remain local after public exposure closes.
