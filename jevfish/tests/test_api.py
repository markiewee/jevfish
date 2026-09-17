import io
import time

import pytest

from jevfish.api import create_app
from jevfish.llm import FakeLLM
from jevfish.service import Service
from tests.test_pipeline import SEED, settings


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    s = settings(tmp_path)
    app = create_app(s, Service(s, llm=FakeLLM()))
    return app.test_client()


def wait(client, task, timeout=120):
    end = time.time() + timeout
    while True:
        t = client.get(f"/api/tasks/{task['id']}").get_json()
        if t["status"] not in ("queued", "running"):
            assert t["status"] == "done", t
            return t
        assert time.time() < end, t
        time.sleep(0.05)


def test_full_flow_over_http(client):
    assert client.get("/api/health").get_json()["judge"] == "fake"
    r = client.post("/api/projects", json={"name": "Demo", "requirement": "Will renters book a viewing?", "seed_text": SEED})
    assert r.status_code == 201
    pid = r.get_json()["id"]
    r = client.post(f"/api/projects/{pid}/files", data={"file": (io.BytesIO(b"Omega Homes launched in Bishan."), "extra.txt")},
                    content_type="multipart/form-data")
    assert r.status_code == 200 and len(r.get_json()["sources"]) == 2
    assert "Omega Homes" in client.get(f"/api/projects/{pid}/seed").get_json()["text"]

    assert client.get(f"/api/projects/{pid}/graph").status_code == 400
    wait(client, client.post(f"/api/projects/{pid}/graph").get_json())
    graph = client.get(f"/api/projects/{pid}/graph").get_json()
    assert graph["nodes"]
    assert client.get(f"/api/projects/{pid}/graph/search?q=Lazybee").get_json()

    wait(client, client.post(f"/api/projects/{pid}/prepare", json={"public_size": 10, "max_stakeholders": 2}).get_json())
    frame = client.get(f"/api/projects/{pid}/frame").get_json()
    frame["variants"] = [{"id": "A", "label": "Now", "subject": {}}, {"id": "B", "label": "Upgrade", "subject": {"cleaning": "weekly"}}]
    assert client.put(f"/api/projects/{pid}/frame", json=frame).status_code == 200
    bad = dict(frame, stance={"levels": ["x"]})
    assert client.put(f"/api/projects/{pid}/frame", json=bad).status_code == 400
    crowd = client.get(f"/api/projects/{pid}/crowd").get_json()
    assert len(crowd["agents"]) >= 10

    config = {"platform": "lite", "rounds": 2, "agents_per_round_min": 3, "agents_per_round_max": 5}
    est = client.post(f"/api/projects/{pid}/estimate", json=config).get_json()
    assert est["planned_requests"] > 0 and est["est_cost_usd"] >= 0 and est["polls"] == [0, 1, 2]
    r = client.post(f"/api/projects/{pid}/runs", json=config)
    assert r.status_code == 202
    run_id = r.get_json()["run"]["id"]
    wait(client, r.get_json()["task"])
    run = client.get(f"/api/projects/{pid}/runs/{run_id}").get_json()
    assert run["status"] == "done" and run["summary"]["variants"][1]["id"] == "B"
    acts = client.get(f"/api/projects/{pid}/runs/{run_id}/actions?since=0&limit=5").get_json()
    assert len(acts) <= 5
    assert client.get(f"/api/projects/{pid}/runs/{run_id}/polls").get_json()

    assert client.get(f"/api/projects/{pid}/runs/{run_id}/report").status_code == 400
    wait(client, client.post(f"/api/projects/{pid}/runs/{run_id}/report").get_json())
    assert "Prediction" in client.get(f"/api/projects/{pid}/runs/{run_id}/report").get_json()["markdown"]

    agent_id = crowd["agents"][0]["agent_id"]
    r = client.post(f"/api/projects/{pid}/runs/{run_id}/chat", json={"agent_id": agent_id, "message": "Thoughts?", "variant": "B"})
    assert r.status_code == 200 and r.get_json()["reply"]
    assert len(client.get(f"/api/projects/{pid}/runs/{run_id}/chat/{agent_id}?variant=B").get_json()) == 2
    assert client.post(f"/api/projects/{pid}/runs/{run_id}/chat", json={"agent_id": "x", "message": "hi"}).status_code == 400
    assert client.post(f"/api/projects/{pid}/runs/{run_id}/chat", json={"agent_id": 9999, "message": "hi"}).status_code == 400
    r = client.post(f"/api/projects/{pid}/runs/{run_id}/ask", json={"question": "Would they move in this month?", "variant": "B"})
    assert r.status_code == 200 and r.get_json()["summary"]["n"] == len(crowd["agents"])
    assert client.get(f"/api/projects/{pid}/runs/{run_id}/ask").get_json()
    assert client.post(f"/api/projects/{pid}/runs/{run_id}/ask", json={"question": "hi", "variant": "Z"}).status_code == 400

    overview = client.get(f"/api/projects/{pid}").get_json()
    assert overview["stage"] == "prepared" and overview["runs"] and overview["crowd_stats"]["size"] == len(crowd["agents"])
    assert client.get("/api/projects").get_json()[0]["id"] == pid


def test_errors_are_json(client):
    assert client.get("/api/projects/p_0000000000").status_code == 404
    assert client.get("/api/projects/../../etc").status_code in (404, 400)
    assert client.get("/api/tasks/t_nope").status_code == 404
    assert client.post("/api/projects", json={"name": "x"}).status_code == 400
    r = client.get("/api/nothing-here")
    assert r.status_code == 404 and r.get_json()["error"]
    assert client.post("/api/projects/p_0000000000/runs", json={"platform": "lite"}).status_code == 404


def test_root_serves_something(client):
    r = client.get("/")
    assert r.status_code == 200
