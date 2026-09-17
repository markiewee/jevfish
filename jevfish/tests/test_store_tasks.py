import time

import pytest

from jevfish.store import NotFound, Store
from jevfish.tasks import TaskManager


def test_project_lifecycle(tmp_path):
    store = Store(tmp_path)
    p = store.create_project("Rent test", "Will renters book?", "Seed paragraph")
    assert p["stage"] == "seeded"
    assert "Seed paragraph" in store.seed_text(p["id"])
    store.add_seed(p["id"], "Second doc", "notes.md")
    text = store.seed_text(p["id"])
    assert "# Source: notes.md" in text and "Second doc" in text
    assert [s["name"] for s in store.get_project(p["id"])["sources"]] == ["pasted text", "notes.md"]
    store.update_project(p["id"], stage="graph")
    assert store.list_projects()[0]["stage"] == "graph"
    run = store.create_run(p["id"], {"rounds": 3})
    store.update_run(p["id"], run["id"], status="running")
    assert store.list_runs(p["id"])[0]["status"] == "running"
    store.append_jsonl(store.run_dir(p["id"], run["id"]) / "x.jsonl", {"a": 1})
    store.append_jsonl(store.run_dir(p["id"], run["id"]) / "x.jsonl", {"a": 2})
    assert store.read_jsonl(store.run_dir(p["id"], run["id"]) / "x.jsonl", since=1) == [{"a": 2}]


def test_bad_ids_are_not_found(tmp_path):
    store = Store(tmp_path)
    for bad in ["../etc", "p_zz", "", "p_0123456789/.."]:
        with pytest.raises(NotFound):
            store.project_dir(bad)


def wait(task, timeout=5):
    end = time.time() + timeout
    while task.status in ("queued", "running") and time.time() < end:
        time.sleep(0.01)
    return task


def test_tasks_report_progress_results_and_errors():
    tm = TaskManager(workers=2)

    def ok(task):
        task.update(0.5, "half")
        return {"answer": 42}

    def boom(task):
        raise ValueError("bad seed")

    a = wait(tm.submit("graph", "p_0000000000", ok))
    b = wait(tm.submit("graph", "p_0000000000", boom))
    assert a.status == "done" and a.result == {"answer": 42} and a.progress == 1.0
    assert b.status == "failed" and "bad seed" in b.error
    assert tm.active("p_0000000000", "graph") is None


def test_tasks_can_be_cancelled():
    tm = TaskManager(workers=1)

    def slow(task):
        for i in range(500):
            task.update(i / 500)
            time.sleep(0.005)

    t = tm.submit("run", "p_0000000000", slow)
    time.sleep(0.05)
    tm.cancel(t.id)
    assert wait(t).status == "cancelled"
