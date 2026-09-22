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

Use the existing OpenClaw WhatsApp channel. Generate assignment text with `taskcheck.whatsapp_assignment(...)` and send with OpenClaw's deterministic message command. Do not create a second WhatsApp provider when the configured channel is healthy.

## Templates

Templates are versioned JSON files under `taskcheck/templates/`. Add a new file with a stable `template_id`, integer `version`, title/description and `checks[]`. Each check has `id`, `title`, `instruction`, `help`, `expected_result`, `required`, `severity`, `evidence_allowed`, `note_allowed`; labels default to PASS/FAIL/SKIP. Load with `taskcheck.load_builtin_templates()`.

## Status logic

Routine status is deterministic. Any HIGH/CRITICAL failure yields `HOLD_PAYMENT`; other FAIL/SKIP/unanswered facts yield `REVIEW_REQUIRED`; a fully passed checklist yields `READY_FOR_REVIEW`. This is not a purchase decision. `WALK_AWAY` is reserved for future templates with explicit critical rules.

## Security / deployment

Serve only through HTTPS for external assignees. Tokens are unique, revocable and expiring. The server validates task ownership, file type/size and token scope. Never place provider secrets in frontend assets. A stable production deployment should use the existing Mark-2 host behind a managed HTTPS ingress/domain or a future approved Cloudflare tunnel.
