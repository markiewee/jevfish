"""The pipeline behind the API: projects move seeded -> graph -> prepared -> runs -> reports."""

from __future__ import annotations

from dataclasses import replace
import io
from pathlib import Path

from . import interact
from .config import Settings
from .crowd import build_crowd
from .frame import build_frame, normalize_frame
from .graph import build_graph, search
from .llm import LLM, build_llm
from .report import write_report
from .simulate import RunConfig, planned_requests, run_simulation
from .store import Store, now
from .tasks import TaskManager

STAGES = ["new", "seeded", "graph", "prepared"]


class PipelineError(ValueError):
    pass


class Service:
    def __init__(self, settings: Settings, store: Store | None = None, llm: LLM | None = None, tasks: TaskManager | None = None):
        self.settings = settings
        self.store = store or Store(settings.data_dir)
        self._llm = llm
        self._llm_injected = llm is not None
        self.tasks = tasks or TaskManager()

    def reload(self, settings: Settings) -> None:
        """Use new keys from now on. Tasks already running keep what they started with.
        The data folder never changes while the server runs."""
        self.settings = replace(settings, data_dir=self.settings.data_dir)
        if not self._llm_injected:
            self._llm = None

    def active_tasks(self) -> int:
        return sum(1 for t in self.tasks.list() if t.status in ("queued", "running"))

    @property
    def llm(self) -> LLM:
        if self._llm is None:
            self._llm = build_llm(self.settings)
        return self._llm

    # -- projects --------------------------------------------------------
    def create_project(self, name: str, requirement: str, seed_text: str = "") -> dict:
        if not requirement.strip():
            raise PipelineError("a prediction requirement is required")
        return self.store.create_project(name, requirement, seed_text)

    def add_file(self, pid: str, filename: str, data: bytes) -> dict:
        suffix = Path(filename).suffix.lower()
        if suffix == ".pdf":
            try:
                from pypdf import PdfReader
            except ModuleNotFoundError as e:
                raise PipelineError(
                    "reading a PDF seed needs the pdf extra: pip install 'jevfish[pdf]'. "
                    "Or paste the text straight into the form instead of uploading a file."
                ) from e

            reader = PdfReader(io.BytesIO(data))
            text = "\n\n".join(page.extract_text() or "" for page in reader.pages)
        elif suffix in (".txt", ".md", ".markdown", ".csv", ".json", ""):
            text = data.decode("utf-8", errors="replace")
        else:
            raise PipelineError(f"unsupported file type {suffix}; use .txt, .md or .pdf")
        if not text.strip():
            raise PipelineError(f"no text found in {filename}")
        return self.store.add_seed(self.store._checked(pid), text, Path(filename).name)

    def overview(self, pid: str) -> dict:
        project = self.store.get_project(pid)
        pdir = self.store.project_dir(pid)
        graph = self.store.read(pdir / "graph.json")
        frame = self.store.read(pdir / "frame.json")
        crowd = self.store.read(pdir / "crowd.json")
        return {
            **project,
            "seed_chars": len(self.store.seed_text(pid)),
            "graph_stats": graph.get("stats") if graph else None,
            "has_frame": frame is not None,
            "crowd_stats": {"size": len(crowd["agents"]), **crowd.get("stats", {})} if crowd else None,
            "runs": self.store.list_runs(pid),
            "tasks": [t.to_dict() for t in self.tasks.list(pid)[:10]],
        }

    def _require(self, pid: str, name: str, what: str):
        data = self.store.read(self.store.project_dir(pid) / name)
        if data is None:
            raise PipelineError(f"{what} is missing; run the earlier step first")
        return data

    def _one_at_a_time(self, pid: str, kind: str) -> None:
        active = self.tasks.active(pid, kind)
        if active:
            raise PipelineError(f"a {kind} task is already running ({active.id})")

    # -- stage 1 ---------------------------------------------------------
    def start_graph(self, pid: str):
        project = self.store.get_project(pid)
        if not self.store.seed_text(pid).strip():
            raise PipelineError("add seed text or a file first")
        self._one_at_a_time(pid, "graph")

        def job(task):
            graph = build_graph(self.llm, project["requirement"], self.store.seed_text(pid), task.update, self.settings.llm_workers)
            self.store.write(self.store.project_dir(pid) / "graph.json", graph)
            self.store.update_project(pid, stage="graph")
            return graph["stats"]

        return self.tasks.submit("graph", pid, job)

    def graph(self, pid: str) -> dict:
        return self._require(pid, "graph.json", "the knowledge graph")

    def search_graph(self, pid: str, query: str, limit: int = 10) -> list[dict]:
        return search(self.graph(pid), query, limit)

    # -- stage 2 ---------------------------------------------------------
    def start_prepare(self, pid: str, public_size: int = 60, max_stakeholders: int = 20, seed: int = 0):
        project = self.store.get_project(pid)
        graph = self.graph(pid)
        if not 1 <= public_size <= 2000 or not 0 <= max_stakeholders <= 200:
            raise PipelineError("public_size must be 1 to 2000 and max_stakeholders 0 to 200")
        self._one_at_a_time(pid, "prepare")

        def job(task):
            task.update(0.05, "Writing the prediction frame")
            frame = build_frame(self.llm, project["requirement"], graph)
            self.store.write(self.store.project_dir(pid) / "frame.json", frame)
            task.update(0.25, f"Frame ready: {len(frame['talking_points'])} talking points, {len(frame['variants'])} variant(s)")
            crowd = build_crowd(
                self.llm, project["requirement"], graph,
                public_size=public_size, max_stakeholders=max_stakeholders, seed=seed,
                workers=self.settings.llm_workers, progress=task.update,
            )
            self.store.write(self.store.project_dir(pid) / "crowd.json", crowd)
            self.store.update_project(pid, stage="prepared")
            return {"talking_points": len(frame["talking_points"]), "variants": len(frame["variants"]), **crowd["stats"]}

        return self.tasks.submit("prepare", pid, job)

    def frame(self, pid: str) -> dict:
        return self._require(pid, "frame.json", "the frame")

    def update_frame(self, pid: str, data: dict) -> dict:
        frame = normalize_frame(data, self.store.get_project(pid)["requirement"])
        self.store.write(self.store.project_dir(pid) / "frame.json", frame)
        return frame

    def crowd(self, pid: str) -> dict:
        return self._require(pid, "crowd.json", "the crowd")

    # -- stage 3 ---------------------------------------------------------
    def start_run(self, pid: str, config: dict):
        frame, crowd = self.frame(pid), self.crowd(pid)
        cfg = RunConfig.from_dict(config)
        if not self.settings.judge_ready:
            raise PipelineError("TYPESAFE_API_KEY is not set")
        planned = planned_requests(frame, crowd, cfg)
        cap = cfg.max_requests or self.settings.max_requests
        if planned > cap:
            raise PipelineError(f"this run needs up to {planned} Jev requests but the cap is {cap}; lower rounds or crowd size, or raise max_requests")
        self._one_at_a_time(pid, "run")
        run = self.store.create_run(pid, {**cfg.to_dict(), "max_requests": cap})
        self.store.update_run(pid, run["id"], planned_requests=planned)
        rid = run["id"]

        def job(task):
            summary = run_simulation(self.store, self.settings, self.llm, pid, rid, task.update)
            return {"run_id": rid, "partial": summary["partial"], "requests": summary["judge"]["requests"]}

        task = self.tasks.submit("run", pid, job)
        self.store.update_run(pid, rid, task_id=task.id)
        return self.store.get_run(pid, rid), task

    def run(self, pid: str, rid: str) -> dict:
        run = self.store.get_run(pid, rid)
        run["summary"] = self.store.read(self.store.run_dir(pid, rid) / "summary.json")
        run["report_ready"] = (self.store.run_dir(pid, rid) / "report.json").exists()
        return run

    def actions(self, pid: str, rid: str, since: int = 0, limit: int = 200) -> list[dict]:
        return self.store.read_jsonl(self.store.run_dir(pid, rid) / "actions.jsonl", since=since, limit=limit)

    def polls(self, pid: str, rid: str) -> list[dict]:
        return self.store.read_jsonl(self.store.run_dir(pid, rid) / "polls.jsonl")

    def cancel_run(self, pid: str, rid: str) -> dict:
        run = self.store.get_run(pid, rid)
        if run.get("task_id"):
            try:
                self.tasks.cancel(run["task_id"])
            except KeyError:
                pass
        return run

    # -- stage 4 ---------------------------------------------------------
    def start_report(self, pid: str, rid: str):
        summary = self.store.read(self.store.run_dir(pid, rid) / "summary.json")
        if summary is None:
            raise PipelineError("the run has not finished yet")
        self._one_at_a_time(pid, "report")
        graph = self.store.read(self.store.project_dir(pid) / "graph.json")
        crowd = self.crowd(pid)

        def job(task):
            task.update(0.2, "Writing the report")
            report = write_report(self.llm, summary, graph, crowd)
            report["created_at"] = now()
            self.store.write(self.store.run_dir(pid, rid) / "report.json", report)
            return {"chars": len(report["markdown"])}

        return self.tasks.submit("report", pid, job)

    def report(self, pid: str, rid: str) -> dict:
        report = self.store.read(self.store.run_dir(pid, rid) / "report.json")
        if report is None:
            raise PipelineError("no report yet")
        return report

    # -- stage 5 ---------------------------------------------------------
    def _variant(self, pid: str, rid: str, variant: str | None) -> str:
        run = self.store.get_run(pid, rid)
        variants = run.get("variants") or [v["id"] for v in self.frame(pid)["variants"]]
        if variant is None:
            return variants[0]
        if variant not in variants:
            raise PipelineError(f"variant '{variant}' was not part of this run")
        return variant

    def chat(self, pid: str, rid: str, agent_id: int, message: str, variant: str | None = None) -> dict:
        if not message.strip():
            raise PipelineError("message is empty")
        agents = {a["agent_id"]: a for a in self.crowd(pid)["agents"]}
        if agent_id not in agents:
            raise PipelineError(f"no person with id {agent_id}")
        variant = self._variant(pid, rid, variant)
        run_dir = self.store.run_dir(pid, rid)
        history_path = run_dir / "chats" / f"{variant}_{agent_id}.json"
        history = self.store.read(history_path, [])
        reply = interact.chat(
            self.llm, self.frame(pid), agents[agent_id], variant,
            self.store.read_jsonl(run_dir / "actions.jsonl"), self.polls(pid, rid), history, message,
        )
        history += [{"role": "user", "content": message, "at": now()}, {"role": "assistant", "content": reply, "at": now()}]
        self.store.write(history_path, history)
        return {"agent_id": agent_id, "variant": variant, "reply": reply, "history": history}

    def chat_history(self, pid: str, rid: str, agent_id: int, variant: str | None = None) -> list[dict]:
        variant = self._variant(pid, rid, variant)
        return self.store.read(self.store.run_dir(pid, rid) / "chats" / f"{variant}_{agent_id}.json", [])

    def ask_crowd(self, pid: str, rid: str, question: str, variant: str | None = None) -> dict:
        if not question.strip():
            raise PipelineError("question is empty")
        variant = self._variant(pid, rid, variant)
        run_dir = self.store.run_dir(pid, rid)
        result = interact.ask_crowd(
            self.settings, self.store.project_dir(pid) / "verdicts.sqlite", self.frame(pid), self.crowd(pid)["agents"],
            variant, self.polls(pid, rid), self.store.read_jsonl(run_dir / "actions.jsonl"), question,
        )
        result["at"] = now()
        self.store.append_jsonl(run_dir / "questions.jsonl", result)
        return result

    def asked(self, pid: str, rid: str) -> list[dict]:
        return self.store.read_jsonl(self.store.run_dir(pid, rid) / "questions.jsonl")
