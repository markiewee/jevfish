"""jevfish command line: `serve` starts the app, `demo` runs the whole pipeline once."""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

from . import example
from .config import load_settings


def cmd_serve(args) -> int:
    from .api import create_app

    settings = load_settings()
    print("JevFish settings:", settings.health())
    local = args.host in ("127.0.0.1", "localhost", "::1")
    if not local:
        print("Warning: listening beyond this computer. Anyone who can reach it can change the keys.")
    app = create_app(settings, allow_remote=not local)
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


def cmd_anchor(args) -> int:
    """Record what actually happened, which is the only thing that buys calibration."""
    from .anchors import Anchor, load_anchors, save_anchor
    from .calibrate import conformal_half_width, fit_map

    settings = load_settings()
    path = settings.data_dir / "anchors.json"

    if args.action == "list":
        anchors = load_anchors(path)
        if not anchors:
            print(f"No resolved outcomes recorded yet ({path}).")
            print("Until there is at least one, JevFish reports an uncalibrated number and")
            print("an interval that covers sampling noise only. Record one with:")
            print('  jevfish anchor add --question "..." --option "..." --predicted 0.57 --actual 0.89 --n 801')
            return 0
        print(f"{len(anchors)} resolved outcome(s) in {path}\n")
        print(f"{'question':<34}{'option':<16}{'pred':>7}{'actual':>8}{'err':>7}{'n':>6}  model")
        for a in anchors:
            print(
                f"{a.question[:33]:<34}{a.option[:15]:<16}{a.predicted:>7.3f}"
                f"{a.actual:>8.3f}{a.residual:>7.3f}{a.n:>6}  {a.model_version or '?'}"
            )
        print(f"\n{fit_map(anchors).describe()}")
        try:
            hw = conformal_half_width([a.residual for a in anchors], alpha=0.10)
            print(f"90% interval half-width from these errors: {hw * 100:.1f} points")
        except ValueError as e:
            print(f"No honest interval yet: {e}")
        return 0

    anchor = Anchor(
        question=args.question,
        option=args.option,
        predicted=args.predicted,
        actual=args.actual,
        n=args.n,
        estimand=args.estimand,
        model_version=args.model_version or settings.jev_model,
        note=args.note,
    )
    save_anchor(path, anchor)
    anchors = load_anchors(path, question=anchor.question, estimand=anchor.estimand)
    print(f"Recorded. {len(anchors)} outcome(s) for this question and estimand.")
    print(f"  {fit_map(anchors).describe()}")
    need = {1: "5 for level plus scale", 5: "9 for a 90% interval"}
    for have, nxt in sorted(need.items()):
        if len(anchors) <= have:
            print(f"  Next milestone: {nxt}.")
            break
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="jevfish", description="Swarm prediction on TypeSafe Jev, MiroFish-style.")
    sub = parser.add_subparsers(dest="command", required=True)
    serve = sub.add_parser("serve", help="start the web app and API")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=5055)
    serve.set_defaults(func=cmd_serve)
    demo = sub.add_parser("demo", help="run graph, prepare, simulate and report on a seed document")
    demo.add_argument("--seed", default=str(example.PATH))
    demo.add_argument("--name", default=example.NAME)
    demo.add_argument("--question", default=example.QUESTION)
    demo.add_argument("--platform", default="reddit", choices=["reddit", "twitter", "lite"])
    demo.add_argument("--rounds", type=int, default=6)
    demo.add_argument("--public", type=int, default=40)
    demo.add_argument("--stakeholders", type=int, default=8)
    demo.add_argument("--min-active", type=int, default=6)
    demo.add_argument("--max-active", type=int, default=14)
    demo.set_defaults(func=cmd_demo)

    anchor = sub.add_parser(
        "anchor",
        help="record or list resolved outcomes, which is what makes calibration possible",
    )
    anchor_sub = anchor.add_subparsers(dest="action", required=True)
    anchor_list = anchor_sub.add_parser("list", help="show recorded outcomes and the fitted map")
    anchor_list.set_defaults(func=cmd_anchor, action="list")
    anchor_add = anchor_sub.add_parser("add", help="record one resolved outcome")
    anchor_add.add_argument("--question", required=True, help="must match the frame's question")
    anchor_add.add_argument("--option", required=True, help="which variant, for example 'MYR 300'")
    anchor_add.add_argument("--predicted", type=float, required=True, help="what JevFish said, 0 to 1")
    anchor_add.add_argument("--actual", type=float, required=True, help="what happened, 0 to 1")
    anchor_add.add_argument("--n", type=int, required=True, help="crowd size behind the prediction")
    anchor_add.add_argument(
        "--estimand",
        default="acceptance_rate_independent",
        choices=["acceptance_rate_independent", "choice_share_of_described_set", "event_probability"],
    )
    anchor_add.add_argument("--model-version", default="", help="defaults to the configured Jev model")
    anchor_add.add_argument("--note", default="", help="how the outcome was measured")
    anchor_add.set_defaults(func=cmd_anchor, action="add")

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
