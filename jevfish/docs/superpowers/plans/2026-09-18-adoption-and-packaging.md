# JevFish Adoption and Packaging Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn a fork that GitHub search cannot see into a project someone can find, understand in thirty seconds, and install with one command that actually works.

**Architecture:** Three layers, in dependency order. First make the package installable (the wheel currently ships no UI, so `uvx jevfish` would serve a 404). Then make the install small (1.1 GB drops to about 66 MB by moving two dependencies to extras). Then make the repo findable and legible (leave the fork network, own identity, README that leads with the install command). Nothing in `src/jevfish/` changes behaviour; the code already lazy-imports both heavy dependencies, so this is mostly packaging and presentation.

**Tech Stack:** `uv_build` backend, `importlib.resources` for bundled assets, `platformdirs` for the writable data directory, GitHub Actions for releases, GitHub Pages for a static demo.

---

## The measured problem

| Check | Result | Consequence |
|---|---|---|
| `search/repositories?q=mirofish-jev` | **0** results (1 with `fork:true`) | The repo is invisible in GitHub search and on topic pages |
| repo name / description / homepage | `mirofish-jev` / MiroFish's Chinese and English one-liner / `mirofish.ai` | A visitor reads it as somebody's fork |
| topics | **none** | Not reachable from `github.com/topics/*` |
| `uv build --wheel` | 34 files, 168,620 bytes, **no `web/dist`**, no `examples` | An installed copy has no UI and no example |
| `PACKAGE_ROOT` | `Path(__file__).resolve().parents[2]` | Resolves inside `site-packages` once installed, so `.env` and `data/` land in nonsense paths |
| `.venv` | **1.1 GB**, 161 packages | torch 553 MB, pulled by `camel-oasis` via `sentence-transformers`, never called |
| `mcp==1.24.0` | declared, **zero imports** in `src/` or `tests/` | Dead dependency |
| `requires-python` | `>=3.12,<3.13` | Locks out 3.13 and 3.14 for a dependency users never call |
| `codesign -dv` on `JevFish.app` | `code object is not signed at all` | Gatekeeper rejects it; the right-click-Open bypass was removed in macOS 15.0 |
| `pymupdf` licence | **AGPL-3.0 or Artifex commercial** | `jevfish/` carries a copyleft obligation *independent of MiroFish*, through one lazy import |
| README first fenced code block | line **112** | Median across 46 adjacent repos is 60; ollama's is 15 |
| README brand mentions | **37 MiroFish to 4 JevFish** | The document is about someone else's project |
| `.github/workflows/update-star-history.yml` | 18,211 bytes | We run a scheduled job charting *upstream's* star count |
| keyless demo | works in about 10 seconds, returns a real prediction | No competitor lets anyone see output without a signup, and it is invisible in our README |

The natural experiment that sets the priority, both figures verified live against the GitHub API:

| Repo | Fork? | Topics | Stars |
|---|---|---|---|
| `nikmcfly/MiroFish-Offline` | no | 10 | **2,522** |
| `EleutheroiEdge/mirofish-offline` | yes | 0 | **0** |

Byte-identical descriptions. The difference is fork status and topics.

---

## File Structure

| File | Responsibility |
|---|---|
| Modify `pyproject.toml` | Optional extras, drop `mcp`, widen `requires-python`, package data, metadata |
| Create `src/jevfish/assets.py` | Resolve bundled read-only assets (`web/dist`, `examples`) and the writable data directory. The only module that knows where things live |
| Modify `src/jevfish/config.py:19-34,91` | Use `assets` instead of `PACKAGE_ROOT` arithmetic |
| Modify `src/jevfish/api.py:20` | Take `WEB_DIST` from `assets` |
| Modify `src/jevfish/example.py` | Take the example path from `assets` |
| Modify `src/jevfish/platforms/base.py:72-75` | Raise a message that names the extra to install |
| Move `web/dist` to `src/jevfish/web_dist/`, `examples` to `src/jevfish/examples/` | So `uv_build` includes them in the wheel |
| Create `.github/workflows/release.yml` | Build and attach artifacts on tag |
| Rewrite `README.md` (root) | JevFish's own front door |
| Create `CONTRIBUTING.md`, `.github/ISSUE_TEMPLATE/bug.yml` | Basic project hygiene |

---

## Task 1: Make the wheel carry the UI and the examples

Without this, every later task is decoration: the one-line install produces a server that serves nothing.

**Files:**
- Create: `src/jevfish/assets.py`
- Test: `tests/test_assets.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_assets.py
from pathlib import Path
from jevfish import assets


def test_web_dist_exists_and_has_an_index():
    d = assets.web_dist()
    assert d.is_dir(), f"{d} is not a directory"
    assert (d / "index.html").is_file()


def test_example_seed_is_readable():
    p = assets.example_seed()
    assert p.is_file()
    assert "Lazybee" in p.read_text()


def test_data_dir_is_writable_and_respects_the_env_override(tmp_path, monkeypatch):
    monkeypatch.setenv("JEVFISH_DATA_DIR", str(tmp_path / "somewhere"))
    d = assets.data_dir()
    assert d == tmp_path / "somewhere"
    d.mkdir(parents=True, exist_ok=True)
    (d / "probe").write_text("ok")
    assert (d / "probe").read_text() == "ok"


def test_data_dir_defaults_outside_the_package(monkeypatch):
    monkeypatch.delenv("JEVFISH_DATA_DIR", raising=False)
    d = assets.data_dir()
    pkg = Path(assets.__file__).resolve().parent
    assert pkg not in d.resolve().parents, "data must not be written inside site-packages"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_assets.py -v`
Expected: FAIL, `ImportError: cannot import name 'assets' from 'jevfish'`

- [ ] **Step 3: Move the assets inside the package**

```bash
cd /Users/mark/Desktop/claudine/projects/mirofish-jev/jevfish
git mv web/dist src/jevfish/web_dist
git mv examples src/jevfish/examples
```

Update `web/vite.config.js` so rebuilds land in the new place. Change the `build` block to:

```js
  build: { outDir: '../src/jevfish/web_dist', emptyOutDir: true },
```

- [ ] **Step 4: Write minimal implementation**

