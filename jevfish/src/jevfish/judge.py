"""Judges answer typed questions about a JSON state.

The engine only talks to the `Judge` protocol. `TypeSafeJudge` calls Jev,
`FakeJudge` returns deterministic noise for tests and request-count estimates,
`CachingJudge` makes reruns free, and `Meter` enforces a request budget.
Stack them as CachingJudge(Meter(TypeSafeJudge())) so cache hits never count
against the budget.
"""

from __future__ import annotations

import hashlib
import json
import math
import random
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

JSON = Any


@dataclass(frozen=True)
class NoulQ:
    instructions: JSON
    criteria: dict[str, JSON] | None = None


@dataclass(frozen=True)
class ChoiceQ:
    instructions: JSON
    criteria: dict[str, JSON]


@dataclass(frozen=True)
class ScoreQ:
    instructions: JSON
    criteria: list[JSON]


Question = NoulQ | ChoiceQ | ScoreQ


@dataclass(frozen=True)
class NoulA:
    p: float


@dataclass(frozen=True)
class ChoiceA:
    choice: str
    probabilities: dict[str, float]
    confidence: float


@dataclass(frozen=True)
class ScoreA:
    score: float
    probabilities: dict[int, float]
    confidence: float


Answer = NoulA | ChoiceA | ScoreA


@dataclass(frozen=True)
class Verdict:
    answers: dict[str, Answer]
    input_tokens: int
    output_tokens: int
    cached: bool = False


class Judge(Protocol):
    model: str

    async def ask(self, state: JSON, questions: dict[str, Question]) -> Verdict: ...

    async def aclose(self) -> None: ...


class BudgetExceeded(RuntimeError):
    pass


def question_to_json(q: Question) -> dict[str, JSON]:
    if isinstance(q, NoulQ):
        out: dict[str, JSON] = {"type": "noul", "instructions": q.instructions}
        if q.criteria is not None:
            out["criteria"] = q.criteria
        return out
    if isinstance(q, ChoiceQ):
        return {"type": "choice", "instructions": q.instructions, "criteria": q.criteria}
    return {"type": "score", "instructions": q.instructions, "criteria": q.criteria}


def answer_to_json(a: Answer) -> dict[str, JSON]:
    if isinstance(a, NoulA):
        return {"type": "noul", "noul": a.p}
    if isinstance(a, ChoiceA):
        return {
            "type": "choice",
            "choice": a.choice,
            "probabilities": a.probabilities,
            "confidence": a.confidence,
        }
    return {
        "type": "score",
        "score": a.score,
        "probabilities": {str(k): v for k, v in a.probabilities.items()},
        "confidence": a.confidence,
    }


def answer_from_json(d: dict[str, JSON]) -> Answer:
    if d["type"] == "noul":
        return NoulA(float(d["noul"]))
    if d["type"] == "choice":
        return ChoiceA(d["choice"], dict(d["probabilities"]), float(d["confidence"]))
    return ScoreA(
        float(d["score"]),
        {int(k): float(v) for k, v in d["probabilities"].items()},
        float(d["confidence"]),
    )


def request_key(model: str, state: JSON, questions: dict[str, Question]) -> str:
    payload = json.dumps(
        {
            "model": model,
            "state": state,
            "questions": {k: question_to_json(q) for k, q in questions.items()},
        },
        sort_keys=True,
        ensure_ascii=False,
    )
    return hashlib.sha256(payload.encode()).hexdigest()


