# JevFish Prediction Accuracy Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stop JevFish reporting a number it cannot justify, by removing the frame artifact that currently dictates its answers, adding a scoring harness that can measure accuracy, and adding a calibration layer with honest intervals fitted from real anchor outcomes.

**Architecture:** Four new modules behind the existing pipeline, none of which change how a run executes. `frame_audit.py` validates and neutralises per-option wording and reports frame sensitivity. `scoring.py` holds proper scoring rules and takes resolved outcomes as input. `calibrate.py` fits and applies a per-persona monotone logit map plus split-conformal intervals. `anchors.py` stores resolved outcomes on disk. `metrics.summarize_poll` grows optional calibration and honest-interval arguments and keeps its current behaviour when they are absent, so nothing existing breaks.

**Tech Stack:** Python 3.12, pytest, no new runtime dependencies (all maths is stdlib `math` and `statistics`; do not add numpy or scipy, see the packaging plan).

---

## Why this order

Established by measurement in `docs/research/calibration-experiment.md`, not by preference:

| Finding | Measured effect | Priority |
|---|---|---|
| Frame wording sets the slope | elasticity -1.432 vs -0.090 on identical inputs; flips the decision | 1 |
| No scoring harness exists | cannot measure whether any change helps | 2 |
| Interval excludes model error | true error was 11.5x the stated half-width | 3 |
| No calibration layer | level error -32.4pp; 1 anchor removes it | 4 |
| Option order fixed | literature: randomising collapsed 43 models toward uniform | 5 |
| Persona enrichment | sd up 2.4x but mean moved away from truth; literature 0.748 vs 0.734 | deprioritised |
| Exogeneity sentence | -0.001. Does not replicate on Jev | dropped |

Task 1 comes first because no downstream correction recovers a slope that was dictated by the prompt.

---

## File Structure

| File | Responsibility |
|---|---|
| Create `src/jevfish/frame_audit.py` | Detect comparative or evaluative language in per-variant subject values; produce a neutralised copy of a frame; nothing else |
| Create `src/jevfish/scoring.py` | Proper scoring rules and decomposition. Pure functions, no I/O |
| Create `src/jevfish/calibrate.py` | Fit and apply `sigmoid(a + b*logit(q))`; split-conformal half-widths. Pure functions plus a small dataclass |
| Create `src/jevfish/anchors.py` | Read and write resolved outcomes as JSON on disk |
| Modify `src/jevfish/frame.py` | Add the neutrality rule to `FRAME_SYSTEM`; call the audit from `normalize_frame` |
| Modify `src/jevfish/metrics.py` | `summarize_poll` accepts an optional calibration map and an optional honest half-width |
| Modify `src/jevfish/policy.py` | Randomise `ChoiceQ` option order per person, deterministically from the seed |
| Test files mirror each module under `tests/` | |

Each module is under 150 lines. `scoring.py` and `calibrate.py` are pure so they can be tested without keys or network.

---

## Task 1: Detect comparative language in per-option wording

This is the fix for the finding that decided a revenue recommendation on one adjective.

**Files:**
- Create: `src/jevfish/frame_audit.py`
- Test: `tests/test_frame_audit.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_frame_audit.py
from jevfish.frame_audit import comparative_spans, audit_variants


def test_flags_the_exact_strings_that_broke_the_pureloft_run():
    # These are verbatim from the stored frame that produced elasticity -1.432.
    assert comparative_spans("a third below the current rate") == ["below", "current"]
    assert comparative_spans("two thirds above the current rate") == ["above", "current"]
    assert comparative_spans("the rate Pureloft actually charges") == ["actually"]


def test_passes_neutral_wording():
    assert comparative_spans("the nightly rate for these dates") == []
    assert comparative_spans("MYR 300 per night") == []


def test_audit_reports_per_variant_and_per_key():
    variants = [
        {"id": "p300", "label": "MYR 300", "subject": {"rate_note": "the current rate"}},
        {"id": "p500", "label": "MYR 500", "subject": {"rate_note": "well above market"}},
    ]
    problems = audit_variants(variants)
    assert problems == [
        {"variant": "p300", "key": "rate_note", "terms": ["current"]},
        {"variant": "p500", "key": "rate_note", "terms": ["above"]},
    ]


def test_audit_is_quiet_when_options_differ_only_in_the_quantity():
    variants = [
        {"id": "a", "label": "MYR 300", "subject": {"nightly_rate_myr": 300}},
        {"id": "b", "label": "MYR 500", "subject": {"nightly_rate_myr": 500}},
    ]
    assert audit_variants(variants) == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_frame_audit.py -v`
Expected: FAIL, `ModuleNotFoundError: No module named 'jevfish.frame_audit'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/jevfish/frame_audit.py
"""Catch per-option wording that tells the judge which option is better.

A frame that labels one option "a third below the current rate" does not measure a
price response, it states one. On the Pureloft ladder that wording alone moved fitted
elasticity from -0.090 to -1.432 and flipped the revenue recommendation. See
docs/research/calibration-experiment.md, Finding 7.
"""

from __future__ import annotations

import re

# Words that position an option against another option or against a norm.
COMPARATIVE = (
    "above", "below", "higher", "lower", "cheaper", "dearer", "more", "less",
    "current", "existing", "status quo", "baseline", "today", "actually",
    "premium", "discount", "discounted", "market rate", "well above", "well below",
    "better", "worse", "best", "worst", "aggressive", "conservative",
    "third above", "third below", "double", "half",
)


def comparative_spans(text: str) -> list[str]:
    """Comparative terms present in `text`, in the order COMPARATIVE lists them."""
    low = str(text).lower()
    found = []
    for term in COMPARATIVE:
        if re.search(rf"\b{re.escape(term)}\b", low) and term not in found:
            found.append(term)
    return found


def audit_variants(variants: list[dict]) -> list[dict]:
    """One row per (variant, key) whose value carries comparative language."""
    problems = []
    for v in variants:
        for key, value in (v.get("subject") or {}).items():
            if not isinstance(value, str):
                continue
            terms = comparative_spans(value)
            if terms:
                problems.append({"variant": v["id"], "key": key, "terms": terms})
    return problems
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_frame_audit.py -v`
Expected: PASS, 4 passed

Note the first test asserts multi-word terms are not double-reported: "a third below the current rate" matches `below` and `current` but also `third below`. Fix by checking longer terms first and skipping a term whose span is already covered, or by asserting the actual returned list. If the implementation returns `["below", "current", "third below"]`, change `COMPARATIVE` iteration to sort by descending length and drop overlaps:

```python
def comparative_spans(text: str) -> list[str]:
    low = str(text).lower()
    hits: list[tuple[int, str]] = []
    for term in COMPARATIVE:
        m = re.search(rf"\b{re.escape(term)}\b", low)
        if m:
            hits.append((m.start(), term))
    hits.sort()
    out: list[str] = []
    covered: list[tuple[int, int]] = []
    for start, term in sorted(hits, key=lambda h: -len(h[1])):
        end = start + len(term)
        if any(s <= start and end <= e for s, e in covered):
            continue
        covered.append((start, end))
        out.append(term)
    return [t for _, t in sorted((low.index(t), t) for t in out)]
```