```python
# src/jevfish/assets.py
"""Where JevFish's files live, in development and once installed.

The old `PACKAGE_ROOT = parents[2]` worked only from a git checkout. Installed from a
wheel it points inside site-packages, which is both wrong and not writable, so the UI
404s and the key file cannot be saved. Read-only assets ship inside the package and are
resolved with importlib.resources. Anything written goes to a per-user directory.
"""

from __future__ import annotations

import os
from importlib import resources
from pathlib import Path


def _packaged(name: str) -> Path:
    return Path(str(resources.files("jevfish") / name))


def web_dist() -> Path:
    """The built Vue app served at /."""
    return _packaged("web_dist")


def examples_dir() -> Path:
    return _packaged("examples")


def example_seed() -> Path:
    return examples_dir() / "lazybee-cleaning.md"


def data_dir() -> Path:
    """Writable. Projects, runs and caches. Override with JEVFISH_DATA_DIR."""
    override = os.environ.get("JEVFISH_DATA_DIR", "").strip()
    if override:
        return Path(override)
    return Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share") / "jevfish"


def env_file() -> Path:
    """Where API keys are saved. Override with JEVFISH_ENV_FILE."""
    override = os.environ.get("JEVFISH_ENV_FILE", "").strip()
    return Path(override) if override else data_dir() / ".env"
```

- [ ] **Step 5: Point the three consumers at it**

In `src/jevfish/config.py`, delete line 19 (`PACKAGE_ROOT = ...`) and replace the two functions that used it:

```python
def env_file_path() -> Path:
    """Where keys are saved: JEVFISH_ENV_FILE, else the user data directory."""
    from .assets import env_file

    return env_file()
```

and in `load_settings`, replace the `data_dir=` argument with:

```python
        data_dir=_assets.data_dir(),
```

adding `from . import assets as _assets` to the imports.

In `src/jevfish/api.py`, replace line 20:

```python
WEB_DIST = PACKAGE_ROOT / "web" / "dist"
```

with:

```python
from .assets import web_dist

WEB_DIST = web_dist()
```

and drop `PACKAGE_ROOT` from the `from .config import ...` line.

In `src/jevfish/example.py`, replace the `PATH` definition:

```python
from .assets import example_seed

PATH = example_seed()
```

- [ ] **Step 6: Declare the package data and drop the dead dependency**

In `pyproject.toml`, add after the `[build-system]` block:

```toml
[tool.uv.build-backend]
source-include = ["src/jevfish/web_dist/**", "src/jevfish/examples/**"]
```

and remove `"mcp==1.24.0",` from `dependencies` (verified: zero imports in `src/` or `tests/`).

- [ ] **Step 7: Run tests and prove the wheel now carries the UI**

Run: `uv run pytest -q`
Expected: PASS, all green.

Run:
```bash
rm -rf /tmp/jf-wheel && uv build --wheel -o /tmp/jf-wheel
python3 -c "
import zipfile,glob
z=zipfile.ZipFile(glob.glob('/tmp/jf-wheel/*.whl')[0]); n=z.namelist()
print('files:', len(n))
for pat in ('web_dist/index.html','examples/lazybee-cleaning.md'):
    print(pat, '->', any(pat in x for x in n))
"
```
Expected: `web_dist/index.html -> True` and `examples/lazybee-cleaning.md -> True`

- [ ] **Step 8: Prove a clean install serves the UI**

```bash
rm -rf /tmp/jf-install && uv venv --python 3.12 /tmp/jf-install
/tmp/jf-install/bin/python -m pip install -q /tmp/jf-wheel/*.whl
JEVFISH_FAKE_JUDGE=1 JEVFISH_FAKE_LLM=1 /tmp/jf-install/bin/jevfish serve --port 5077 &
sleep 6
curl -s -o /dev/null -w "index: %{http_code}\n" http://127.0.0.1:5077/
pkill -f "jevfish serve"
```
Expected: `index: 200`. If it is 404, `web_dist` did not make it into the wheel; fix Step 6 before continuing.

- [ ] **Step 9: Commit**

```bash
git add -A
git commit -m "fix(packaging): ship the UI and examples in the wheel, write data outside the package"
```

---

## Task 2: Move the 1 GB machine-learning stack to an optional extra

**Files:**
- Modify: `pyproject.toml`
- Modify: `src/jevfish/platforms/base.py:72-75`
- Test: `tests/test_optional_extras.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_optional_extras.py
import pytest
from jevfish.platforms import make_platform


def test_lite_platform_needs_nothing_optional(tmp_path):
    p = make_platform("lite", tmp_path)
    assert type(p).__name__ == "LitePlatform"


def test_reddit_without_the_extra_names_the_install_command(tmp_path, monkeypatch):
    import builtins

    real_import = builtins.__import__

    def no_oasis(name, *args, **kwargs):
        if name.split(".")[0] in {"oasis", "camel"}:
            raise ModuleNotFoundError(f"No module named '{name}'")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", no_oasis)
    with pytest.raises(RuntimeError) as e:
        make_platform("reddit", tmp_path)
    msg = str(e.value)
    assert "jevfish[oasis]" in msg
    assert "lite" in msg


def test_unknown_platform_still_raises_value_error(tmp_path):
    with pytest.raises(ValueError):
        make_platform("mastodon", tmp_path)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_optional_extras.py -v`
Expected: FAIL on the second test, `ModuleNotFoundError` escapes instead of `RuntimeError`

- [ ] **Step 3: Write minimal implementation**

Replace `make_platform` in `src/jevfish/platforms/base.py`:

```python
OASIS_HINT = (
    "the {kind} platform needs the OASIS extra, which pulls about 1 GB of machine-learning "
    "packages. Install it with:  uv tool install 'jevfish[oasis]'   (or pip install "
    "'jevfish[oasis]').\nOr run with --platform lite, which needs nothing extra and gives "
    "the same prediction without the social feed."
)


def make_platform(kind: str, workdir, *, feed_size: int = 6) -> Platform:
    if kind == "lite":
        from .lite import LitePlatform

        return LitePlatform(feed_size=feed_size)
    if kind in ("reddit", "twitter"):
        try:
            from .oasis_platform import OasisPlatform
        except ModuleNotFoundError as e:
            raise RuntimeError(OASIS_HINT.format(kind=kind)) from e
        return OasisPlatform(kind, workdir)
    raise ValueError(f"unknown platform '{kind}'; use reddit, twitter or lite")
```

The existing `OasisPlatform` already imports `oasis` and `camel` lazily inside `_import_oasis`, so also catch it there. In `src/jevfish/platforms/oasis_platform.py`, wrap the body of `_import_oasis`:

