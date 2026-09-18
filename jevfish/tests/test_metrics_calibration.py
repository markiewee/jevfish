import pytest

from jevfish import metrics
from jevfish.calibrate import CalibrationMap, IDENTITY


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
    with pytest.raises(ValueError) as e:
        metrics.summarize_poll(records([0.5]), n_levels=5, estimand="occupancy")
    assert "occupancy" in str(e.value)


def test_calibration_map_is_applied_and_reports_the_raw_number_too():
    # b=1.8906 is the shift fitted on the real 801-person Pureloft distribution. Fed a
    # degenerate input of identical values it lands at 0.897, not 0.892, because the
    # mean of sigmoid is not sigmoid of the mean. That is not a bug, it is the reason
    # the map is applied per persona. See the next test.
    m = CalibrationMap(a=1.8906, b=1.0, anchors_used=1)
    s = metrics.summarize_poll(records([0.568] * 5), n_levels=5, calibration=m)
    assert s["calibrated"] is True
    assert s["mean_outcome"] == pytest.approx(0.8970, abs=1e-3)
    assert s["mean_outcome_raw"] == pytest.approx(0.568)
    assert "1 resolved outcome" in s["calibration_note"]


def test_calibrating_per_persona_is_not_the_same_as_calibrating_the_aggregate():
    """Why apply_map takes the whole crowd and not the mean.

    Measured on the real 801-person Pureloft poll: per-persona gives 0.8920, which is the
    actual outcome, while calibrating the aggregate gives 0.8969. sigmoid is non-linear,
    so the two are different functions and only one of them is right.
    """
    from jevfish.calibrate import apply_map

    m = CalibrationMap(a=1.8906, b=1.0, anchors_used=1)
    spread = [0.40, 0.50, 0.568, 0.64, 0.73]
    per_persona = sum(apply_map(spread, m)) / len(spread)
    on_aggregate = apply_map([sum(spread) / len(spread)], m)[0]
    assert per_persona != pytest.approx(on_aggregate, abs=1e-4)
    # summarize_poll must use the per-persona route
    s = metrics.summarize_poll(records(spread), n_levels=5, calibration=m)
    assert s["mean_outcome"] == pytest.approx(per_persona)


def test_the_identity_map_reports_uncalibrated():
    s = metrics.summarize_poll(records([0.5]), n_levels=5, calibration=IDENTITY)
    assert s["calibrated"] is False
    assert "uncalibrated" in s["calibration_note"]


def test_honest_half_width_replaces_the_sampling_interval_and_says_so():
    s = metrics.summarize_poll(records([0.5] * 100), n_levels=5, honest_half_width=0.30)
    assert s["low"] == pytest.approx(20.0)
    assert s["high"] == pytest.approx(80.0)
    assert s["interval_covers"] == "our own past errors on resolved outcomes"


def test_honest_half_width_is_clamped_to_zero_one():
    s = metrics.summarize_poll(records([0.9] * 10), n_levels=5, honest_half_width=0.5)
    assert s["low"] == pytest.approx(4.0)
    assert s["high"] == pytest.approx(10.0)


def test_the_sampling_interval_narrows_with_n_which_is_the_bug_we_are_labelling():
    """This is why interval_covers exists. The number is real but it measures the wrong thing."""
    small = metrics.summarize_poll(records([0.5] * 50), n_levels=5)
    large = metrics.summarize_poll(records([0.5] * 800), n_levels=5)
    small_hw = (small["high"] - small["low"]) / 2 / small["n"]
    large_hw = (large["high"] - large["low"]) / 2 / large["n"]
    assert large_hw < small_hw
    assert small["interval_covers"] == large["interval_covers"]
