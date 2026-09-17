# JevFish One-Click Mac App Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Anyone on a Mac can start JevFish by double-clicking `JevFish.app` and do everything else, keys included, in the web app. No terminal.

**Architecture:** `JevFish.app` is a tiny shell-script bundle at the repo root. It finds the repo and runs `jevfish/launcher/launch.sh`. That script installs uv and the Python packages if they are missing, reuses or starts the Flask server on a free port, and opens the browser. The web app gains a Setup screen that saves keys to `jevfish/.env`, checks them with free API calls, and hot-reloads the running server. The built web app is committed, so Node is not needed to run it.

**Tech stack:** bash and osascript for the launcher; Flask blueprint, python-dotenv, typesafe-sdk and openai for setup; Vue 3 and Vite for the screen; pytest.

**Approval:** On 17 Sep 2026 Mark said "for jev fish make it with jaust a ui and one click setup". He then picked a Mac app with no Terminal window, Macs only, and keeping the upstream code, and set the goal "build jevfish". The first JevFish build used the same pattern: a build goal counted as approval, and the PRD and PR summary went to Mark inline with the result.

---

## PRD

### Problem
Running JevFish today means opening a terminal and typing eight commands: `uv sync`, `npm install`, `npm run build`, two key exports and `uv run jevfish serve`. Keys only come from environment variables, and without them the app shows a warning with no way to fix it. Kavi and Trisha cannot start it without help, and Mark cannot start it from Finder.

### Users
Mark, Kavi, Trisha, and anyone else on a Mac who gets the repo, either as a git clone or as the GitHub ZIP.

### Requirements
1. **One click to start.** Double-clicking `JevFish.app` in the repo folder opens JevFish in the default browser.
   - First start: installs uv if missing, into `~/Library/Application Support/JevFish/bin`, with no admin password. Then installs the Python packages, about 1 GB. Needs internet only; no Xcode, no Homebrew, no Node.
   - Later starts: a few seconds. If JevFish is already running, it opens the existing server instead of starting another.
   - Picks the first free port from 5055 to 5064.
   - Failures show a macOS alert in plain words with a "Show log" button. Logs go to `~/Library/Logs/JevFish/`.
   - Still works when the app was moved out of the folder (it remembers the repo path) and when macOS runs a downloaded copy from a temporary path (it finds the folder with Spotlight).
2. **Setup in the app.** Opening the app with keys missing lands on a Setup screen.
   - Jev: the TypeSafe API key.
   - Language model: Gemini (key only) or any other OpenAI-compatible model (address, model name, key).
   - One button, "Save and check". It saves to `jevfish/.env` (mode 600, gitignored), applies at once without a restart, and checks both keys with free calls: listing models for Jev and Gemini, and a one-token request for other providers.
   - Saved keys are never sent back to the browser, only their last four characters.
   - Test mode on or off (fake Jev and fake model), for trying the UI without keys.
   - "Stop JevFish" shuts the server down.
   - Settings stay reachable from the header.
3. **Example in the app.** "Fill in the example" on the new-prediction form loads the Lazybee example that `jevfish demo` uses.
4. **Safety.** The API only answers when the Host is the local machine, which blocks DNS rebinding. Changing requests from another website's Origin are refused. `serve --host 0.0.0.0` turns the guard off on purpose and prints a warning.
5. **No regressions.** The CLI (`serve`, `demo`), env-var configuration and all 60 existing tests keep working.

### Out of scope
- Windows and Linux launchers.
- Code signing and notarisation. These need a paid Apple Developer account.
- Auto-update.
- A native window. It opens in the browser.
- Moving existing project data.

### Known limit
A copy downloaded as a ZIP is quarantined by macOS. The first open is blocked with "Apple could not verify". The user goes once to System Settings, Privacy & Security, Open Anyway. The README says so. Git clones are not affected.

### Success check
- On this Mac, from a fresh local clone with an empty state folder and uv hidden from PATH, a double-click (`open JevFish.app`) installs uv and the packages, opens the Setup screen, saves real keys, both checks pass, and a test-mode project runs end to end.
- `uv run pytest -q` passes, including the new setup, env-file and launcher tests.
- Headless Chrome QA of the Setup screen at 375, 768 and 1280 wide, in light and dark, shows no console errors and no horizontal scroll.

---

## File structure

| File | Change | Responsibility |
| --- | --- | --- |
| `jevfish/src/jevfish/config.py` | modify | `env_file_path()`, health gains `app` and `setup_needed` |
| `jevfish/src/jevfish/keys.py` | create | read and write the .env file, turn the setup form into changes, check keys |
| `jevfish/src/jevfish/example.py` | create | the Lazybee example, shared by the CLI and the API |
| `jevfish/src/jevfish/setup_api.py` | create | Flask blueprint for `/api/settings`, `/api/settings/check`, `/api/example`, `/api/shutdown`; the local-only guard |
| `jevfish/src/jevfish/service.py` | modify | `Service.reload()` |
| `jevfish/src/jevfish/api.py` | modify | use `svc.settings`, register the blueprint and guard |
| `jevfish/src/jevfish/cli.py` | modify | use `example.py`, allow remote when host is not loopback |
| `jevfish/tests/test_keys.py` | create | env file and form tests, key checks with fake clients |
| `jevfish/tests/test_setup_api.py` | create | endpoint tests |
| `jevfish/tests/test_launcher.py` | create | launcher and app bundle tests with fake uv and a fake server |
| `jevfish/web/src/lib/api.js` | modify | new calls |
| `jevfish/web/src/lib/health.js` | create | shared health state |
| `jevfish/web/src/views/SetupView.vue` | create | Setup screen |
| `jevfish/web/src/router.js` | modify | `/setup` route, first-load redirect |
| `jevfish/web/src/App.vue` | modify | Settings link, banners link to setup |
| `jevfish/web/src/views/ProjectsView.vue` | modify | "Fill in the example" |
| `jevfish/web/dist/` | commit | built app |
| `jevfish/.gitignore` | modify | stop ignoring `web/dist/` |
| `jevfish/launcher/launch.sh` | create | install, start, open |
| `jevfish/launcher/jevfish-folder-marker` | create | lets Spotlight find the folder |
| `jevfish/launcher/make-icon.sh` | create | rebuilds `AppIcon.icns` from the logo |
| `JevFish.app/Contents/{Info.plist,MacOS/JevFish,Resources/AppIcon.icns}` | create | the double-click app |
| `.github/workflows/jevfish-web.yml` | create | fails when `web/dist` is stale |
| `README.md`, `jevfish/README.md`, `jevfish/docs/api.md` | modify | docs |

---

### Task 1: Config, env file path and health fields

**Files:**
- Modify: `jevfish/src/jevfish/config.py`
- Test: `jevfish/tests/test_keys.py`

- [ ] **Step 1: Write the failing test**

```python
# jevfish/tests/test_keys.py
from jevfish.config import env_file_path, load_settings
from tests.test_pipeline import settings


def test_env_file_path_follows_env(tmp_path, monkeypatch):
    monkeypatch.setenv("JEVFISH_ENV_FILE", str(tmp_path / "x.env"))
    assert env_file_path() == tmp_path / "x.env"


def test_health_reports_app_and_setup_needed(tmp_path):
    ready = settings(tmp_path).health()
    assert ready["app"] == "jevfish" and ready["setup_needed"] is False
    missing = settings(tmp_path, fake_judge=False, fake_llm=False).health()
    assert missing["setup_needed"] is True
```

- [ ] **Step 2: Run it and see it fail**

