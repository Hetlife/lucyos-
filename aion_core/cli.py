"""`aion` command line — the machine-side interface OpenClaw drives."""
from __future__ import annotations

import argparse
import getpass
import json
import sys
from pathlib import Path

from . import (agents, approvals, backup, bootstrap, config, db, errors, fable, health,
               memory, metrics, notebook, owner_setup, packets, reports, resume, router,
               security, seed, sessions, tasks, util)


def _print(text):
    print(text if isinstance(text, str) else json.dumps(text, indent=2, default=str))


class CliError(Exception):
    """A user-facing failure: printed as one line, never as a traceback."""


def main(argv=None) -> int:
    try:
        return _main(argv)
    except (tasks.TaskError, approvals.ApprovalError, packets.PacketError,
            security.SecretLeak, memory.ValueError if False else ValueError,
            FileNotFoundError, CliError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


def _main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="aion", description="AION control layer")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("init", help="create/repair the shared brain")
    sub.add_parser("boot", help="startup + resume loop")
    sub.add_parser("status", help="owner status summary")
    sub.add_parser("today")
    sub.add_parser("money")
    sub.add_parser("blockers")
    sub.add_parser("errors")
    sub.add_parser("agents")
    sub.add_parser("report")
    sub.add_parser("sync-docs", help="regenerate markdown surfaces from the database")
    sub.add_parser("owner-setup", help="regenerate OWNER_SETUP_REQUIRED.md")
    sub.add_parser("fable-pack", help="build/refresh the Fable launch pack")
    sub.add_parser("fable-ready", help="run the Fable readiness test")
    sub.add_parser("seed", help="seed the opening objective, decisions and task queue")
    bk = sub.add_parser("backup", help="create a backup and restore-test it")
    bk.add_argument("--verify-only", action="store_true")

    t = sub.add_parser("tasks", help="list top tasks")
    t.add_argument("--limit", type=int, default=10)

    tc = sub.add_parser("task-add")
    tc.add_argument("title")
    tc.add_argument("--project", default="default")
    tc.add_argument("--priority", type=int, default=3)
    tc.add_argument("--impact", type=float, default=3)
    tc.add_argument("--cost", type=float, default=1)
    tc.add_argument("--risk", type=float, default=1)
    tc.add_argument("--model-class", default="B")
    tc.add_argument("--success", default="", help="success criteria")
    tc.add_argument("--next", default="", help="next action")
    tc.add_argument("--depends", default="")

    tu = sub.add_parser("task-update")
    tu.add_argument("task_id")
    tu.add_argument("--status")
    tu.add_argument("--next")
    tu.add_argument("--owner")

    td = sub.add_parser("task-done")
    td.add_argument("task_id")
    td.add_argument("--evidence", required=True)
    td.add_argument("--next", default="")

    tf = sub.add_parser("task-fail")
    tf.add_argument("task_id")
    tf.add_argument("--error", required=True)

    ap = sub.add_parser("approval-add")
    ap.add_argument("action")
    for f in ("why", "cost", "max-downside", "expected-benefit", "reversibility",
              "prepared", "resumes", "owner-action", "task-id"):
        ap.add_argument(f"--{f}", default="")

    ad = sub.add_parser("approve")
    ad.add_argument("approval_id")
    dn = sub.add_parser("deny")
    dn.add_argument("approval_id")
    sub.add_parser("approvals", help="list pending approvals")

    ing = sub.add_parser("ingest", help="ingest an AI sync packet")
    ing.add_argument("path", nargs="?", help="packet file; omit to read stdin")
    sub.add_parser("ingest-inbox", help="process INBOX/pending")

    wa = sub.add_parser("whatsapp", help="route one owner message")
    wa.add_argument("message", nargs="+")
    wa.add_argument("--sender", default="owner")

    hc = sub.add_parser("health")
    hc.add_argument("--deep", action="store_true")

    rt = sub.add_parser("route", help="decide which model class should do a task")
    rt.add_argument("kind")
    rt.add_argument("--complexity", type=int, default=2)
    rt.add_argument("--stakes", default="low")
    rt.add_argument("--ambiguity", default="low")

    us = sub.add_parser("usage", help="record model usage")
    us.add_argument("model")
    us.add_argument("model_class")
    us.add_argument("--in-tokens", type=int, default=0)
    us.add_argument("--out-tokens", type=int, default=0)
    us.add_argument("--cost", type=float, default=0.0)
    us.add_argument("--task-id")
    us.add_argument("--note", default="")

    mo = sub.add_parser("money-add", help="record money with an explicit reality stage")
    mo.add_argument("kind", choices=["revenue", "cost", "reserve"])
    mo.add_argument("amount", type=float)
    mo.add_argument("--stage", default="ACTUAL", choices=list(metrics.STAGES))
    mo.add_argument("--description", default="")
    mo.add_argument("--evidence", default="")

    rem = sub.add_parser("remember")
    rem.add_argument("kind", choices=list(memory.KINDS))
    rem.add_argument("title")
    rem.add_argument("body")
    rem.add_argument("--confidence", default="INFERENCE", choices=list(memory.CONFIDENCE))
    rem.add_argument("--source", default="")

    se = sub.add_parser("search")
    se.add_argument("query", nargs="+")
    se.add_argument("--limit", type=int, default=10)

    de = sub.add_parser("decide")
    de.add_argument("subject")
    de.add_argument("decision")
    de.add_argument("--rationale", default="")
    de.add_argument("--evidence", default="")

    wy = sub.add_parser("why")
    wy.add_argument("ref_id")

    er = sub.add_parser("error-add")
    er.add_argument("component")
    er.add_argument("message")
    er.add_argument("--detail", default="")
    er.add_argument("--task-id")

    ere = sub.add_parser("error-resolve")
    ere.add_argument("error_id")
    ere.add_argument("--root-cause", required=True)
    ere.add_argument("--fix", required=True)
    ere.add_argument("--lesson", default="")

    ck = sub.add_parser("checkpoint")
    for f in ("objective", "current-state", "current-task", "last-verified-success",
              "last-failure", "bottleneck", "next-action", "files-to-read"):
        ck.add_argument(f"--{f}")

    sc = sub.add_parser("scan", help="scan a path for secrets before committing")
    sc.add_argument("path", nargs="?", default=".")

    sec = sub.add_parser("secrets")
    sec.add_argument("op", choices=["init", "set", "list"])
    sec.add_argument("name", nargs="?")

    nb = sub.add_parser("notebook", help="the hand-editable shared notebook")
    nb.add_argument("op", choices=["sync", "path", "recent"], nargs="?", default="sync")

    ss = sub.add_parser("session", help="per-session work log")
    ss.add_argument("op", choices=["start", "log", "end", "index", "open"])
    ss.add_argument("session_id", nargs="?")
    ss.add_argument("--text", default="", help="log entry text")
    ss.add_argument("--actor", default="openclaw")
    ss.add_argument("--model", default="")
    ss.add_argument("--model-class", default="B")
    ss.add_argument("--objective", default="")
    ss.add_argument("--kind", default="note")
    ss.add_argument("--outcome", default="")
    ss.add_argument("--resume-point", default="")
    ss.add_argument("--spend", type=float, default=0.0)

    ctx = sub.add_parser("context", help="build a task-specific context packet")
    ctx.add_argument("task_id")

    args = p.parse_args(argv)
    cmd = args.cmd

    if cmd != "init":
        bootstrap.ensure()

    if cmd == "init":
        n = bootstrap.ensure()
        reports.render_markdown_surfaces()
        owner_setup.write()
        _print(f"shared brain ready at {config.home()} ({n} paths created)")
    elif cmd == "boot":
        _print(resume.boot())
    elif cmd == "status":
        reports.render_markdown_surfaces()
        _print(reports.status())
    elif cmd == "today":
        _print(reports.today())
    elif cmd == "money":
        _print(reports.money())
    elif cmd == "blockers":
        _print(reports.blockers())
    elif cmd == "errors":
        _print(reports.error_list())
    elif cmd == "agents":
        _print(reports.agent_list())
    elif cmd == "report":
        _print(reports.full_report())
    elif cmd == "sync-docs":
        _print("\n".join(reports.render_markdown_surfaces()))
    elif cmd == "owner-setup":
        _print(owner_setup.write())
    elif cmd == "fable-pack":
        _print("\n".join(fable.build_pack()))
    elif cmd == "fable-ready":
        _print(fable.readiness_report())
    elif cmd == "seed":
        result = seed.apply()
        if result["skipped"]:
            _print("already seeded — nothing changed")
        else:
            reports.render_markdown_surfaces()
            _print(f"seeded {result['decisions']} decisions and "
                   f"{len(result['tasks'])} opening tasks")
    elif cmd == "backup":
        if not args.verify_only:
            _print(f"created {backup.create()}")
        result = backup.verify()
        _print(result["detail"])
        return 0 if result["ok"] else 1
    elif cmd == "tasks":
        _print(reports.task_list(args.limit))
    elif cmd == "task-add":
        _print(tasks.create(args.title, project=args.project, priority=args.priority,
                            impact=args.impact, cost=args.cost, risk=args.risk,
                            model_class=args.model_class, success_criteria=args.success,
                            next_action=args.next, dependencies=args.depends))
    elif cmd == "task-update":
        kw = {k: v for k, v in (("status", args.status), ("next_action", args.next),
                                ("owner_agent", args.owner)) if v}
        tasks.update(args.task_id, **kw)
        _print(dict(tasks.get(args.task_id)))
    elif cmd == "task-done":
        tasks.complete(args.task_id, args.evidence, args.next)
        _print(f"{args.task_id} DONE with evidence recorded")
    elif cmd == "task-fail":
        _print(f"{args.task_id} -> {tasks.fail(args.task_id, args.error)}")
    elif cmd == "approval-add":
        aid = approvals.create(
            args.action, why=args.why, cost=args.cost or "none",
            max_downside=args.max_downside, expected_benefit=args.expected_benefit,
            reversibility=args.reversibility or "unknown", prepared=args.prepared,
            resumes=args.resumes, owner_action=args.owner_action,
            task_id=args.task_id or None)
        reports.render_markdown_surfaces()
        _print(approvals.render(approvals.get(aid)))
    elif cmd in ("approve", "deny"):
        _print(router.handle(f"{cmd} {args.approval_id}", sender="owner-cli"))
    elif cmd == "approvals":
        rows = approvals.pending()
        _print("\n\n".join(approvals.render(r) for r in rows) or "no pending approvals")
    elif cmd == "ingest":
        text = Path(args.path).read_text(encoding="utf-8") if args.path else sys.stdin.read()
        _print(packets.ingest(text, source_path=Path(args.path) if args.path else None))
    elif cmd == "ingest-inbox":
        _print(packets.ingest_inbox())
    elif cmd == "whatsapp":
        _print(router.handle(" ".join(args.message), sender=args.sender))
    elif cmd == "health":
        r = health.run_all(deep=args.deep)
        for c in r["checks"]:
            print(f"{'OK  ' if c['ok'] else 'FAIL'} {c['name']}: {c['detail']}")
        print("healthy" if r["healthy"] else "FAILING: " + ", ".join(r["failing"]))
        return 0 if r["healthy"] else 1
    elif cmd == "route":
        _print(agents.route(args.kind, args.complexity, args.stakes, args.ambiguity))
    elif cmd == "usage":
        metrics.record_usage(args.model, args.model_class, input_tokens=args.in_tokens,
                             output_tokens=args.out_tokens, cost_inr=args.cost,
                             task_id=args.task_id, note=args.note)
        _print(metrics.budget_status())
    elif cmd == "money-add":
        metrics.record_money(args.kind, args.amount, stage=args.stage,
                             description=args.description, evidence=args.evidence)
        _print(reports.money())
    elif cmd == "remember":
        _print(memory.remember(args.kind, args.title, args.body, confidence=args.confidence,
                               source=args.source))
    elif cmd == "search":
        rows = memory.search(" ".join(args.query), limit=args.limit)
        _print("\n".join(f"{r['memory_id']} [{r['kind']}/{r['confidence']}] {r['title']}"
                         for r in rows) or "no matches")
    elif cmd == "decide":
        _print(memory.decide(args.subject, args.decision, args.rationale, args.evidence))
    elif cmd == "why":
        _print(memory.why(args.ref_id))
    elif cmd == "error-add":
        _print(errors.record(args.component, args.message, args.detail, args.task_id))
    elif cmd == "error-resolve":
        errors.resolve(args.error_id, args.root_cause, args.fix, args.lesson)
        _print(f"{args.error_id} resolved")
    elif cmd == "checkpoint":
        _print(resume.checkpoint(**{
            k: getattr(args, k) for k in
            ("objective", "current_state", "current_task", "last_verified_success",
             "last_failure", "bottleneck", "next_action", "files_to_read")
            if getattr(args, k, None)}))
    elif cmd == "scan":
        found = security.scan_paths(Path(args.path))
        if not found:
            _print("clean: no credential-shaped content found")
            return 0
        for f in found:
            print(f"{f['file']}:{f['line']} {f['kind']} {f['preview']}")
        return 1
    elif cmd == "secrets":
        if args.op == "init":
            _print(str(bootstrap.init_secret_store()))
        elif args.op == "set":
            if not args.name:
                print("usage: aion secrets set <NAME>", file=sys.stderr)
                return 2
            value = getpass.getpass(f"value for {args.name} (hidden, stays on this machine): ")
            bootstrap.set_secret(args.name, value)
            _print(f"{args.name} stored in {config.secrets_file()} (0600). Value not logged.")
        else:
            sf = config.secrets_file()
            names = [l.split("=", 1)[0] for l in sf.read_text().splitlines()
                     if l.strip() and not l.startswith("#")] if sf.exists() else []
            _print("\n".join(names) or "no secrets stored")
    elif cmd == "notebook":
        if args.op == "path":
            _print(str(notebook.ensure()))
        elif args.op == "recent":
            _print("\n".join(f"{r['entry_id']} [{r['kind']}] {r['title']} "
                             f"(by {r['author']} -> {r['created_ref']})"
                             for r in notebook.recent()) or "notebook is empty")
        else:
            _print(notebook.sync())
    elif cmd == "session":
        if args.op == "start":
            _print(sessions.start(args.actor, model=args.model, model_class=args.model_class,
                                  objective=args.objective))
        elif args.op == "log":
            if not args.session_id or not args.text:
                print("usage: aion session log <SESSION_ID> --text '...' [--kind KIND]",
                      file=sys.stderr)
                return 2
            sessions.log(args.session_id, args.kind, args.text)
            _print("logged")
        elif args.op == "end":
            if not args.session_id:
                print("usage: aion session end <SESSION_ID> --outcome '...'", file=sys.stderr)
                return 2
            _print(sessions.end(args.session_id, outcome=args.outcome,
                                resume_point=args.resume_point, spend_inr=args.spend))
        elif args.op == "open":
            _print("\n".join(f"{r['session_id']} {r['actor']} since {r['started_at']}"
                             for r in sessions.open_sessions()) or "no open sessions")
        else:
            _print("\n".join(f"{r['session_id']} {r['actor']:9} {r['started_at'][:16]} "
                             f"{r['status']:7} INR{r['spend_inr']:>6} {(r['outcome'] or '')[:60]}"
                             for r in sessions.index()) or "no sessions recorded")
    elif cmd == "context":
        from . import context
        _print(context.build(args.task_id))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
