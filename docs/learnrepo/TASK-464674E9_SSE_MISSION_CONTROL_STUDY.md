# TASK-464674E9 — SSE Mission Control pattern study

Date: 2026-09-17
Scope: bounded LearnRepo review only; no package, source, or runtime integration
Candidate reviewed: `AgentSystemLabs/mission-control`
Candidate URL: https://github.com/AgentSystemLabs/mission-control

## Evidence boundary

The work order did not name a source repository. A public-repository search found several
projects named Mission Control. This review selects `AgentSystemLabs/mission-control`
because its published architecture most closely matches the objective: an in-process event
bus, an SSE endpoint, SQLite, and explicitly no Socket.IO or Redis. This identification is
an assumption and must be confirmed before any source-derived implementation.

Evidence observed on 2026-09-17:

- Candidate README: describes `src/server/events.ts` as an in-process SSE event bus,
  `/api/events` as the stream, and SQLite as persistence. It states the server binds to
  `127.0.0.1` and uses no Socket.IO/Redis for updates.
- Candidate README: says writable API routes require bearer authentication and the SSE
  route exchanges bearer authentication for a short-lived ticket because browser
  `EventSource` cannot set an `Authorization` header.
- Candidate LICENSE: MIT, copyright 2026 AgentSystem Labs. Copying substantial source
  would require retaining its copyright and permission notice.
- Local observation: `bridges/http_server.py` is a dependency-free
  `ThreadingHTTPServer`, authenticates every `/api/*` request with a bearer token, sets
  `Cache-Control: no-store`, applies a strict same-origin CSP, and binds to loopback by
  default.
- Local observation: `web/app.js` performs authenticated REST snapshot refreshes, stores
  bounded offline snapshots, and already has one rendering path per domain. The service
  worker deliberately does not cache `/api/` responses.
- Source-clone attempt: a shallow HTTPS clone to a temporary directory failed because the
  execution sandbox could not resolve `github.com`. No candidate code was executed or
  installed. The review therefore does not claim line-level source verification or a
  dependency audit.

## Extracted pattern

Use SSE only as a small invalidation signal layered over the existing REST snapshot API:

1. The browser obtains a short-lived, single-use stream ticket through an existing
   bearer-authenticated POST request.
2. It opens one same-origin `EventSource` connection with that ticket. The ticket is
   consumed at connection time and expires quickly; it is not logged or persisted.
3. The server sends small typed frames such as `snapshot.changed`, containing an opaque
   monotonic event ID and affected domains, not canonical task records or secrets.
4. The browser coalesces event bursts and calls the existing `refresh()` REST path. REST
   remains the authoritative hydration and redaction boundary.
5. The stream emits comment heartbeats, caps each subscriber's pending work, disconnects
   slow clients, and removes subscribers on socket close.
6. Native EventSource reconnection is accepted, but clients also retain the current manual
   refresh/poll fallback and saved offline snapshot. Reconnect triggers a full REST refresh,
   so missed events do not corrupt state.

This is deliberately an invalidate-then-fetch design. It avoids duplicating canonical
SQLite state in a second event store, avoids importing the candidate's Electron/TanStack/
Drizzle stack, and keeps the current PWA rendering and offline behavior intact.

## Security gate

Verdict: **NEEDS_REVIEW before implementation**.

Required controls for a LucyOS implementation:

- Never place `AION_INTERFACE_TOKEN` or another long-lived credential in an SSE URL.
- Ticket values must be random, short-lived, single-use, bound to the intended stream and
  client context where practical, compared safely, and excluded from logs/error text.
- Preserve loopback-by-default serving, private HTTPS tunnel guidance, same-origin CSP,
  `no-store`, redaction, and authentication on all state hydration routes.
- Keep event payloads allowlisted and metadata-only. Do not stream commands, hidden model
  content, credentials, raw logs, or unredacted database rows.
- Bound connection count, heartbeat interval, payload size, queue depth, and write time;
  slow or abandoned subscribers must be removed to prevent thread/socket exhaustion.
- Send `X-Accel-Buffering: no` where relevant and document reverse-proxy buffering and idle
  timeout requirements. Do not weaken CSP or expose the interface beyond its current
  network boundary.
- Test ticket expiry/replay, unauthorized access, disconnect cleanup, slow-client limits,
  redaction, reconnection, and polling fallback before enabling the feature.

The candidate repository page shows no published GitHub security advisories, but absence of
listed advisories is not proof of safety. A pinned-source review remains mandatory.

## License gate

Verdict: **PASS for learning the generic SSE pattern; NEEDS_REVIEW for copying source**.

SSE and invalidate-then-fetch are general architectural patterns. No candidate source was
copied. The candidate is MIT-licensed; if a future change copies substantial code, retain
the MIT copyright and permission notice and record the exact pinned revision and copied
files. Prefer a clean, LucyOS-native implementation using Python's standard library and the
browser's native `EventSource`, which adds no runtime dependency.

## Fit decision

Recommended for a later, separately approved implementation spike:

- one authenticated SSE invalidation stream;
- one in-process, bounded subscriber registry;
- existing REST endpoints for authoritative data;
- existing polling/manual refresh as fallback;
- no new dashboard framework, database, broker, package, or scheduler.

Not approved by this study:

- importing or vendoring Mission Control;
- adopting Electron, TanStack, React, Drizzle, Socket.IO, Redis, or another event store;
- changing canonical SQLite semantics or the operating loop;
- exposing the service publicly;
- enabling any SSE route in production.

## Stop condition and next evidence

Study complete and stopped before integration. Before coding, confirm the intended Mission
Control repository, pin a commit, inspect the exact event bus/route/ticket implementation,
and approve a LucyOS design covering ticket lifecycle and bounded-resource behavior. Then
implement behind a disabled feature flag with focused HTTP and browser-client tests.