Run: `cd jevfish && uv run pytest tests/test_keys.py -q`
Expected: FAIL, `ImportError: cannot import name 'env_file_path'`.

- [ ] **Step 3: Implement**

In `config.py`, replace `_load_env_file` with:

```python
def env_file_path() -> Path:
    """Where keys are saved: JEVFISH_ENV_FILE, else jevfish/.env."""
    return Path(os.environ.get("JEVFISH_ENV_FILE") or PACKAGE_ROOT / ".env")


def _load_env_file() -> None:
    path = env_file_path()
    if path.exists():
        from dotenv import load_dotenv

        load_dotenv(path, override=False)
```

and make `health()` start with:

```python
        return {
            "app": "jevfish",
            "setup_needed": not (self.llm_ready and self.judge_ready),
            "judge": ...  # unchanged from here
```

- [ ] **Step 4: Run it and see it pass**

Run: `uv run pytest tests/test_keys.py -q`. Expected: 2 passed.

- [ ] **Step 5: Commit**

`git commit -am "feat(jevfish): env file path and setup_needed in health"`

### Task 2: keys.py, the env file and key checks

**Files:**
- Create: `jevfish/src/jevfish/keys.py`
- Test: `jevfish/tests/test_keys.py` (append)

- [ ] **Step 1: Write the failing tests**

```python
import os
import stat

import pytest
from dotenv import dotenv_values

from jevfish import keys
from jevfish.keys import SetupError, updates_from_form, write_env


def test_write_env_keeps_other_lines_and_round_trips(tmp_path):
    path = tmp_path / ".env"
    path.write_text("# mine\nOTHER=1\nTYPESAFE_API_KEY=old\nTYPESAFE_API_KEY=dupe\nJEVFISH_FAKE_LLM=1\n")
    tricky = "k'e\\y$HOME\"x"
    write_env(path, {"TYPESAFE_API_KEY": tricky, "JEVFISH_FAKE_LLM": None, "GEMINI_API_KEY": "g123"})
    text = path.read_text()
    assert text.startswith("# mine\nOTHER=1\n")
    assert text.count("TYPESAFE_API_KEY") == 1 and "JEVFISH_FAKE_LLM" not in text
    values = dotenv_values(path)
    assert values["TYPESAFE_API_KEY"] == tricky and values["GEMINI_API_KEY"] == "g123" and values["OTHER"] == "1"
    assert stat.S_IMODE(os.stat(path).st_mode) == 0o600


def test_write_env_rejects_newlines(tmp_path):
    with pytest.raises(SetupError):
        write_env(tmp_path / ".env", {"TYPESAFE_API_KEY": "a\nb"})


def test_form_gemini_blank_key_keeps_saved():
    env = {"GEMINI_API_KEY": "saved"}
    assert updates_from_form({"llm_provider": "gemini", "llm_key": " "}, env) == {
        "LLM_API_KEY": None, "LLM_BASE_URL": None, "LLM_MODEL": None}
    with pytest.raises(SetupError):
        updates_from_form({"llm_provider": "gemini"}, {})


def test_form_openai_needs_address_model_and_key():
    form = {"llm_provider": "openai", "llm_base_url": "https://api.openai.com/v1", "llm_model": "gpt-4o-mini", "llm_key": "sk-1"}
    assert updates_from_form(form, {}) == {"LLM_BASE_URL": "https://api.openai.com/v1", "LLM_MODEL": "gpt-4o-mini", "LLM_API_KEY": "sk-1"}
    for bad in ({"llm_base_url": "ftp://x"}, {"llm_model": ""}, {"llm_key": ""}):
        with pytest.raises(SetupError):
            updates_from_form({**form, **bad}, {})


def test_form_test_mode_and_jev_key():
    assert updates_from_form({"test_mode": True, "typesafe_key": " ts "}, {}) == {
        "JEVFISH_FAKE_JUDGE": "1", "JEVFISH_FAKE_LLM": "1", "TYPESAFE_API_KEY": "ts"}
    assert updates_from_form({"test_mode": False}, {}) == {"JEVFISH_FAKE_JUDGE": None, "JEVFISH_FAKE_LLM": None}
    with pytest.raises(SetupError):
        updates_from_form({"llm_provider": "claude"}, {})


def test_hint_shows_only_last_four():
    assert keys.hint(None) is None
    assert keys.hint("short") == ""
    assert keys.hint("abcdefghijkl1234") == "1234"


class _Models:
    def __init__(self, result):
        self.result = result

    def list(self):
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


def test_check_jev_maps_errors():
    from typesafe_sdk import TypeSafeAuthenticationError

    class Model:
        def __init__(self, name):
            self.name = name

    class Listing:
        models = (Model("jev-latest"),)

    def factory(result):
        class Client:
            def __init__(self, **kw):
                self.models = _Models(result)

            def close(self):
                pass
        return Client

    assert keys.check_jev("k", client_factory=factory(Listing()))["ok"] is True
    assert keys.check_jev("k", "jev-9", client_factory=factory(Listing()))["ok"] is False
    err = TypeSafeAuthenticationError.__new__(TypeSafeAuthenticationError)
    Exception.__init__(err, "401")
    bad = keys.check_jev("k", client_factory=factory(err))
    assert bad == {"ok": False, "message": "TypeSafe rejected this key."}


def test_check_llm_gemini_and_openai():
    import httpx
    from openai import AuthenticationError, BadRequestError

    req = httpx.Request("GET", "https://x")

    def err(cls, code):
        return cls("no", response=httpx.Response(code, request=req), body=None)

    class Gemini:
        def __init__(self, result):
            self.result = result

        def __call__(self, **kw):
            self.kw = kw
            self.models = _Models(self.result)
            return self

    ok = keys.check_llm("gemini", "g", client_factory=Gemini([]))
    assert ok["ok"] is True
    assert keys.check_llm("gemini", "g", client_factory=Gemini(err(BadRequestError, 400)))["message"] == "Google rejected this key."

    class Chat:
        def __init__(self, result):
            self.result = result
            self.completions = self

        def create(self, **kw):
            self.kw = kw
            if isinstance(self.result, Exception):
                raise self.result
            return self.result

    class Other:
        def __init__(self, result):
            self.chat = Chat(result)

        def __call__(self, **kw):
            return self

    good = Other(object())
    assert keys.check_llm("openai", "k", "https://x/v1", "m", client_factory=good)["ok"] is True
    assert good.chat.kw["max_tokens"] == 1 and good.chat.kw["model"] == "m"
    assert keys.check_llm("openai", "k", "https://x/v1", "m", client_factory=Other(err(AuthenticationError, 401)))["message"] == "The provider rejected this key."
```

- [ ] **Step 2: Run them and see them fail**

Run: `uv run pytest tests/test_keys.py -q`. Expected: FAIL, `ImportError: cannot import name 'keys'`.

- [ ] **Step 3: Implement `keys.py`**

```python
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
    except APIConnectionError:
        return {"ok": False, "message": f"Could not reach {base_url or GEMINI_BASE_URL}."}
    return {"ok": True, "message": "Gemini key works." if choice == "gemini" else f"{model} answered."}
```

Note: `APITimeoutError` is a subclass of `APIConnectionError`, so one `except` covers both.

- [ ] **Step 4: Run and pass**

Run: `uv run pytest tests/test_keys.py -q`. Expected: all pass.

- [ ] **Step 5: Commit**

`git add src/jevfish/keys.py tests/test_keys.py && git commit -m "feat(jevfish): save keys to .env and check them for free"`

