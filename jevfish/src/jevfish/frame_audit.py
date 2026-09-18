"""Catch a frame that tells the judge which option is better.

A frame that labels one option "a third below the current rate" does not measure a price
response, it states one. Measured on the Pureloft ladder, 40 personas, five rates, nothing
else changed:

    rate_note as shipped (comparative)   elasticity -1.432   recommends cutting to MYR 250
    rate_note neutral, same length       elasticity -0.090   recommends raising to MYR 500
    rate_note removed                    elasticity -0.113   recommends raising to MYR 500

Neutral and absent agree to within 0.023, so it is the comparative content and not the
field. One LLM-authored adjective per option decided a revenue recommendation and pointed
it the opposite way. Neither number is a measurement.

Full write-up in docs/research/calibration-experiment.md, Finding 7.

Note the methodological trap that caught me first time round: testing a frame change at a
single option measures the level and says nothing about the slope. At MYR 300 the note read
"the rate Pureloft actually charges", which is roughly neutral, so the change looked
negligible. The bias lives at the ends of the ladder, which is exactly where the slope is
set. Any frame check has to sweep the whole option set, which is why `sensitivity_verdict`
and `curve_check` both take every option at once.
"""

from __future__ import annotations

import copy
import math
import re

# Words that position an option against another option or against a norm. Longer phrases
# first so that "third below" is reported instead of a bare "below".
COMPARATIVE = (
    "status quo",
    "market rate",
    "well above",
    "well below",
    "third above",
    "third below",
    "above",
    "below",
    "higher",
    "lower",
    "cheaper",
    "dearer",
    "current",
    "existing",
    "baseline",
    "usual",
    "standard",
    "today",
    "actually",
    "premium",
    "discount",
    "discounted",
    "better",
    "worse",
    "best",
    "worst",
    "aggressive",
    "conservative",
    "double",
    "half",
)


def comparative_spans(text: str) -> list[str]:
    """Comparative terms in `text`, longest match wins, in order of appearance.

    Word-boundary matching, so "aboveboard" does not count as "above".
    """
    low = str(text).lower()
    hits: list[tuple[int, int, str]] = []
    for term in COMPARATIVE:
        for m in re.finditer(rf"\b{re.escape(term)}\b", low):
            hits.append((m.start(), m.end(), term))
    # Longest first, so a longer phrase claims its span before a word inside it can.
    kept: list[tuple[int, int, str]] = []
    for start, end, term in sorted(hits, key=lambda h: (-(h[1] - h[0]), h[0])):
        if any(s <= start and end <= e for s, e, _ in kept):
            continue
        kept.append((start, end, term))
    return [term for _, _, term in sorted(kept)]


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


def neutralise(frame: dict) -> dict:
    """A deep copy of `frame` with comparative per-option text removed.

    A key is dropped from EVERY variant, not only the guilty one. Dropping it from just
    one leaves the options describing different things, which is worse than the original
    problem. Labels lose any trailing parenthetical such as "(current)".
    """
    out = copy.deepcopy(frame)
    bad_keys = {p["key"] for p in audit_variants(out.get("variants") or [])}
    for v in out.get("variants") or []:
        subject = v.get("subject") or {}
        v["subject"] = {k: val for k, val in subject.items() if k not in bad_keys}
        if "label" in v:
            v["label"] = re.sub(r"\s*\([^)]*\)\s*$", "", str(v["label"])).strip()
    return out


TOLERANCE = 0.05


def sensitivity_verdict(as_written: dict, neutralised: dict) -> dict:
    """Compare the same option set run with and without its per-option wording.

    If the two disagree, the run is reporting its own prompt. A rank change fails even
    when every shift is inside tolerance, because the rank is what a decision reads.
    """
    if set(as_written) != set(neutralised):
        raise ValueError("both runs must cover the same options")
    keys = list(as_written)
    if not keys:
        raise ValueError("need at least one option")
    shifts = {k: as_written[k] - neutralised[k] for k in keys}
    max_shift = max(abs(s) for s in shifts.values())
    rank_a = sorted(keys, key=lambda k: -as_written[k])
    rank_b = sorted(keys, key=lambda k: -neutralised[k])
    agreement = sum(x == y for x, y in zip(rank_a, rank_b)) / len(keys)
    agrees = max_shift <= TOLERANCE and agreement == 1.0
    if agrees:
        message = "the result holds when the per-option wording is neutralised"
    else:
        moved = round((1 - agreement) * len(keys))
        message = (
            f"the result depends on the frame's own wording: the largest option moved "
            f"{max_shift:.3f} and {moved} of {len(keys)} options changed rank. Treat this "
            "run as a statement about the prompt, not about the world."
        )
    return {
        "agrees": agrees,
        "max_shift": max_shift,
        "rank_agreement": agreement,
        "shifts": shifts,
        "message": message,
    }


FLAT = 0.02


def curve_check(shares: dict, *, expect: str, max_abs_elasticity: float) -> dict:
    """Refuse a response curve that is flat, runs backwards, or is implausibly steep.

    `shares` maps the numeric level of the varying attribute to the predicted share.

    `max_abs_elasticity` is REQUIRED and has no default, deliberately. A default would
    smuggle a benchmark into the code, and we got burned by exactly that. The "-0.36
    Cornell property-level benchmark" and the "-0.13 to -0.95 published property-level
    range" we had been judging runs against are both unsourced. Checked 18 September 2026:
    -0.36 is in neither Corgel, Lane and Woodworth (2012) nor Enz, Canina and van der Rest
    (2015), and the latter does not measure elasticity at all.

    What is supported for room rates: market-level estimates cluster in -0.1 to -0.9 (Singh
    and Corsun 2023, 2,503 US hotels, 2SLS, -0.165 short run and -0.79 long run). But
    Corgel et al. state that "elasticity tends to increase with data disaggregation", that
    individual-hotel elasticity "will be higher than their market level elasticity
    suggests", and that their figures "cannot be directly applied to an individual hotel".
    So one differentiated property can legitimately sit outside -0.9, and 2.0 is the
    defensible ceiling for a room-rate ladder rather than 1.0.

    The caller states the ceiling and the message repeats it, so anything this gate blocks
    traces back to a stated assumption instead of a hidden one.
    """
    if len(shares) < 3:
        raise ValueError("need at least three levels to check a curve")
    if expect not in ("decreasing", "increasing"):
        raise ValueError("expect must be 'decreasing' or 'increasing'")
    xs = [math.log(float(k)) for k in shares]
    ys = [math.log(max(1e-9, float(v))) for v in shares.values()]
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    elasticity = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sxx if sxx else 0.0

    wanted = -1 if expect == "decreasing" else 1
    if abs(elasticity) < FLAT:
        ok, message = False, (
            f"no measurable response: fitted elasticity {elasticity:+.3f} is flat. The run "
            "cannot tell the options apart, so do not read a winner off it."
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
            "caller supplied. Check the per-option wording before trusting this, and "
            "check that the ceiling itself is sourced."
        )
    else:
        ok, message = True, (
            f"fitted elasticity {elasticity:+.3f}, inside the stated ceiling of "
            f"{max_abs_elasticity:.1f}"
        )
    return {"ok": ok, "elasticity": elasticity, "message": message}
