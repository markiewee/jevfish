import json

import httpx
import pytest

from jevfish.llm import FakeLLM, LLMError, OpenAILLM, parse_json


def test_parse_json_tolerates_fences_and_prose():
    assert parse_json('```json\n{"a": 1}\n```') == {"a": 1}
    assert parse_json('Sure! Here it is: {"a": [1, 2]} hope that helps') == {"a": [1, 2]}
    assert parse_json("[1, 2]") == [1, 2]
    with pytest.raises(LLMError):
        parse_json("no json here")


def make(responses, models=("m1", "m2")):
    seen = []

    def handler(request):
        body = json.loads(request.content)
        seen.append(body)
        status, content = responses.pop(0)
        if status != 200:
            return httpx.Response(status, json={"error": {"message": "busy", "code": status}})
        return httpx.Response(200, json={
            "id": "x", "object": "chat.completion", "created": 0, "model": body["model"],
            "choices": [{"index": 0, "finish_reason": "stop", "message": {"role": "assistant", "content": content}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
        })

    llm = OpenAILLM("k", "http://llm.test/v1", list(models), sleep=lambda s: None,
                    http_client=httpx.Client(transport=httpx.MockTransport(handler)))
    return llm, seen


def test_retries_rotate_models_on_overload():
    llm, seen = make([(503, None), (429, None), (200, "hello")])
    assert llm.chat("t", [{"role": "user", "content": "hi"}]) == "hello"
    assert [b["model"] for b in seen] == ["m1", "m2", "m1"]
    assert llm.usage.failures == 2 and llm.usage.calls == 1 and llm.usage.by_task == {"t": 1}


def test_json_mode_and_repair():
    llm, seen = make([(200, "not json at all"), (200, '{"ok": true}')])
    assert llm.json("t", [{"role": "user", "content": "x"}]) == {"ok": True}
    assert seen[0]["response_format"] == {"type": "json_object"}
    assert seen[1]["messages"][-1]["content"].startswith("That was not valid JSON")


def test_non_retryable_error_raises_immediately():
    llm, seen = make([(401, None)])
    with pytest.raises(LLMError, match="HTTP 401"):
        llm.chat("t", [{"role": "user", "content": "x"}])
    assert len(seen) == 1


def test_gives_up_after_max_attempts():
    llm, seen = make([(503, None)] * 5)
    with pytest.raises(LLMError, match="all attempts failed"):
        llm.chat("t", [{"role": "user", "content": "x"}])
    assert len(seen) == 5


def test_think_tags_are_stripped():
    llm, _ = make([(200, "<think>hmm</think>Answer")])
    assert llm.chat("t", [{"role": "user", "content": "x"}]) == "Answer"


def test_fake_llm_dispatches_by_task():
    fake = FakeLLM({"echo": lambda m: {"said": m[-1]["content"]}})
    assert fake.json("echo", [{"role": "user", "content": "hi"}]) == {"said": "hi"}
    with pytest.raises(LLMError, match="no handler"):
        fake.chat("unknown", [])
