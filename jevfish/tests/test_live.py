"""Live smoke test against real Jev and a real LLM. Run with `uv run pytest -m live -s`.

Uses the real Gemini/OpenAI-compatible model for graph, frame, crowd and posts, and real Jev
for every decision, on the in-memory platform to keep it fast (about 60 Jev requests).
"""

import os
import time

import pytest

from jevfish.config import load_settings
from jevfish.service import Service

pytestmark = [
    pytest.mark.live,
    pytest.mark.skipif(
        not os.environ.get("TYPESAFE_API_KEY") or not (os.environ.get("LLM_API_KEY") or os.environ.get("GEMINI_API_KEY")),
        reason="needs TYPESAFE_API_KEY and an LLM key",
    ),
]

SEED = """Harbour Books is an independent bookshop in Tanjong Pagar, Singapore.
It plans to open a cafe corner and stay open until 11pm on Fridays and Saturdays.
Regular customers are office workers, students from nearby schools and families at weekends.
Some neighbours worry about noise late at night. The owner, Lim Wei, says evening events
like author talks have been popular. A nearby chain, PageTurner, already closes at 9pm."""


def wait(task, timeout=600):
    end = time.time() + timeout
    while task.status in ("queued", "running"):
        assert time.time() < end, task.to_dict()
        time.sleep(0.5)
    assert task.status == "done", task.to_dict()
    return task.result


def test_live_pipeline_small(tmp_path, monkeypatch):
    monkeypatch.setenv("JEVFISH_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.chdir(tmp_path)
    svc = Service(load_settings())
    p = svc.create_project("Bookshop hours", "Will more customers visit if Harbour Books opens until 11pm with a cafe?", SEED)
    graph = wait(svc.start_graph(p["id"]))
    print("\ngraph", graph)
    assert graph["nodes"] >= 3
    prep = wait(svc.start_prepare(p["id"], public_size=12, max_stakeholders=3))
    print("prepare", prep)
    frame = svc.frame(p["id"])
    assert "`agent`" in frame["outcome"]["instructions"]
    run, task = svc.start_run(p["id"], {"platform": "lite", "rounds": 2, "agents_per_round_min": 4, "agents_per_round_max": 6,
                                        "poll_rounds": [0, 2]})
    wait(task)
    summary = svc.run(p["id"], run["id"])["summary"]
    for v in summary["variants"]:
        print(v["id"], v["label"], {k: round(x, 3) for k, x in v["final"].items() if isinstance(x, float)})
    print("judge", summary["judge"], "llm", summary["llm"])
    assert summary["judge"]["fake"] is False and summary["judge"]["requests"] > 0
    assert all(0 <= v["final"]["mean_outcome"] <= 1 for v in summary["variants"])
    wait(svc.start_report(p["id"], run["id"]))
    report = svc.report(p["id"], run["id"])["markdown"]
    print(report[:600])
    assert "Prediction" in report