Re-run until the asserted lists match exactly.

- [ ] **Step 5: Commit**

```bash
git add src/jevfish/frame_audit.py tests/test_frame_audit.py
git commit -m "feat(frame): detect comparative wording in per-option text"
```

---

## Task 2: Produce a neutralised copy of a frame

**Files:**
- Modify: `src/jevfish/frame_audit.py`
- Test: `tests/test_frame_audit.py`

- [ ] **Step 1: Write the failing test**

```python
# append to tests/test_frame_audit.py
from jevfish.frame_audit import neutralise


def test_neutralise_drops_offending_keys_and_keeps_the_quantity():
    frame = {
        "subject": {"property": "a 4-bedroom apartment"},
        "variants": [
            {"id": "p300", "label": "MYR 300 (current)",
             "subject": {"nightly_rate_myr": 300, "rate_note": "the current rate"}},
            {"id": "p500", "label": "MYR 500",
             "subject": {"nightly_rate_myr": 500, "rate_note": "two thirds above the current rate"}},
        ],
    }
    out = neutralise(frame)
    assert out["variants"][0]["subject"] == {"nightly_rate_myr": 300}
    assert out["variants"][1]["subject"] == {"nightly_rate_myr": 500}
    assert out["variants"][0]["label"] == "MYR 300"
    assert frame["variants"][0]["subject"]["rate_note"] == "the current rate"  # input untouched


def test_neutralise_is_a_no_op_on_a_clean_frame():
    frame = {"subject": {}, "variants": [{"id": "a", "label": "A", "subject": {"price": 1}}]}
    assert neutralise(frame) == frame
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_frame_audit.py::test_neutralise_drops_offending_keys_and_keeps_the_quantity -v`
Expected: FAIL, `ImportError: cannot import name 'neutralise'`

- [ ] **Step 3: Write minimal implementation**

```python
# append to src/jevfish/frame_audit.py
import copy


def neutralise(frame: dict) -> dict:
    """A deep copy of `frame` with comparative per-option text removed.

    Keys whose value carries comparative language are dropped from every variant, so
    the options differ only in the quantities under test. Labels are stripped of
    parenthetical asides such as "(current)".
    """
    out = copy.deepcopy(frame)
    bad_keys = {p["key"] for p in audit_variants(out.get("variants") or [])}
    for v in out.get("variants") or []:
        subject = v.get("subject") or {}
        v["subject"] = {k: val for k, val in subject.items() if k not in bad_keys}
        v["label"] = re.sub(r"\s*\([^)]*\)\s*$", "", str(v.get("label", ""))).strip()
    return out
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_frame_audit.py -v`
Expected: PASS, 6 passed

- [ ] **Step 5: Commit**

```bash
git add src/jevfish/frame_audit.py tests/test_frame_audit.py
git commit -m "feat(frame): neutralise comparative per-option wording"
```

---

## Task 3: Refuse to build a frame with comparative option wording

**Files:**
- Modify: `src/jevfish/frame.py:19-39` (the `FRAME_SYSTEM` prompt) and `normalize_frame`
- Test: `tests/test_frame_crowd.py`

- [ ] **Step 1: Write the failing test**

```python
# append to tests/test_frame_crowd.py
import pytest
from jevfish.frame import FrameError, normalize_frame

BASE = {
    "question": "q",
    "outcome": {"instructions": "would they book?"},
    "stance": {"levels": ["no", "maybe", "yes"]},
    "talking_points": [{"id": "p", "text": "a point", "side": "pro"}],
}


def test_normalize_frame_rejects_comparative_variant_wording():
    data = {**BASE, "variants": [
        {"id": "a", "label": "MYR 300", "subject": {"rate": 300, "note": "the current rate"}},
        {"id": "b", "label": "MYR 500", "subject": {"rate": 500, "note": "well above market"}},
    ]}
    with pytest.raises(FrameError) as e:
        normalize_frame(data, "q")
    assert "note" in str(e.value)
    assert "current" in str(e.value)


def test_normalize_frame_accepts_options_differing_only_in_the_quantity():
    data = {**BASE, "variants": [
        {"id": "a", "label": "MYR 300", "subject": {"rate": 300}},
        {"id": "b", "label": "MYR 500", "subject": {"rate": 500}},
    ]}
    frame = normalize_frame(data, "q")
    assert [v["subject"] for v in frame["variants"]] == [{"rate": 300}, {"rate": 500}]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_frame_crowd.py::test_normalize_frame_rejects_comparative_variant_wording -v`
Expected: FAIL, `DID NOT RAISE <class 'jevfish.frame.FrameError'>`

- [ ] **Step 3: Write minimal implementation**

In `src/jevfish/frame.py`, add the import at the top of the imports block:

```python
from .frame_audit import audit_variants
```

Replace the two `FRAME_SYSTEM` rule lines currently reading:

```
- variants only when the question compares options; otherwise an empty list. The first variant is the status quo.
- Every variant, including the status quo, sets the same changing subject keys to its own values (for example price and cleaning), so each option is fully described. Keep facts shared by all options in subject.
```

with:

```
- variants only when the question compares options; otherwise an empty list.
- Every variant sets the same changing subject keys to its own values (for example price and cleaning), so each option is fully described. Keep facts shared by all options in subject.
- NEVER position one option against another or against a norm. Do not write "the current rate", "a third above", "cheaper", "the baseline", "premium", "discounted", or any word that says which option is better, higher, lower or usual. Each option states only its own facts. A reader must not be able to tell from an option's own text which one is the incumbent. Labels are the bare value, for example "MYR 300", never "MYR 300 (current)".
```

Then in `normalize_frame`, immediately after the `variants` list is built and before `if not variants:`, insert:

```python
    problems = audit_variants(variants)
    if problems:
        detail = "; ".join(
            f"variant {p['variant']} key '{p['key']}' says {', '.join(p['terms'])}" for p in problems
        )
        raise FrameError(
            "variant wording positions the options against each other, which dictates the "
            f"result instead of measuring it: {detail}"
        )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_frame_crowd.py -v`
Expected: PASS

Run: `uv run pytest -q`
Expected: PASS. If a stored fixture frame now fails, that fixture contains the artifact and its expected value must be updated, not the validator.

- [ ] **Step 5: Commit**

```bash
git add src/jevfish/frame.py tests/test_frame_crowd.py
git commit -m "feat(frame): refuse frames whose option wording dictates the answer"
```

---

## Task 4: Proper scoring rules