### Task 3: The example module and Service.reload

**Files:**
- Create: `jevfish/src/jevfish/example.py`
- Modify: `jevfish/src/jevfish/cli.py`, `jevfish/src/jevfish/service.py`
- Test: `jevfish/tests/test_setup_api.py` (created in Task 4; the reload test goes there)

- [ ] **Step 1: Create `example.py`**

```python
"""The example project: made-up figures for a Singapore co-living brand."""

from __future__ import annotations

from .config import PACKAGE_ROOT

PATH = PACKAGE_ROOT / "examples" / "lazybee-cleaning.md"
NAME = "Lazybee cleaning upgrade (example)"
QUESTION = ("If Lazybee adds weekly professional cleaning for S$100 more a month (example figure), "
            "will more Singapore renters book a viewing?")


def example() -> dict:
    return {"name": NAME, "requirement": QUESTION, "seed_text": PATH.read_text()}
```

- [ ] **Step 2: Point `cli.py` at it**

Replace `EXAMPLE = PACKAGE_ROOT / "examples" / "lazybee-cleaning.md"` with `from . import example`, and use `example.PATH`, `example.NAME` and `example.QUESTION` as the `demo` defaults.

- [ ] **Step 3: Add `Service.reload`**

In `Service.__init__`, add `self._llm_injected = llm is not None`. Then add:

```python
    def reload(self, settings: Settings) -> None:
        """Use new keys from now on. Tasks already running keep what they started with.
        The data folder never changes while the server runs."""
        self.settings = replace(settings, data_dir=self.settings.data_dir)
        if not self._llm_injected:
            self._llm = None

    def active_tasks(self) -> int:
        return sum(1 for t in self.tasks.list() if t.status in ("queued", "running"))
```

with `from dataclasses import replace` at the top.

- [ ] **Step 4: Run the existing suite**

Run: `uv run pytest -q`. Expected: all pass (60 plus Task 1 and 2 tests).

- [ ] **Step 5: Commit**

`git commit -am "refactor(jevfish): shared example, Service.reload"`

### Task 4: Setup API and the local-only guard

**Files:**
- Create: `jevfish/src/jevfish/setup_api.py`
- Modify: `jevfish/src/jevfish/api.py`, `jevfish/src/jevfish/cli.py`
- Test: `jevfish/tests/test_setup_api.py`

- [ ] **Step 1: Write the failing tests**

```python
import os

import pytest

from jevfish import keys
from jevfish.api import create_app
from jevfish.llm import FakeLLM
from jevfish.service import Service
from tests.test_pipeline import settings

MANAGED = ("TYPESAFE_API_KEY", "GEMINI_API_KEY", "LLM_API_KEY", "LLM_BASE_URL", "LLM_MODEL", "LLM_MODEL_NAME",
           "JEVFISH_FAKE_JUDGE", "JEVFISH_FAKE_LLM", "JEVFISH_DATA_DIR")


@pytest.fixture
def env_file(tmp_path):
    # saving settings edits os.environ directly, so snapshot and restore all of it
    before = dict(os.environ)
    for k in MANAGED:
        os.environ.pop(k, None)
    path = tmp_path / "keys.env"
    os.environ["JEVFISH_ENV_FILE"] = str(path)
    yield path
    os.environ.clear()
    os.environ.update(before)


@pytest.fixture
def app(tmp_path, env_file):
    s = settings(tmp_path, fake_judge=False, fake_llm=False)
    stopped = []
    app = create_app(s, Service(s, llm=FakeLLM()))
    app.config["JEVFISH_STOP"] = lambda: stopped.append(True)
    app.stopped = stopped
    return app


def test_first_run_needs_setup_then_save_applies_without_restart(app, env_file, tmp_path):
    c = app.test_client()
    assert c.get("/api/health").get_json()["setup_needed"] is True
    got = c.get("/api/settings").get_json()
    assert got["typesafe_key"] is None and got["llm_provider"] == "gemini" and got["setup_needed"] is True
    r = c.put("/api/settings", json={"typesafe_key": "ts-abcdefgh9999", "llm_provider": "gemini", "llm_key": "gm-abcdefgh7777"})
    assert r.status_code == 200, r.get_json()
    body = r.get_json()
    assert body["typesafe_key"] == "9999" and body["gemini_key"] == "7777" and body["setup_needed"] is False
    assert "ts-abcdefgh9999" not in r.get_data(as_text=True)
    assert "TYPESAFE_API_KEY='ts-abcdefgh9999'" in env_file.read_text()
    health = c.get("/api/health").get_json()
    assert health["judge"] == "jev" and health["setup_needed"] is False
    assert health["data_dir"] == str(tmp_path / "data")


def test_test_mode_toggle(app):
    c = app.test_client()
    assert c.put("/api/settings", json={"test_mode": True}).get_json()["test_mode"] is True
    assert c.get("/api/health").get_json()["judge"] == "fake"
    assert c.put("/api/settings", json={"test_mode": False}).get_json()["test_mode"] is False
    assert c.get("/api/health").get_json()["setup_needed"] is True


def test_bad_form_is_400(app):
    r = app.test_client().put("/api/settings", json={"llm_provider": "openai", "llm_base_url": "nope"})
    assert r.status_code == 400 and "http" in r.get_json()["error"]


def test_check_uses_form_keys_then_saved(app, monkeypatch):
    calls = []
    monkeypatch.setattr(keys, "check_jev", lambda key, model="jev-latest": calls.append(("jev", key)) or {"ok": True, "message": "j"})
    monkeypatch.setattr(keys, "check_llm", lambda choice, key, base_url=None, model=None: calls.append((choice, key)) or {"ok": False, "message": "l"})
    c = app.test_client()
    r = c.post("/api/settings/check", json={"typesafe_key": "typed", "llm_provider": "gemini"}).get_json()
    assert r["jev"]["ok"] is True and r["llm"] == {"ok": False, "message": "No Gemini key yet."}
    assert calls == [("jev", "typed")]
    monkeypatch.setenv("GEMINI_API_KEY", "saved-g")
    c.post("/api/settings/check", json={})
    assert calls[-1] == ("gemini", "saved-g")


def test_example_and_shutdown(app):
    c = app.test_client()
    ex = c.get("/api/example").get_json()
    assert "Lazybee" in ex["name"] and ex["seed_text"].strip() and ex["requirement"].endswith("?")
    assert c.post("/api/shutdown").get_json()["ok"] is True
    import time
    time.sleep(0.5)
    assert app.stopped == [True]


def test_guard_blocks_other_hosts_and_origins(app):
    c = app.test_client()
    assert c.get("/api/health", headers={"Host": "evil.example"}).status_code == 403
    assert c.get("/api/health", headers={"Host": "127.0.0.1:5055"}).status_code == 200
    assert c.put("/api/settings", json={"test_mode": True}, headers={"Origin": "https://evil.example"}).status_code == 403
    assert c.put("/api/settings", json={"test_mode": True}, headers={"Origin": "http://localhost:5173"}).status_code == 200
    assert c.get("/", headers={"Host": "evil.example"}).status_code == 200  # the page itself holds no data


def test_guard_can_be_turned_off(tmp_path, env_file):
    s = settings(tmp_path)
    app = create_app(s, Service(s, llm=FakeLLM()), allow_remote=True)
    assert app.test_client().get("/api/health", headers={"Host": "192.168.1.9:5055"}).status_code == 200
```

- [ ] **Step 2: Run and fail**

Run: `uv run pytest tests/test_setup_api.py -q`. Expected: FAIL (404s and `allow_remote` TypeError).

