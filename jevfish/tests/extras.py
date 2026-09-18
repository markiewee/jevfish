"""Shared markers for the optional extras.

The OASIS reddit and twitter platforms live behind the `[oasis]` extra, and PDF seed
upload behind `[pdf]`, because together they were 97 percent of a 1.1 GB install that the
prediction itself never touched. Tests that need one skip cleanly when it is absent, so
`uv run pytest` passes on a core install and covers everything on `uv sync --all-extras`.
"""

import importlib.util

import pytest

HAS_OASIS = importlib.util.find_spec("oasis") is not None
HAS_PYPDF = importlib.util.find_spec("pypdf") is not None

needs_oasis = pytest.mark.skipif(
    not HAS_OASIS, reason="needs the oasis extra: uv sync --extra oasis"
)
needs_pypdf = pytest.mark.skipif(
    not HAS_PYPDF, reason="needs the pdf extra: uv sync --extra pdf"
)