**Files:**
- Create: `src/jevfish/scoring.py`
- Test: `tests/test_scoring.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_scoring.py
import math
import pytest
from jevfish.scoring import brier, log_score, crps_share, murphy_decomposition, skill_score


def test_brier_is_squared_error():
    assert brier([1.0], [1]) == 0.0
    assert brier([0.0], [1]) == 1.0
    assert brier([0.5, 0.5], [1, 0]) == 0.25


def test_log_score_is_negative_log_likelihood_and_clips_certainty():
    assert log_score([0.5], [1]) == pytest.approx(math.log(2))
    assert log_score([1.0], [1]) == pytest.approx(0.0, abs=1e-9)
    assert log_score([0.0], [1]) < 40           # clipped, not infinite
    assert math.isfinite(log_score([0.0], [1]))


def test_crps_share_is_absolute_error_for_a_point_forecast():
    assert crps_share([0.6], [0.6]) == 0.0
    assert crps_share([0.568], [0.892]) == pytest.approx(0.324, abs=1e-9)


def test_murphy_decomposition_separates_level_from_shape():
    # Predictions perfectly ordered but uniformly 0.3 too low.
    preds = [0.1, 0.3, 0.5, 0.7]
    truth = [0.4, 0.6, 0.8, 1.0]
    d = murphy_decomposition(preds, truth)
    assert d["bias"] == pytest.approx(-0.3)
    assert d["spearman"] == pytest.approx(1.0)
    assert d["mae"] == pytest.approx(0.3)


def test_skill_score_against_a_named_baseline():
    # model mae 0.1, baseline mae 0.4 -> 75% of the baseline error removed
    assert skill_score(0.1, 0.4) == pytest.approx(0.75)
    assert skill_score(0.4, 0.4) == 0.0
    assert skill_score(0.8, 0.4) == pytest.approx(-1.0)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_scoring.py -v`
Expected: FAIL, `ModuleNotFoundError: No module named 'jevfish.scoring'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/jevfish/scoring.py
"""Proper scoring rules, and a decomposition that separates level error from shape error.

Brier and log score are proper for a binary outcome. CRPS is proper for a share.
Expected Calibration Error is deliberately absent: it is not a proper scoring rule and
a model with no discriminatory power can drive it to zero
(arxiv.org/pdf/2408.02841).

Every score here is oriented so that LOWER IS BETTER, except skill_score.
"""

from __future__ import annotations

import math

EPS = 1e-15


def brier(preds: list[float], outcomes: list[int]) -> float:
    """Mean squared error of probabilities against 0/1 outcomes."""
    if len(preds) != len(outcomes):
        raise ValueError("preds and outcomes must be the same length")
    if not preds:
        raise ValueError("need at least one prediction")
    return sum((p - o) ** 2 for p, o in zip(preds, outcomes)) / len(preds)


def log_score(preds: list[float], outcomes: list[int]) -> float:
    """Mean negative log likelihood. Clipped so a confident miss is finite."""
    if len(preds) != len(outcomes):
        raise ValueError("preds and outcomes must be the same length")
    if not preds:
        raise ValueError("need at least one prediction")
    total = 0.0
    for p, o in zip(preds, outcomes):
        q = min(1 - EPS, max(EPS, p))
        total += -math.log(q if o else 1 - q)
    return total / len(preds)


def crps_share(preds: list[float], truths: list[float]) -> float:
    """CRPS of a point forecast for a share, which reduces to mean absolute error."""
    if len(preds) != len(truths):
        raise ValueError("preds and truths must be the same length")
    if not preds:
        raise ValueError("need at least one prediction")
    return sum(abs(p - t) for p, t in zip(preds, truths)) / len(preds)


def _rank(xs: list[float]) -> list[float]:
    order = sorted(range(len(xs)), key=lambda i: xs[i])
    ranks = [0.0] * len(xs)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and xs[order[j + 1]] == xs[order[i]]:
            j += 1
        shared = (i + j) / 2 + 1
        for k in range(i, j + 1):
            ranks[order[k]] = shared
        i = j + 1
    return ranks


def murphy_decomposition(preds: list[float], truths: list[float]) -> dict:
    """Split the error into a level part and a shape part.

    bias is the mean signed error, so it is the part a calibration shift can remove.
    spearman is rank correlation, so it is the part calibration cannot change.
    """
    if len(preds) != len(truths) or not preds:
        raise ValueError("preds and truths must be the same non-zero length")
    n = len(preds)
    bias = sum(p - t for p, t in zip(preds, truths)) / n
    mae = sum(abs(p - t) for p, t in zip(preds, truths)) / n
    rp, rt = _rank(preds), _rank(truths)
    mp, mt = sum(rp) / n, sum(rt) / n
    num = sum((a - mp) * (b - mt) for a, b in zip(rp, rt))
    den = math.sqrt(sum((a - mp) ** 2 for a in rp) * sum((b - mt) ** 2 for b in rt))
    return {
        "bias": bias,
        "mae": mae,
        "spearman": (num / den) if den else float("nan"),
        "mae_after_removing_bias": sum(abs((p - bias) - t) for p, t in zip(preds, truths)) / n,
    }


def skill_score(model_error: float, baseline_error: float) -> float:
    """Fraction of the baseline's error the model removes. 0 means no better than baseline."""
    if baseline_error <= 0:
        raise ValueError("baseline_error must be positive")
    return 1.0 - model_error / baseline_error
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_scoring.py -v`
Expected: PASS, 5 passed

- [ ] **Step 5: Commit**

```bash
git add src/jevfish/scoring.py tests/test_scoring.py
git commit -m "feat(scoring): proper scoring rules and level-vs-shape decomposition"
```

---

## Task 5: The anchor store

An anchor is one resolved outcome: a question, an option, what JevFish predicted, and what actually happened.

**Files:**
- Create: `src/jevfish/anchors.py`
- Test: `tests/test_anchors.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_anchors.py
from jevfish.anchors import Anchor, load_anchors, save_anchor


def test_save_then_load_roundtrips(tmp_path):
    path = tmp_path / "anchors.json"
    a = Anchor(question="pureloft nightly rate", option="MYR 300",
               predicted=0.568, actual=0.892, n=801, note="610 resolved nights")
    save_anchor(path, a)
    got = load_anchors(path)
    assert len(got) == 1
    assert got[0].predicted == 0.568
    assert got[0].actual == 0.892
    assert got[0].question == "pureloft nightly rate"


def test_load_is_empty_when_the_file_does_not_exist(tmp_path):
    assert load_anchors(tmp_path / "missing.json") == []


def test_anchors_append_and_filter_by_question(tmp_path):
    path = tmp_path / "anchors.json"
    save_anchor(path, Anchor("rates", "MYR 300", 0.568, 0.892, 801))
    save_anchor(path, Anchor("rates", "MYR 400", 0.395, 0.700, 801))
    save_anchor(path, Anchor("cleaning", "plus S$100", 0.45, 0.30, 48))
    assert len(load_anchors(path)) == 3
    assert len(load_anchors(path, question="rates")) == 2


def test_anchor_rejects_a_probability_outside_zero_to_one(tmp_path):
    import pytest
    with pytest.raises(ValueError):
        Anchor("q", "o", 1.2, 0.5, 10)
    with pytest.raises(ValueError):
        Anchor("q", "o", 0.5, -0.1, 10)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_anchors.py -v`