- [ ] **Step 3: Implement `setup_api.py`**

```python
"""Setup endpoints (keys, test mode, the example, stopping) and the local-only guard."""

from __future__ import annotations

import os
import signal
import threading
from urllib.parse import urlsplit

from flask import Blueprint, current_app, jsonify, request

from . import example, keys
from .config import env_file_path, load_settings
from .keys import SetupError

bp = Blueprint("setup", __name__)
LOCAL_NAMES = {"127.0.0.1", "localhost", "::1"}


def _svc():
    return current_app.extensions["jevfish"]


def _form() -> dict:
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise SetupError("Send the settings as JSON.")
    return data


def is_local(netloc: str) -> bool:
    return (urlsplit("//" + netloc).hostname or "") in LOCAL_NAMES


def guard():
    """Only this computer may use the API. Blocks DNS rebinding and other sites' forms."""
    if not request.path.startswith("/api/") or current_app.config.get("JEVFISH_ALLOW_REMOTE"):
        return None
    if not is_local(request.host):
        return jsonify(error="JevFish only answers on this computer. Open http://127.0.0.1 instead."), 403
    origin = request.headers.get("Origin")
    if request.method not in ("GET", "HEAD", "OPTIONS") and origin is not None and not is_local(urlsplit(origin).netloc):
        return jsonify(error="Requests from other websites are blocked."), 403
    return None


@bp.errorhandler(SetupError)
def setup_error(e):
    return jsonify(error=str(e)), 400


@bp.get("/api/settings")
def get_settings():
    env, svc = os.environ, _svc()
    s = svc.settings
    return jsonify(
        env_file=str(env_file_path()),
        test_mode=s.fake_judge or s.fake_llm,
        setup_needed=not (s.llm_ready and s.judge_ready),
        typesafe_key=keys.hint(env.get("TYPESAFE_API_KEY")),
        llm_provider=keys.provider(env),
        gemini_key=keys.hint(env.get("GEMINI_API_KEY")),
        llm_key=keys.hint(env.get("LLM_API_KEY")),
        llm_base_url=env.get("LLM_BASE_URL", ""),
        llm_model=env.get("LLM_MODEL", "") or env.get("LLM_MODEL_NAME", ""),
        active_tasks=svc.active_tasks(),
    )


@bp.put("/api/settings")
def put_settings():
    updates = keys.updates_from_form(_form(), os.environ)
    keys.write_env(env_file_path(), updates)
    keys.apply(updates)
    _svc().reload(load_settings())
    return get_settings()


@bp.post("/api/settings/check")
def check():
    form, env = _form(), os.environ
    jev_key = keys.text(form, "typesafe_key") or env.get("TYPESAFE_API_KEY", "")
    jev = keys.check_jev(jev_key, _svc().settings.jev_model) if jev_key else {"ok": False, "message": "No Jev key yet."}
    choice = form.get("llm_provider") or keys.provider(env)
    typed = keys.text(form, "llm_key")
    if choice == "gemini":
        key = typed or env.get("GEMINI_API_KEY", "")
        llm = keys.check_llm("gemini", key) if key else {"ok": False, "message": "No Gemini key yet."}
    else:
        key = typed or env.get("LLM_API_KEY", "")
        base = keys.text(form, "llm_base_url") or env.get("LLM_BASE_URL", "")
        model = keys.text(form, "llm_model") or env.get("LLM_MODEL", "")
        llm = keys.check_llm("openai", key, base, model) if key and base and model else {
            "ok": False, "message": "Fill in the address, model and key first."}
    return jsonify(jev=jev, llm=llm)


@bp.get("/api/example")
def get_example():
    return jsonify(example.example())


def _stop_process() -> None:
    os.kill(os.getpid(), signal.SIGTERM)


@bp.post("/api/shutdown")
def shutdown():
    stop = current_app.config.get("JEVFISH_STOP") or _stop_process
    threading.Timer(0.3, stop).start()  # let the response go out first
    return jsonify(ok=True)
```

- [ ] **Step 4: Wire it into `api.py`**

- Signature: `def create_app(settings=None, service=None, allow_remote: bool = False) -> Flask:`.
- After `app.extensions["jevfish"] = svc`, add:
  - `app.config["JEVFISH_ALLOW_REMOTE"] = allow_remote`
  - `app.before_request(guard)`
  - `app.register_blueprint(setup_bp)`
- Import with `from .setup_api import bp as setup_bp, guard`.
- `health()` returns `jsonify(ok=True, **svc.settings.health())`.
- `estimate()` uses `svc.settings.max_requests`.

The blueprint must be registered before the catch-all `web` route is declared. Flask matches `/api/settings` over `/<path:path>` either way, because static rules win, but register first for clarity.

- [ ] **Step 5: `cli.py` serve**

```python
    local = args.host in ("127.0.0.1", "localhost", "::1")
    if not local:
        print("Warning: listening beyond this computer. Anyone who can reach it can change the keys.")
    app = create_app(settings, allow_remote=not local)
```

- [ ] **Step 6: Run and pass**

Run: `uv run pytest -q`. Expected: all pass.

- [ ] **Step 7: Commit**

`git add -A src tests && git commit -m "feat(jevfish): setup API (keys, test mode, example, stop) and local-only guard"`

### Task 5: Web app, Setup screen and example button

**Files:**
- Create: `jevfish/web/src/lib/health.js`, `jevfish/web/src/views/SetupView.vue`
- Modify: `jevfish/web/src/lib/api.js`, `jevfish/web/src/router.js`, `jevfish/web/src/App.vue`, `jevfish/web/src/views/ProjectsView.vue`

- [ ] **Step 1: `api.js`**

Add to the `api` object:

```js
  settings: () => request('GET', '/settings'),
  saveSettings: (body) => request('PUT', '/settings', body),
  checkKeys: (body) => request('POST', '/settings/check', body),
  example: () => request('GET', '/example'),
  shutdown: () => request('POST', '/shutdown'),
```

- [ ] **Step 2: `lib/health.js`**

```js
// One shared copy of /api/health, so the banner and the Setup screen agree.
import { ref } from 'vue'
import { api } from './api.js'

export const health = ref(null)
export const healthError = ref('')

export async function refreshHealth() {
  try {
    health.value = await api.health()
    healthError.value = ''
  } catch (e) {
    healthError.value = e.message
  }
  return health.value
}
```

- [ ] **Step 3: `router.js`**

- Import `SetupView`.
- Add `{ path: '/setup', name: 'setup', component: SetupView }` before the catch-all.
- Export the router, then add:

```js
// First load only: send people without keys to Setup.
let firstLoad = true
router.beforeEach(async (to) => {
  if (!firstLoad) return true
  firstLoad = false
  const h = await refreshHealth()
  if (h && h.setup_needed && to.name !== 'setup') return { name: 'setup' }
  return true
})
```

- [ ] **Step 4: `App.vue`**

- Drop the local `health`/`healthError` refs and the `onMounted` fetch. Import them from `lib/health.js`.
- Import `useRoute`, and hide the banners on the setup route: `const onSetup = computed(() => route.name === 'setup')`.
- The template banners wrapper becomes `v-if="!onSetup && (warnings.length || healthError)"`.
- Each warning gets `<RouterLink to="/setup">Open settings</RouterLink>` after the text.
- Add `<RouterLink to="/setup" class="btn small ghost">Settings</RouterLink>` before the theme switch.
- Warning wording: "Jev is not set up yet." and "No language model is set up yet."

