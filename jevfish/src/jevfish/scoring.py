"""Proper scoring rules, and a decomposition that separates level error from shape error.

Brier and log score are proper for a binary outcome. CRPS is proper for a share. Every
score here is oriented so that LOWER IS BETTER, except `skill_score`.

Expected Calibration Error is deliberately absent. It is not a proper scoring rule, and a
model with no discriminatory power at all can drive it to zero, so it can certify a useless
predictor as well calibrated.

`murphy_decomposition` is the one to read first on a bad result. `bias` is the part a
calibration shift can remove and `spearman` is the part it cannot, because a monotone
calibration map never reorders anything. On the Pureloft backtest the rank order was
perfect while the level was 32.4 points low, which is the signature of a level problem
rather than a modelling problem.
"""

from __future__ import annotations

import math

EPS = 1e-15


def _pairs(a: list[float], b: list, name_b: str) -> None:
    if len(a) != len(b):
        raise ValueError(f"preds and {name_b} must be the same length")
    if not a:
        raise ValueError("need at least one prediction")


def brier(preds: list[float], outcomes: list[int]) -> float:
    """Mean squared error of probabilities against 0/1 outcomes. Proper."""
    _pairs(preds, outcomes, "outcomes")
    return sum((p - o) ** 2 for p, o in zip(preds, outcomes)) / len(preds)


def log_score(preds: list[float], outcomes: list[int]) -> float:
    """Mean negative log likelihood. Proper. Clipped so a confident miss stays finite."""
    _pairs(preds, outcomes, "outcomes")
    total = 0.0
    for p, o in zip(preds, outcomes):
        q = min(1 - EPS, max(EPS, p))
        total += -math.log(q if o else 1 - q)
    return total / len(preds)


def crps_share(preds: list[float], truths: list[float]) -> float:
    """CRPS of a point forecast for a share, which reduces to mean absolute error."""
    _pairs(preds, truths, "truths")
    return sum(abs(p - t) for p, t in zip(preds, truths)) / len(preds)


def _rank(xs: list[float]) -> list[float]:
    """Ranks with ties averaged, so a flat prediction does not fake a correlation."""
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
    """Split the error into the part calibration can fix and the part it cannot.

    `bias` is the mean signed error, removable by a level shift. `spearman` is rank
    correlation, which a monotone calibration map leaves untouched, so it is the real
    measure of whether the model orders the options correctly.
    """
    _pairs(preds, truths, "truths")
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
    """Fraction of a named baseline's error the model removes. Higher is better.

    0 means no better than the baseline. Negative means worse. Always name the baseline
    when reporting this: the honest one for JevFish is a single LLM call with an empty
    persona, because if the graph, the crowd and the simulation rounds do not beat that,
    they are pure cost.
    """
    if baseline_error <= 0:
        raise ValueError("baseline_error must be positive")
    return 1.0 - model_error / baseline_error