Expected: FAIL, `ModuleNotFoundError: No module named 'jevfish.anchors'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/jevfish/anchors.py
"""Resolved outcomes, which are the only thing that makes calibration possible.

One anchor buys a level shift. About five buys level plus scale. Nine buys a 90 percent
conformal interval (four buys 80 percent, nineteen buys 95 percent). About seventy buys
near-optimal decisions (arxiv.org/html/2606.16183v1). Without anchors JevFish cannot
state an accuracy.

`model_version` and `frame_hash` are not bookkeeping. Bisbee et al. showed the same
prompt gives significantly different distributions across model versions and across a
three-month gap, so a calibration fitted on one version does not transfer to another.
An anchor without its model version is not reusable, and silently mixing versions in one
fit is a way to produce a confident wrong number.

`estimand` must match between an anchor and the run being calibrated. The `NoulQ` path
yields `acceptance_rate_independent` (each person judged on their own) and the `ChoiceQ`
path yields `choice_share_of_described_set` (people allocated across a fixed option set).
These are different quantities and one calibration map cannot serve both.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path


@dataclass
class Anchor:
    question: str
    option: str
    predicted: float
    actual: float
    n: int
    estimand: str = "acceptance_rate_independent"
    model_version: str = ""
    frame_hash: str = ""
    note: str = ""
    recorded_at: str = field(default="")

    def __post_init__(self) -> None:
        for name in ("predicted", "actual"):
            value = getattr(self, name)
            if not 0.0 <= float(value) <= 1.0:
                raise ValueError(f"{name} must be a probability in [0, 1], got {value}")
        if int(self.n) < 1:
            raise ValueError("n must be at least 1")


def load_anchors(path: str | Path, question: str | None = None) -> list[Anchor]:
    p = Path(path)
    if not p.exists():
        return []
    rows = json.loads(p.read_text() or "[]")
    out = [Anchor(**row) for row in rows]
    return [a for a in out if question is None or a.question == question]


def save_anchor(path: str | Path, anchor: Anchor) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    rows = json.loads(p.read_text()) if p.exists() and p.read_text().strip() else []
    rows.append(asdict(anchor))
    p.write_text(json.dumps(rows, indent=1, ensure_ascii=False))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_anchors.py -v`
Expected: PASS, 4 passed

- [ ] **Step 5: Commit**

```bash
git add src/jevfish/anchors.py tests/test_anchors.py
git commit -m "feat(anchors): store resolved outcomes for calibration"
```

---

## Task 6: Fit and apply the calibration map

The map is `sigmoid(a + b * logit(q))`, applied **per persona before aggregation**, because sigmoid is non-linear so a map on the aggregate is not the same thing.

**Files:**
- Create: `src/jevfish/calibrate.py`
- Test: `tests/test_calibrate.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_calibrate.py
import math
import pytest
from jevfish.anchors import Anchor
from jevfish.calibrate import CalibrationMap, fit_map, apply_map, conformal_half_width


def test_identity_map_changes_nothing():
    m = CalibrationMap(a=0.0, b=1.0, anchors_used=0)
    assert apply_map([0.2, 0.5, 0.8], m) == pytest.approx([0.2, 0.5, 0.8])


def test_one_anchor_fits_a_shift_only_and_hits_the_target():
    # 801 persona probabilities averaging 0.568, target 0.892
    persona = [0.568] * 10
    anchors = [Anchor("q", "MYR 300", predicted=0.568, actual=0.892, n=801)]
    m = fit_map(anchors)
    assert m.b == 1.0                      # one anchor cannot identify the scale
    assert m.anchors_used == 1
    got = sum(apply_map(persona, m)) / len(persona)
    assert got == pytest.approx(0.892, abs=1e-6)


def test_map_is_strictly_monotone_so_it_cannot_reorder_options():
    m = CalibrationMap(a=1.89, b=1.0, anchors_used=1)
    out = apply_map([0.325, 0.395, 0.568, 0.670, 0.690], m)
    assert out == sorted(out)


def test_five_anchors_fit_both_level_and_scale():
    anchors = [
        Anchor("q", "a", 0.10, 0.30, 100), Anchor("q", "b", 0.30, 0.50, 100),
        Anchor("q", "c", 0.50, 0.70, 100), Anchor("q", "d", 0.70, 0.85, 100),
        Anchor("q", "e", 0.90, 0.95, 100),
    ]
    m = fit_map(anchors)
    assert m.anchors_used == 5
    assert m.b != 1.0
    assert m.b > 0                          # monotonicity requires b > 0


def test_fit_map_with_no_anchors_returns_the_identity_and_says_so():
    m = fit_map([])
    assert (m.a, m.b, m.anchors_used) == (0.0, 1.0, 0)


def test_conformal_half_width_needs_nine_anchors_for_ninety_percent():
    with pytest.raises(ValueError) as e:
        conformal_half_width([0.1] * 8, alpha=0.10)
    assert "9" in str(e.value)
    # nine residuals, all 0.2 -> half-width 0.2
    assert conformal_half_width([0.2] * 9, alpha=0.10) == pytest.approx(0.2)


def test_conformal_half_width_is_the_quantile_of_absolute_residuals():
    residuals = [0.01, 0.02, 0.03, 0.04, 0.05, 0.06, 0.07, 0.08, 0.09, 0.30]
    hw = conformal_half_width(residuals, alpha=0.10)
    assert hw == pytest.approx(0.30)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_calibrate.py -v`
Expected: FAIL, `ModuleNotFoundError: No module named 'jevfish.calibrate'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/jevfish/calibrate.py
"""Map raw judge probabilities onto observed frequencies, and say how wrong we usually are.

The map is T(q) = sigmoid(a + b * logit(q)) with b > 0, from
arxiv.org/html/2606.16183v1, which reached 90% of optimal revenue on a near-identical
persona pricing system using about 73 real observations. `a` fixes the level, `b`
rescales the shape, and because the map is strictly monotone it can never reorder the
options.

Applied PER PERSONA before aggregation. A map on the aggregate share is a different
function, because sigmoid is non-linear.

Intervals come from split conformal on our own past absolute errors, which is
distribution-free and needs n >= 1/alpha - 1 anchors (9 for 90% coverage).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

EPS = 1e-6


def _logit(p: float) -> float:
    q = min(1 - EPS, max(EPS, p))
    return math.log(q / (1 - q))


def _sigmoid(x: float) -> float:
    if x >= 0:
        return 1.0 / (1.0 + math.exp(-x))
    e = math.exp(x)
    return e / (1.0 + e)


@dataclass(frozen=True)
class CalibrationMap:
    a: float
    b: float
    anchors_used: int

    @property
    def is_identity(self) -> bool:
        return self.a == 0.0 and self.b == 1.0

    def describe(self) -> str:
        if self.is_identity:
            return "uncalibrated: no resolved outcomes recorded yet"
        scale = "" if self.b == 1.0 else f", scale {self.b:+.3f}"
        return f"calibrated on {self.anchors_used} resolved outcome(s): shift {self.a:+.3f}{scale}"


def apply_map(persona_probabilities: list[float], m: CalibrationMap) -> list[float]:
    """Calibrate each persona probability. Aggregate AFTER this, never before."""
    if m.is_identity:
        return list(persona_probabilities)
    return [_sigmoid(m.a + m.b * _logit(p)) for p in persona_probabilities]


def fit_map(anchors: list) -> CalibrationMap:
    """Least squares in logit space. One anchor fits `a` only; two or more fit `a` and `b`."""
    pairs = [(_logit(x.predicted), _logit(x.actual)) for x in anchors]
    if not pairs:
        return CalibrationMap(0.0, 1.0, 0)
    if len(pairs) == 1:
        x, y = pairs[0]
        return CalibrationMap(a=y - x, b=1.0, anchors_used=1)
    n = len(pairs)
    mx = sum(x for x, _ in pairs) / n
    my = sum(y for _, y in pairs) / n
    sxx = sum((x - mx) ** 2 for x, _ in pairs)
    if sxx == 0:
        return CalibrationMap(a=my - mx, b=1.0, anchors_used=n)
    b = sum((x - mx) * (y - my) for x, y in pairs) / sxx
    b = max(EPS, b)                       # b > 0 keeps the map monotone
    return CalibrationMap(a=my - b * mx, b=b, anchors_used=n)


def conformal_half_width(abs_residuals: list[float], alpha: float = 0.10) -> float:
    """Split-conformal half-width. Distribution-free, needs n >= 1/alpha - 1 residuals.

    Four residuals buy 80 percent coverage, nine buy 90, nineteen buy 95. Below four,
    print the raw historical errors rather than an interval: a made-up interval is the
    failure mode this whole module exists to remove.

    Coverage is marginal, not conditional. It does not protect a question unlike anything
    in the anchor set, so `estimand` and `question` must match before pooling residuals.
    """
    need = math.ceil(1 / alpha - 1)
    if len(abs_residuals) < need:
        raise ValueError(
            f"split conformal at alpha={alpha} needs at least {need} resolved outcomes, "
            f"got {len(abs_residuals)}. Report the raw errors instead of an interval."
        )
    rs = sorted(abs(r) for r in abs_residuals)
    n = len(rs)
    k = math.ceil((n + 1) * (1 - alpha))
    return rs[min(n - 1, k - 1)]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_calibrate.py -v`
