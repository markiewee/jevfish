import json

import httpx2
import pytest

from jevfish.judge import (
    BudgetExceeded,
    CachingJudge,
    ChoiceA,
    ChoiceQ,
    FakeJudge,
    Meter,
    NoulA,
    NoulQ,
    ScoreA,
    ScoreQ,
    TypeSafeJudge,
    Verdict,
    question_to_json,
)

QUESTIONS = {
    "urgent": NoulQ("Is `ticket` urgent?", {"true": "time sensitive", "false": "can wait"}),
    "team": ChoiceQ("Which team handles `ticket`?", {"billing": "payments", "tech": None}),
    "anger": ScoreQ("How angry is `ticket`?", ["calm", "annoyed", "furious"]),
}
STATE = {"ticket": "I was charged twice and nobody replies!"}


def test_question_to_json_matches_http_api_shape():
    assert question_to_json(QUESTIONS["urgent"]) == {
        "type": "noul",
        "instructions": "Is `ticket` urgent?",
        "criteria": {"true": "time sensitive", "false": "can wait"},
    }
    assert question_to_json(NoulQ("x")) == {"type": "noul", "instructions": "x"}
    assert question_to_json(QUESTIONS["team"])["criteria"] == {"billing": "payments", "tech": None}
    assert question_to_json(QUESTIONS["anger"]) == {
        "type": "score",
        "instructions": "How angry is `ticket`?",
        "criteria": ["calm", "annoyed", "furious"],
    }


async def test_fake_judge_is_deterministic_and_valid():
    judge = FakeJudge()
    a = await judge.ask(STATE, QUESTIONS)
    b = await judge.ask(STATE, QUESTIONS)
    assert a.answers == b.answers
    assert 0 <= a.answers["urgent"].p <= 1
    team = a.answers["team"]
    assert team.choice in {"billing", "tech"}
    assert sum(team.probabilities.values()) == pytest.approx(1)
    assert team.probabilities[team.choice] == max(team.probabilities.values())
    anger = a.answers["anger"]
    assert set(anger.probabilities) == {0, 1, 2}
    assert anger.score == pytest.approx(sum(k * v for k, v in anger.probabilities.items()))
    assert a.input_tokens > 0


async def test_fake_judge_differs_by_state():
    judge = FakeJudge()
    a = await judge.ask({"ticket": "one"}, QUESTIONS)
    b = await judge.ask({"ticket": "two"}, QUESTIONS)
    assert a.answers != b.answers


class CountingJudge:
    model = "count"

    def __init__(self):
        self.calls = 0

    async def ask(self, state, questions):
        self.calls += 1
        return Verdict(
            answers={
                "urgent": NoulA(0.7),
                "team": ChoiceA("tech", {"billing": 0.2, "tech": 0.8}, 0.5),
                "anger": ScoreA(1.2, {0: 0.1, 1: 0.6, 2: 0.3}, 0.4),
            },
            input_tokens=10,
            output_tokens=2,
        )

    async def aclose(self):
        pass


async def test_caching_judge_reuses_answers(tmp_path):
    inner = CountingJudge()
    judge = CachingJudge(inner, tmp_path / "cache.sqlite")
    first = await judge.ask(STATE, QUESTIONS)
    second = await judge.ask(STATE, QUESTIONS)
    assert inner.calls == 1
    assert not first.cached and second.cached
    assert second.answers == first.answers
    await judge.aclose()
    reopened = CachingJudge(CountingJudge(), tmp_path / "cache.sqlite")
    third = await reopened.ask(STATE, QUESTIONS)
    assert third.cached and third.answers == first.answers
    await reopened.aclose()


async def test_meter_counts_and_enforces_budget():
    meter = Meter(CountingJudge(), max_requests=2)
    await meter.ask(STATE, QUESTIONS)
    await meter.ask(STATE, QUESTIONS)
    assert meter.requests == 2
    assert meter.input_tokens == 20 and meter.output_tokens == 4
    with pytest.raises(BudgetExceeded):
        await meter.ask(STATE, QUESTIONS)


async def test_cache_in_front_of_meter_does_not_charge_hits(tmp_path):
    meter = Meter(CountingJudge(), max_requests=1)
    judge = CachingJudge(meter, tmp_path / "c.sqlite")
    await judge.ask(STATE, QUESTIONS)
    await judge.ask(STATE, QUESTIONS)
    assert meter.requests == 1 and judge.hits == 1


async def test_typesafe_judge_sends_api_body_and_converts_answers():
    seen = {}

    def handler(request: httpx2.Request) -> httpx2.Response:
        seen["url"] = str(request.url)
        seen["auth"] = request.headers.get("authorization")
        seen["body"] = json.loads(request.content)
        return httpx2.Response(
            200,
            json={
                "model": "jev-latest",
                "answers": {
                    "urgent": {"type": "noul", "noul": 0.9},
                    "team": {
                        "type": "choice",
                        "choice": "billing",
                        "probabilities": {"billing": 0.85, "tech": 0.15},
                        "confidence": 0.7,
                    },
                    "anger": {
                        "type": "score",
                        "score": 1.6,
                        "legend": {"0": "calm", "1": "annoyed", "2": "furious"},
                        "probabilities": {"0": 0.05, "1": 0.3, "2": 0.65},
                        "confidence": 0.6,
                    },
                },
                "usage": {"input_tokens": 312, "output_tokens": 48},
            },
        )

    judge = TypeSafeJudge(api_key="sk-test", transport=httpx2.MockTransport(handler))
    verdict = await judge.ask(STATE, QUESTIONS)
    await judge.aclose()

    assert seen["url"].endswith("/v1/systemone")
    assert seen["auth"] == "Bearer sk-test"
    assert seen["body"]["model"] == "jev-latest"
    assert seen["body"]["state"] == STATE
    assert seen["body"]["questions"]["team"]["type"] == "choice"
    assert verdict.answers["urgent"] == NoulA(0.9)
    assert verdict.answers["team"] == ChoiceA("billing", {"billing": 0.85, "tech": 0.15}, 0.7)
    assert verdict.answers["anger"] == ScoreA(1.6, {0: 0.05, 1: 0.3, 2: 0.65}, 0.6)
    assert (verdict.input_tokens, verdict.output_tokens) == (312, 48)
