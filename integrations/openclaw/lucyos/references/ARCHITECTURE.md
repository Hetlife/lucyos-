# OpenClaw ↔ LucyOS architecture

OpenClaw owns chat/channel ingress, conversational UX, and tool execution surfaces.
LucyOS owns canonical operational state, task orchestration, approvals, resource/cost policy, skill registry, LearnRepo evidence, architecture checks, and resumability.

Flow:
Human/channel -> OpenClaw agent -> LucyOS preflight/context/skill selection -> approved executor -> evidence/result -> LucyOS state -> OpenClaw response.

OpenClaw must not become a second canonical business brain. Its own runtime state remains implementation-local; business/project truth and autonomous workflow state remain in LucyOS.