- [ ] **Step 5: `SetupView.vue`**

Complete file:

```vue
<script setup>
import { computed, onMounted, ref } from 'vue'
import { api } from '../lib/api.js'
import { health, refreshHealth } from '../lib/health.js'

const saved = ref(null)
const loadError = ref('')
const typesafeKey = ref('')
const provider = ref('gemini')
const llmKey = ref('')
const baseUrl = ref('')
const model = ref('')
const busy = ref('')
const formError = ref('')
const checks = ref(null)
const stopped = ref(false)

async function load() {
  try {
    const s = await api.settings()
    saved.value = s
    provider.value = s.llm_provider
    baseUrl.value = s.llm_base_url
    model.value = s.llm_model
  } catch (e) {
    loadError.value = e.message
  }
}
onMounted(load)

const firstRun = computed(() => saved.value && saved.value.setup_needed && !saved.value.test_mode)
const savedLlmKey = computed(() => (saved.value ? (provider.value === 'gemini' ? saved.value.gemini_key : saved.value.llm_key) : null))
const ready = computed(() => health.value && !health.value.setup_needed)

function savedText(h) {
  if (h === null || h === undefined) return ''
  return h ? `A key ending in ${h} is saved. Leave this blank to keep it.` : 'A key is saved. Leave this blank to keep it.'
}

function form() {
  const f = { typesafe_key: typesafeKey.value, llm_provider: provider.value, llm_key: llmKey.value }
  if (provider.value === 'openai') Object.assign(f, { llm_base_url: baseUrl.value, llm_model: model.value })
  return f
}

async function saveAndCheck() {
  formError.value = ''
  checks.value = null
  if (!typesafeKey.value.trim() && !(saved.value && saved.value.typesafe_key !== null)) {
    formError.value = 'Paste your Jev key first.'
    return
  }
  busy.value = 'save'
  try {
    saved.value = await api.saveSettings(form())
    typesafeKey.value = ''
    llmKey.value = ''
    await refreshHealth()
    busy.value = 'check'
    checks.value = await api.checkKeys({ llm_provider: provider.value })
  } catch (e) {
    formError.value = e.message
  } finally {
    busy.value = ''
  }
}

async function setTestMode(on) {
  formError.value = ''
  busy.value = 'test'
  try {
    saved.value = await api.saveSettings({ test_mode: on })
    await refreshHealth()
  } catch (e) {
    formError.value = e.message
  } finally {
    busy.value = ''
  }
}

async function stop() {
  const n = saved.value ? saved.value.active_tasks : 0
  const extra = n ? ` ${n} running ${n === 1 ? 'job' : 'jobs'} will stop too.` : ''
  if (!window.confirm(`Stop JevFish on this computer?${extra}`)) return
  try {
    await api.shutdown()
    stopped.value = true
  } catch (e) {
    formError.value = e.message
  }
}
</script>

<template>
  <div v-if="stopped" class="panel empty">
    <h3>JevFish has stopped</h3>
    <p>You can close this tab. Open JevFish.app to start it again.</p>
  </div>
  <div v-else class="stack-lg setup">
    <section class="intro">
      <h1>{{ firstRun ? 'Set up JevFish' : 'Settings' }}</h1>
      <p class="muted">
        JevFish needs two keys. Jev decides what each simulated person does, and a language model writes the graph, the crowd and
        the posts. Keys stay in a file on this computer.
      </p>
    </section>

    <div v-if="loadError" class="notice error" role="alert">{{ loadError }}</div>

    <form v-if="saved" class="stack-lg" @submit.prevent="saveAndCheck">
      <section class="panel stack" aria-labelledby="jev-head">
        <div class="panel-head">
          <h2 id="jev-head">Jev</h2>
          <p>Get a key at <a href="https://console.typesafe.ai" target="_blank" rel="noopener">console.typesafe.ai</a>. A typical run costs about US$0.04.</p>
        </div>
        <label class="field">
          <span class="label">TypeSafe API key</span>
          <input v-model="typesafeKey" type="password" autocomplete="off" spellcheck="false" :placeholder="saved.typesafe_key !== null ? 'Saved' : 'Paste the key'" />
          <span class="hint">{{ savedText(saved.typesafe_key) }}</span>
        </label>
        <div v-if="checks" class="notice" :class="checks.jev.ok ? 'ok' : 'error'" role="status">{{ checks.jev.message }}</div>
      </section>

      <section class="panel stack" aria-labelledby="llm-head">
        <div class="panel-head">
          <h2 id="llm-head">Language model</h2>
          <span class="spacer"></span>
          <div class="seg" role="group" aria-label="Model provider">
            <button type="button" :aria-pressed="provider === 'gemini'" @click="provider = 'gemini'">Gemini</button>
            <button type="button" :aria-pressed="provider === 'openai'" @click="provider = 'openai'">Other</button>
          </div>
        </div>
        <p v-if="provider === 'gemini'" class="muted small">
          Free key at <a href="https://aistudio.google.com/apikey" target="_blank" rel="noopener">aistudio.google.com/apikey</a>. The free tier is enough for normal runs.
        </p>
        <p v-else class="muted small">Any service that speaks the OpenAI API: OpenAI, OpenRouter, Groq, or a local model.</p>
        <div v-if="provider === 'openai'" class="form-grid wide">
          <label class="field">
            <span class="label">Address</span>
            <input v-model="baseUrl" type="url" spellcheck="false" placeholder="https://api.openai.com/v1" />
          </label>
          <label class="field">
            <span class="label">Model</span>
            <input v-model="model" type="text" spellcheck="false" placeholder="gpt-4o-mini" />
          </label>
        </div>
        <label class="field">
          <span class="label">{{ provider === 'gemini' ? 'Gemini API key' : 'API key' }}</span>
          <input v-model="llmKey" type="password" autocomplete="off" spellcheck="false" :placeholder="savedLlmKey !== null ? 'Saved' : 'Paste the key'" />
          <span class="hint">{{ savedText(savedLlmKey) }}</span>
        </label>
        <div v-if="checks" class="notice" :class="checks.llm.ok ? 'ok' : 'error'" role="status">{{ checks.llm.message }}</div>
      </section>

      <div v-if="formError" class="notice error" role="alert">{{ formError }}</div>
      <div class="row">
        <button class="btn primary" type="submit" :disabled="!!busy">
          {{ busy === 'save' ? 'Saving' : busy === 'check' ? 'Checking keys' : 'Save and check' }}
        </button>
        <RouterLink v-if="ready" to="/" class="btn">Start a prediction</RouterLink>
      </div>
    </form>

    <section v-if="saved" class="panel stack" aria-labelledby="test-head">
      <div class="panel-head">
        <h2 id="test-head">Test mode</h2>
        <p>Try every screen without keys. Every number it shows is made up.</p>
      </div>
      <div class="row">
        <span class="pill" :class="saved.test_mode ? 'warn' : ''">{{ saved.test_mode ? 'On' : 'Off' }}</span>
        <button class="btn small" type="button" :disabled="!!busy" @click="setTestMode(!saved.test_mode)">
          {{ saved.test_mode ? 'Turn off test mode' : 'Turn on test mode' }}
        </button>
      </div>
    </section>

    <section v-if="saved" class="panel stack" aria-labelledby="stop-head">
      <div class="panel-head">
        <h2 id="stop-head">Stop JevFish</h2>
        <p>Shuts JevFish down on this computer. Open JevFish.app to start it again.</p>
      </div>
      <div class="row">
        <button class="btn small danger" type="button" @click="stop">Stop JevFish</button>
      </div>
      <p class="caveat break">Keys are saved in {{ saved.env_file }}</p>
    </section>
  </div>
</template>

<style scoped>
.setup { max-width: 760px; }
.intro h1 { font-size: 32px; letter-spacing: -0.02em; margin-bottom: 8px; }
.intro p { font-size: 16px; }
@media (max-width: 600px) { .intro h1 { font-size: 26px; } }
.form-grid.wide { grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); }
</style>
```

