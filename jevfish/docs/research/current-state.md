# JevFish current state: code audit, 18 Sep 2026

Read of every file in `src/jevfish/` plus a live offline run and five UI screenshots.
This is the baseline the improvement plan is written against.

## What is already good

The engine is genuinely well built. 4,027 lines of Python, 26 modules, no module over 464
lines, every file carrying a docstring that says why it exists.

- `judge.py` has the right abstraction. Everything talks to a `Judge` protocol, and the
  standard stack is `CachingJudge(Meter(TypeSafeJudge()))`, so reruns are free and a budget
  is enforced before any money moves. A `FakeJudge` makes the whole pipeline runnable with
  no keys and no network, which is rare and valuable.
- The pipeline is honestly separated: `graph` then `frame` plus `crowd` then `simulate`
  then `report`. Each stage persists, so a stage can be rerun without redoing the last one.
- The web app is better than expected: clean type, working light and dark modes, a five-step
  nav, a live request estimate with a cost figure before you spend anything.
- Offline verification passed. `JEVFISH_FAKE_JUDGE=1 JEVFISH_FAKE_LLM=1 uv run jevfish demo`
  completed the full five stages in one pass, 131 requests, no failures.

## The accuracy gaps, located in the code

### 1. There is no calibration layer at all

`metrics.py:16` `summarize_poll` is the whole of it:

```python
expected = sum(ps)                      # ps = raw Jev noul probabilities
...
"mean_outcome": expected / n if n else 0.0,
```

`mean_outcome` is the unweighted arithmetic mean of raw model probabilities. Nothing maps
model output to observed frequency. This is the direct cause of the measured -32.4pp level
error on the Pureloft backtest: the number is a mean model score being read as a rate.

### 2. The intervals are knowingly wrong, and the code says so

`metrics.py:6`: "The 90% range covers only that chance element, not model error."

Variance is Poisson-binomial, `sum p(1-p)`, so the interval only covers the sampling noise
of a synthetic crowd that does not exist. Model error, frame error and crowd-composition
error are all excluded. On the Pureloft run the true error was 32pp while the stated 90%
range was a few points wide. An interval that excludes the dominant error term is worse
than no interval, because it invites trust.

### 3. The crowd composition is invented by the LLM, ungrounded

`crowd.py:22` `PLAN_SYSTEM` asks the LLM to output segments with `share` weights, then
`sample_public` (`crowd.py:149`) draws people from exactly those shares. Nothing checks
those shares against a real population. There is no post-stratification, no census
marginals, no target distribution to weight back to. The crowd's makeup is a guess, and the
level of the answer is a direct function of the makeup.

### 4. Option order is fixed, so order bias is baked in

`ChoiceQ.criteria` is a plain `dict` and is passed through in insertion order
(`judge.py:94`, `policy.py:140`). Every persona sees the options in the same order every
time. Any primacy or recency effect in the judge applies identically to all N people, so it
does not average out. It becomes a systematic shift in the answer, not noise.

### 5. One frame, one crowd draw, one seed. No ensemble

A run uses a single LLM-written frame and a single sampled crowd. Frame wording is known to
be the largest lever (rewriting rivals as differentiated moved measured elasticity from
-3.29 to -1.93, a bigger move than anything else we tried), yet the run treats one frame's
output as the answer. Nothing varies the frame, the seed or the crowd draw and pools the
results.

### 6. There is no scoring harness

No Brier score, no log score, no calibration curve, no reliability diagram, nothing in
`metrics.py` that takes a known outcome as input. Every backtest so far was arithmetic done
by hand outside the tool. The tool cannot tell you how accurate it has been, which means it
cannot improve and a user cannot decide whether to trust it.

### 7. The report leads with the wrong number

The variant cards show `expected_yes` as a raw count ("454.9"). A prediction tool's first
line should be a rate with an honest interval. The screenshot of the report page leads with
an empty "No report yet" panel instead of the answer.

## The adoption gaps

### 8. The GitHub front door belongs to MiroFish, not JevFish

Confirmed against the live repo:

| Field | Current value |
|---|---|
| repo name | `mirofish-jev` |
| description | "A Simple and Universal Swarm Intelligence Engine, Predicting Anything. 简洁通用的群体智能引擎，预测万物" |
| homepage | `https://mirofish.ai` |
| topics | none |
| stars | 0 |
| releases | `v0.1.0`, `v0.1.1`, `v0.1.2`, all inherited upstream tags, no JevFish release |
| root README first screen | MiroFish logo, MiroFish Trendshift badge, MiroFish star and Discord badges, MiroFish's vision statement |

JevFish appears as a blockquote at the top pointing into a subfolder. A visitor landing here
reads it as somebody's fork of a Chinese prediction engine. Nothing tells them JevFish is a
thing they can download, and there is no artifact to download.

