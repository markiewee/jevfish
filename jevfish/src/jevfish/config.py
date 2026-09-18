"""Settings from the environment.

LLM: any OpenAI-compatible endpoint via LLM_API_KEY / LLM_BASE_URL / LLM_MODEL. If only
GEMINI_API_KEY is set, Google's OpenAI-compatible Gemini endpoint is used.
Jev: TYPESAFE_API_KEY. JEVFISH_FAKE_JUDGE=1 and JEVFISH_FAKE_LLM=1 swap in deterministic
fakes for tests and demos without keys.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from . import assets as _assets

GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"
GEMINI_MODEL = "gemini-flash-latest"
GEMINI_FALLBACKS = ["gemini-2.5-flash", "gemini-flash-lite-latest"]
GEMINI_FAST = ["gemini-flash-lite-latest", "gemini-2.5-flash-lite", "gemini-flash-latest"]


def _flag(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes"}


def env_file_path() -> Path:
    """Where keys are saved: JEVFISH_ENV_FILE, else the per-user data directory."""
    from .assets import env_file

    return env_file()


def _load_env_file() -> None:
    path = env_file_path()
    if path.exists():
        from dotenv import load_dotenv

        load_dotenv(path, override=False)


@dataclass(frozen=True)
class Settings:
    data_dir: Path
    typesafe_key: str | None
    jev_model: str
    fake_judge: bool
    llm_api_key: str | None
    llm_base_url: str | None
    llm_models: list[str] = field(default_factory=list)
    llm_fast_models: list[str] = field(default_factory=list)
    fake_llm: bool = False
    max_requests: int = 5000
    llm_workers: int = 4

    @property
    def llm_ready(self) -> bool:
        return self.fake_llm or bool(self.llm_api_key)

    @property
    def judge_ready(self) -> bool:
        return self.fake_judge or bool(self.typesafe_key)

    def health(self) -> dict:
        return {
            "app": "jevfish",
            "setup_needed": not (self.llm_ready and self.judge_ready),
            "judge": "fake" if self.fake_judge else ("jev" if self.typesafe_key else "missing TYPESAFE_API_KEY"),
            "jev_model": self.jev_model,
            "llm": "fake" if self.fake_llm else (self.llm_models[0] if self.llm_api_key else "missing LLM_API_KEY"),
            "llm_fallbacks": self.llm_models[1:],
            "llm_fast": self.llm_fast_models or self.llm_models[:1],
            "llm_base_url": self.llm_base_url,
            "data_dir": str(self.data_dir),
        }


def load_settings() -> Settings:
    _load_env_file()
    env = os.environ
    llm_key = env.get("LLM_API_KEY", "").strip() or None
    base_url = env.get("LLM_BASE_URL", "").strip() or None
    model = env.get("LLM_MODEL", "").strip() or env.get("LLM_MODEL_NAME", "").strip()
    fallbacks = [m.strip() for m in env.get("LLM_FALLBACK_MODELS", "").split(",") if m.strip()]
    fast = [m.strip() for m in env.get("LLM_FAST_MODELS", "").split(",") if m.strip()]
    if not llm_key and env.get("GEMINI_API_KEY", "").strip():
        llm_key = env["GEMINI_API_KEY"].strip()
        base_url = base_url or GEMINI_BASE_URL
        model = model or GEMINI_MODEL
        fallbacks = fallbacks or list(GEMINI_FALLBACKS)
        fast = fast or list(GEMINI_FAST)
    models = [model or "gpt-4o-mini", *[f for f in fallbacks if f != model]]
    return Settings(
        data_dir=_assets.data_dir(),
        typesafe_key=env.get("TYPESAFE_API_KEY", "").strip() or None,
        jev_model=env.get("JEV_MODEL", "").strip() or "jev-latest",
        fake_judge=_flag("JEVFISH_FAKE_JUDGE"),
        llm_api_key=llm_key,
        llm_base_url=base_url,
        llm_models=models,
        llm_fast_models=fast,
        fake_llm=_flag("JEVFISH_FAKE_LLM"),
        max_requests=int(env.get("JEVFISH_MAX_REQUESTS", "5000")),
        llm_workers=int(env.get("JEVFISH_LLM_WORKERS", "4")),
    )
