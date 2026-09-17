"""jevfish command line: `serve` starts the app, `demo` runs the whole pipeline once."""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

from .config import PACKAGE_ROOT, load_settings

EXAMPLE = PACKAGE_ROOT / "examples" / "lazybee-cleaning.md"


def cmd_serve(args) -> int:
    from .api import create_app

    settings = load_settings()
    print("JevFish settings:", settings.health())
    app = create_app(settings)
    print(f"Open http://{args.host}:{args.port}")
    app.run(host=args.host, port=args.port, threaded=True, debug=False)
    return 0


def _wait(task, label: str) -> dict:
    last = ""
    while task.status in ("queued", "running"):
        line = f"  {label}: {task.progress:.0%} {task.message}"
        if line != last:
            print(line[:160])
            last = line
        time.sleep(0.5)
    if task.status != "done":
        raise SystemExit(f"{label} {task.status}: {task.error}")
    return task.result


def cmd_demo(args) -> int:
    from .service import Service

    settings = load_settings()
    if not settings.llm_ready or not settings.judge_ready:
        print("Missing keys:", settings.health(), "\nSet TYPESAFE_API_KEY and LLM_API_KEY/GEMINI_API_KEY, or JEVFISH_FAKE_JUDGE=1 JEVFISH_FAKE_LLM=1.")
        return 2
    svc = Service(settings)
    seed = Path(args.seed).read_text()
    project = svc.create_project(args.name, args.question, seed)
    pid = project["id"]
    print(f"project {pid}")
    print("graph:", _wait(svc.start_graph(pid), "graph"))
    print("prepare:", _wait(svc.start_prepare(pid, public_size=args.public, max_stakeholders=args.stakeholders), "prepare"))
    run, task = svc.start_run(pid, {"platform": args.platform, "rounds": args.rounds,
                                    "agents_per_round_min": args.min_active, "agents_per_round_max": args.max_active})
    print("run:", _wait(task, "run"))
    summary = svc.run(pid, run["id"])["summary"]
    for v in summary["variants"]:
        f = v["final"]
        print(f"  {v['id']} {v['label']}: {f['expected_yes']:.1f} of {f['n']} (90% {f['low']:.1f} to {f['high']:.1f}), "
              f"first poll {v['baseline']['expected_yes']:.1f}")
    for c in summary["comparisons"]:
        print(f"  {c['variant']} vs {c['baseline']}: {c['diff_expected_yes']:+.1f} ({c['verdict']})")
    print("  jev:", summary["judge"], "\n  llm:", summary["llm"])
    _wait(svc.start_report(pid, run["id"]), "report")
    print("\n" + svc.report(pid, run["id"])["markdown"])
    print(f"\nOpen the app and pick project {pid}, run {run['id']}.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="jevfish", description="Swarm prediction on TypeSafe Jev, MiroFish-style.")
    sub = parser.add_subparsers(dest="command", required=True)
    serve = sub.add_parser("serve", help="start the web app and API")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=5055)
    serve.set_defaults(func=cmd_serve)
    demo = sub.add_parser("demo", help="run graph, prepare, simulate and report on a seed document")
    demo.add_argument("--seed", default=str(EXAMPLE))
    demo.add_argument("--name", default="Lazybee cleaning upgrade (example)")
    demo.add_argument("--question", default="If Lazybee adds weekly professional cleaning for S$100 more a month (example figure), will more Singapore renters book a viewing?")
    demo.add_argument("--platform", default="reddit", choices=["reddit", "twitter", "lite"])
    demo.add_argument("--rounds", type=int, default=6)
    demo.add_argument("--public", type=int, default=40)
    demo.add_argument("--stakeholders", type=int, default=8)
    demo.add_argument("--min-active", type=int, default=6)
    demo.add_argument("--max-active", type=int, default=14)
    demo.set_defaults(func=cmd_demo)
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