Expected: PASS, 7 passed

- [ ] **Step 5: Commit**

```bash
git add src/jevfish/calibrate.py tests/test_calibrate.py
git commit -m "feat(calibrate): per-persona logit map and conformal intervals"
```

---

## Task 7: Report the calibrated number, the estimand, and an honest interval

**Files:**
- Modify: `src/jevfish/metrics.py:16-35` (`summarize_poll`)
- Test: `tests/test_metrics_calibration.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_metrics_calibration.py
import pytest
from jevfish.calibrate import CalibrationMap
from jevfish import metrics


def records(ps):
    return [{"outcome_p": p, "stance": 2.0, "agent_id": i} for i, p in enumerate(ps)]


def test_uncalibrated_summary_is_unchanged_and_labelled_honestly():
    s = metrics.summarize_poll(records([0.5, 0.5, 0.5]), n_levels=5)
    assert s["mean_outcome"] == pytest.approx(0.5)
    assert s["calibrated"] is False
    assert s["estimand"] == "acceptance_rate_independent"
    assert s["estimand_label"] == "acceptance rate among the described crowd"
    assert s["interval_covers"] == "sampling noise in the synthetic crowd only"


def test_choice_path_reports_the_other_estimand():
    s = metrics.summarize_poll(
        records([0.4, 0.6]), n_levels=5, estimand="choice_share_of_described_set"
    )
    assert s["estimand_label"] == "share of the described option set"


def test_an_unknown_estimand_is_refused_rather_than_mislabelled():
    with pytest.raises(ValueError):
        metrics.summarize_poll(records([0.5]), n_levels=5, estimand="occupancy")


def test_calibration_map_is_applied_per_persona():
    m = CalibrationMap(a=1.8906, b=1.0, anchors_used=1)
    s = metrics.summarize_poll(records([0.568] * 5), n_levels=5, calibration=m)
    assert s["calibrated"] is True
    assert s["mean_outcome"] == pytest.approx(0.892, abs=1e-3)
    assert s["mean_outcome_raw"] == pytest.approx(0.568)
    assert "1 resolved outcome" in s["calibration_note"]


def test_honest_half_width_replaces_the_sampling_interval_and_says_so():
    s = metrics.summarize_poll(records([0.5] * 100), n_levels=5, honest_half_width=0.30)
    assert s["low"] == pytest.approx(0.20)
    assert s["high"] == pytest.approx(0.80)
    assert s["interval_covers"] == "our own past errors on resolved outcomes"


def test_honest_half_width_is_clamped_to_zero_one():
    s = metrics.summarize_poll(records([0.9] * 10), n_levels=5, honest_half_width=0.5)
    assert s["low"] == 0.4
    assert s["high"] == 1.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_metrics_calibration.py -v`
Expected: FAIL, `TypeError: summarize_poll() got an unexpected keyword argument 'calibration'`

- [ ] **Step 3: Write minimal implementation**

Replace `summarize_poll` in `src/jevfish/metrics.py` with:

```python
ESTIMANDS = {
    "acceptance_rate_independent": "acceptance rate among the described crowd",
    "choice_share_of_described_set": "share of the described option set",
    "event_probability": "probability of the event",
}


def summarize_poll(
    records: list[dict],
    n_levels: int,
    *,
    calibration=None,
    honest_half_width: float | None = None,
    estimand: str = "acceptance_rate_independent",
) -> dict:
    """Summarise one poll.

    `mean_outcome` is NOT a real-world rate. Which quantity it is depends on how the
    question was asked, and the two are not interchangeable: a `NoulQ` judges each person
    on their own (`acceptance_rate_independent`), while a `ChoiceQ` allocates people
    across a fixed option set (`choice_share_of_described_set`). One calibration map
    cannot serve both.

    Neither is occupancy. A listing with a 22% choice share can sit in a flat running at
    89% occupancy, because occupancy is arrival volume over supply. The market-research
    trade has known this for decades: share of preference assumes equal awareness and
    equal distribution, and getting to market share needs availability, awareness, an
    exponent and a share adjustment. JevFish has none of those inputs, so it cannot
    produce occupancy, and a calibration map fitted on resolved outcomes is the only
    honest bridge.

    With no `honest_half_width` the interval is Poisson-binomial, which covers sampling
    noise inside a synthetic crowd and NOT model, frame or crowd-composition error. On
    the Pureloft backtest the real error was 11.5x that half-width, and it shrinks as
    1/sqrt(n) while the real error does not move. The returned `interval_covers` field
    says which of the two is in force.
    """
    from .calibrate import apply_map

    if estimand not in ESTIMANDS:
        raise ValueError(
            f"unknown estimand '{estimand}'; use one of {', '.join(ESTIMANDS)}. "
            "A real-world rate such as occupancy is not an estimand JevFish produces; "
            "it is what a calibration map converts an estimand into."
        )
    n = len(records)
    raw = [r["outcome_p"] for r in records]
    ps = apply_map(raw, calibration) if calibration is not None else raw
    calibrated = calibration is not None and not calibration.is_identity

    expected = sum(ps)
    variance = sum(p * (1 - p) for p in ps)
    mean_outcome = expected / n if n else 0.0

    if honest_half_width is not None:
        low = max(0.0, mean_outcome - honest_half_width) * n
        high = min(1.0, mean_outcome + honest_half_width) * n
        covers = "our own past errors on resolved outcomes"
    else:
        half = Z90 * math.sqrt(variance)
        low, high = max(0.0, expected - half), min(float(n), expected + half)
        covers = "sampling noise in the synthetic crowd only"

    hist = [0] * n_levels
    for r in records:
        hist[min(n_levels - 1, max(0, int(r["stance"] + 0.5)))] += 1

    out = {
        "n": n,
        "mean_outcome": mean_outcome,
        "expected_yes": expected,
        "variance": variance,
        "low": low,
        "high": high,
        "likely_yes": sum(p >= 0.5 for p in ps),
        "stance_mean": sum(r["stance"] for r in records) / n if n else 0.0,
        "stance_hist": hist,
        "estimand": estimand,
        "estimand_label": ESTIMANDS[estimand],
        "calibrated": calibrated,
        "interval_covers": covers,
    }
    if calibration is not None:
        out["mean_outcome_raw"] = sum(raw) / n if n else 0.0
        note = calibration.describe()
        out["calibration_note"] = note.replace("outcome(s)", "outcome") if calibration.anchors_used == 1 else note
    return out
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_metrics_calibration.py -v`
Expected: PASS, 4 passed