class TypeSafeJudge:
    """Calls Jev through the official async SDK. Reads TYPESAFE_API_KEY when api_key is None."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str = "jev-latest",
        transport: Any = None,
        timeout: float | None = None,
    ):
        from typesafe_sdk import AsyncTypeSafeClient

        self.model = model
        self._client = AsyncTypeSafeClient(
            api_key=api_key, model=model, transport=transport, timeout=timeout
        )

    async def ask(self, state: JSON, questions: dict[str, Question]) -> Verdict:
        from typesafe_sdk import ChoiceAnswer, NoulAnswer

        response = await self._client.system_one(
            state=state,
            questions={k: _to_sdk(q) for k, q in questions.items()},
            model=self.model,
        )
        answers: dict[str, Answer] = {}
        for key, a in response.answers.items():
            if isinstance(a, NoulAnswer):
                answers[key] = NoulA(a.noul)
            elif isinstance(a, ChoiceAnswer):
                answers[key] = ChoiceA(a.choice, dict(a.probabilities), a.confidence)
            else:
                answers[key] = ScoreA(a.score, dict(a.probabilities), a.confidence)
        return Verdict(
            answers=answers,
            input_tokens=response.usage.input_tokens or 0,
            output_tokens=response.usage.output_tokens or 0,
        )

    async def aclose(self) -> None:
        await self._client.aclose()


def _to_sdk(q: Question):
    from typesafe_sdk import Choice, Noul, Score

    if isinstance(q, NoulQ):
        return Noul(instructions=q.instructions, criteria=q.criteria)
    if isinstance(q, ChoiceQ):
        return Choice(instructions=q.instructions, criteria=q.criteria)
    return Score(instructions=q.instructions, criteria=q.criteria)


class FakeJudge:
    """Deterministic, meaningless answers. For tests, dry runs and request-count estimates only."""

    model = "fake"

    async def ask(self, state: JSON, questions: dict[str, Question]) -> Verdict:
        answers: dict[str, Answer] = {}
        for key, q in questions.items():
            rng = random.Random(request_key(self.model, state, {key: q}))
            if isinstance(q, NoulQ):
                answers[key] = NoulA(round(rng.random(), 4))
            elif isinstance(q, ChoiceQ):
                probs = _peaked(rng, list(q.criteria))
                best = max(probs, key=probs.__getitem__)
                answers[key] = ChoiceA(best, probs, _confidence(probs.values()))
            else:
                probs = _peaked(rng, list(range(len(q.criteria))))
                score = sum(level * p for level, p in probs.items())
                answers[key] = ScoreA(round(score, 4), probs, _confidence(probs.values()))
        size = len(json.dumps(state, ensure_ascii=False)) + sum(
            len(json.dumps(question_to_json(q), ensure_ascii=False)) for q in questions.values()
        )
        return Verdict(answers, input_tokens=max(1, size // 4), output_tokens=8 * len(questions))

    async def aclose(self) -> None:
        pass


def _peaked(rng: random.Random, keys: list) -> dict:
    weights = [rng.random() ** 3 for _ in keys]
    total = sum(weights) or 1.0
    return {k: round(w / total, 4) for k, w in zip(keys, weights)}


def _confidence(probs) -> float:
    ps = [p for p in probs if p > 0]
    if len(ps) <= 1:
        return 1.0
    entropy = -sum(p * math.log(p) for p in ps)
    return round(max(0.0, 1 - entropy / math.log(len(ps))), 4)


class CachingJudge:
    """Stores every verdict in sqlite, keyed on model, state and questions."""

    def __init__(self, inner: Judge, path: str | Path):
        self.inner = inner
        self.model = inner.model
        self.hits = 0
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._db = sqlite3.connect(str(path))
        self._db.execute("create table if not exists verdicts (key text primary key, body text)")

    async def ask(self, state: JSON, questions: dict[str, Question]) -> Verdict:
        key = request_key(self.model, state, questions)
        row = self._db.execute("select body from verdicts where key = ?", (key,)).fetchone()
        if row:
            self.hits += 1
            body = json.loads(row[0])
            return Verdict(
                {k: answer_from_json(v) for k, v in body["answers"].items()},
                body["input_tokens"],
                body["output_tokens"],
                cached=True,
            )
        verdict = await self.inner.ask(state, questions)
        body = {
            "answers": {k: answer_to_json(v) for k, v in verdict.answers.items()},
            "input_tokens": verdict.input_tokens,
            "output_tokens": verdict.output_tokens,
        }
        self._db.execute("insert or replace into verdicts values (?, ?)", (key, json.dumps(body)))
        self._db.commit()
        return verdict

    async def aclose(self) -> None:
        self._db.close()
        await self.inner.aclose()


class Meter:
    """Counts real requests and tokens, and refuses to go past max_requests."""

    def __init__(self, inner: Judge, max_requests: int):
        self.inner = inner
        self.model = inner.model
        self.max_requests = max_requests
        self.requests = 0
        self.input_tokens = 0
        self.output_tokens = 0

    async def ask(self, state: JSON, questions: dict[str, Question]) -> Verdict:
        if self.requests >= self.max_requests:
            raise BudgetExceeded(
                f"request budget of {self.max_requests} used up; raise --max-requests to continue"
            )
        self.requests += 1
        verdict = await self.inner.ask(state, questions)
        self.input_tokens += verdict.input_tokens
        self.output_tokens += verdict.output_tokens
        return verdict

    async def aclose(self) -> None:
        await self.inner.aclose()


class JudgeUnavailable(RuntimeError):
    pass


def build_judge(settings, cache_path: Path, max_requests: int | None = None) -> tuple[CachingJudge, Meter]:
    """The standard stack: cache in front of a budget meter in front of Jev (or the fake)."""
    if settings.fake_judge:
        inner: Judge = FakeJudge()
    elif settings.typesafe_key:
        inner = TypeSafeJudge(api_key=settings.typesafe_key, model=settings.jev_model)
    else:
        raise JudgeUnavailable("TYPESAFE_API_KEY is not set (or set JEVFISH_FAKE_JUDGE=1)")
    meter = Meter(inner, max_requests or settings.max_requests)
    return CachingJudge(meter, cache_path), meter