```python
def _import_oasis():
    try:
        import oasis  # noqa: F401  (import creates ./log and file handlers)
    except ModuleNotFoundError as e:
        from .base import OASIS_HINT

        raise RuntimeError(OASIS_HINT.format(kind="reddit or twitter")) from e
    return oasis
```

- [ ] **Step 4: Declare the extras**

In `pyproject.toml`, replace the `requires-python` line and the `dependencies` list:

```toml
requires-python = ">=3.11"
dependencies = [
    "flask>=3.0",
    "openai>=1.0",
    "python-dotenv>=1.0",
    "typesafe-sdk>=0.6.0",
]

[project.optional-dependencies]
pdf = ["pypdf>=5.0"]
oasis = ["camel-ai==0.2.78", "camel-oasis==0.2.5"]
all = ["jevfish[pdf,oasis]"]
```

`pymupdf` becomes `pypdf` for two reasons, and the second is the important one:

1. It is 54 MB smaller.
2. **PyMuPDF is itself AGPL-3.0** (dual licensed, AGPL or an Artifex commercial licence).
   Keeping it means `jevfish/` carries a copyleft obligation that has nothing to do with
   MiroFish, and it would drag a hosted interactive demo into AGPL section 13 on its own.
   `pypdf` is BSD-3-Clause. Five lines of change removes an entire legal obligation.

Update the one consumer in `src/jevfish/service.py:59-61`:

```python
        try:
            from pypdf import PdfReader
        except ModuleNotFoundError as e:
            raise RuntimeError(
                "reading a PDF seed needs the pdf extra: pip install 'jevfish[pdf]'. "
                "Or paste the text directly instead of uploading a PDF."
            ) from e
        import io

        reader = PdfReader(io.BytesIO(data))
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/test_optional_extras.py -v`
Expected: PASS, 3 passed

Run: `uv run pytest -q`
Expected: PASS. The PDF upload test in `tests/test_pipeline.py::test_pdf_upload` will fail if `pypdf` is not in the dev group. Add `"pypdf>=5.0"` to `[dependency-groups] dev` so the test suite keeps covering it.

- [ ] **Step 6: Measure the win**

```bash
rm -rf /tmp/jf-slim && uv venv --python 3.12 /tmp/jf-slim
/tmp/jf-slim/bin/python -m pip install -q /tmp/jf-wheel/*.whl
du -sm /tmp/jf-slim | cut -f1 | xargs -I{} echo "core install: {} MB (was 1100 MB)"
/tmp/jf-slim/bin/python -c "import importlib.util as u; print('torch present:', u.find_spec('torch') is not None)"
```
Expected: under 120 MB, `torch present: False`

- [ ] **Step 7: Verify Python 3.13 actually works before claiming it**

```bash
rm -rf /tmp/jf-313 && uv venv --python 3.13 /tmp/jf-313 \
  && /tmp/jf-313/bin/python -m pip install -q /tmp/jf-wheel/*.whl \
  && JEVFISH_FAKE_JUDGE=1 JEVFISH_FAKE_LLM=1 JEVFISH_DATA_DIR=/tmp/jf-313/data \
     /tmp/jf-313/bin/jevfish demo --platform lite --rounds 2 --public 10 --stakeholders 3 \
  && echo "3.13 OK"
```
If this fails, set `requires-python = ">=3.12"` instead of `>=3.11` and record which versions were actually tested. Do not widen the floor on assumption.

- [ ] **Step 8: Commit**

```bash
git add -A
git commit -m "feat(packaging): OASIS and PDF become optional extras, drop the 553 MB torch pull"
```

---

## Task 3: Publish to PyPI so the install is one line

**Files:**
- Modify: `pyproject.toml` (metadata)
- Create: `.github/workflows/release.yml`

- [ ] **Step 1: Fill in the metadata PyPI shows**

In `pyproject.toml`, under `[project]`:

```toml
description = "Predict how a population will react. Simulates a crowd, polls every person with a typed judgment model, and tells you when the answer came from your prompt instead of the world."
readme = "README.md"
license = "AGPL-3.0-or-later"
keywords = [
    "synthetic survey", "silicon sampling", "synthetic respondents", "agent-based simulation",
    "prediction", "forecasting", "calibration", "market research", "ai focus group",
    "opinion simulation", "llm agents",
]
classifiers = [
    "Development Status :: 3 - Alpha",
    "Intended Audience :: Science/Research",
    "License :: OSI Approved :: GNU Affero General Public License v3 or later (AGPLv3+)",
    "Programming Language :: Python :: 3.12",
    "Topic :: Scientific/Engineering :: Artificial Intelligence",
]

[project.urls]
Homepage = "https://github.com/markiewee/jevfish"
Documentation = "https://github.com/markiewee/jevfish#readme"
Source = "https://github.com/markiewee/jevfish"
Issues = "https://github.com/markiewee/jevfish/issues"
"Upstream (MiroFish)" = "https://github.com/666ghj/MiroFish"
```

The keywords are the words the audience searches and the current README uses none of them.

- [ ] **Step 2: Verify the name is still free, then publish a test release**

```bash
curl -s -o /dev/null -w "pypi jevfish: %{http_code}\n" https://pypi.org/pypi/jevfish/json
```
Expected: `404`. If it is `200` the name was taken since 18 Sep 2026 and a new name must be chosen before continuing.

```bash
uv build
uv publish --publish-url https://test.pypi.org/legacy/    # needs a TestPyPI token
```

- [ ] **Step 3: Prove `uvx` works end to end from TestPyPI**

```bash
JEVFISH_FAKE_JUDGE=1 JEVFISH_FAKE_LLM=1 \
  uvx --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ \
  jevfish demo --platform lite --rounds 2 --public 10 --stakeholders 3
```
Expected: the five stages complete. This is the exact command a new user will run, so it must pass before the README promises it.

- [ ] **Step 4: Add the release workflow**

```yaml
# .github/workflows/release.yml
name: release
on:
  push:
    tags: ["v*"]
permissions:
  contents: write
  id-token: write
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v5
      - name: Build the web app
        run: |
          cd jevfish/web && npm ci && npm run build
      - name: Build sdist and wheel
        run: cd jevfish && uv build
      - name: Check the wheel carries the UI
        run: |
          cd jevfish
          python3 -c "
          import zipfile, glob, sys
          z = zipfile.ZipFile(glob.glob('dist/*.whl')[0]); n = z.namelist()
          missing = [p for p in ('web_dist/index.html', 'examples/lazybee-cleaning.md')
                     if not any(p in x for x in n)]
          sys.exit('wheel is missing: ' + ', '.join(missing) if missing else 0)
          "
      - uses: softprops/action-gh-release@v3     # v2 is end-of-life on Node 20
        with:
          files: jevfish/dist/*
          generate_release_notes: true
      - name: Publish to PyPI
        run: cd jevfish && uv publish
```

