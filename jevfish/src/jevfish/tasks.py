"""Long jobs (graph build, prepare, run, report) run on worker threads with visible progress."""

from __future__ import annotations

import threading
import traceback
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Any

from .store import new_id, now


class Cancelled(Exception):
    pass


@dataclass
class Task:
    id: str
    kind: str
    project_id: str
    status: str = "queued"  # queued, running, done, failed, cancelled
    progress: float = 0.0
    message: str = ""
    result: Any = None
    error: str | None = None
    created_at: str = field(default_factory=now)
    updated_at: str = field(default_factory=now)
    _cancel: threading.Event = field(default_factory=threading.Event, repr=False)

    def update(self, progress: float | None = None, message: str | None = None) -> None:
        if self._cancel.is_set():
            raise Cancelled(self.id)
        if progress is not None:
            self.progress = max(0.0, min(1.0, progress))
        if message is not None:
            self.message = message
        self.updated_at = now()

    @property
    def cancelled(self) -> bool:
        return self._cancel.is_set()

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "kind": self.kind,
            "project_id": self.project_id,
            "status": self.status,
            "progress": round(self.progress, 4),
            "message": self.message,
            "result": self.result,
            "error": self.error,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class TaskManager:
    def __init__(self, workers: int = 4):
        self._pool = ThreadPoolExecutor(max_workers=workers, thread_name_prefix="jevfish-task")
        self._tasks: dict[str, Task] = {}
        self._lock = threading.Lock()

    def submit(self, kind: str, project_id: str, fn: Callable[[Task], Any]) -> Task:
        task = Task(new_id("t"), kind, project_id)
        with self._lock:
            self._tasks[task.id] = task

        def run() -> None:
            task.status = "running"
            task.updated_at = now()
            try:
                task.result = fn(task)
                task.status = "done"
                task.progress = 1.0
            except Cancelled:
                task.status = "cancelled"
            except Exception as e:  # surfaced to the UI, full trace kept in the message log
                task.status = "failed"
                task.error = f"{type(e).__name__}: {e}"
                task.message = traceback.format_exc(limit=6)
            task.updated_at = now()

        self._pool.submit(run)
        return task

    def get(self, task_id: str) -> Task:
        return self._tasks[task_id]

    def list(self, project_id: str | None = None, kind: str | None = None) -> list[Task]:
        tasks = [t for t in self._tasks.values() if (project_id is None or t.project_id == project_id)]
        if kind:
            tasks = [t for t in tasks if t.kind == kind]
        return sorted(tasks, key=lambda t: t.created_at, reverse=True)

    def active(self, project_id: str, kind: str) -> Task | None:
        for t in self.list(project_id, kind):
            if t.status in ("queued", "running"):
                return t
        return None

    def cancel(self, task_id: str) -> Task:
        task = self._tasks[task_id]
        task._cancel.set()
        return task

    def shutdown(self) -> None:
        for t in self._tasks.values():
            t._cancel.set()
        self._pool.shutdown(wait=False, cancel_futures=True)
