import json
import time

import pytest

from jevfish.config import Settings
from jevfish.frame import normalize_frame
from jevfish.llm import FakeLLM
from jevfish.service import PipelineError, Service
from jevfish.simulate import RunConfig, RunConfigError

SEED = """Lazybee runs co-living homes in Thomson, Singapore.

Mark Wee founded Lazybee with Jason Park. Thomson Grove is one of the homes.

Acme Realty competes with Lazybee. Renters compare rooms on price and cleanliness."""


def settings(tmp_path, **kw):
    base = dict(data_dir=tmp_path / "data", typesafe_key=None, jev_model="jev-latest", fake_judge=True,
                llm_api_key=None, llm_base_url=None, llm_models=["fake"], fake_llm=True, llm_workers=2)
    base.update(kw)
    return Settings(**base)


def wait(task, timeout=120):
    end = time.time() + timeout
    while task.status in ("queued", "running"):
        if time.time() > end:
            raise TimeoutError(task.to_dict())
        time.sleep(0.02)
    assert task.status == "done", task.to_dict()
    return task.result


@pytest.fixture
def prepared(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    svc = Service(settings(tmp_path), llm=FakeLLM())
    p = svc.create_project("Lazybee", "Will renters book a viewing?", SEED)
    wait(svc.start_graph(p["id"]))
    result = wait(svc.start_prepare(p["id"], public_size=12, max_stakeholders=3))
    assert result["public"] == 12
    return svc, p["id"]


def two_variant_frame(svc, pid):
    frame = svc.frame(pid)
    frame["variants"] = [
        {"id": "A", "label": "Now", "subject": {}},
        {"id": "B", "label": "Cheaper", "subject": {"price": "lower"}},
    ]
    svc.update_frame(pid, frame)


@pytest.mark.parametrize("platform", ["lite", "reddit"])
def test_full_pipeline(prepared, platform):
    svc, pid = prepared
    two_variant_frame(svc, pid)
    config = {"platform": platform, "rounds": 3, "agents_per_round_min": 4, "agents_per_round_max": 8,
              "injections": [{"round": 2, "text": "Breaking: rents fall across Thomson"}]}
    run, task = svc.start_run(pid, config)
    wait(task)
    rid = run["id"]
    detail = svc.run(pid, rid)
    assert detail["status"] == "done" and detail["progress"] == 1.0
    summary = detail["summary"]
    assert [v["id"] for v in summary["variants"]] == ["A", "B"]
    crowd_size = len(svc.crowd(pid)["agents"])
    for v in summary["variants"]:
        assert [p["round"] for p in v["polls"]] == [0, 1, 3]
        assert v["final"]["n"] == crowd_size
        assert 0 <= v["final"]["low"] <= v["final"]["expected_yes"] <= v["final"]["high"] <= crowd_size
        assert v["posts_total"] >= 2  # opening post + injection at least
        assert "group" in v["segments"] and "kind" in v["segments"]
    assert summary["comparisons"][0]["variant"] == "B"
    assert summary["judge"]["fake"] is True and summary["judge"]["requests"] > 0

    actions = svc.actions(pid, rid)
    assert any(a.get("opening") for a in actions)
    assert any(a.get("injection") and a["round"] == 2 for a in actions)
    decided = [a for a in actions if a["round"] > 0 and "jev_action" in a]
    assert decided
    assert all(a["ok"] for a in decided), [a for a in decided if not a["ok"]][:3]
    texts = [a for a in decided if a["action"] in ("create_post", "create_comment")]
    assert all(a["content"] for a in texts)
    assert len(svc.actions(pid, rid, since=len(actions) - 1)) == 1

    polls = svc.polls(pid, rid)
    assert len(polls) == 2 * 3 * crowd_size

    wait(svc.start_report(pid, rid))
    report = svc.report(pid, rid)
    assert report["markdown"].startswith("## Prediction")
    assert report["data"]["headline"]["A"]["n"] == crowd_size

    first = svc.crowd(pid)["agents"][0]["agent_id"]
    reply = svc.chat(pid, rid, first, "Would you book a viewing?", variant="B")
    assert reply["reply"] and len(reply["history"]) == 2
    assert len(svc.chat_history(pid, rid, first, variant="B")) == 2
    answer = svc.ask_crowd(pid, rid, "Would they recommend Lazybee to a friend?")
    assert answer["summary"]["n"] == crowd_size and answer["variant"] == "A"
    assert answer["requests"] + answer["cache_hits"] == crowd_size
    assert svc.asked(pid, rid)[0]["question"] == "Would they recommend Lazybee to a friend?"

    rerun, task2 = svc.start_run(pid, config)
    wait(task2)
    again = svc.run(pid, rerun["id"])["summary"]
    assert again["judge"]["requests"] == 0, "identical rerun should be answered from the cache"
    assert [v["final"] for v in again["variants"]] == [v["final"] for v in summary["variants"]]


def test_budget_stop_marks_run_partial(prepared):
    from jevfish.simulate import run_simulation

    svc, pid = prepared
    # The service refuses runs whose upper-bound estimate exceeds the cap, so drive the runner directly.
    run = svc.store.create_run(pid, {"platform": "lite", "rounds": 3, "max_requests": 40,
                                     "agents_per_round_min": 4, "agents_per_round_max": 4})
    run_simulation(svc.store, svc.settings, svc.llm, pid, run["id"], lambda p, m: None)
    detail = svc.run(pid, run["id"])
    assert detail["status"] == "partial"
    assert "budget" in detail["summary"]["partial"]
    assert detail["summary"]["judge"]["requests"] == 40


def test_run_guards(prepared):
    svc, pid = prepared
    with pytest.raises(PipelineError, match="needs up to"):
        svc.start_run(pid, {"platform": "lite", "rounds": 400, "max_requests": 100})
    with pytest.raises(RunConfigError):
        svc.start_run(pid, {"platform": "myspace"})
    with pytest.raises(RunConfigError):
        svc.start_run(pid, {"rounds": 3, "injections": [{"round": 9, "text": "x"}]})
    with pytest.raises(RunConfigError, match="unknown run settings"):
        RunConfig.from_dict({"roundz": 3})
    no_key = Service(settings(svc.settings.data_dir.parent, fake_judge=False), store=svc.store, llm=FakeLLM())
    with pytest.raises(PipelineError, match="TYPESAFE_API_KEY"):
        no_key.start_run(pid, {"platform": "lite", "rounds": 1})


def test_pipeline_guards(tmp_path):
    svc = Service(settings(tmp_path), llm=FakeLLM())
    with pytest.raises(PipelineError):
        svc.create_project("x", "   ")
    p = svc.create_project("x", "Will it work?")
    with pytest.raises(PipelineError, match="seed"):
        svc.start_graph(p["id"])
    with pytest.raises(PipelineError, match="graph"):
        svc.start_prepare(p["id"])
    svc.add_file(p["id"], "notes.md", b"Alpha Beta runs Gamma Corp.")
    with pytest.raises(PipelineError, match="unsupported"):
        svc.add_file(p["id"], "x.exe", b"MZ")
    wait(svc.start_graph(p["id"]))
    assert svc.overview(p["id"])["graph_stats"]["nodes"] >= 1


def test_frame_edit_validation(prepared):
    svc, pid = prepared
    frame = svc.frame(pid)
    frame["stance"]["levels"] = ["only one"]
    with pytest.raises(ValueError):
        svc.update_frame(pid, frame)
    good = normalize_frame(svc.frame(pid))
    assert svc.update_frame(pid, good) == good


def test_pdf_upload(tmp_path):
    import fitz

    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "Delta Housing announced new rules.")
    data = doc.tobytes()
    svc = Service(settings(tmp_path), llm=FakeLLM())
    p = svc.create_project("pdf", "Will tenants accept the rules?")
    svc.add_file(p["id"], "rules.pdf", data)
    assert "Delta Housing" in svc.store.seed_text(p["id"])
    assert json.loads((svc.store.project_dir(p["id"]) / "project.json").read_text())["sources"][0]["name"] == "rules.pdf"
