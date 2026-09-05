# FABLE DECISIONS

Already decided. Do not relitigate without new evidence.

- **DEC-06AC9B28** state ownership → The Ubuntu PC holds canonical state; WhatsApp is a control surface only (VERIFIED_FACT; A chat app cannot be a database. If WhatsApp, a model provider or the network goes down, the PC must still know everything and be able to resume.)
- **DEC-296DA3F9** command surface → Owner commands are answered by deterministic code, not by a model (VERIFIED_FACT; Reading `status` does not need intelligence. Making the control channel free and always-available matters more than making it conversational.)
- **DEC-F3CA1000** authorization form → Only the exact form APPROVE <ID> or DENY <ID> decides an approval (VERIFIED_FACT; Casual agreement in chat is ambiguous and easy to manufacture. A unique id per consequential action makes intent unmistakable and auditable.)
- **DEC-7E49C177** secrets channel → No credential ever travels through WhatsApp; values are entered on the PC (VERIFIED_FACT; Chat history is stored on third-party servers and on the phone. The secret store is 0600, excluded from backups and from git.)
- **DEC-8C92B0FC** spend order → Deterministic code first, then local model, then cheap cloud, then strong model (VERIFIED_FACT; Most of this workload is mechanical. Paying a strong model to format text or count rows is waste that compounds daily.)
- **DEC-688673BB** mission scope → Nothing in the control layer may be hard-coded to one business (VERIFIED_FACT; A lakh a month from a single lucky offer is not the goal; machinery that onboards the next business without a rewrite is. Every project carries its own `project` key and anything business-specific lives in PROJECTS/, never in aion_core/.)
- **DEC-0E269B58** growth honesty → A milestone counts only when measured, never when projected (VERIFIED_FACT; The path runs M0 to M6 in order. Skipping one because a spreadsheet says the next is reachable is how a system convinces its owner it is working while earning nothing.)
- **DEC-947D445A** money honesty → Revenue is only ACTUAL with transaction evidence; forecasts stay labelled (VERIFIED_FACT; A forecast recorded as revenue makes the whole system lie to its owner about the one number that decides whether any of this is worth continuing.)
