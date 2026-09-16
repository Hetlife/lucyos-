# Healthchecks.io — extracted patterns only

Official material consulted: Healthchecks.io documentation pages for configuring checks,
START/SUCCESS/FAIL signals, grace time, run duration/run IDs, systemd monitoring and reliability.

## What we learned
- Distinguish **started**, **successful**, **failed**, **late**, and **down/missed** states.
- Grace time absorbs expected scheduling jitter and also bounds excessive run duration after START.
- START plus terminal status enables measured duration and distinguishes “did not run” from “ran and failed”.
- Monitoring network calls need explicit timeouts and should not block the underlying job.

## Pattern LucyOS copies
- START/SUCCESS/FAIL lifecycle plus LATE/MISSED classification.
- Expected time, grace seconds, run ID, start/end timestamps and measured duration.
- Escalate after deterministic evidence, not on small timing jitter.

## What LucyOS does not import
- Healthchecks.io Django/database/server stack, hosted ping service or notification infrastructure.

## Known cautions
- External monitoring transport can itself fail; an offline probe is DEGRADED and retriable rather than
  automatically becoming AI/code-repair work.
