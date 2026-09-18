"""Setup endpoints (keys, test mode, the example, stopping) and the local-only guard."""

from __future__ import annotations

import os
import signal
import threading
from urllib.parse import urlsplit

from flask import Blueprint, current_app, jsonify, request

from . import example, keys
from .config import env_file_path, load_settings
from .keys import SetupError

bp = Blueprint("setup", __name__)
LOCAL_NAMES = {"127.0.0.1", "localhost", "::1"}


def _svc():
    return current_app.extensions["jevfish"]


def _form() -> dict:
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise SetupError("Send the settings as JSON.")
    return data


def is_local(netloc: str) -> bool:
    try:
        return (urlsplit("//" + netloc).hostname or "") in LOCAL_NAMES
    except ValueError:
        return False


def _origin_is_local(origin: str) -> bool:
    try:
        return is_local(urlsplit(origin).netloc)
    except ValueError:
        return False


def guard():
    """Only this computer may use the API. Blocks DNS rebinding and other sites' forms."""
    if not request.path.startswith("/api/") or current_app.config.get("JEVFISH_ALLOW_REMOTE"):
        return None
    if not is_local(request.host):
        return jsonify(error="JevFish only answers on this computer. Open http://127.0.0.1 instead."), 403
    origin = request.headers.get("Origin")
    if request.method not in ("GET", "HEAD", "OPTIONS") and origin is not None and not _origin_is_local(origin):
        return jsonify(error="Requests from other websites are blocked."), 403
    return None


@bp.errorhandler(SetupError)
def setup_error(e):
    return jsonify(error=str(e)), 400


@bp.get("/api/settings")
def get_settings():
    env, svc = os.environ, _svc()
    s = svc.settings
    return jsonify(
        env_file=str(env_file_path()),
        test_mode=s.fake_judge or s.fake_llm,
        setup_needed=not (s.llm_ready and s.judge_ready),
        typesafe_key=keys.hint(env.get("TYPESAFE_API_KEY")),
        llm_provider=keys.provider(env),
        gemini_key=keys.hint(env.get("GEMINI_API_KEY")),
        llm_key=keys.hint(env.get("LLM_API_KEY")),
        llm_base_url=env.get("LLM_BASE_URL", ""),
        llm_model=env.get("LLM_MODEL", "") or env.get("LLM_MODEL_NAME", ""),
        active_tasks=svc.active_tasks(),
    )


@bp.put("/api/settings")
def put_settings():
    updates = keys.updates_from_form(_form(), os.environ)
    keys.write_env(env_file_path(), updates)
    keys.apply(updates)
    _svc().reload(load_settings())
    return get_settings()


@bp.post("/api/settings/check")
def check():
    form, env = _form(), os.environ
    jev_key = keys.text(form, "typesafe_key") or env.get("TYPESAFE_API_KEY", "")
    jev = keys.check_jev(jev_key, _svc().settings.jev_model) if jev_key else {"ok": False, "message": "No Jev key yet."}
    choice = form.get("llm_provider") or keys.provider(env)
    typed = keys.text(form, "llm_key")
    if choice == "gemini":
        key = typed or env.get("GEMINI_API_KEY", "")
        llm = keys.check_llm("gemini", key) if key else {"ok": False, "message": "No Gemini key yet."}
    else:
        key = typed or env.get("LLM_API_KEY", "")
        base = keys.text(form, "llm_base_url") or env.get("LLM_BASE_URL", "")
        model = keys.text(form, "llm_model") or env.get("LLM_MODEL", "")
        llm = keys.check_llm("openai", key, base, model) if key and base and model else {
            "ok": False, "message": "Fill in the address, model and key first."}
    return jsonify(jev=jev, llm=llm)


@bp.get("/api/example")
def get_example():
    return jsonify(example.example())


def _stop_process() -> None:
    os.kill(os.getpid(), signal.SIGTERM)


@bp.post("/api/shutdown")
def shutdown():
    stop = current_app.config.get("JEVFISH_STOP") or _stop_process
    threading.Timer(0.3, stop).start()  # let the response go out first
    return jsonify(ok=True)