The wheel check is the important step: it fails the release rather than shipping a build that serves a 404.

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml .github/workflows/release.yml
git commit -m "build: PyPI metadata and a release workflow that verifies the wheel"
```

---

## Task 4: Leave the fork network and take on JevFish's own identity

**This task needs Mark's explicit go-ahead before any step runs.** Leaving a fork network is not reversible through the UI.

- [ ] **Step 1: Confirm it is safe to detach**

```bash
gh api repos/markiewee/mirofish-jev \
  --jq '"stars=\(.stargazers_count) forks=\(.forks_count) issues=\(.open_issues_count) fork=\(.fork) parent=\(.parent.full_name)"'
```
Expected: `stars=0 forks=0 issues=0`. If any is non-zero, stop and re-check with Mark, because detaching moves those.

- [ ] **Step 2: Leave the fork network**

In the browser: repo Settings, scroll to the Danger Zone, "Leave fork network", confirm. There is no `gh` command for this.

- [ ] **Step 3: Verify the repo became searchable**

```bash
gh api repos/markiewee/mirofish-jev --jq '.fork'          # expect: false
sleep 60
gh api "search/repositories?q=repo:markiewee/mirofish-jev" --jq '.total_count'   # expect: 1
```

- [ ] **Step 4: Rename and set the metadata**

```bash
gh repo rename jevfish --repo markiewee/mirofish-jev
gh repo edit markiewee/jevfish \
  --description "Predict how a population will react. Simulates a crowd, polls every person, and tells you when the answer came from your prompt instead of the world." \
  --homepage "https://github.com/markiewee/jevfish" \
  --add-topic synthetic-survey --add-topic silicon-sampling \
  --add-topic agent-based-simulation --add-topic prediction \
  --add-topic forecasting --add-topic calibration \
  --add-topic market-research --add-topic llm-agents \
  --add-topic simulation --add-topic python
```

GitHub redirects the old URL, so existing clones keep working.

- [ ] **Step 5: Verify**

```bash
gh repo view markiewee/jevfish --json name,description,repositoryTopics,homepageUrl,isFork
```
Expected: `isFork: false`, 10 topics, JevFish's own description.

---

## Task 5: A README that leads with the install command

The benchmark from the comparable-projects survey: ollama puts its install command at 4 percent of the README, uv at 15 percent, MiroFish at 84 percent. The current root README puts JevFish's at roughly 2 percent but buries it under MiroFish's logo and badges.

**Files:**
- Rewrite: `README.md` (root)
- Move: current `README.md` to `docs/UPSTREAM-README.md`
- Modify: `README-ZH.md` (add a pointer to upstream, since it describes MiroFish not JevFish)

- [ ] **Step 1: Preserve the upstream README where the AGPL notice can point at it**

```bash
git mv README.md docs/UPSTREAM-README.md
git mv README-ZH.md docs/UPSTREAM-README-ZH.md
```

- [ ] **Step 2: Write the new root README**

```markdown
# JevFish

**Ask how a population will react. JevFish simulates a crowd, polls every person, and tells you when the answer came from your prompt instead of from the world.**

**See it work before you sign up for anything:**

```bash
JEVFISH_FAKE_JUDGE=1 JEVFISH_FAKE_LLM=1 uvx jevfish demo --platform lite
```

Ten seconds, no API keys, no account. Runs all five stages on deterministic stand-in
answers and prints a real report. Then, with keys:

```bash
uvx jevfish serve
```

That is the whole install. It opens in your browser and asks for the two keys on screen.
No clone, no Node, no Homebrew. About 66 MB.

<img src="docs/media/demo.gif" alt="JevFish running a five-rate price ladder" width="880">

<img src="docs/media/calibration.png" alt="Predicted share against actual outcome, before and after calibration" width="880">

*Above: what JevFish predicted against what happened. Nobody else in this market shows
you this plot.*

## What it does

You give it a yes-or-no question and the documents behind it. It then:

1. **Graph** reads the documents and pulls out the people, places and facts.
2. **Crowd** writes a segmented synthetic public plus the real named stakeholders.
3. **Simulate** lets them argue on a social feed, then polls every single one.
4. **Report** gives you the number, the segments behind it, and what moved.
5. **Ask** lets you interview any one of them afterwards.

Every person's judgment comes from a typed decision model, not from free text, so a
1,000-person poll costs cents rather than dollars.

## What it will not do

This is the part most tools leave out, so it goes above the screenshots.

- **The number is a share of the option set you described, not a real-world rate.** A
  listing with a 22 percent choice share can sit in a flat running at 89 percent
  occupancy, because occupancy is demand volume over supply. Converting one into the
  other needs at least one real resolved outcome, which JevFish will ask you for.
- **Without resolved outcomes it reports no confidence interval worth trusting.** On our
  own backtest the naive interval was 11.5 times too narrow, and it got narrower as we
  added people. JevFish now says which kind of interval you are looking at.
- **It checks whether it is quoting your own prompt.** Re-run any comparison with the
  per-option wording neutralised. On one real price ladder the shipped wording gave
  elasticity -1.43 and said cut the rate, while neutral wording gave -0.09 and said
  raise it. JevFish now flags that disagreement instead of printing a number.

Full write-up of what we measured, including the failures:
[docs/research/calibration-experiment.md](jevfish/docs/research/calibration-experiment.md).

## Install

| | Command | Size |
|---|---|---|
| Just the predictor | `uvx jevfish serve` | about 66 MB |
| With the OASIS social feed | `uv tool install 'jevfish[oasis]'` | about 1.1 GB |
| With PDF seed upload | `uv tool install 'jevfish[pdf]'` | plus 5 MB |
| Everything | `uv tool install 'jevfish[all]'` | about 1.1 GB |

No `uv`? `curl -LsSf https://astral.sh/uv/install.sh | sh`, or use `pipx install jevfish`.

