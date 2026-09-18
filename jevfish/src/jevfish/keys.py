"""Keys saved from the Setup screen, and free checks that they work.

Keys live in the .env file `config` loads (jevfish/.env unless JEVFISH_ENV_FILE says
otherwise). Saving also updates os.environ, so the running server uses them at once.
Checks cost nothing: listing models needs a valid key, and other providers get a
one-token request.
"""

from __future__ import annotations

import os
import re
from collections.abc import Mapping
from pathlib import Path

from .config import GEMINI_BASE_URL

_LINE = re.compile(r"^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=")
TIMEOUT = 15


class SetupError(ValueError):
    pass


def _quote(value: str) -> str:
    if "\n" in value or "\r" in value:
        raise SetupError("Keys cannot contain line breaks.")
    # single quotes: python-dotenv reads them literally, so $ in a key is not expanded
    return "'" + value.replace("\\", "\\\\").replace("'", "\\'") + "'"


def write_env(path: Path, updates: Mapping[str, str | None]) -> None:
    """Set (str) or remove (None) keys in a .env file. Other lines stay as they were."""
    lines = path.read_text().splitlines() if path.exists() else []
    pending = dict(updates)
    out: list[str] = []
    for line in lines:
        m = _LINE.match(line)
        if m and m.group(1) in updates:
            value = pending.pop(m.group(1), None)  # later duplicates find nothing and drop
            if value is not None:
                out.append(f"{m.group(1)}={_quote(value)}")
            continue
        out.append(line)
    out += [f"{k}={_quote(v)}" for k, v in pending.items() if v is not None]
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        f.write("\n".join(out) + ("\n" if out else ""))
    os.chmod(tmp, 0o600)
    os.replace(tmp, path)


def apply(updates: Mapping[str, str | None]) -> None:
    for key, value in updates.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value


def hint(value: str | None) -> str | None:
    """None when unset; otherwise the last four characters, or "" for short values."""
    if not value:
        return None
    return value[-4:] if len(value) >= 12 else ""


def provider(env: Mapping[str, str]) -> str:
    return "openai" if env.get("LLM_API_KEY") or env.get("LLM_BASE_URL") else "gemini"


def text(form: Mapping, name: str) -> str:
    value = form.get(name)
    return value.strip() if isinstance(value, str) else ""


def updates_from_form(form: Mapping, env: Mapping[str, str]) -> dict[str, str | None]:
    """Turn the Setup form into .env changes. A blank key field keeps the saved key."""
    updates: dict[str, str | None] = {}
    if form.get("test_mode") is not None:
        on = bool(form["test_mode"])
        updates["JEVFISH_FAKE_JUDGE"] = "1" if on else None
        updates["JEVFISH_FAKE_LLM"] = "1" if on else None
    if text(form, "typesafe_key"):
        updates["TYPESAFE_API_KEY"] = text(form, "typesafe_key")
    choice = form.get("llm_provider")
    key = text(form, "llm_key")
    if choice == "gemini":
        if not (key or env.get("GEMINI_API_KEY")):
            raise SetupError("Paste your Gemini API key.")
        if key:
            updates["GEMINI_API_KEY"] = key
        updates.update(LLM_API_KEY=None, LLM_BASE_URL=None, LLM_MODEL=None)
    elif choice == "openai":
        base, model = text(form, "llm_base_url"), text(form, "llm_model")
        if not base.startswith(("http://", "https://")):
            raise SetupError("The model address must start with http:// or https://.")
        if not model:
            raise SetupError("Name the model to use, for example gpt-4o-mini.")
        if not (key or env.get("LLM_API_KEY")):
            raise SetupError("Paste the API key for this model.")
        updates.update(LLM_BASE_URL=base, LLM_MODEL=model)
        if key:
            updates["LLM_API_KEY"] = key
    elif choice is not None:
        raise SetupError("llm_provider must be gemini or openai.")
    return updates


def _short(err: Exception) -> str:
    return str(err).split(" (request_id")[0][:200]


def check_jev(key: str, model: str = "jev-latest", client_factory=None) -> dict:
    from typesafe_sdk import TypeSafeAuthenticationError, TypeSafeClient, TypeSafeError, TypeSafePermissionDeniedError

    try:
        client = (client_factory or TypeSafeClient)(api_key=key, timeout=TIMEOUT)
        try:
            names = [m.name for m in client.models.list().models]
        finally:
            client.close()
    except (TypeSafeAuthenticationError, TypeSafePermissionDeniedError):
        return {"ok": False, "message": "TypeSafe rejected this key."}
    except TypeSafeError as e:
        return {"ok": False, "message": f"Could not check the key with TypeSafe: {_short(e)}"}
    if model not in names:
        return {"ok": False, "message": f"The key works, but {model} is not available to it."}
    return {"ok": True, "message": "Jev key works."}


def check_llm(choice: str, key: str, base_url: str | None = None, model: str | None = None, client_factory=None) -> dict:
    from openai import APIConnectionError, APIStatusError, OpenAI

    make = client_factory or OpenAI
    try:
        if choice == "gemini":
            make(api_key=key, base_url=GEMINI_BASE_URL, timeout=TIMEOUT, max_retries=0).models.list()
        else:
            make(api_key=key, base_url=base_url, timeout=TIMEOUT, max_retries=0).chat.completions.create(
                model=model, messages=[{"role": "user", "content": "Say OK"}], max_tokens=1)
    except APIStatusError as e:
        who = "Google" if choice == "gemini" else "The provider"
        if e.status_code in (401, 403) or (choice == "gemini" and e.status_code == 400):
            return {"ok": False, "message": f"{who} rejected this key."}
        if e.status_code == 404:
            return {"ok": False, "message": f"The provider has no model called {model}."}
        return {"ok": False, "message": f"{who} refused the test request (HTTP {e.status_code}): {_short(e)}"}
    except APIConnectionError:  # includes timeouts
        return {"ok": False, "message": f"Could not reach {base_url or GEMINI_BASE_URL}."}
    return {"ok": True, "message": "Gemini key works." if choice == "gemini" else f"{model} answered."}
