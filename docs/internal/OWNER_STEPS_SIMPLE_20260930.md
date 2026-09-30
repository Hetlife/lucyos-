# What only YOU can do — in plain words

You do **not** need to know how to code. Every step below is either "click a button on
GitHub" or "copy one line into the terminal and copy back what it says". If a line is
unclear, stop and ask; nothing here is urgent.

The AI helpers (Claude, Codex, ChatGPT) prepare changes. **They are not allowed to approve
their own work.** That safety rule is deliberate, and it is why these steps are yours.

---

## Step 1 — Approve the changes (GitHub website, about 10 minutes)

The changes are waiting on GitHub as "pull requests" (PRs). Think of a PR as a proposed edit
that needs your OK before it becomes real.

Approve them **in this order** (each one builds on the one before). Every PR from #76 on
now points at the main branch, so order is a recommendation, not a trap:

| Order | PR | What it fixes, in one line |
|---|---|---|
| 1 | #75 | A setup message told you to run a command that doesn't exist |
| 2 | #76 | Setup now asks for everything the WhatsApp bridge needs |
| 3 | #77 | A guide + checker for connecting WhatsApp through Meta |
| 4 | #78 | Proof the bridge starts; catches passwords with special characters |
| 5 | #79 | Meta WhatsApp is now "optional" because you use OpenClaw |
| 6 | #80 | Passwords with special characters are saved safely |

For **each** one, in order:
1. Open the link, for example `https://github.com/Hetlife/lucyos-/pull/75`.
2. Look at the list of checks near the bottom. If any show a red ✗, **stop and tell me**.
   Green ✓ (or no checks at all) is fine.
3. Click the green **Merge pull request** button, then **Confirm merge**.
4. Clicking **Delete branch** is now fine. Every one of these PRs points straight at the
   main branch, so deleting a branch cannot close another PR. (Earlier they were chained to
   each other, and deleting a branch closed the next one. That happened to #76 and #77. Both
   were reopened and fixed, and nothing was lost.)

If a PR says "conflicts" or the merge button is grey, stop and tell me which number.

## Step 2 — Update LucyOS on your computer (2 minutes)

Open the terminal on the computer where LucyOS is installed and copy these lines **one at a
time**, pressing Enter after each:

```
cd ~/lucyos
git pull
aion boot
aion status
```

`aion status` prints a short summary. Copy what it prints and send it to me.

## Step 3 — Check your WhatsApp through OpenClaw (2 minutes)

You told me OpenClaw carries your WhatsApp. I can't see your computer, so I don't know if
it is connected right now. In the terminal:

```
aion openclaw-check
```

Copy **everything it prints** and send it to me. It only reads information; it changes
nothing. What it says tells us what to do next.

## Step 4 — If anything looks wrong

```
aion health --deep
aion errors
```

Copy what they print and send it to me. Never paste a password or key into a chat — these two
commands do not show any.

---

## Things you can safely ignore for now

- **The Meta "Cloud API" setup.** You use OpenClaw, so you don't need it.
- **Adding money for the strong AI model.** Not needed today. When you want to, the system
  will tell you the amount first; it has a hard monthly limit and won't overspend.
- **The many old branches on GitHub.** That's a clean-up job for later.

## Two things I will ask you for later (not today)

1. **A short ID to unlock one tiny setting** (so the test runs stop leaving a stray file that
   nags the AI helpers). It is cosmetic. Skip it forever if you like.
2. **A "re-freeze" of the safety checksums.** It's a routine reset of an alarm that has been
   ringing quietly. I'll give you the exact line to copy when it's time.

## The safety rules you can rely on

- Nothing spends money or contacts anyone without asking you first.
- Passwords and keys are typed **only on your computer**, never through chat or WhatsApp.
- Every change is a proposal on GitHub until **you** press Merge, and you can undo a merge.