- [ ] **Step 6: `ProjectsView.vue`, fill in the example**

Script:

```js
const exampleNote = ref(false)

async function loadExample() {
  createError.value = ''
  try {
    const ex = await api.example()
    name.value = ex.name
    question.value = ex.requirement
    seedText.value = ex.seed_text
    showForm.value = true
    exampleNote.value = true
  } catch (e) {
    createError.value = e.message
  }
}
```

In the panel head, before the Hide/Show form button, add:

```html
<button class="btn small ghost" type="button" @click="loadExample">Fill in the example</button>
```

At the top of the form, add:

```html
<p v-if="exampleNote" class="notice info">The example is a Singapore co-living brand with made-up figures.</p>
```

- [ ] **Step 7: Build**

Run: `cd web && npm run build`. Expected: `built in` with no errors.

- [ ] **Step 8: Commit**

`git add web/src && git commit -m "feat(jevfish): Setup screen, first-run redirect, fill-in example"`

### Task 6: Ship the built web app

**Files:**
- Modify: `jevfish/.gitignore`
- Create: `.github/workflows/jevfish-web.yml`
- Test: `jevfish/tests/test_launcher.py` (web dist check)

- [ ] **Step 1: `.gitignore`**

Replace the `web/dist/` line with `!web/dist/`. That line re-includes the folder, which the repo root's `dist/` rule would otherwise ignore.

- [ ] **Step 2: Workflow**

```yaml
name: JevFish web build is committed

on:
  pull_request:
    paths: ["jevfish/web/**"]
  push:
    branches: [main]
    paths: ["jevfish/web/**"]

jobs:
  dist:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: 22
      - run: npm ci
        working-directory: jevfish/web
      - run: npm run build
        working-directory: jevfish/web
      - name: web/dist matches the source
        run: git status --porcelain jevfish/web/dist && test -z "$(git status --porcelain jevfish/web/dist)"
```

- [ ] **Step 3: Test**

In `tests/test_launcher.py`:

```python
import re

from jevfish.config import PACKAGE_ROOT


def test_built_web_app_is_present():
    dist = PACKAGE_ROOT / "web" / "dist"
    html = (dist / "index.html").read_text()
    assets = re.findall(r'(?:src|href)="/(assets/[^"]+)"', html)
    assert assets and all((dist / a).is_file() for a in assets)
```

- [ ] **Step 4: Commit**

`git add .gitignore web/dist ../.github/workflows/jevfish-web.yml tests/test_launcher.py && git commit -m "build(jevfish): commit the built web app so no Node is needed"`

### Task 7: Launcher script

**Files:**
- Create: `jevfish/launcher/launch.sh` (mode 755), `jevfish/launcher/jevfish-folder-marker`
- Test: `jevfish/tests/test_launcher.py`

- [ ] **Step 1: Write the failing tests**

```python
import os
import signal
import socket
import subprocess
import sys
import time

import pytest

LAUNCH = PACKAGE_ROOT / "launcher" / "launch.sh"
mac_only = pytest.mark.skipif(sys.platform != "darwin", reason="Mac launcher")

FAKE_SERVER = """#!{python}
import http.server, json, os, sys
port = int(sys.argv[sys.argv.index("--port") + 1])
open({pidfile!r}, "a").write(str(os.getpid()) + "\\n")
class H(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        body = json.dumps({{"app": "jevfish", "ok": True}}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(body)
    def log_message(self, *a):
        pass
http.server.HTTPServer(("127.0.0.1", port), H).serve_forever()
"""

FAKE_UV = """#!/bin/sh
echo "uv $*" >> "{calls}"
mkdir -p .venv/bin
cp "{server}" .venv/bin/jevfish
chmod +x .venv/bin/jevfish
"""


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture
def sandbox(tmp_path):
    root = tmp_path / "repo"
    jf = root / "jevfish"
    (jf / "web" / "dist").mkdir(parents=True)
    (jf / "web" / "dist" / "index.html").write_text("<p>app</p>")
    (jf / "pyproject.toml").write_text("")
    (jf / "uv.lock").write_text("")
    server = tmp_path / "fake-server"
    pidfile = tmp_path / "pids"
    server.write_text(FAKE_SERVER.format(python=sys.executable, pidfile=str(pidfile)))
    server.chmod(0o755)
    calls = tmp_path / "uv-calls"
    uv = tmp_path / "fake-uv"
    uv.write_text(FAKE_UV.format(calls=calls, server=server))
    uv.chmod(0o755)
    home = tmp_path / "home"
    env = {
        "HOME": str(home), "PATH": "/usr/bin:/bin:/usr/sbin:/sbin", "JEVFISH_EXTRA_PATH": "",
        "JEVFISH_NO_GUI": "1", "JEVFISH_NO_OPEN": "1", "JEVFISH_PORTS": str(free_port()),
    }
    box = dict(root=root, jf=jf, uv=uv, calls=calls, env=env, home=home,
               state=home / "Library" / "Application Support" / "JevFish",
               log=home / "Library" / "Logs" / "JevFish" / "launcher.log")
    yield box
    if pidfile.exists():
        for pid in pidfile.read_text().split():
            try:
                os.kill(int(pid), signal.SIGTERM)
            except ProcessLookupError:
                pass


def launch(box, **extra):
    return subprocess.run(["/bin/bash", str(LAUNCH), str(box["root"])], env={**box["env"], **extra}, timeout=90)


@mac_only
def test_first_start_installs_then_second_reuses(sandbox):
    (sandbox["state"] / "bin").mkdir(parents=True)
    (sandbox["state"] / "bin" / "uv").symlink_to(sandbox["uv"])
    assert launch(sandbox).returncode == 0
    log = sandbox["log"].read_text()
    port = sandbox["env"]["JEVFISH_PORTS"]
    assert f"ready http://127.0.0.1:{port}/" in log
    assert sandbox["calls"].read_text().strip() == "uv sync --frozen"
    assert (sandbox["jf"] / ".venv" / ".jevfish-synced").exists()
    assert (sandbox["state"] / "repo-path").read_text().strip() == str(sandbox["root"])
    assert launch(sandbox).returncode == 0
    assert f"already running on {port}" in sandbox["log"].read_text()
    assert sandbox["calls"].read_text().count("sync") == 1


@mac_only
def test_installs_uv_when_missing(sandbox, tmp_path):
    installer = tmp_path / "install.sh"
    installer.write_text(f'#!/bin/sh\nmkdir -p "$UV_INSTALL_DIR"\ncp "{sandbox["uv"]}" "$UV_INSTALL_DIR/uv"\n')
    assert launch(sandbox, JEVFISH_UV_INSTALLER=f"file://{installer}").returncode == 0
    log = sandbox["log"].read_text()
    assert "Installing uv" in log and "ready http://" in log
    assert (sandbox["state"] / "bin" / "uv").exists()


@mac_only
def test_missing_files_fail_cleanly(sandbox):
    (sandbox["jf"] / "pyproject.toml").unlink()
    assert launch(sandbox).returncode == 1
    assert "error: The JevFish files are missing" in sandbox["log"].read_text()
```