You need a [TypeSafe](https://console.typesafe.ai/settings/keys) key and any
OpenAI-compatible key (a free Google Gemini key works). The app asks for both on first run
and checks them before spending anything.

### Try it with no keys at all

```bash
JEVFISH_FAKE_JUDGE=1 JEVFISH_FAKE_LLM=1 uvx jevfish demo --platform lite
```

Runs the whole pipeline on deterministic fake answers. Useful for seeing the shape of the
output and for CI.

## Credits and licence

JevFish is a rebuild of the five-stage pipeline from
**[MiroFish](https://github.com/666ghj/MiroFish)** by 666ghj, on a different decision
engine. The original MiroFish README is kept at
[docs/UPSTREAM-README.md](docs/UPSTREAM-README.md), and the upstream `backend/` and
`frontend/` trees are unchanged in this repository as reference.

Licensed **AGPL-3.0-or-later**, inherited from MiroFish. If you run a modified JevFish as a
network service, AGPL section 13 requires you to offer your users the corresponding source.
```

- [ ] **Step 3: Record the demo GIF**

```bash
mkdir -p docs/media
```

**Target 300 to 900 KB, not megabytes.** That is the band the best-presented tools sit in
(lazygit 665 KB, zoxide 627 KB). AnythingLLM's 30 MB GIF has to be hosted as a release
asset and Khoj's 19 MB one bloats every clone. Reference it with `<img src>` rather than
Markdown image syntax so it renders on the PyPI project page too.

Record the five-step flow at 1280x800. Use the `lite` platform with fake keys so it is
reproducible:

```bash
JEVFISH_FAKE_JUDGE=1 JEVFISH_FAKE_LLM=1 jevfish serve --port 5055
```

Then capture with any screen recorder and convert:

```bash
ffmpeg -i recording.mov -vf "fps=10,scale=880:-1:flags=lanczos,split[s0][s1];[s0]palettegen=max_colors=64[p];[s1][p]paletteuse" \
  -loop 0 docs/media/demo.gif
du -h docs/media/demo.gif
```
If it exceeds 900 KB, cut the clip shorter before cutting quality. A 12-second GIF that
shows one complete run beats a 40-second tour.

**The second image matters more than the GIF.** Generate a calibration plot from the
stored backtest: predicted share on one axis, actual outcome on the other, raw points and
calibrated points. It is the one claim no commercial vendor in this market makes, and it
is the reason to trust the tool rather than a picture of its buttons.

```bash
uv run python -c "
# Plot predicted against actual for every anchor on file. Matplotlib is a dev-only
# dependency: add it to [dependency-groups] dev, never to runtime.
import json, pathlib
from jevfish.anchors import load_anchors
from jevfish.calibrate import fit_map, apply_map
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
anchors = load_anchors(pathlib.Path('docs/demo/anchors.json'))
m = fit_map(anchors)
fig, ax = plt.subplots(figsize=(8.8, 4.4), dpi=100)
ax.plot([0,1],[0,1], lw=1, color='#999', ls='--', label='perfect')
ax.scatter([a.predicted for a in anchors], [a.actual for a in anchors], label='raw')
ax.scatter([apply_map([a.predicted], m)[0] for a in anchors], [a.actual for a in anchors], label='calibrated')
ax.set_xlabel('JevFish predicted share'); ax.set_ylabel('what actually happened')
ax.legend(frameon=False); fig.tight_layout()
fig.savefig('docs/media/calibration.png')
print('wrote docs/media/calibration.png')
"
```

This step depends on the accuracy plan's Tasks 5 and 6 being done, because it needs
`anchors.py` and `calibrate.py`. Until then, ship the GIF alone and leave the second
`<img>` out of the README rather than committing a placeholder.

- [ ] **Step 4: Verify every command in the README actually runs**

Run each of these and confirm it succeeds, because a README command that fails is worse
than no README:

```bash
JEVFISH_FAKE_JUDGE=1 JEVFISH_FAKE_LLM=1 uvx jevfish demo --platform lite --rounds 2 --public 10
uvx jevfish serve --help
```

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "docs: JevFish's own README, leading with the install command and the limits"
```

---

## Task 5b: Meet the AGPL obligations we are currently not meeting

Not optional, and cheap. The research found three specific gaps. This is a licence we
inherited, so the obligations are real whether or not anyone has complained.

**Files:**
- Create: `NOTICE`
- Create: `THIRD_PARTY.md`
- Modify: `README.md`, `docs/UPSTREAM-README.md`

- [ ] **Step 1: Date the modification notice (AGPL section 5(a))**

Section 5(a) requires modified files to carry prominent notices stating that you changed
them **and the date**. The current fork notice has no date. In `README.md`, the credits
section becomes:

```markdown
## Credits and licence

JevFish is a rebuild of the five-stage pipeline from
**[MiroFish](https://github.com/666ghj/MiroFish)** by 666ghj, running on a different
decision engine.

**Modifications by Mark Wee, from 17 September 2026.** The `jevfish/` tree is new work.
The upstream `backend/`, `frontend/`, `locales/`, `scripts/` and `static/` trees are
unmodified and kept as reference. The original MiroFish README is preserved at
[docs/UPSTREAM-README.md](docs/UPSTREAM-README.md).

### Licence

[![Licence: AGPL v3](https://img.shields.io/badge/licence-AGPL--3.0--or--later-blue.svg)](LICENSE)

JevFish is licensed **AGPL-3.0-or-later**, inherited from MiroFish. In plain terms:

- You may use, study, change and redistribute it.
- If you distribute a modified version, you must release your changes under the same
  licence, with a dated notice of what you changed.
- **Section 13:** if you run a modified JevFish as a service others reach over a network,
  you must offer those users the corresponding source of your version. A static replay
  of a finished run is not covered, because nothing is accepting requests.

Full text in [LICENSE](LICENSE). Third-party components and their licences are listed in
[THIRD_PARTY.md](THIRD_PARTY.md).
```

- [ ] **Step 2: Add the NOTICE file (AGPL section 4)**

```
JevFish
Copyright (c) 2026 Mark Wee

This product includes software developed as MiroFish
(https://github.com/666ghj/MiroFish), Copyright (c) 666ghj and contributors,
licensed under the GNU Affero General Public License version 3 or later.

JevFish is a derivative work. The jevfish/ directory is new work by Mark Wee,
first published 17 September 2026. The backend/, frontend/, locales/, scripts/
and static/ directories are unmodified upstream code retained for reference.

This program is distributed WITHOUT ANY WARRANTY, without even the implied
warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
Affero General Public License for more details.

"MiroFish" is used only to identify the upstream project. "Jev" and "TypeSafe"
are used only to identify TypeSafe AI's model and API. "Gemini" identifies
Google's model. No endorsement by any of them is claimed or implied, and none of
their logos are used.
```

- [ ] **Step 3: Add THIRD_PARTY.md**

```markdown
# Third-party components

| Component | Licence | Why it is here |
|---|---|---|
| [MiroFish](https://github.com/666ghj/MiroFish) | AGPL-3.0 | JevFish reimplements its five-stage pipeline. Upstream trees kept unmodified |
| [typesafe-sdk](https://pypi.org/project/typesafe-sdk/) | see package | Calls the Jev decision model |
| [Flask](https://flask.palletsprojects.com/) | BSD-3-Clause | HTTP API and static file serving |
| [openai](https://pypi.org/project/openai/) | Apache-2.0 | Any OpenAI-compatible endpoint |
| [python-dotenv](https://pypi.org/project/python-dotenv/) | BSD-3-Clause | Reads the key file |
| [pypdf](https://pypi.org/project/pypdf/) | BSD-3-Clause | Optional `[pdf]` extra, PDF seed upload |
| [camel-ai](https://github.com/camel-ai/camel), [camel-oasis](https://github.com/camel-ai/oasis) | Apache-2.0 | Optional `[oasis]` extra, the reddit and twitter feeds |
| [Vue](https://vuejs.org/) | MIT | The web app |

**Removed deliberately:** PyMuPDF, which is AGPL-3.0 or an Artifex commercial licence.
It was replaced by `pypdf` so that the optional PDF path carries no copyleft obligation
of its own and the install is 54 MB smaller.

**Trademarks:** product names are used for identification only. No affiliation with or
endorsement by TypeSafe AI, Google or the MiroFish authors is claimed.
```

- [ ] **Step 4: Stop advertising upstream's numbers**

```bash
git rm .github/workflows/update-star-history.yml
git rm -r .github/star-history
```

That workflow is 18,211 bytes of scheduled job charting `666ghj/MiroFish`'s star count.
Also delete, from the new `README.md`, the three `img.shields.io` badges pointing at
`666ghj/MiroFish` stars, watchers and forks, and the upstream Trendshift badge. Keep the
count of badges at or below five; past that they stop helping.

- [ ] **Step 5: Verify nothing still claims to be upstream**

```bash
grep -rn "666ghj\|mirofish.ai\|trendshift" README.md .github/ 2>/dev/null | grep -v UPSTREAM
```
Expected: only the credits link to `github.com/666ghj/MiroFish`, which is required
attribution, and nothing pointing at `mirofish.ai` or Trendshift.

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "docs: meet AGPL 4, 5(a) and 5(b), add NOTICE and THIRD_PARTY"
```

---

## Task 6: Repo hygiene and the social preview

- [ ] **Step 1: Contributing guide**

```markdown
<!-- CONTRIBUTING.md -->
# Contributing to JevFish

## Setup

```bash
git clone https://github.com/markiewee/jevfish
cd jevfish/jevfish
uv sync
uv run pytest -q
```

84 tests should pass in about 26 seconds. Nothing needs API keys.

## Running it

```bash
JEVFISH_FAKE_JUDGE=1 JEVFISH_FAKE_LLM=1 uv run jevfish serve
```

To change the web app you need Node: `cd web && npm ci && npm run dev`. The built app is
committed to `src/jevfish/web_dist`, so rebuild and commit it with any UI change.

## Tests that cost money

`uv run pytest -m live` calls real Jev and a real language model, and needs keys. It is
excluded by default via `addopts = "-m 'not live'"`. Run it before any release.

## What a good pull request looks like

- A failing test first, then the change that makes it pass.
- No new runtime dependency without a measured size figure. The core install is about
  66 MB and we intend to keep it there. Anything heavy goes in an optional extra.
- If you change anything that affects a prediction, say what you measured. "It feels
  better" is not reviewable. A two-cent probe against 40 personas is, and
  `docs/research/calibration-experiment.md` shows the format.
- No em-dashes in user-facing strings.

## Licence

AGPL-3.0-or-later. By contributing you agree your work ships under it.
```

- [ ] **Step 2: Bug report template**

```yaml
# .github/ISSUE_TEMPLATE/bug.yml
name: Bug report
description: Something did not work
labels: [bug]
body:
  - type: input
    id: version
    attributes:
      label: JevFish version
      description: "Output of: jevfish --version, or the commit you are on"
    validations:
      required: true
  - type: dropdown
    id: install
    attributes:
      label: How did you install it?
      options: [uvx, uv tool install, pipx, pip, from a git clone, JevFish.app]
    validations:
      required: true
  - type: dropdown
    id: platform
    attributes:
      label: Which run platform?
      options: [lite, reddit, twitter, "not applicable"]
  - type: textarea
    id: what
    attributes:
      label: What happened, and what did you expect instead?
    validations:
      required: true
  - type: textarea
    id: repro
    attributes:
      label: The exact command you ran
      render: shell
  - type: checkboxes
    id: offline
    attributes:
      label: Did you try it with fake keys?
      description: "JEVFISH_FAKE_JUDGE=1 JEVFISH_FAKE_LLM=1 jevfish demo --platform lite"
      options:
        - label: Yes, and it still happens
        - label: No
```

- [ ] **Step 3: Set the social preview image**

Create a 1280x640 PNG at `docs/media/social-preview.png` carrying the name, the one-line
description and the install command. Upload it in repo Settings, Social preview. This is
what renders when the repo is linked anywhere, and GitHub's default is the owner avatar
plus text, which reads as a personal scratch repo.

- [ ] **Step 4: Commit**

```bash
git add CONTRIBUTING.md .github/ISSUE_TEMPLATE/bug.yml docs/media/
git commit -m "docs: contributing guide, issue template, social preview"
```

---

## Task 7: A static demo anyone can try without installing

Upstream does exactly this at `666ghj.github.io/mirofish-demo/`: a pre-computed run served
as static files. No backend, no keys, and no AGPL section 13 exposure, because nothing is
being run as a service.

**Files:**
- Create: `.github/workflows/demo.yml`
- Create: `src/jevfish/web_dist` replay mode (a JSON fixture plus a query flag)

- [ ] **Step 1: Export a finished run as a static fixture**

```bash
uv run python -c "
import json, pathlib
from jevfish.service import Service
from jevfish.config import load_settings
svc = Service(load_settings())
pid, rid = 'p_71f65447c6', 'r_2f97f45e18'
out = {
  'project': svc.project(pid),
  'frame': svc.frame(pid),
  'crowd': svc.crowd(pid),
  'summary': svc.run(pid, rid)['summary'],
}
p = pathlib.Path('docs/demo/run.json'); p.parent.mkdir(parents=True, exist_ok=True)
p.write_text(json.dumps(out))
print('wrote', p, p.stat().st_size, 'bytes')
"
```

If any of those `Service` methods has a different name, read `src/jevfish/service.py` and
use the actual ones. Do not guess.

- [ ] **Step 2: Serve the fixture when there is no API**

In `web/src/lib/api.js`, add at the top of the module:

```js
// Static demo: when ?demo=1 is set, read a committed run instead of calling the API.
const DEMO = new URLSearchParams(location.search).get('demo') === '1'
let demoData = null
async function demo() {
  if (!demoData) demoData = await fetch('./run.json').then(r => r.json())
  return demoData
}
```

and in each read-only fetch helper, return the fixture slice when `DEMO` is set. Leave
every write path throwing a clear "this is a read-only demo" error.

- [ ] **Step 3: Publish it**

```yaml
# .github/workflows/demo.yml
name: demo
on:
  push:
    branches: [main]
    paths: ["jevfish/web/**", "jevfish/docs/demo/**"]
permissions:
  contents: read
  pages: write
  id-token: write
jobs:
  deploy:
    runs-on: ubuntu-latest
    environment:
      name: github-pages
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: "22" }
      - run: cd jevfish/web && npm ci && npm run build -- --base=./
      - run: cp jevfish/docs/demo/run.json jevfish/src/jevfish/web_dist/run.json
      - uses: actions/upload-pages-artifact@v3
        with: { path: jevfish/src/jevfish/web_dist }
      - uses: actions/deploy-pages@v4
```

- [ ] **Step 4: Verify and link it**

Open `https://markiewee.github.io/jevfish/?demo=1`, walk all five steps, confirm no
network call goes anywhere but `run.json`. Then add to the README, directly under the
install block:

```markdown
**Try it first:** [live demo](https://markiewee.github.io/jevfish/?demo=1), a real
finished run, no keys and no install.
```

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "feat(demo): static replay of a finished run on GitHub Pages"
```

---

## Task 8: Fix the Mac app, or retire it

The `.app` is a 148 KB unsigned shell that downloads 1 GB on first launch. `spctl` rejects
it, and the right-click-Open bypass was removed in macOS 15.0, so a user must visit System
Settings and click Open Anyway with an admin password. Notarization costs USD 99 a year and
would certify a wrapper, not the code it fetches.

Once `uvx jevfish serve` works, the app's only remaining job is serving people who will not
open a terminal.

- [ ] **Step 1: Ship a DMG instead of a ZIP**

Near-zero cost, and it does two things: it ends App Translocation, which the launcher
currently works around with `mdfind`, and it changes the Gatekeeper dialog's default button
from "Move to Trash" to "Open".

```bash
mkdir -p /tmp/jf-dmg && cp -R JevFish.app /tmp/jf-dmg/
ln -s /Applications /tmp/jf-dmg/Applications
hdiutil create -volname JevFish -srcfolder /tmp/jf-dmg -ov -format UDZO JevFish-macos.dmg
hdiutil verify JevFish-macos.dmg && echo "DMG OK"
```

**Keep the asset name free of the version number.** With `JevFish-macos.dmg` the URL
`https://github.com/markiewee/jevfish/releases/latest/download/JevFish-macos.dmg` is
permanently valid, so the README link never goes stale. `JevFish-v0.2.0.dmg` breaks it on
every release.

Also put the AGPL section 6(d) source pointer in the release body: the repository URL, the
tag and the commit SHA the artifact was built from.

- [ ] **Step 2: Attach it to the release**

In `.github/workflows/release.yml`, the `files:` list becomes:

```yaml
        with:
          files: |
            jevfish/dist/*
            JevFish-macos.dmg
          generate_release_notes: true
```

Building the DMG needs a macOS runner, so add a second job with `runs-on: macos-latest`
that builds the DMG and uploads it as an artifact the release job consumes.

- [ ] **Step 3: Tell the truth about it in the README**

Under Install, after the table:

```markdown
### Mac, without a terminal

Download `JevFish.dmg` from the [latest release](https://github.com/markiewee/jevfish/releases/latest),
drag it to Applications, and open it. It is not code-signed, so the first launch needs
System Settings, Privacy and Security, Open Anyway. If that annoys you, `uvx jevfish serve`
does the same thing in one line and skips the dialog.
```

- [ ] **Step 4: Decide on notarization**

Do not spend the USD 99 yet. Revisit only if release download counts show the DMG
outpacing PyPI installs. Record the decision so it is not re-litigated:

```markdown
<!-- append to CONTRIBUTING.md -->
## Why the Mac app is not signed

Signing and notarizing costs USD 99 a year and would certify a 148 KB launcher that
downloads everything it runs afterwards, so it would attest to almost nothing. `uvx` is a
one-line install with no Gatekeeper dialog at all, so it is the recommended path and the
`.app` is a convenience. Revisit if DMG downloads overtake PyPI installs.
```

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "build(mac): ship a DMG, and say plainly that it is unsigned"
```

---

## Task 9: Silence the debug output

A 24-person run prints 28 raw `user_profile` dicts to stdout. It is the first thing a new
user sees.

**Files:**
- Modify: `src/jevfish/platforms/oasis_platform.py`
- Test: `tests/test_platforms.py`

- [ ] **Step 1: Write the failing test**

```python
# append to tests/test_platforms.py
def test_lite_run_prints_nothing_to_stdout(capsys, tmp_path):
    from jevfish.platforms import make_platform

    p = make_platform("lite", tmp_path)
    agents = [{"agent_id": i, "username": f"u{i}", "persona": "x", "name": f"n{i}",
               "bio": "b", "follows": [], "activity": 0.5, "influence": 0.1} for i in range(3)]
    p.start(agents)
    out = capsys.readouterr()
    assert out.out == "", f"unexpected stdout: {out.out[:200]}"
```

Read `src/jevfish/platforms/lite.py` for the real `start` signature and match it. If the
lite platform has no `start`, point this test at whichever method the simulation calls
first.

- [ ] **Step 2: Run test to verify it fails or passes**

Run: `uv run pytest tests/test_platforms.py -v`

If it passes, the printing is in the OASIS path only. Write the equivalent test for
`OasisPlatform`, marked `@pytest.mark.skipif` on `oasis` not being importable, and proceed.

- [ ] **Step 3: Route the noise through logging**

Find the `print` calls in `src/jevfish/platforms/oasis_platform.py` (and any in the vendored
`oasis` interaction path we control) and replace each with:

```python
import logging

log = logging.getLogger(__name__)
...
log.debug("agent profile: %s", profile)
```

If the printing comes from inside the `oasis` package itself rather than our code, suppress
it at the import boundary in `_import_oasis` instead:

```python
    import logging

    logging.getLogger("oasis").setLevel(logging.WARNING)
```

and, if it is a bare `print` inside the dependency, wrap the platform's own `start` in
`contextlib.redirect_stdout(io.StringIO())` and log the captured text at debug level. Do not
leave it printing.

- [ ] **Step 4: Verify on a real run**

```bash
JEVFISH_FAKE_JUDGE=1 JEVFISH_FAKE_LLM=1 uv run jevfish demo --rounds 3 --public 20 --stakeholders 4 2>&1 \
  | grep -c "user_profile"
```
Expected: `0`

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "fix(platforms): send agent-profile debug output to the logger"
```

---

## Task 10: Fix the overlapping chart labels

Found on the report page: the stance histogram's x-axis labels run into each other
("Rules it out: clearly wo..." overlapping "Leans towards somewhe...").

**Files:**
- Modify: `web/src/components/GroupedBars.vue`

- [ ] **Step 1: Reproduce it**

```bash
JEVFISH_FAKE_JUDGE=1 JEVFISH_FAKE_LLM=1 uv run jevfish serve --port 5055
```

Open the report page for a project with five stance levels and confirm the overlap at a
1280 px window width.

- [ ] **Step 2: Fix it**

Stance levels are full sentences by design (`FRAME_SYSTEM` requires "a concrete situation,
not a degree word"), so they will never fit horizontally. In `GroupedBars.vue`, truncate the
axis label to its first three words with a `title` attribute carrying the full text, and
stagger alternate labels onto a second line:

```vue
<text
  v-for="(label, i) in labels"
  :key="i"
  :x="bandCentre(i)"
  :y="axisY + (i % 2 ? 26 : 12)"
  text-anchor="middle"
  class="axis-label"
>
  {{ shortLabel(label) }}
  <title>{{ label }}</title>
</text>
```

```js
function shortLabel(text) {
  const words = String(text).split(/\s+/)
  return words.length <= 3 ? text : words.slice(0, 3).join(' ') + '...'
}
```

Increase the chart's bottom margin by 20 px so the staggered row is not clipped.

- [ ] **Step 3: Rebuild and verify**

```bash
cd web && npm ci && npm run build && cd ..
JEVFISH_FAKE_JUDGE=1 JEVFISH_FAKE_LLM=1 uv run jevfish serve --port 5055
```

Confirm at 1280 px and at 390 px (iPhone width) that no two labels overlap and hovering
shows the full sentence.

- [ ] **Step 4: Commit**

```bash
git add web/src/components/GroupedBars.vue src/jevfish/web_dist
git commit -m "fix(web): stop stance-axis labels overlapping"
```

---

## Sequencing

Tasks 1, 2 and 3 are the critical path and must go in that order: the wheel has to carry
the UI before the extras are worth measuring, and both have to be right before anything is
published to PyPI under a name we only get to use once.

Task 4 needs Mark's go-ahead and is otherwise independent.

Task 5b can go first and should. It is a legal obligation, it takes under an hour, and it
does not depend on anything else. Doing it before Task 4 also means the repo is compliant
at the moment it becomes findable.

Task 5 depends on Tasks 1 to 3, because the README promises `uvx jevfish serve` and must
not promise it before Step 8 of Task 1 returns a 200.

Tasks 6, 9 and 10 are independent and can run at any point.

Task 7 depends on Task 1, since the demo serves from `web_dist`.

Task 8 depends on Task 3, because the README's honest recommendation of `uvx` over the DMG
only makes sense once `uvx` works.

---

## Self-review

**Spec coverage.** Fork invisibility: Task 4. Repo identity: Task 4. One-line install: Tasks 1, 2, 3. Install size: Task 2. Hero media and README structure: Task 5. Keyless demo promoted to the first command: Task 5 Step 2. AGPL sections 4, 5(a), 5(b) and 6(d), NOTICE, THIRD_PARTY, and removing upstream's badges and star-history workflow: Task 5b and Task 8 Step 1. PyMuPDF's independent AGPL obligation: Task 2 Step 4. Releases with stable asset URLs: Task 3 Step 4, Task 8 Steps 1 and 2. Hosted demo: Task 7. Repo hygiene and social preview: Task 6. Discoverability vocabulary: Task 3 Step 1 keywords and Task 4 Step 4 topics. Name availability: Task 3 Step 2. UI defects: Tasks 9, 10.

**Deliberately deferred, with the reason:** Apple Developer Program and notarization (USD 99 a year to seal a 148 KB shell around 1 GB fetched at runtime; Task 8 Step 4 records the decision). PyInstaller or Nuitka freezing (30 to 60 hours, and worth revisiting only after Task 2 brings the tree to 66 MB). Tauri (60 to 120 hours). An interactive hosted demo (Task 7's static replay gets the credibility with no AGPL section 13 exposure and no hosting bill). A Docker image, which is documented as a Linux and power-user path but never the headline, because Docker Desktop costs the visitor about 6 GB and a licensing question. A rename away from "Jev", which is not warranted: the practice is unpoliced in that ecosystem and TypeSafe's terms contain no naming clause. One item stays genuinely open: a manual USPTO check of `JEV` in classes 9 and 42 at tmsearch.uspto.gov before the name goes on anything commercial, since USPTO blocks automated queries.

**Placeholder scan.** No TBDs. Where the exact code cannot be known in advance (the `Service` method names in Task 7 Step 1, the lite platform's first method in Task 9 Step 1, the source of the stray `print` in Task 9 Step 3), the step says to read the specific file and gives the fallback rather than inventing a signature. Task 2 Step 7 and Task 3 Step 2 both carry an explicit stop condition instead of assuming the happy path.

**Type consistency.** `assets.web_dist()`, `assets.examples_dir()`, `assets.example_seed()`, `assets.data_dir()` and `assets.env_file()` all return `Path` and are called with those names in `config.py`, `api.py` and `example.py`. `OASIS_HINT` is defined once in `platforms/base.py` and imported by `oasis_platform.py`, formatted with the single field `kind` at both call sites. The published path `src/jevfish/web_dist` is used identically in `pyproject.toml`, `vite.config.js`, both workflows and Task 10's commit.
