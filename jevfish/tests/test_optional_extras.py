"""The heavy dependencies are optional, and asking for them must explain itself."""

import builtins

import pytest

from jevfish.platforms import make_platform
from jevfish.platforms.base import OASIS_HINT


def test_lite_platform_needs_nothing_optional(tmp_path):
    assert type(make_platform("lite", tmp_path)).__name__ == "LitePlatform"


def test_reddit_without_the_extra_names_the_install_command(monkeypatch):
    """The refusal fires in _import_oasis, not make_platform.

    oasis_platform.py imports oasis lazily inside _import_oasis, so the module itself
    imports fine without the extra and make_platform returns an object. The missing
    dependency surfaces the moment the platform actually starts. Verified against a real
    27 MB install: `jevfish demo --platform reddit` prints exactly this message.
    """
    import sys

    from jevfish.platforms.oasis_platform import _import_oasis

    monkeypatch.setitem(sys.modules, "oasis", None)
    with pytest.raises(RuntimeError) as e:
        _import_oasis()
    msg = str(e.value)
    assert "jevfish[oasis]" in msg
    assert "--platform lite" in msg


def test_make_platform_also_guards_the_module_level_import(tmp_path, monkeypatch):
    """Belt and braces: if oasis_platform itself ever fails to import, say the same thing."""
    real_import = builtins.__import__

    def no_oasis_platform(name, *args, **kwargs):
        if "oasis_platform" in name:
            raise ModuleNotFoundError(f"No module named '{name}'")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", no_oasis_platform)
    with pytest.raises(RuntimeError) as e:
        make_platform("reddit", tmp_path)
    assert "jevfish[oasis]" in str(e.value)


def test_the_hint_offers_a_way_forward_not_just_a_refusal():
    msg = OASIS_HINT.format(kind="reddit")
    assert "install" in msg.lower()
    assert "lite" in msg
    assert "1 GB" in msg


def test_unknown_platform_still_raises_value_error(tmp_path):
    with pytest.raises(ValueError):
        make_platform("mastodon", tmp_path)


def test_a_pdf_without_the_extra_is_refused_with_a_way_forward(tmp_path, monkeypatch):
    from jevfish.llm import FakeLLM
    from jevfish.service import PipelineError, Service

    from .test_pipeline import settings

    real_import = builtins.__import__

    def no_pypdf(name, *args, **kwargs):
        if name.split(".")[0] == "pypdf":
            raise ModuleNotFoundError("No module named 'pypdf'")
        return real_import(name, *args, **kwargs)

    svc = Service(settings(tmp_path), llm=FakeLLM())
    p = svc.create_project("pdf", "Will it work?")
    monkeypatch.setattr(builtins, "__import__", no_pypdf)
    with pytest.raises(PipelineError) as e:
        svc.add_file(p["id"], "x.pdf", b"%PDF-1.4")
    assert "jevfish[pdf]" in str(e.value)
    assert "paste the text" in str(e.value)