Run: `uv run pytest -q`
Expected: PASS, 84 existing tests still green (the new keyword arguments default to the old behaviour).

- [ ] **Step 5: Commit**

```bash
git add src/jevfish/metrics.py tests/test_metrics_calibration.py
git commit -m "feat(metrics): calibrated share, named estimand, honest interval"
```

---

## Task 8: Randomise option order per person

**Files:**
- Modify: `src/jevfish/policy.py:133-155` (`build_questions`) and `src/jevfish/policy.py:158-162` (`poll_questions`)
- Test: `tests/test_policy_order.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_policy_order.py
from jevfish.policy import shuffled_criteria


def test_same_seed_and_person_give_the_same_order():
    c = {"a": "A", "b": "B", "c": "C", "d": "D"}
    assert list(shuffled_criteria(c, seed=1, agent_id=7)) == list(shuffled_criteria(c, seed=1, agent_id=7))


def test_different_people_get_different_orders():
    c = {f"k{i}": f"V{i}" for i in range(8)}
    orders = {tuple(shuffled_criteria(c, seed=1, agent_id=i)) for i in range(20)}
    assert len(orders) > 1


def test_contents_are_preserved_exactly():
    c = {"a": "A", "b": "B", "c": "C"}
    out = shuffled_criteria(c, seed=3, agent_id=2)
    assert dict(out) == c


def test_reserved_none_option_stays_last():
    c = {"x": "X", "none": "None of these", "y": "Y"}
    for agent_id in range(30):
        assert list(shuffled_criteria(c, seed=1, agent_id=agent_id, pin_last={"none"}))[-1] == "none"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_policy_order.py -v`
Expected: FAIL, `ImportError: cannot import name 'shuffled_criteria'`

- [ ] **Step 3: Write minimal implementation**

Append to `src/jevfish/policy.py`:

```python
def shuffled_criteria(
    criteria: dict, *, seed: int, agent_id: int, pin_last: set[str] = frozenset()
) -> dict:
    """The same options in a per-person order, so position bias averages out.

    Option order is a real effect, not noise. With a fixed order every person sees the
    same positions, so any primacy or recency bias in the judge becomes a systematic
    shift in the crowd's answer rather than something that cancels. Randomising per
    person converts it back into noise. Deterministic in (seed, agent_id) so reruns and
    the request cache still hit.
    """
    keys = [k for k in criteria if k not in pin_last]
    tail = [k for k in criteria if k in pin_last]
    random.Random(f"order:{seed}:{agent_id}").shuffle(keys)
    return {k: criteria[k] for k in keys + tail}
```

Then thread a seed and agent id through. Change the signature of `build_questions` from:

```python
def build_questions(frame: dict, feed: list[FeedPost], actions: list[str], labels: dict[int, str], mind: Mind, self_id: int, blocked: set[int]) -> dict[str, Question]:
```

to:

```python
def build_questions(frame: dict, feed: list[FeedPost], actions: list[str], labels: dict[int, str], mind: Mind, self_id: int, blocked: set[int], *, seed: int = 0) -> dict[str, Question]:
```

and wrap each `ChoiceQ` criteria dict. Replace:

```python
    qs["action"] = ChoiceQ(ACTION_INSTRUCTIONS, {a: ACTION_TEXT[a] for a in actions})
```

with:

```python
    order = {"seed": seed, "agent_id": self_id}
    qs["action"] = ChoiceQ(
        ACTION_INSTRUCTIONS,
        shuffled_criteria({a: ACTION_TEXT[a] for a in actions}, **order),
    )
```

Replace:

```python
        points = {p["id"]: p["text"] for p in frame["talking_points"]}
        points[NO_POINT] = POINT_NONE
        qs["point"] = ChoiceQ(POINT_INSTRUCTIONS, points)
```

with:

```python
        points = {p["id"]: p["text"] for p in frame["talking_points"]}
        points[NO_POINT] = POINT_NONE
        qs["point"] = ChoiceQ(
            POINT_INSTRUCTIONS, shuffled_criteria(points, **order, pin_last={NO_POINT})
        )
```

In `src/jevfish/simulate.py`, find the single call site in `turn` (around line 280) and pass the seed:

```python
        questions = build_questions(
            self.ctx.frame, feed, actions, self.labels, mind, agent_id, self.blocked,
            seed=self.cfg.seed,
        )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_policy_order.py -v`
Expected: PASS, 4 passed

Run: `uv run pytest -q`
Expected: PASS, all green.

- [ ] **Step 5: Verify a real run still works offline**

Run:
```bash
JEVFISH_FAKE_JUDGE=1 JEVFISH_FAKE_LLM=1 uv run jevfish demo --platform lite --rounds 3 --public 20 --stakeholders 4
```
Expected: completes through report, no exception.

- [ ] **Step 6: Commit**

```bash
git add src/jevfish/policy.py src/jevfish/simulate.py tests/test_policy_order.py
git commit -m "feat(policy): randomise option order per person"
```

---

## Task 9: A frame-sensitivity check that runs on every comparison

The run must tell the user whether its answer came from the world or from its own wording.

**Files:**
- Modify: `src/jevfish/frame_audit.py`
- Test: `tests/test_frame_audit.py`

- [ ] **Step 1: Write the failing test**

```python
# append to tests/test_frame_audit.py
from jevfish.frame_audit import sensitivity_verdict


def test_agreeing_curves_pass():
    v = sensitivity_verdict({"a": 0.55, "b": 0.53, "c": 0.52}, {"a": 0.554, "b": 0.534, "c": 0.527})
    assert v["agrees"] is True
    assert v["max_shift"] < 0.01
    assert v["rank_agreement"] == 1.0


def test_the_pureloft_case_fails_loudly():
    # Arm A (as shipped) against Arm C (neutralised), verbatim from the experiment.
    shipped = {"200": 0.686, "250": 0.656, "300": 0.517, "400": 0.267, "500": 0.211}
    neutral = {"200": 0.554, "250": 0.534, "300": 0.527, "400": 0.510, "500": 0.498}
    v = sensitivity_verdict(shipped, neutral)
    assert v["agrees"] is False
    assert v["max_shift"] > 0.2
    assert "wording" in v["message"]


def test_verdict_requires_the_same_options_on_both_sides():
    import pytest
    with pytest.raises(ValueError):
        sensitivity_verdict({"a": 0.5}, {"b": 0.5})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_frame_audit.py::test_the_pureloft_case_fails_loudly -v`