- [ ] **Step 2: Run and fail**

Run: `uv run pytest tests/test_launcher.py -q`. Expected: the launcher tests FAIL (no `launch.sh`).

- [ ] **Step 3: Write `launch.sh`**

```bash
#!/bin/bash
# One-click start for JevFish on a Mac. JevFish.app runs this with the repo folder as $1.
# First start: installs uv (into ~/Library/Application Support/JevFish/bin, no admin
# password) and the Python packages. Every start: reuses a running JevFish or starts one
# on a free port, then opens it in the browser.
#
# Test hooks: JEVFISH_NO_GUI=1 logs instead of showing dialogs, JEVFISH_NO_OPEN=1 skips the
# browser, JEVFISH_UV_INSTALLER replaces the uv install script, JEVFISH_PORTS lists ports,
# JEVFISH_EXTRA_PATH replaces the usual tool folders added to PATH.
set -u -o pipefail

ROOT="${1:-$(cd "$(dirname "$0")/../.." && pwd)}"
JF="$ROOT/jevfish"
STATE="${JEVFISH_HOME:-$HOME/Library/Application Support/JevFish}"
LOGS="$HOME/Library/Logs/JevFish"
LOG="$LOGS/launcher.log"
PORTS="${JEVFISH_PORTS:-5055 5056 5057 5058 5059 5060 5061 5062 5063 5064}"
# Finder starts apps with a bare PATH, so add the usual places uv lives.
export PATH="$STATE/bin:$PATH${JEVFISH_EXTRA_PATH-:$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin}"

mkdir -p "$STATE" "$LOGS"
exec >>"$LOG" 2>&1
echo "== $(date '+%Y-%m-%d %H:%M:%S') start from $ROOT"

gui() { [ "${JEVFISH_NO_GUI:-}" != "1" ]; }

tell() {  # a dialog that closes itself, so setup carries on behind it
  echo "note: $1"
  gui && osascript -e "display dialog \"$1\" with title \"JevFish\" buttons {\"OK\"} default button \"OK\" giving up after 30" >/dev/null 2>&1 &
}

fail() {
  echo "error: $1"
  if gui; then
    choice=$(osascript -e "button returned of (display alert \"JevFish could not start\" message \"$1\" as critical buttons {\"Show log\", \"OK\"} default button \"OK\")" 2>/dev/null)
    [ "$choice" = "Show log" ] && open -a Console "$LOG"
  fi
  exit 1
}

running_port() {  # prints the port of a JevFish already running here
  for p in $PORTS; do
    if curl -fsS --max-time 1 "http://127.0.0.1:$p/api/health" 2>/dev/null | grep -q '"app": *"jevfish"'; then
      echo "$p"
      return 0
    fi
  done
  return 1
}

open_app() {
  echo "ready http://127.0.0.1:$1/"
  printf '%s\n' "$ROOT" >"$STATE/repo-path"
  [ "${JEVFISH_NO_OPEN:-}" = "1" ] || open "http://127.0.0.1:$1/"
  exit 0
}

[ -f "$JF/pyproject.toml" ] || fail "The JevFish files are missing from $ROOT. Download JevFish again."

if port=$(running_port); then
  echo "already running on $port"
  open_app "$port"
fi

# 1. uv, the tool that installs Python and the packages
UV="$(command -v uv || true)"
if [ -z "$UV" ]; then
  tell "Installing uv, a small tool JevFish needs. This happens once."
  curl -LsSf "${JEVFISH_UV_INSTALLER:-https://astral.sh/uv/install.sh}" |
    env UV_INSTALL_DIR="$STATE/bin" UV_NO_MODIFY_PATH=1 sh ||
    fail "Could not install uv. Check the internet connection and open JevFish again."
  UV="$STATE/bin/uv"
  [ -x "$UV" ] || fail "uv did not install. The log has the details."
fi
echo "uv: $UV"

# 2. Python and the packages, again only when the lock file changed
STAMP="$JF/.venv/.jevfish-synced"
if [ ! -x "$JF/.venv/bin/jevfish" ] || [ ! -f "$STAMP" ] || [ "$JF/uv.lock" -nt "$STAMP" ] || [ "$JF/pyproject.toml" -nt "$STAMP" ]; then
  if [ -x "$JF/.venv/bin/jevfish" ]; then
    tell "Updating JevFish. Your browser opens when it is ready."
  else
    tell "Setting up JevFish. The first start downloads about 1 GB and takes around 5 minutes. Your browser opens when it is ready."
  fi
  (cd "$JF" && "$UV" sync --frozen) || fail "Installing the Python packages failed. Check the internet connection and open JevFish again."
  touch "$STAMP"
fi

# 3. The web app ships built. Rebuild only if someone deleted it and Node is around.
if [ ! -f "$JF/web/dist/index.html" ]; then
  command -v npm >/dev/null || fail "The web app is missing from jevfish/web/dist. Download JevFish again."
  (cd "$JF/web" && npm install && npm run build) || fail "Building the web app failed."
fi

# 4. Start on the first free port and wait for it
port=""
for p in $PORTS; do
  if ! nc -z 127.0.0.1 "$p" >/dev/null 2>&1; then
    port="$p"
    break
  fi
done
[ -n "$port" ] || fail "Ports $PORTS are all in use. Close whatever is using them and open JevFish again."
echo "starting on $port"
(cd "$JF" && nohup "$JF/.venv/bin/jevfish" serve --port "$port" >>"$LOGS/server.log" 2>&1 &)
for _ in $(seq 1 240); do
  if curl -fsS --max-time 1 "http://127.0.0.1:$port/api/health" 2>/dev/null | grep -q '"app": *"jevfish"'; then
    open_app "$port"
  fi
  sleep 0.5
done
fail "JevFish did not start within two minutes. The log has the details."
```

`jevfish-folder-marker` contents: `This file lets JevFish.app find this folder when macOS runs the app from a temporary copy. Keep it.`

- [ ] **Step 4: Run and pass**

Run: `chmod +x launcher/launch.sh && uv run pytest tests/test_launcher.py -q`. Expected: 4 passed.

- [ ] **Step 5: Commit**

`git add launcher tests/test_launcher.py && git commit -m "feat(jevfish): Mac launcher script"`

### Task 8: JevFish.app bundle and icon

**Files:**
- Create: `JevFish.app/Contents/Info.plist`, `JevFish.app/Contents/MacOS/JevFish` (755), `JevFish.app/Contents/Resources/AppIcon.icns`, `jevfish/launcher/make-icon.sh`
- Test: `jevfish/tests/test_launcher.py` (append)

- [ ] **Step 1: Failing test**