### 9. The install path is one unsigned Mac app inside that fork

`JevFish.app` is unsigned and un-notarized, so macOS Gatekeeper blocks it and the README has
to teach the user to click through Privacy and Security. It also breaks if the folder sits in
Desktop, Documents or Downloads, because those directories need TCC permission the app does
not have, so it silently falls back to a Terminal window. There is no Linux path, no Windows
path, no one-line install, and no hosted demo to try before downloading.

### 10. Debug output leaks to stdout

The OASIS layer prints a raw `user_profile` dict per agent during a run (28 lines in a
24-person run). Cosmetic, but it is the first thing a new user sees in their terminal.

## Verification notes

- Offline run: `JEVFISH_FAKE_JUDGE=1 JEVFISH_FAKE_LLM=1 uv run jevfish demo --rounds 4
  --public 24 --stakeholders 5` completed, 131 requests, 0 LLM failures.
- UI screenshots taken with Playwright at 1600x1000, deviceScaleFactor 2, against a local
  server on port 5055 with the real Pureloft backtest project loaded.
- One visual defect found: on the report page, the stance-histogram x-axis labels overlap
  each other and are unreadable ("Rules it out: clearly wo..." running into "Leans towards
  somewhe...").
- Chrome extension was not connected, so Playwright was used per the escalation ladder.

---

## Finding 11: the install is 1.1 GB, and 97 percent of it is never used

Measured against the working `.venv`, and then proved by building a clean one.

`pyproject.toml` declares `camel-ai==0.2.78` and `camel-oasis==0.2.5` as hard dependencies.
Those two pull the entire PyTorch machine-learning stack transitively:

| Package | Size | Used by JevFish? |
|---|---|---|
| torch 2.14.0 | 553 MB | No. Pulled in by `sentence-transformers`, itself pulled by camel-ai |
| scipy | 83 MB | No |
| transformers | 59 MB | No |
| pymupdf | 59 MB | Only for optional PDF seed upload |
| pandas | 49 MB | No |
| sympy | 42 MB | No |
| sklearn | 34 MB | No |
| numpy | 26 MB | No |
| camel | 10 MB | Only for the OASIS reddit and twitter platforms |
| **total venv** | **1.1 GB** | |

JevFish makes HTTP calls to Jev and to an OpenAI-compatible endpoint. It does no local
inference and no numerical work beyond the arithmetic in `metrics.py`. None of the ML stack
is needed for the prediction itself.

### The code is already structured for this

Both heavy imports are already lazy:

- `platforms/base.py:67` `make_platform` imports `LitePlatform` or `OasisPlatform` inside
  the function body, so nothing camel-shaped loads unless a reddit or twitter run starts.
- `service.py:59` imports `fitz` (pymupdf) inside the PDF branch only.

So the dependency declaration is the only thing forcing the 1.1 GB download. The runtime
already does the right thing.

### Proved with a clean environment

Built a fresh Python 3.12 venv with only `flask`, `openai`, `python-dotenv` and
`typesafe-sdk`:

```
installed size: 26 MB   (against 1,100 MB now)
camel      installed: False
oasis      installed: False
torch      installed: False
pymupdf    installed: False
```

Then ran the full five-stage pipeline in it:

```
JEVFISH_FAKE_JUDGE=1 JEVFISH_FAKE_LLM=1 python -m jevfish.cli demo \
  --platform lite --rounds 3 --public 20 --stakeholders 4
```

It completed: graph, prepare (8 talking points, 3 stakeholders, 20 public), a 97-request run,
and a report. No import errors, no missing modules.

### What this is worth

**26 MB against 1.1 GB, a 42x reduction, for a change to `pyproject.toml` and a clear error
message when someone picks a reddit or twitter run without the extra installed.**

It also removes the reason `requires-python` is pinned to `>=3.12,<3.13`. That pin almost
certainly comes from camel-ai's own constraint, and it currently blocks every user on 3.13
or 3.14 for a dependency they will never call. Widening it needs checking, not assuming.

The shape of the fix:

```toml
requires-python = ">=3.11"
dependencies = ["flask>=3.0", "openai>=1.0", "python-dotenv>=1.0", "typesafe-sdk>=0.6.0"]

[project.optional-dependencies]
oasis = ["camel-ai==0.2.78", "camel-oasis==0.2.5"]   # reddit and twitter platforms
pdf   = ["pymupdf>=1.24"]                             # PDF seed upload
all   = ["jevfish[oasis,pdf]"]
```

`jevfish` is unclaimed on PyPI (404), and `[project.scripts]` already exposes a `jevfish`
console script. So `uvx jevfish serve` becomes a genuine one-line install with no fork, no
unsigned app bundle and no Gatekeeper dialog. That is the cheapest large adoption win
available, and it is mostly packaging rather than engineering.
