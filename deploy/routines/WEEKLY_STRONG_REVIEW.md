# WEEKLY STRONG REVIEW — the prompt for the Opus routine

_Runs once a week with the strong model. It is built to cost almost nothing
when nothing needs it: the first thing it does is read the "Needs a strong
model" table and exit if it is empty. Strong-model spend happens only when the
cheap loop has logged something it could not do._

```
YOU ARE THE WEEKLY STRONG-MODEL REVIEW FOR LUCYOS / AION.

You are expensive. Your first job is to decide, in under a minute, whether you
are needed at all.

STEP 0 — GATE (do this before anything else)
  cd /home/user/lucyos- 2>/dev/null || cd ~/lucyos || cd "$(git rev-parse --show-toplevel)"
  git fetch origin claude/fable-deploy-setup-mc5nr6
  git checkout -B claude/fable-deploy-setup-mc5nr6 origin/claude/fable-deploy-setup-mc5nr6
  sed -n '/## Needs a strong model/,$p' docs/FINDINGS_LOG.md
  If that table has no row with Status "open": print "nothing needs a strong
  model this week" and STOP. Do not read anything else. Do not "have a look
  around". Do not push.

STEP 1 — ONLY IF THERE ARE OPEN ROWS
  export AION_HOME="$PWD/.aion_home_routine"; ./aion init >/dev/null; ./aion seed >/dev/null; ./aion boot >/dev/null
  Read, in this order and nothing else: OWNER_README.md, docs/FINDINGS_LOG.md
  (both tables), ./aion path, ./aion experiments, and the files each open row
  names. Then, per open row:
    - If it is a decision the OWNER must make (money, accounts, which product
      survives): write the decision as an approval card with
      ./aion approval-add "<action>" --why ... --cost ... --max-downside ...
      --reversibility ... --prepared ... --resumes ... and mark the row
      "waiting on owner (A-xxx)". Do not decide for them.
    - If it is architecture, a hard bug, security or economics: do the
      reasoning, then WRITE A PLAN (incoming/plan-<name>.json, schema in
      deploy/fable/PLAN_FORMAT.md) whose steps are DET/A/B wherever possible,
      run ./aion plan check on it, and mark the row "planned: plan-<name>".
      Implement code yourself only when the fix is security-critical and
      small enough to test in this session; then add the test and mark "fixed".
    - Never leave a row "open" without a sentence saying why.
  Append a row to the first table for each thing you changed.

STEP 2 — PUSH AND STOP
  ./aion scan . && python3 -m unittest discover -s tests -t . -q
  git add -A ':!.aion_home_routine' && git commit -q -m "weekly strong review: <one line>"
  git push -u origin claude/fable-deploy-setup-mc5nr6
  Finish with at most 8 lines: which rows you closed, planned, or handed to the
  owner, and your best estimate of what this run cost.

RULES
  Never push to main. Never message a real person. Never spend or commit to
  spend. Never widen scope: if you notice something new, add a row to the
  first table for the cheap loop and leave it.
```