```python
import shutil

APP = PACKAGE_ROOT.parent / "JevFish.app"


@mac_only
def test_app_bundle_is_valid_and_finds_the_repo(tmp_path):
    assert subprocess.run(["plutil", "-lint", str(APP / "Contents" / "Info.plist")]).returncode == 0
    exe = APP / "Contents" / "MacOS" / "JevFish"
    assert os.access(exe, os.X_OK)
    assert (APP / "Contents" / "Resources" / "AppIcon.icns").stat().st_size > 10_000
    repo = tmp_path / "repo"
    shutil.copytree(APP, repo / "JevFish.app", symlinks=True)
    stub = repo / "jevfish" / "launcher" / "launch.sh"
    stub.parent.mkdir(parents=True)
    out = tmp_path / "got"
    stub.write_text(f'#!/bin/bash\necho "$1" > "{out}"\n')
    env = {"HOME": str(tmp_path / "home"), "PATH": "/usr/bin:/bin"}
    subprocess.run([str(repo / "JevFish.app" / "Contents" / "MacOS" / "JevFish")], env=env, timeout=30, check=True)
    assert out.read_text().strip() == str(repo)
    # moved away from the folder: falls back to the remembered path
    moved = tmp_path / "Applications"
    moved.mkdir()
    shutil.move(str(repo / "JevFish.app"), moved / "JevFish.app")
    state = tmp_path / "home" / "Library" / "Application Support" / "JevFish"
    state.mkdir(parents=True)
    (state / "repo-path").write_text(f"{repo}\n")
    out.unlink()
    subprocess.run([str(moved / "JevFish.app" / "Contents" / "MacOS" / "JevFish")], env=env, timeout=30, check=True)
    assert out.read_text().strip() == str(repo)
```

- [ ] **Step 2: Run and fail**

Run: `uv run pytest tests/test_launcher.py -q -k bundle`. Expected: FAIL (no Info.plist).

- [ ] **Step 3: Info.plist**

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
	<key>CFBundleDevelopmentRegion</key>
	<string>en</string>
	<key>CFBundleDisplayName</key>
	<string>JevFish</string>
	<key>CFBundleExecutable</key>
	<string>JevFish</string>
	<key>CFBundleIconFile</key>
	<string>AppIcon</string>
	<key>CFBundleIdentifier</key>
	<string>com.markiewee.jevfish</string>
	<key>CFBundleInfoDictionaryVersion</key>
	<string>6.0</string>
	<key>CFBundleName</key>
	<string>JevFish</string>
	<key>CFBundlePackageType</key>
	<string>APPL</string>
	<key>CFBundleShortVersionString</key>
	<string>0.2.0</string>
	<key>CFBundleVersion</key>
	<string>0.2.0</string>
	<key>LSMinimumSystemVersion</key>
	<string>12.0</string>
	<key>NSHighResolutionCapable</key>
	<true/>
</dict>
</plist>
```

- [ ] **Step 4: `MacOS/JevFish`**

```bash
#!/bin/bash
# Finder runs this when JevFish.app is opened. The work happens in jevfish/launcher/launch.sh.
here="$(cd "$(dirname "$0")" && pwd)"
root="$(cd "$here/../../.." && pwd)"
state="$HOME/Library/Application Support/JevFish"
has_launcher() { [ -f "$1/jevfish/launcher/launch.sh" ]; }

# Moved out of its folder: use the folder from the last good start.
if ! has_launcher "$root" && [ -f "$state/repo-path" ]; then
  root="$(head -n 1 "$state/repo-path")"
fi
# A downloaded copy can run from a temporary path (App Translocation). Ask Spotlight.
if ! has_launcher "$root"; then
  while IFS= read -r marker; do
    candidate="$(cd "$(dirname "$marker")/../.." 2>/dev/null && pwd)"
    if has_launcher "$candidate"; then
      root="$candidate"
      break
    fi
  done < <(mdfind -name jevfish-folder-marker 2>/dev/null)
fi
if ! has_launcher "$root"; then
  osascript -e 'display alert "JevFish cannot find its files" message "Keep JevFish.app inside the JevFish folder you downloaded and open it from there." as critical' >/dev/null 2>&1
  exit 1
fi
exec /bin/bash "$root/jevfish/launcher/launch.sh" "$root"
```

- [ ] **Step 5: Icon**

`launcher/make-icon.sh` writes the header logo as a 1024 px SVG (tile `#0e5a6b`, white dots, the same seven circles scaled by 32). It renders the SVG with `qlmanage -t -s 1024`, builds the iconset sizes with `sips -z`, and packs it with `iconutil -c icns` into `JevFish.app/Contents/Resources/AppIcon.icns`. If `qlmanage` output is not square or not transparent, fall back to headless Chrome `--screenshot` with a transparent background. Run it once, eyeball the PNG, commit the `.icns`.

- [ ] **Step 6: Run and pass, commit**

Run: `uv run pytest tests/test_launcher.py -q`. Expected: 5 passed.

`git add ../JevFish.app launcher/make-icon.sh tests/test_launcher.py && git commit -m "feat: JevFish.app, the double-click launcher"`

### Task 9: Docs

- [ ] Root `README.md`: under the fork note, add "Start JevFish on a Mac":
  - Download the ZIP (or clone) and double-click `JevFish.app`.
  - What the first start does.
  - The Open Anyway step for ZIP downloads.
  - Where the logs are.
- [ ] `jevfish/README.md`: "Run it" leads with the app and the Setup screen. The terminal steps move under "From the terminal". Add a "Setup and safety" section: keys in `.env` mode 600, the local-only guard, and `--host` turning it off.
- [ ] `jevfish/docs/api.md`:
  - Document `GET/PUT /api/settings`, `POST /api/settings/check`, `GET /api/example` and `POST /api/shutdown`.
  - Health gains `app` and `setup_needed`.
  - Add a note on the 403 guard.
- [ ] Commit `docs(jevfish): one-click start`.

### Task 10: Verify for real

- [ ] `uv run pytest -q`: everything passes.
- [ ] Fresh-machine run:
  - Clone the branch locally into the scratchpad.
  - Use a scratch `JEVFISH_HOME`, PATH without uv, and `JEVFISH_EXTRA_PATH=""`.
  - Run `launch.sh` with `JEVFISH_NO_GUI=1`.
  - Expect uv installed from astral.sh, `uv sync` done, the server up, `ready` in the log. Record the time.
- [ ] Real double-click path: `open JevFish.app` from the working copy. The browser opens on the Setup screen when no keys are saved. Stop the server afterwards via `POST /api/shutdown`.
- [ ] Real keys through the API:
  - Save Mark's keys from `~/.chudbrain/secrets.env` into `jevfish/.env` via `PUT /api/settings`, without printing them.
  - `POST /api/settings/check` returns both `ok: true`.
- [ ] Browser QA of `/setup`, `/` (with the example filled in) and the banners:
  - 375, 768 and 1280 px, light and dark.
  - No console errors, no horizontal scroll.
  - Test mode on runs a lite project end to end.
- [ ] Open the PR (`feat/jevfish-one-click`) with the PR body below, then merge.

---

## PR draft

**Title:** JevFish: double-click Mac app and in-app setup

**Summary**
- `JevFish.app` at the repo root. Double-click it and it installs uv and the Python packages on first start (no admin password, no Xcode, no Node), starts JevFish on a free port or reuses a running one, and opens the browser. Errors come up as a macOS alert with a "Show log" button.
- Setup screen in the app. It takes the Jev key and a Gemini or any OpenAI-compatible model, then "Save and check" writes `jevfish/.env` (mode 600) and applies it without a restart. It checks both keys with free calls. The screen also has test mode and a Stop button. First load without keys lands there.
- "Fill in the example" on the new-prediction form.
- The API now only answers requests addressed to this computer, and refuses changing requests from other websites. `serve --host` beyond loopback turns this off and warns.
- The built web app is committed, and a workflow fails if it goes stale.

**Tests**
- `uv run pytest -q`: new env-file, key-check, setup API, guard, launcher (fake uv and a fake server) and bundle tests.
- A fresh-install run on this Mac with uv hidden.
- A real double-click.
- Real key checks.
- Browser QA at three widths in both themes.

**Known limit:** ZIP downloads are quarantined by macOS, so the first open needs Privacy & Security, Open Anyway. Signing would need a paid Apple account.
