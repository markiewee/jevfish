import pytest

from jevfish.anchors import Anchor
from jevfish.calibrate import (
    CalibrationMap,
    IDENTITY,
    apply_map,
    conformal_half_width,
    fit_map,
)


def test_identity_map_changes_nothing():
    assert apply_map([0.2, 0.5, 0.8], IDENTITY) == pytest.approx([0.2, 0.5, 0.8])
    assert IDENTITY.is_identity
    assert "uncalibrated" in IDENTITY.describe()


def test_one_anchor_fits_a_shift_only_and_hits_the_target():
    persona = [0.568] * 10
    anchors = [Anchor("q", "MYR 300", predicted=0.568, actual=0.892, n=801)]
    m = fit_map(anchors)
    assert m.b == 1.0, "one anchor cannot identify the scale"
    assert m.anchors_used == 1
    assert sum(apply_map(persona, m)) / len(persona) == pytest.approx(0.892, abs=1e-6)
    assert "1 resolved outcome:" in m.describe()


def test_map_is_strictly_monotone_so_it_cannot_reorder_options():
    m = CalibrationMap(a=1.89, b=1.0, anchors_used=1)
    out = apply_map([0.325, 0.395, 0.568, 0.670, 0.690], m)
    assert out == sorted(out)


def test_five_anchors_fit_both_level_and_scale():
    anchors = [
        Anchor("q", "a", 0.10, 0.30, 100),
        Anchor("q", "b", 0.30, 0.50, 100),
        Anchor("q", "c", 0.50, 0.70, 100),
        Anchor("q", "d", 0.70, 0.85, 100),
        Anchor("q", "e", 0.90, 0.95, 100),
    ]
    m = fit_map(anchors)
    assert m.anchors_used == 5
    assert m.b != 1.0
    assert m.b > 0, "monotonicity requires b > 0"
    assert "scale" in m.describe()


def test_a_perfect_predictor_fits_the_identity():
    anchors = [Anchor("q", str(i), p, p, 100) for i, p in enumerate((0.2, 0.5, 0.8))]
    m = fit_map(anchors)
    assert m.a == pytest.approx(0.0, abs=1e-9)
    assert m.b == pytest.approx(1.0, abs=1e-9)


def test_anchors_all_at_one_predicted_value_fall_back_to_a_shift():
    anchors = [Anchor("q", str(i), 0.5, 0.8, 100) for i in range(3)]
    m = fit_map(anchors)
    assert m.b == 1.0
    assert m.anchors_used == 3


def test_fit_map_with_no_anchors_returns_the_identity_and_says_so():
    m = fit_map([])
    assert (m.a, m.b, m.anchors_used) == (0.0, 1.0, 0)


def test_conformal_half_width_needs_nine_anchors_for_ninety_percent():
    with pytest.raises(ValueError) as e:
        conformal_half_width([0.1] * 8, alpha=0.10)
    assert "9" in str(e.value)
    assert conformal_half_width([0.2] * 9, alpha=0.10) == pytest.approx(0.2)


def test_conformal_half_width_is_the_quantile_of_absolute_residuals():
    residuals = [0.01, 0.02, 0.03, 0.04, 0.05, 0.06, 0.07, 0.08, 0.09, 0.30]
    assert conformal_half_width(residuals, alpha=0.10) == pytest.approx(0.30)


def test_conformal_thresholds_match_the_stated_schedule():
    assert conformal_half_width([0.1] * 4, alpha=0.20) == pytest.approx(0.1)
    with pytest.raises(ValueError):
        conformal_half_width([0.1] * 3, alpha=0.20)
    assert conformal_half_width([0.1] * 19, alpha=0.05) == pytest.approx(0.1)
    with pytest.raises(ValueError):
        conformal_half_width([0.1] * 18, alpha=0.05)
