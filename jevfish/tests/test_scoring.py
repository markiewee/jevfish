import math

import pytest

from jevfish.scoring import (
    brier,
    crps_share,
    log_score,
    murphy_decomposition,
    skill_score,
)


def test_brier_is_squared_error():
    assert brier([1.0], [1]) == 0.0
    assert brier([0.0], [1]) == 1.0
    assert brier([0.5, 0.5], [1, 0]) == 0.25


def test_log_score_is_negative_log_likelihood_and_clips_certainty():
    assert log_score([0.5], [1]) == pytest.approx(math.log(2))
    assert log_score([1.0], [1]) == pytest.approx(0.0, abs=1e-9)
    assert math.isfinite(log_score([0.0], [1]))
    assert log_score([0.0], [1]) < 40


def test_crps_share_is_absolute_error_for_a_point_forecast():
    assert crps_share([0.6], [0.6]) == 0.0
    assert crps_share([0.568], [0.892]) == pytest.approx(0.324, abs=1e-9)


def test_murphy_decomposition_separates_level_from_shape():
    preds = [0.1, 0.3, 0.5, 0.7]
    truth = [0.4, 0.6, 0.8, 1.0]
    d = murphy_decomposition(preds, truth)
    assert d["bias"] == pytest.approx(-0.3)
    assert d["spearman"] == pytest.approx(1.0)
    assert d["mae"] == pytest.approx(0.3)
    assert d["mae_after_removing_bias"] == pytest.approx(0.0, abs=1e-9)


def test_murphy_spearman_is_nan_when_predictions_are_flat():
    # A flat prediction has no rank information; it must not report a correlation.
    d = murphy_decomposition([0.5, 0.5, 0.5], [0.1, 0.5, 0.9])
    assert math.isnan(d["spearman"])


def test_skill_score_against_a_named_baseline():
    assert skill_score(0.1, 0.4) == pytest.approx(0.75)
    assert skill_score(0.4, 0.4) == 0.0
    assert skill_score(0.8, 0.4) == pytest.approx(-1.0)
    with pytest.raises(ValueError):
        skill_score(0.1, 0.0)


def test_every_rule_refuses_mismatched_or_empty_input():
    for fn in (brier, log_score, crps_share):
        with pytest.raises(ValueError):
            fn([0.5], [1, 0])
        with pytest.raises(ValueError):
            fn([], [])
