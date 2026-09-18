"""HTTP API (Flask). Serves the Vue app from web/dist at /."""

from __future__ import annotations

from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory
from werkzeug.exceptions import HTTPException

from .assets import web_dist
from .config import Settings, load_settings
from .frame import FrameError
from .judge import JudgeUnavailable
from .llm import LLMError
from .service import PipelineError, Service
from .setup_api import bp as setup_bp
from .setup_api import guard
from .simulate import RunConfig, RunConfigError, planned_requests
from .store import NotFound

WEB_DIST = web_dist()
TOKENS_PER_REQUEST = 1400  # measured ~1,230 on the Lazybee demo; rounded up
PRICE_PER_M_INPUT = 0.042


def create_app(settings: Settings | None = None, service: Service | None = None, allow_remote: bool = False) -> Flask:
    """allow_remote turns off the local-only guard; only for `serve --host` beyond loopback."""
    settings = settings or load_settings()
    svc = service or Service(settings)
    app = Flask(__name__, static_folder=None)
    app.config["MAX_CONTENT_LENGTH"] = 25 * 1024 * 1024
    app.config["JEVFISH_ALLOW_REMOTE"] = allow_remote
    app.extensions["jevfish"] = svc
    app.before_request(guard)
    app.register_blueprint(setup_bp)

    def body() -> dict:
        data = request.get_json(silent=True)
        return data if isinstance(data, dict) else {}

    def int_arg(name: str, default: int) -> int:
        try:
            return int(request.args.get(name, default))
        except ValueError:
            raise PipelineError(f"{name} must be a number")

    @app.errorhandler(NotFound)
    def not_found(e):
        return jsonify(error=f"not found: {e.args[0] if e.args else ''}"), 404

    @app.errorhandler(KeyError)
    def key_error(e):
        return jsonify(error=f"not found: {e.args[0] if e.args else ''}"), 404

    @app.errorhandler(PipelineError)
    @app.errorhandler(FrameError)
    @app.errorhandler(RunConfigError)
    def bad_request(e):
        return jsonify(error=str(e)), 400

    @app.errorhandler(JudgeUnavailable)
    @app.errorhandler(LLMError)
    def unavailable(e):
        return jsonify(error=str(e)), 503

    @app.errorhandler(HTTPException)
    def http_error(e):
        if request.path.startswith("/api/"):
            return jsonify(error=e.description), e.code
        return e

    # -- meta ------------------------------------------------------------
    @app.get("/api/health")
    def health():
        return jsonify(ok=True, **svc.settings.health())

    @app.get("/api/tasks/<tid>")
    def task(tid):
        return jsonify(svc.tasks.get(tid).to_dict())

    @app.post("/api/tasks/<tid>/cancel")
    def cancel_task(tid):
        return jsonify(svc.tasks.cancel(tid).to_dict())

    # -- projects --------------------------------------------------------
    @app.get("/api/projects")
    def projects():
        return jsonify(svc.store.list_projects())

    @app.post("/api/projects")
    def create_project():
        b = body()
        project = svc.create_project(str(b.get("name", "")), str(b.get("requirement", "")), str(b.get("seed_text", "")))
        return jsonify(project), 201

    @app.get("/api/projects/<pid>")
    def project(pid):
        return jsonify(svc.overview(pid))

    @app.patch("/api/projects/<pid>")
    def patch_project(pid):
        b = body()
        fields = {k: str(b[k]) for k in ("name", "requirement") if k in b}
        if "requirement" in fields and not fields["requirement"].strip():
            raise PipelineError("requirement cannot be empty")
        return jsonify(svc.store.update_project(pid, **fields))

    @app.delete("/api/projects/<pid>")
    def delete_project(pid):
        svc.store.delete_project(pid)
        return jsonify(ok=True)

    @app.get("/api/projects/<pid>/seed")
    def seed(pid):
        return jsonify(text=svc.store.seed_text(pid))

    @app.post("/api/projects/<pid>/seed")
    def add_seed(pid):
        b = body()
        text = str(b.get("text", ""))
        if not text.strip():
            raise PipelineError("text is empty")
        return jsonify(svc.store.add_seed(pid, text, str(b.get("source") or "pasted text")))

    @app.post("/api/projects/<pid>/files")
    def upload(pid):
        files = request.files.getlist("file")
        if not files:
            raise PipelineError("attach at least one file as 'file'")
        project = None
        for f in files:
            project = svc.add_file(pid, f.filename or "upload.txt", f.read())
        return jsonify(project)

    # -- stage 1 ---------------------------------------------------------
    @app.post("/api/projects/<pid>/graph")
    def start_graph(pid):
        return jsonify(svc.start_graph(pid).to_dict()), 202

    @app.get("/api/projects/<pid>/graph")
    def graph(pid):
        return jsonify(svc.graph(pid))

    @app.get("/api/projects/<pid>/graph/search")
    def graph_search(pid):
        return jsonify(svc.search_graph(pid, request.args.get("q", ""), int_arg("limit", 10)))

    # -- stage 2 ---------------------------------------------------------
    @app.post("/api/projects/<pid>/prepare")
    def prepare(pid):
        b = body()
        task = svc.start_prepare(
            pid,
            public_size=int(b.get("public_size", 60)),
            max_stakeholders=int(b.get("max_stakeholders", 20)),
            seed=int(b.get("seed", 0)),
        )
        return jsonify(task.to_dict()), 202

    @app.get("/api/projects/<pid>/frame")
    def frame(pid):
        return jsonify(svc.frame(pid))

    @app.put("/api/projects/<pid>/frame")
    def put_frame(pid):
        return jsonify(svc.update_frame(pid, body()))

    @app.get("/api/projects/<pid>/crowd")
    def crowd(pid):
        return jsonify(svc.crowd(pid))

    # -- stage 3 ---------------------------------------------------------
    @app.post("/api/projects/<pid>/estimate")
    def estimate(pid):
        cfg = RunConfig.from_dict(body())
        planned = planned_requests(svc.frame(pid), svc.crowd(pid), cfg)
        return jsonify(
            planned_requests=planned,
            cap=cfg.max_requests or svc.settings.max_requests,
            est_input_tokens=planned * TOKENS_PER_REQUEST,
            est_cost_usd=round(planned * TOKENS_PER_REQUEST / 1_000_000 * PRICE_PER_M_INPUT, 4),
            polls=cfg.polls(),
        )

    @app.get("/api/projects/<pid>/runs")
    def runs(pid):
        return jsonify(svc.store.list_runs(pid))

    @app.post("/api/projects/<pid>/runs")
    def start_run(pid):
        run, task = svc.start_run(pid, body())
        return jsonify(run=run, task=task.to_dict()), 202

    @app.get("/api/projects/<pid>/runs/<rid>")
    def run(pid, rid):
        return jsonify(svc.run(pid, rid))

    @app.post("/api/projects/<pid>/runs/<rid>/cancel")
    def cancel_run(pid, rid):
        return jsonify(svc.cancel_run(pid, rid))

    @app.get("/api/projects/<pid>/runs/<rid>/actions")
    def actions(pid, rid):
        return jsonify(svc.actions(pid, rid, since=int_arg("since", 0), limit=min(int_arg("limit", 200), 1000)))

    @app.get("/api/projects/<pid>/runs/<rid>/polls")
    def polls(pid, rid):
        return jsonify(svc.polls(pid, rid))

    # -- stage 4 ---------------------------------------------------------
    @app.post("/api/projects/<pid>/runs/<rid>/report")
    def start_report(pid, rid):
        return jsonify(svc.start_report(pid, rid).to_dict()), 202

    @app.get("/api/projects/<pid>/runs/<rid>/report")
    def report(pid, rid):
        return jsonify(svc.report(pid, rid))

    # -- stage 5 ---------------------------------------------------------
    @app.post("/api/projects/<pid>/runs/<rid>/chat")
    def chat(pid, rid):
        b = body()
        try:
            agent_id = int(b.get("agent_id"))
        except (TypeError, ValueError):
            raise PipelineError("agent_id must be a number")
        return jsonify(svc.chat(pid, rid, agent_id, str(b.get("message", "")), b.get("variant")))

    @app.get("/api/projects/<pid>/runs/<rid>/chat/<int:agent_id>")
    def chat_history(pid, rid, agent_id):
        return jsonify(svc.chat_history(pid, rid, agent_id, request.args.get("variant")))

    @app.post("/api/projects/<pid>/runs/<rid>/ask")
    def ask(pid, rid):
        b = body()
        return jsonify(svc.ask_crowd(pid, rid, str(b.get("question", "")), b.get("variant")))

    @app.get("/api/projects/<pid>/runs/<rid>/ask")
    def asked(pid, rid):
        return jsonify(svc.asked(pid, rid))

    # -- web app ---------------------------------------------------------
    @app.get("/", defaults={"path": ""})
    @app.get("/<path:path>")
    def web(path):
        if path.startswith("api/"):
            return jsonify(error="not found"), 404
        dist = Path(WEB_DIST)
        if path and (dist / path).is_file():
            return send_from_directory(dist, path)
        if (dist / "index.html").is_file():
            return send_from_directory(dist, "index.html")
        return (
            "<h1>JevFish API is running</h1><p>The web app is not built yet. Run <code>npm install &amp;&amp; npm run build</code> in <code>jevfish/web</code>.</p>",
            200,
        )

    return app
