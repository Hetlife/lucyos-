# 07 — Unresolved Questions

Each item: who can resolve it, how, and what changes if the answer is surprising.

| # | Question | Resolver | Method | If surprising |
|---|---|---|---|---|
| U-01 | Current runtime state of Mark-2 (services, timers, errors, disk, RAM, Ollama models, linger, DO backup image present?) | worker session on Mark-2 | LQ-05 sanitized inventory | If services are dead or disk full, Phase 0 starts with repair, not hardening |
| U-02 | Is SCS.ADMIN01 the office Radeon PC? Is OpenClaw gateway still running there? What is exposed? | owner | one-line answer + LQ-05 run there | If the gateway holds WhatsApp creds and shell tools, it enters the hardening list as another S-01 |
| U-03 | Exact Radeon GPU SKU and OS | owner | `lspci`/Adrenalin screenshot or model name | Unsupported SKU ⇒ appliance plan dropped; cloud only |
| U-04 | Does `strategy-factory` history contain secrets or client data? | worker with repo access | LQ-04 | Rotate and consider history rewrite before/after making private |
| U-05 | Real model spend to date and which cloud CLI is configured as class B | worker | `aion money`, `aion agents`, `meta.cloud_worker_cmd` | If nothing is configured, class B has never run; telemetry starts at zero |
| U-06 | Who else has the interface/bridge tokens or SSH access to Mark-2? | owner | statement | Any second person ⇒ per-person identity, not shared token |
| U-07 | Is the DO droplet's weekly backup actually producing images? | owner/DO console | check Backups tab | If none: LQ-02 becomes the *only* recovery path; raise priority |
| U-08 | Google Drive API enablement for the service-account project | owner | Cloud console | If not enabled: Drive bridge stays parked; not blocking anything else |
| U-09 | WhatsApp Cloud API current pricing/template rules for business-initiated alerts in India | worker with web access | official Meta docs | If costly: Telegram (LQ-16) becomes the alert channel |
| U-10 | Current India prices for M6 Mac mini configs, Linux mini-PCs, Runpod/other GPU clouds | worker with web access at purchase time | vendor pages | Only matters at the Phase-1 gate |
| U-11 | Which business workflow costs the owner the most time today? | owner | 5-minute answer | May reorder OD-07 |
| U-12 | Do any client contracts prohibit cloud processing of their documents? | owner/lawyer | contract review | Forces on-prem document store earlier (ADR-10) |
| U-13 | Does Mark-2 have any inbound ports open besides SSH (ufw status)? | worker | LQ-05 | Open Ollama/HTTP ports ⇒ immediate close |
| U-14 | Does the existing `aion-work.timer` run today, and has it ever completed a class B task with evidence? | worker | `aion tasks`, events | If zero accepted results ever: the loop is cost without value; leave disabled until first workflow |