Expected: FAIL, `ImportError: cannot import name 'sensitivity_verdict'`

- [ ] **Step 3: Write minimal implementation**

```python
# append to src/jevfish/frame_audit.py
TOLERANCE = 0.05


def sensitivity_verdict(as_written: dict[str, float], neutralised: dict[str, float]) -> dict:
    """Compare the same option set run with and without its per-option wording.

    If the two disagree, the run is reporting its own prompt. On the Pureloft ladder the
    shipped wording gave a 0.475 shift on one option and reversed which rate maximised
    revenue, so this check is the difference between a measurement and an artifact.
    """
    if set(as_written) != set(neutralised):
        raise ValueError("both runs must cover the same options")
    keys = list(as_written)
    shifts = {k: as_written[k] - neutralised[k] for k in keys}
    max_shift = max(abs(s) for s in shifts.values()) if shifts else 0.0
    rank_a = sorted(keys, key=lambda k: -as_written[k])
    rank_b = sorted(keys, key=lambda k: -neutralised[k])
    agreement = sum(x == y for x, y in zip(rank_a, rank_b)) / len(keys)
    agrees = max_shift <= TOLERANCE and agreement == 1.0
    if agrees:
        message = "the result holds when the per-option wording is neutralised"
    else:
        message = (
            f"the result depends on the frame's own wording: the largest option moved "
            f"{max_shift:.3f} and {int((1 - agreement) * len(keys))} of {len(keys)} options "
            "changed rank. Treat this run as a statement about the prompt, not the world."
        )
    return {
        "agrees": agrees,
        "max_shift": max_shift,
        "rank_agreement": agreement,
        "shifts": shifts,
        "message": message,
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_frame_audit.py -v`
Expected: PASS, 9 passed

- [ ] **Step 5: Commit**

```bash
git add src/jevfish/frame_audit.py tests/test_frame_audit.py
git commit -m "feat(frame): verdict on whether a result survives neutral wording"
```

---

## Task 9b: Block a run whose curve is impossible

The complement to Task 9. Frame sensitivity asks "did the wording decide this?".
Monotonicity asks "is this curve even possible?". The -3.29 elasticity that started all of
this would have been caught here.

**Files:**
- Modify: `src/jevfish/frame_audit.py`
- Test: `tests/test_frame_audit.py`

- [ ] **Step 1: Write the failing test**

```python
# append to tests/test_frame_audit.py
from jevfish.frame_audit import curve_check


def test_a_plausible_downward_curve_passes():
    v = curve_check({200: 0.69, 250: 0.67, 300: 0.57, 400: 0.40, 500: 0.33},
                    expect="decreasing", max_abs_elasticity=2.0)
    assert v["ok"] is True
    assert v["elasticity"] == pytest.approx(-0.8731, abs=0.001)  # verified by hand


def test_a_curve_steeper_than_the_stated_ceiling_is_blocked():
    # the synthetic run that produced -3.29. Fitted value here is -4.35.
    v = curve_check({200: 0.95, 250: 0.80, 300: 0.45, 400: 0.09, 500: 0.02},
                    expect="decreasing", max_abs_elasticity=2.0)
    assert v["ok"] is False
    assert "steeper" in v["message"]
    assert "2.0" in v["message"]        # the ceiling must be stated, not hidden


def test_the_ceiling_is_required_and_has_no_default():
    # A silent default would smuggle in an unsourced benchmark. Caller must state it.
    with pytest.raises(TypeError):
        curve_check({200: 0.6, 300: 0.5, 400: 0.4}, expect="decreasing")


def test_a_curve_going_the_wrong_way_is_blocked():
    v = curve_check({200: 0.30, 250: 0.40, 300: 0.50, 400: 0.60, 500: 0.70},
                    expect="decreasing", max_abs_elasticity=2.0)
    assert v["ok"] is False
    assert "wrong direction" in v["message"]


def test_a_flat_curve_is_reported_as_no_signal_not_as_a_pass():
    v = curve_check({200: 0.501, 250: 0.500, 300: 0.500, 400: 0.499, 500: 0.499},
                    expect="decreasing", max_abs_elasticity=2.0)
    assert v["ok"] is False
    assert "no measurable response" in v["message"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_frame_audit.py::test_a_plausible_downward_curve_passes -v`
Expected: FAIL, `ImportError: cannot import name 'curve_check'`

- [ ] **Step 3: Write minimal implementation**

```python
# append to src/jevfish/frame_audit.py
import math

FLAT = 0.02


def curve_check(
    shares: dict, *, expect: str, max_abs_elasticity: float
) -> dict:
    """Refuse a response curve that is flat, runs backwards, or is implausibly steep.

    `shares` maps the numeric level of the varying attribute to the predicted share.

    `max_abs_elasticity` is REQUIRED and has no default, deliberately. A default would
    smuggle a benchmark into the code, and we got burned by exactly that: the "-0.36
    Cornell property-level benchmark" and the "-0.13 to -0.95 published property-level
    range" we had been judging runs against are both unsourced. Checked 18 September 2026:
    -0.36 appears in neither Corgel, Lane and Woodworth (2012) nor Enz, Canina and van der
    Rest (2015), and the latter does not measure elasticity at all.

    What the literature does support, for room rates: market-level estimates cluster in
    -0.1 to -0.9 (Singh and Corsun 2023, 2,503 US hotels, 2SLS: -0.165 short run, -0.79
    long run). But Corgel et al. state that "elasticity tends to increase with data
    disaggregation" and that individual-hotel elasticity "will be higher than their market
    level elasticity suggests", and that their figures "cannot be directly applied to an
    individual hotel". So a single differentiated property can legitimately sit outside
    -0.9, and 2.0 is the defensible ceiling for a room-rate ladder rather than 1.0.

    The caller states the ceiling and the returned message repeats it, so any number this
    gate blocks can be traced to a stated assumption rather than a hidden one.
    """
    if len(shares) < 3:
        raise ValueError("need at least three levels to check a curve")
    xs = [math.log(float(k)) for k in shares]
    ys = [math.log(max(1e-9, v)) for v in shares.values()]
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    elasticity = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sxx if sxx else 0.0

    wanted = -1 if expect == "decreasing" else 1
    if abs(elasticity) < FLAT:
        ok, message = False, (
            f"no measurable response: fitted elasticity {elasticity:+.3f} is flat. The run "
            "cannot distinguish the options, so do not read a winner off it."
        )
    elif elasticity * wanted < 0:
        ok, message = False, (
            f"the curve runs the wrong direction: fitted elasticity {elasticity:+.3f} but "
            f"this question family is expected to be {expect}."
        )
    elif abs(elasticity) > max_abs_elasticity:
        ok, message = False, (
            f"the curve is steeper than the stated ceiling: fitted elasticity "
            f"{elasticity:+.3f} against a ceiling of {max_abs_elasticity:.1f} that the "
            "caller supplied. Check the per-option wording before trusting this, and check "
            "that the ceiling itself is sourced."
        )
    else:
        ok, message = True, f"fitted elasticity {elasticity:+.3f}, within the credible range"
    return {"ok": ok, "elasticity": elasticity, "message": message}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_frame_audit.py -v`
