"""Projects and runs live on disk as folders of JSON files."""

from __future__ import annotations

import json
import re
import secrets
import shutil
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ID_PATTERN = re.compile(r"^[a-z]_[0-9a-f]{10}$")


class NotFound(KeyError):
    pass


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def new_id(prefix: str) -> str:
    return f"{prefix}_{secrets.token_hex(5)}"


class Store:
    def __init__(self, root: Path):
        self.root = Path(root)
        (self.root / "projects").mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()

    # paths -------------------------------------------------------------
    def _checked(self, value: str) -> str:
        if not ID_PATTERN.match(value or ""):
            raise NotFound(value)
        return value

    def project_dir(self, pid: str) -> Path:
        path = self.root / "projects" / self._checked(pid)
        if not path.is_dir():
            raise NotFound(pid)
        return path

    def run_dir(self, pid: str, rid: str) -> Path:
        path = self.project_dir(pid) / "runs" / self._checked(rid)
        if not path.is_dir():
            raise NotFound(rid)
        return path

    # json helpers ------------------------------------------------------
    def read(self, path: Path, default: Any = None) -> Any:
        try:
            return json.loads(Path(path).read_text())
        except FileNotFoundError:
            return default

    def write(self, path: Path, obj: Any) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + f".{secrets.token_hex(3)}.tmp")
        tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=2))
        tmp.replace(path)

    def append_jsonl(self, path: Path, obj: Any) -> None:
        with self._lock, Path(path).open("a") as f:
            f.write(json.dumps(obj, ensure_ascii=False) + "\n")

    def read_jsonl(self, path: Path, since: int = 0, limit: int | None = None) -> list:
        try:
            lines = Path(path).read_text().splitlines()
        except FileNotFoundError:
            return []
        rows = lines[since:] if limit is None else lines[since : since + limit]
        return [json.loads(line) for line in rows if line.strip()]

    # projects ----------------------------------------------------------
    def create_project(self, name: str, requirement: str, seed_text: str = "") -> dict:
        with self._lock:
            pid = new_id("p")
            path = self.root / "projects" / pid
            path.mkdir(parents=True)
            project = {
                "id": pid,
                "name": name.strip() or "Untitled prediction",
                "requirement": requirement.strip(),
                "created_at": now(),
                "updated_at": now(),
                "stage": "seeded" if seed_text.strip() else "new",
                "sources": [],
            }
            self.write(path / "project.json", project)
            (path / "seed.md").write_text("")
            if seed_text.strip():
                self.add_seed(pid, seed_text, "pasted text")
            return self.get_project(pid)

    def get_project(self, pid: str) -> dict:
        return self.read(self.project_dir(pid) / "project.json")

    def update_project(self, pid: str, **fields) -> dict:
        with self._lock:
            path = self.project_dir(pid) / "project.json"
            project = self.read(path)
            project.update(fields, updated_at=now())
            self.write(path, project)
            return project

    def list_projects(self) -> list[dict]:
        out = []
        for path in sorted((self.root / "projects").iterdir()):
            project = self.read(path / "project.json")
            if project:
                out.append(project)
        return sorted(out, key=lambda p: p["created_at"], reverse=True)

    def delete_project(self, pid: str) -> None:
        shutil.rmtree(self.project_dir(pid))

    def add_seed(self, pid: str, text: str, source: str) -> dict:
        with self._lock:
            path = self.project_dir(pid) / "seed.md"
            existing = path.read_text()
            block = f"\n\n# Source: {source}\n\n{text.strip()}\n"
            path.write_text((existing + block).lstrip())
            project = self.get_project(pid)
            sources = project.get("sources", []) + [{"name": source, "chars": len(text), "added_at": now()}]
            stage = project["stage"] if project["stage"] != "new" else "seeded"
            return self.update_project(pid, sources=sources, stage=stage)

    def seed_text(self, pid: str) -> str:
        return (self.project_dir(pid) / "seed.md").read_text()

    def project_file(self, pid: str, name: str) -> Path:
        return self.project_dir(pid) / name

    # runs --------------------------------------------------------------
    def create_run(self, pid: str, config: dict) -> dict:
        with self._lock:
            rid = new_id("r")
            path = self.project_dir(pid) / "runs" / rid
            path.mkdir(parents=True)
            run = {"id": rid, "project_id": pid, "config": config, "created_at": now(), "status": "queued"}
            self.write(path / "run.json", run)
            return run

    def get_run(self, pid: str, rid: str) -> dict:
        return self.read(self.run_dir(pid, rid) / "run.json")

    def update_run(self, pid: str, rid: str, **fields) -> dict:
        with self._lock:
            path = self.run_dir(pid, rid) / "run.json"
            run = self.read(path)
            run.update(fields, updated_at=now())
            self.write(path, run)
            return run

    def list_runs(self, pid: str) -> list[dict]:
        base = self.project_dir(pid) / "runs"
        if not base.exists():
            return []
        runs = [self.read(p / "run.json") for p in base.iterdir() if (p / "run.json").exists()]
        return sorted(runs, key=lambda r: r["created_at"], reverse=True)
