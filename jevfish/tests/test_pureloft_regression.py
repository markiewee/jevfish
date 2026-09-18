"""Pins the numbers measured in docs/research/calibration-experiment.md.

Real data: 4,005 stored poll records from the Pureloft Suasana KL backtest, 801 people at
each of five nightly rates. The only real outcome available is the level at MYR 300,
89.2 percent occupancy over 610 resolved nights from Pureloft's own pricing_calendar.

If any of these break, a finding has silently regressed. Do not adjust a number here to
make a test pass; work out which claim changed.
"""

import json
import pathlib

import pytest

from jevfish.anchors import Anchor
from jevfish.calibrate import apply_map, conformal_half_width, fit_map
from jevfish.frame_audit import curve_check, sensitivity_verdict
from jevfish.scoring import crps_share, murphy_decomposition

TRUTH_P300 = 0.892
RATES = {"p200": 200, "p250": 250, "p300": 300, "p400": 400, "p500": 500}
POLLS = json.loads(
    (pathlib.Path(__file__).parent / "fixtures" / "pureloft_polls.json").read_text()
)
P300 = POLLS["p300"]


def mean(xs):
    return sum(xs) / len(xs)


# --- the run we measured ----------------------------------------------------


def test_the_fixture_is_the_run_we_measured():
    assert {k: len(v) for k, v in POLLS.items()} == {k: 801 for k in RATES}
    assert mean(P300) == pytest.approx(0.568, abs=5e-4)


def test_the_raw_level_error_is_32_4_points():
    assert crps_share([mean(P300)], [TRUTH_P300]) == pytest.approx(0.324, abs=5e-4)


def test_the_crowd_is_degenerate():
    """Nobody would definitely book and nobody would definitely refuse."""
    assert min(P300) == pytest.approx(0.35, abs=0.01)
    assert max(P300) == pytest.approx(0.72, abs=0.01)
    assert len(set(P300)) == 30, "Jev's resolution floor: 30 distinct values across 801 people"


def test_four_values_cover_most_of_the_crowd():
    counts = sorted((P300.count(v) for v in set(P300)), reverse=True)
    assert sum(counts[:4]) > 300, "the four commonest values cover 341 of 801"


# --- the interval was 11.5x too narrow --------------------------------------


def test_the_reported_interval_understated_the_error_by_more_than_ten_times():
    from jevfish import metrics

    recs = [{"outcome_p": p, "stance": 2.0, "agent_id": i} for i, p in enumerate(P300)]
    s = metrics.summarize_poll(recs, n_levels=5)
    half_width = (s["high"] - s["low"]) / 2 / s["n"]
    actual_error = abs(s["mean_outcome"] - TRUTH_P300)
    assert half_width == pytest.approx(0.0282, abs=5e-4)
    assert actual_error / half_width > 10
    assert s["interval_covers"] == "sampling noise in the synthetic crowd only"


# --- calibration ------------------------------------------------------------


def test_one_anchor_removes_the_level_error():
    m = fit_map([Anchor("pureloft", "MYR 300", predicted=mean(P300), actual=TRUTH_P300, n=801)])
    assert crps_share([mean(apply_map(P300, m))], [TRUTH_P300]) < 0.01


def test_calibration_cannot_reorder_the_rungs():
    m = fit_map([Anchor("pureloft", "MYR 300", predicted=0.568, actual=TRUTH_P300, n=801)])
    raw = [mean(POLLS[v]) for v in ("p500", "p400", "p300", "p250", "p200")]
    assert raw == sorted(raw), "raw shares rise as the rate falls"
    assert apply_map(raw, m) == sorted(apply_map(raw, m))


def test_decomposition_says_the_error_is_level_not_shape():
    m = fit_map([Anchor("pureloft", "MYR 300", predicted=mean(P300), actual=TRUTH_P300, n=801)])
    order = ["p200", "p250", "p300", "p400", "p500"]
    preds = [mean(POLLS[v]) for v in order]
    calibrated = [mean(apply_map(POLLS[v], m)) for v in order]
    d = murphy_decomposition(preds, calibrated)
    assert d["spearman"] == pytest.approx(1.0), "shape is preserved exactly"
    assert d["bias"] < -0.2, "level is badly low"
    assert d["mae_after_removing_bias"] < d["mae"]


def test_nine_anchors_are_needed_before_an_honest_interval_exists():
    residuals = [0.324]
    with pytest.raises(ValueError):
        conformal_half_width(residuals, alpha=0.10)
    assert conformal_half_width(residuals * 9, alpha=0.10) == pytest.approx(0.324)


# --- the frame wrote the curve ----------------------------------------------


def test_the_frame_wording_flipped_the_recommendation():
    """Finding 7. The load-bearing result, and it needs no elasticity benchmark."""
    shipped = {200: 0.686, 250: 0.656, 300: 0.517, 400: 0.267, 500: 0.211}
    neutral = {200: 0.554, 250: 0.534, 300: 0.527, 400: 0.510, 500: 0.498}

    assert curve_check(shipped, expect="decreasing", max_abs_elasticity=2.0)[
        "elasticity"
    ] == pytest.approx(-1.432, abs=0.01)
    assert curve_check(neutral, expect="decreasing", max_abs_elasticity=2.0)[
        "elasticity"
    ] == pytest.approx(-0.113, abs=0.01)

    best = lambda c: max(c, key=lambda r: r * c[r])  # noqa: E731
    assert best(shipped) == 250, "as shipped, the tool says cut the rate"
    assert best(neutral) == 500, "with neutral wording, it says raise it"

    v = sensitivity_verdict(shipped, neutral)
    assert v["agrees"] is False
    assert v["max_shift"] > 0.2


def test_the_real_stored_frame_still_trips_the_audit():
    """Guards against someone 'fixing' the audit by loosening it."""
    from jevfish.frame_audit import audit_variants

    frame_path = pathlib.Path(__file__).parents[1] / "data/projects/p_71f65447c6/frame.json"
    if not frame_path.exists():
        pytest.skip("the stored Pureloft project is not present in this checkout")
    problems = audit_variants(json.loads(frame_path.read_text())["variants"])
    assert len(problems) == 5, "all five rate options carried comparative wording"
    assert all(p["key"] == "rate_note" for p in problems)
