# Tomorrow, in order

Everything below has been run end to end from a clean clone on a Linux machine.
Nothing needs buying until step 4, and step 4 tells you the exact amount.

## 1. Install (about 2 minutes)

```bash
git clone https://github.com/Hetlife/lucyos- ~/lucyos
cd ~/lucyos
scripts/install.sh
scripts/install_hooks.sh
```

`install.sh` creates the shared brain at `~/openclaw/shared_brain`, seeds the
mission and the opening queue, makes the first backup, restore-tests it, and
prints a health check. Expect `healthy` with `ollama: not installed` — that is
fine, it degrades to cloud.

If `aion` is not found afterwards:

```bash
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc && source ~/.bashrc
```

## 2. See that it works before spending anything

```bash
aion status
aion tasks
aion milestones
python3 bridges/whatsapp_bridge.py stdin     # type: status, money, tasks, help
```

This is the whole owner surface. No model is called to answer any of it, so it
costs nothing and works offline.

## 3. Give it what it needs (batched, once)

```bash
aion owner-setup        # reads the list; nothing here is asked twice
```

Then, on the machine only — never through chat:

```bash
aion secrets set WHATSAPP_BRIDGE_TOKEN
aion secrets set GITHUB_TOKEN            # optional today
```

Free and worth doing while you are there, so routine work costs nothing:

```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama pull llama3.1:8b
aion health                              # should now show local models
```

If you have a cloud CLI already authenticated:

```bash
aion set-cloud-cmd 'claude -p {prompt_file}'
```

## 4. Only now, open the expensive session

```bash
aion fable-ready                                       # must say FABLE READY
cat ~/openclaw/shared_brain/FABLE/FABLE_START_PROMPT.txt
```

Add **INR 750** of credit (not 2,000 — staged on purpose). Paste that file into a
strong-reasoning session. It carries your real task ids, the hard INR 2,000
ceiling and the rule that its output is plans, not code.

## 5. Turn on the loop and walk away

```bash
scripts/install_services.sh
systemctl --user enable --now aion-bridge.service
loginctl enable-linger "$USER"
```

From then on: the build loop runs every 10 minutes, the nightly maintenance run
backs up and restore-tests at 03:15, the budget governor downshifts by itself,
and unattended work moves to Sonnet automatically when the strong budget runs
out. The loop pauses itself when a major milestone lands, because that is your
decision to make.

Your day becomes `status` in the morning and `report` in the evening.

## If something is wrong

```bash
aion health --deep     # every check, measured
aion errors            # unresolved failures
aion boot              # recover; it never blindly repeats the last action
aion why <ID>          # explain any decision, approval, task or error
```

Or just append to `~/openclaw/shared_brain/NOTEBOOK.md`:

```
## [BUG] what went wrong
from: het
what you expected, what happened
```

The next loop turns it into a tracked task and an error row.

## What is not proven yet

- The bridge has never sent a message to your actual phone. It needs the token
  and a transport; that is the top task in the queue.
- No local model is installed here, so class A steps park as WAITING with their
  work orders saved until Ollama exists.
- Real revenue is INR 0. Every number the system reports about money is real or
  labelled as a forecast — none of it is currently claiming otherwise.
