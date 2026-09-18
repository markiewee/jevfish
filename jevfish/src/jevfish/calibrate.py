"""Map raw judge probabilities onto observed frequencies, and say how wrong we usually are.

The map is T(q) = sigmoid(a + b * logit(q)) with b > 0, from
arxiv.org/html/2606.16183v1, whose authors describe it as correcting "the scale of the
probabilities without discarding their ordinal information". `a` fixes the level, `b`
rescales the shape. Because it is strictly monotone it can never reorder the options.

Two things that are easy to get wrong and matter:

1. Apply it PER PERSONA, before aggregation. A map on the aggregate share is a different
   function, because sigmoid is non-linear. The published system calibrates at the persona
   level, and the market-research trade reached the same conclusion independently: a single
   global multiplier was measured as inferior to per-respondent adjustment.
2. Calibration must come before any ensembling or post-stratification. Ensembling
   uncalibrated members was measured to make them worse, while ensembling calibrated ones
   helped.

Intervals come from split conformal on our own past absolute errors, which is
distribution-free and needs n >= 1/alpha - 1 anchors.

Measured on the Pureloft backtest: the reported Poisson-binomial half-width was 2.82pp
against an actual error of 32.4pp, an 11.5x understatement that got worse as the crowd
grew, because sampling noise shrinks as 1/sqrt(n) while model bias does not move.
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
        outcome = "outcome" if self.anchors_used == 1 else "outcomes"
        scale = "" if self.b == 1.0 else f", scale {self.b:+.3f}"
        return (
            f"calibrated on {self.anchors_used} resolved {outcome}: "
            f"shift {self.a:+.3f}{scale}"
        )


IDENTITY = CalibrationMap(0.0, 1.0, 0)


def apply_map(persona_probabilities: list[float], m: CalibrationMap) -> list[float]:
    """Calibrate each persona probability. Aggregate AFTER this, never before."""
    if m.is_identity:
        return list(persona_probabilities)
    return [_sigmoid(m.a + m.b * _logit(p)) for p in persona_probabilities]


def fit_map(anchors: list) -> CalibrationMap:
    """Least squares in logit space. One anchor fits `a` only; two or more fit `a` and `b`.

    With one anchor the scale is not identified, so `b` stays at 1 and only the level
    moves. That is the correct thing to do rather than inventing a slope, and it is what
    the rectification literature does with a single labelled point.
    """
    pairs = [(_logit(x.predicted), _logit(x.actual)) for x in anchors]
    if not pairs:
        return IDENTITY
    if len(pairs) == 1:
        x, y = pairs[0]
        return CalibrationMap(a=y - x, b=1.0, anchors_used=1)
    n = len(pairs)
    mx = sum(x for x, _ in pairs) / n
    my = sum(y for _, y in pairs) / n
    sxx = sum((x - mx) ** 2 for x, _ in pairs)
    if sxx == 0:
        # Every anchor sits at the same predicted value, so the slope is unidentified.
        return CalibrationMap(a=my - mx, b=1.0, anchors_used=n)
    b = sum((x - mx) * (y - my) for x, y in pairs) / sxx
    b = max(EPS, b)  # b > 0 is what keeps the map monotone
    return CalibrationMap(a=my - b * mx, b=b, anchors_used=n)


def conformal_half_width(abs_residuals: list[float], alpha: float = 0.10) -> float:
    """Split-conformal half-width. Distribution-free finite-sample coverage.

    Four residuals buy 80 percent coverage, nine buy 90, nineteen buy 95. Below the
    threshold this raises rather than returning a number, because a made-up interval is
    the exact failure this module exists to remove.

    Coverage is marginal, not conditional. It does not protect a question unlike anything
    in the anchor set, so narrow anchors by question and estimand before pooling residuals.
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