Expected: PASS, 13 passed

Add `import pytest` at the top of the test file if it is not already there.

- [ ] **Step 5: Commit**

```bash
git add src/jevfish/frame_audit.py tests/test_frame_audit.py
git commit -m "feat(frame): block response curves no published estimate supports"
```

---

## Task 10: Regression-test the whole thing against the stored Pureloft run

This locks in the measured findings so they cannot silently regress.

**Files:**
- Create: `tests/test_pureloft_regression.py`
- Create: `tests/fixtures/pureloft_p300_probabilities.json` (801 floats, extracted from the stored run)

- [ ] **Step 1: Build the fixture**

```bash
uv run python -c "
import json
src='data/projects/p_71f65447c6/runs/r_2f97f45e18/polls.jsonl'
ps=[json.loads(l)['outcome_p'] for l in open(src) if json.loads(l)['variant']=='p300']
import pathlib; pathlib.Path('tests/fixtures').mkdir(parents=True, exist_ok=True)
pathlib.Path('tests/fixtures/pureloft_p300_probabilities.json').write_text(json.dumps(ps))
print(len(ps), 'probabilities written')
"
```
Expected: `801 probabilities written`

- [ ] **Step 2: Write the test**

```python
# tests/test_pureloft_regression.py
"""Locks in the numbers measured in docs/research/calibration-experiment.md."""
import json
import pathlib
import pytest
from jevfish.anchors import Anchor
from jevfish.calibrate import fit_map, apply_map
from jevfish.scoring import crps_share, murphy_decomposition

TRUTH = 0.892
PS = json.loads((pathlib.Path(__file__).parent / "fixtures" / "pureloft_p300_probabilities.json").read_text())


def test_the_fixture_is_the_run_we_measured():
    assert len(PS) == 801
    assert sum(PS) / len(PS) == pytest.approx(0.568, abs=5e-4)


def test_the_raw_crowd_is_degenerate():
    # Nobody would definitely book and nobody would definitely refuse.
    assert min(PS) >= 0.30
    assert max(PS) <= 0.75
    assert len(set(PS)) < 40


def test_one_anchor_removes_the_level_error():
    raw_error = crps_share([sum(PS) / len(PS)], [TRUTH])
    assert raw_error == pytest.approx(0.324, abs=5e-4)
    m = fit_map([Anchor("pureloft", "MYR 300", predicted=sum(PS) / len(PS), actual=TRUTH, n=801)])
    cal = apply_map(PS, m)
    assert crps_share([sum(cal) / len(cal)], [TRUTH]) < 0.01


def test_calibration_cannot_reorder_the_rungs():
    m = fit_map([Anchor("pureloft", "MYR 300", predicted=0.568, actual=TRUTH, n=801)])
    rungs = [0.325, 0.395, 0.568, 0.670, 0.690]      # 500, 400, 300, 250, 200
    assert apply_map(rungs, m) == sorted(apply_map(rungs, m))


def test_decomposition_says_the_error_is_level_not_shape():
    preds = [0.690, 0.670, 0.568, 0.395, 0.325]
    truth = [0.935, 0.930, 0.892, 0.795, 0.738]      # after the fitted shift
    d = murphy_decomposition(preds, truth)
    assert d["spearman"] == pytest.approx(1.0)        # shape is perfect
    assert d["bias"] < -0.2                           # level is badly low
    assert d["mae_after_removing_bias"] < d["mae"]
```

- [ ] **Step 3: Run the test**

Run: `uv run pytest tests/test_pureloft_regression.py -v`
Expected: PASS, 5 passed

- [ ] **Step 4: Commit**

```bash
git add tests/test_pureloft_regression.py tests/fixtures/pureloft_p300_probabilities.json
git commit -m "test: lock in the measured Pureloft calibration findings"
```

---

## Deliberately not in this plan

Each of these was considered and rejected on evidence, not omitted by accident.

| Not doing | Why |
|---|---|
| Persona enrichment as an accuracy feature | Measured: sd up 2.4x but the mean moved 0.08 further from truth. Literature: 500-question digital twins score 0.748 against 0.734 for an empty persona (arxiv.org/abs/2509.19088). It buys spread, not accuracy. Keep it as an optional knob, do not sell it as a fix |
| The Gui and Toubia exogeneity sentence | **The literature recommends it and our measurement says no.** Their reported effect is large (elasticity 0.14 to 1.38 across 40 categories; MAE improvements from 1 to over 60 percent). On Jev, with the Finding 7 frame artifact neutralised first so it could not mask anything, it moved elasticity by 0.001 and narrowed the crowd from sd 0.080 to 0.067. Their mechanism needs a generative model inferring unstated confounders while it composes text; Jev returns a typed judgment and writes nothing. Direct measurement on the actual model wins. Re-test if we ever swap the judge |
| Growing the crowd to 1,500 for resolution | The interval that motivated it was the wrong interval. MRP holds MAE at 4 to 5pp from N 1,400 to 14,000, so post-stratify instead of paying for people |
| Extremising the pooled probability | **Ruled out on theory and on our own data, not merely deferred.** Extremising is justified when forecasters hold partly independent information. Jev returned about 30 distinct values across 801 personas, four of them covering 341 people, so the crowd shares almost all its information and the effective number of independent opinions is far below 801. The published human-crowd exponents (2.4 to 3.1) therefore overshoot badly, which is exactly what we measured: a=2.0 and a=3.0 both wrecked the curve. The fitted `b` in the calibration map does the same job with anchors to justify it |
| Changing the aggregation rule from the plain mean | The arithmetic mean is a linear opinion pool, which is the pool matched to the Brier scoring rule. It is the defensible choice and it is not the problem |
| Expected Calibration Error | Not a proper scoring rule. A model with no discriminatory power can drive it to zero |
| MRP post-stratification | Real and well-evidenced (Xbox sample recovered to 0.6pp), but it needs a real population frame with outcome-predictive cells. That is its own plan once anchors exist |

---

## Self-review

**Spec coverage.** Frame artifact: Tasks 1, 2, 3, 9. Scoring harness: Task 4. Anchors: Task 5. Calibration and honest intervals: Tasks 6, 7. Option order: Task 8. Estimand labelling: Task 7. Regression lock: Task 10. The two items from the brief not covered by a task, post-stratification and extremising, are listed above with the reason and the trigger condition.

**Placeholder scan.** No TBDs. Every code step carries the code. Task 1 Step 4 names the specific way the first implementation can fail and gives the corrected function rather than saying "handle overlaps".

**Type consistency.** `CalibrationMap(a, b, anchors_used)` is constructed in `fit_map` and consumed by `apply_map` and `metrics.summarize_poll` with the same field names throughout. `Anchor(question, option, predicted, actual, n, note, recorded_at)` is positional-compatible with every call in Tasks 5, 6 and 10. `shuffled_criteria` is keyword-only on `seed` and `agent_id` in both its definition and all three call sites. `audit_variants` returns `{variant, key, terms}` and every consumer reads those three keys.
