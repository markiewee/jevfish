import os
import stat

import pytest
from dotenv import dotenv_values

from jevfish import keys
from jevfish.config import env_file_path
from jevfish.keys import SetupError, updates_from_form, write_env
from tests.test_pipeline import settings


def test_env_file_path_follows_env(tmp_path, monkeypatch):
    monkeypatch.setenv("JEVFISH_ENV_FILE", str(tmp_path / "x.env"))
    assert env_file_path() == tmp_path / "x.env"


def test_health_reports_app_and_setup_needed(tmp_path):
    ready = settings(tmp_path).health()
    assert ready["app"] == "jevfish" and ready["setup_needed"] is False
    missing = settings(tmp_path, fake_judge=False, fake_llm=False).health()
    assert missing["setup_needed"] is True


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

    assert keys.check_llm("gemini", "g", client_factory=Gemini([]))["ok"] is True
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
    rejected = keys.check_llm("openai", "k", "https://x/v1", "m", client_factory=Other(err(AuthenticationError, 401)))
    assert rejected["message"] == "The provider rejected this key."
