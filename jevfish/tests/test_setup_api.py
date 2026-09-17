import os
import time

import pytest

from jevfish import keys
from jevfish.api import create_app
from jevfish.llm import FakeLLM
from jevfish.service import Service
from tests.test_pipeline import settings

MANAGED = ("TYPESAFE_API_KEY", "GEMINI_API_KEY", "LLM_API_KEY", "LLM_BASE_URL", "LLM_MODEL", "LLM_MODEL_NAME",
           "JEVFISH_FAKE_JUDGE", "JEVFISH_FAKE_LLM", "JEVFISH_DATA_DIR")


@pytest.fixture
def env_file(tmp_path):
    # saving settings edits os.environ directly, so snapshot and restore all of it
    before = dict(os.environ)
    for k in MANAGED:
        os.environ.pop(k, None)
    path = tmp_path / "keys.env"
    os.environ["JEVFISH_ENV_FILE"] = str(path)
    yield path
    os.environ.clear()
    os.environ.update(before)


@pytest.fixture
def app(tmp_path, env_file):
    s = settings(tmp_path, fake_judge=False, fake_llm=False)
    stopped = []
    app = create_app(s, Service(s, llm=FakeLLM()))
    app.config["JEVFISH_STOP"] = lambda: stopped.append(True)
    app.stopped = stopped
    return app


def test_first_run_needs_setup_then_save_applies_without_restart(app, env_file, tmp_path):
    c = app.test_client()
    assert c.get("/api/health").get_json()["setup_needed"] is True
    got = c.get("/api/settings").get_json()
    assert got["typesafe_key"] is None and got["llm_provider"] == "gemini" and got["setup_needed"] is True
    r = c.put("/api/settings", json={"typesafe_key": "ts-abcdefgh9999", "llm_provider": "gemini", "llm_key": "gm-abcdefgh7777"})
    assert r.status_code == 200, r.get_json()
    body = r.get_json()
    assert body["typesafe_key"] == "9999" and body["gemini_key"] == "7777" and body["setup_needed"] is False
    assert "ts-abcdefgh9999" not in r.get_data(as_text=True)
    assert "TYPESAFE_API_KEY='ts-abcdefgh9999'" in env_file.read_text()
    health = c.get("/api/health").get_json()
    assert health["judge"] == "jev" and health["setup_needed"] is False
    assert health["data_dir"] == str(tmp_path / "data")


def test_test_mode_toggle(app):
    c = app.test_client()
    assert c.put("/api/settings", json={"test_mode": True}).get_json()["test_mode"] is True
    assert c.get("/api/health").get_json()["judge"] == "fake"
    assert c.put("/api/settings", json={"test_mode": False}).get_json()["test_mode"] is False
    assert c.get("/api/health").get_json()["setup_needed"] is True


def test_bad_form_is_400(app):
    r = app.test_client().put("/api/settings", json={"llm_provider": "openai", "llm_base_url": "nope"})
    assert r.status_code == 400 and "http" in r.get_json()["error"]
    assert app.test_client().put("/api/settings", data="x").status_code == 400


def test_check_uses_form_keys_then_saved(app, monkeypatch):
    calls = []
    monkeypatch.setattr(keys, "check_jev", lambda key, model="jev-latest": calls.append(("jev", key)) or {"ok": True, "message": "j"})
    monkeypatch.setattr(keys, "check_llm", lambda choice, key, base_url=None, model=None: calls.append((choice, key)) or {"ok": False, "message": "l"})
    c = app.test_client()
    r = c.post("/api/settings/check", json={"typesafe_key": "typed", "llm_provider": "gemini"}).get_json()
    assert r["jev"]["ok"] is True and r["llm"] == {"ok": False, "message": "No Gemini key yet."}
    assert calls == [("jev", "typed")]
    os.environ["GEMINI_API_KEY"] = "saved-g"
    c.post("/api/settings/check", json={})
    assert calls[-1] == ("gemini", "saved-g")


def test_example_and_shutdown(app):
    c = app.test_client()
    ex = c.get("/api/example").get_json()
    assert "Lazybee" in ex["name"] and ex["seed_text"].strip() and ex["requirement"].endswith("?")
    assert c.post("/api/shutdown").get_json()["ok"] is True
    time.sleep(0.5)
    assert app.stopped == [True]


def test_guard_blocks_other_hosts_and_origins(app):
    c = app.test_client()
    assert c.get("/api/health", headers={"Host": "evil.example"}).status_code == 403
    assert c.get("/api/health", headers={"Host": "127.0.0.1:5055"}).status_code == 200
    assert c.get("/api/health", headers={"Host": "[::1]:5055"}).status_code == 200
    assert c.put("/api/settings", json={"test_mode": True}, headers={"Origin": "https://evil.example"}).status_code == 403
    assert c.put("/api/settings", json={"test_mode": True}, headers={"Origin": "null"}).status_code == 403
    assert c.put("/api/settings", json={"test_mode": True}, headers={"Origin": "http://localhost:5173"}).status_code == 200
    assert c.get("/", headers={"Host": "evil.example"}).status_code == 200  # the page itself holds no data


def test_guard_can_be_turned_off(tmp_path, env_file):
    s = settings(tmp_path)
    app = create_app(s, Service(s, llm=FakeLLM()), allow_remote=True)
    assert app.test_client().get("/api/health", headers={"Host": "192.168.1.9:5055"}).status_code == 200
