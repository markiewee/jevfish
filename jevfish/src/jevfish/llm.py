"""The writing model. Used only where text has to be produced: extracting the graph,
writing personas and the frame, phrasing posts Jev decided to make, the report narrative,
and chatting with a simulated person.

Every call names its task (`task=`), which the fake LLM uses to return canned output.
"""

from __future__ import annotations

import json
import random
import re
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Protocol

Messages = list[dict[str, str]]
RETRYABLE_STATUS = {408, 409, 429, 500, 502, 503, 504}


class LLMError(RuntimeError):
    pass


class LLM(Protocol):
    def chat(self, task: str, messages: Messages, *, temperature: float = 0.7, max_tokens: int | None = None) -> str: ...

    def json(self, task: str, messages: Messages, *, temperature: float = 0.3) -> Any: ...


def parse_json(text: str) -> Any:
    """Parse a JSON object or array out of model output, tolerating code fences and prose."""
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip(), flags=re.S)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass
    starts = [i for i in (cleaned.find("{"), cleaned.find("[")) if i >= 0]
    if not starts:
        raise LLMError("no JSON in model output")
    start = min(starts)
    end = max(cleaned.rfind("}"), cleaned.rfind("]"))
    try:
        return json.loads(cleaned[start : end + 1])
    except json.JSONDecodeError as e:
        raise LLMError(f"invalid JSON in model output: {e}") from e


@dataclass
class Usage:
    calls: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    failures: int = 0
    truncated: int = 0
    by_task: dict[str, int] = field(default_factory=dict)
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def add(self, task: str, prompt: int, completion: int) -> None:
        with self._lock:
            self.calls += 1
            self.prompt_tokens += prompt
            self.completion_tokens += completion
            self.by_task[task] = self.by_task.get(task, 0) + 1

    def to_dict(self) -> dict:
        return {
            "calls": self.calls,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "failures": self.failures,
            "truncated": self.truncated,
            "by_task": dict(self.by_task),
        }


class OpenAILLM:
    def __init__(
        self,
        api_key: str,
        base_url: str | None,
        models: list[str],
        *,
        timeout: float = 120,
        max_attempts: int = 5,
        sleep: Callable[[float], None] = time.sleep,
        http_client: Any = None,
    ):
        from openai import OpenAI

        self.client = OpenAI(api_key=api_key, base_url=base_url, timeout=timeout, max_retries=0, http_client=http_client)
        self.models = models
        self.max_attempts = max_attempts
        self.sleep = sleep
        self.usage = Usage()

    def _complete(self, task: str, messages: Messages, *, json_mode: bool, temperature: float, max_tokens: int | None) -> str:
        from openai import APIConnectionError, APIStatusError, APITimeoutError

        last: Exception | None = None
        for attempt in range(self.max_attempts):
            model = self.models[attempt % len(self.models)]  # rotate through fallbacks
            kwargs: dict[str, Any] = {"model": model, "messages": messages, "temperature": temperature}
            if max_tokens:
                kwargs["max_tokens"] = max_tokens
            if json_mode:
                kwargs["response_format"] = {"type": "json_object"}
            try:
                response = self.client.chat.completions.create(**kwargs)
                choice = response.choices[0]
                content = (choice.message.content or "").strip()
                if not content:
                    raise LLMError(f"{model} returned an empty message")
                if choice.finish_reason == "length" and not json_mode:
                    self.usage.truncated += 1
                usage = getattr(response, "usage", None)
                self.usage.add(task, getattr(usage, "prompt_tokens", 0) or 0, getattr(usage, "completion_tokens", 0) or 0)
                return content
            except APIStatusError as e:
                last = e
                if e.status_code not in RETRYABLE_STATUS and e.status_code != 404:
                    raise LLMError(f"{model}: HTTP {e.status_code}: {e.message}") from e
            except (APIConnectionError, APITimeoutError, LLMError) as e:
                last = e
            self.usage.failures += 1
            self.sleep(min(20.0, 1.5 * 2**attempt) + random.random())
        raise LLMError(f"{task}: all attempts failed; last error: {last}")

    def chat(self, task: str, messages: Messages, *, temperature: float = 0.7, max_tokens: int | None = None) -> str:
        text = self._complete(task, messages, json_mode=False, temperature=temperature, max_tokens=max_tokens)
        return re.sub(r"<think>.*?</think>", "", text, flags=re.S).strip()

    def json(self, task: str, messages: Messages, *, temperature: float = 0.3) -> Any:
        text = self._complete(task, messages, json_mode=True, temperature=temperature, max_tokens=None)
        try:
            return parse_json(text)
        except LLMError:
            retry = messages + [
                {"role": "assistant", "content": text[:2000]},
                {"role": "user", "content": "That was not valid JSON. Reply with the JSON only."},
            ]
            return parse_json(self._complete(task, retry, json_mode=True, temperature=0.0, max_tokens=None))


Handler = Callable[[Messages], Any]


class FakeLLM:
    """Deterministic stand-in. `handlers` maps a task name to a function of the messages."""

    def __init__(self, handlers: dict[str, Handler] | None = None):
        from . import fakes

        self.handlers = {**fakes.HANDLERS, **(handlers or {})}
        self.usage = Usage()
        self.calls: list[tuple[str, Messages]] = []

    def _answer(self, task: str, messages: Messages) -> Any:
        self.calls.append((task, messages))
        self.usage.add(task, sum(len(m["content"]) for m in messages) // 4, 50)
        if task not in self.handlers:
            raise LLMError(f"FakeLLM has no handler for task '{task}'")
        return self.handlers[task](messages)

    def chat(self, task: str, messages: Messages, *, temperature: float = 0.7, max_tokens: int | None = None) -> str:
        out = self._answer(task, messages)
        return out if isinstance(out, str) else json.dumps(out)

    def json(self, task: str, messages: Messages, *, temperature: float = 0.3) -> Any:
        out = self._answer(task, messages)
        return parse_json(out) if isinstance(out, str) else out


def build_llm(settings) -> LLM:
    if settings.fake_llm:
        return FakeLLM()
    if not settings.llm_api_key:
        raise LLMError("no LLM configured: set LLM_API_KEY (or GEMINI_API_KEY), or JEVFISH_FAKE_LLM=1")
    return OpenAILLM(settings.llm_api_key, settings.llm_base_url, settings.llm_models)
