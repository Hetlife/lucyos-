# WhatsApp commands

Send these to the bridge from your phone. Ordinary language works too; the
shortcuts are the reliable form.

| Command | Answers |
|---|---|
| `status` | Health, task counts, real money, waiting approvals, next action |
| `today` | What actually happened today: completions, activity, failures, spend |
| `money` | Real revenue, real cost, net, reserve, model budget and governor |
| `tasks` | Top tasks ranked by expected value |
| `blockers` | Only the things that need you, as approval cards |
| `errors` | Unresolved failures with their classification |
| `agents` | Agent health, reliability and current assignment |
| `approve <ID>` | Approves that one action and resumes its prepared step |
| `reject <ID>` / `deny <ID>` | Denies it and cancels only that task |
| `pause` | Holds consequential automation; monitoring continues |
| `resume` | Restarts and reports the new next action |
| `safe mode` | Disables spending, outbound messaging and external writes |
| `safe mode off` | Restores normal tiered autonomy |
| `deep check` | Forces a full verification pass and lists every check |
| `why <ID>` | Explains a decision, approval, task or error |
| `report` | The full detailed report |
| `help` | This list |

## The one rule that matters

**Never send a password, API key, OTP, recovery code or card number here.**
The router detects credential-shaped text, refuses the message, and does not
store it. When AION needs a credential it will say so and ask you to enter it on
the PC with `aion secrets set <NAME>`; you reply `done`.

## Approval cards

A consequential action arrives like this:

```
APPROVAL A-142

ACTION: Purchase Railway Hobby plan
WHY REQUIRED: free resources are insufficient for persistent availability
COST: INR 500/month
MAXIMUM DOWNSIDE: INR 500, cancellable at any time
EXPECTED BENEFIT: the API stays reachable when the PC is off
REVERSIBILITY: reversible — cancel in the console
ALREADY PREPARED: config, deploy file, rollback plan
RESUMES: run the prepared deploy
RECOMMENDATION: APPROVE

REPLY: APPROVE A-142  or  DENY A-142
```

Replying twice is safe: the second reply is recognised as a duplicate and is not
re-applied.

## A normal day

Morning: `status`. During the day: nothing, unless something genuinely needs
your authority. Evening: `report`.
