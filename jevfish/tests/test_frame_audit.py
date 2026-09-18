"""The frame must not tell the judge which option is better.

On the Pureloft ladder the shipped per-option wording produced elasticity -1.432 and said
cut the rate, while neutral wording of the same length produced -0.090 and said raise it,
on identical inputs. See docs/research/calibration-experiment.md, Finding 7.
"""

import pytest

from jevfish.frame_audit import (
    audit_variants,
    comparative_spans,
    curve_check,
    neutralise,
    sensitivity_verdict,
)


# --- detecting the wording -------------------------------------------------


def test_flags_the_exact_strings_that_broke_the_pureloft_run():
    # Verbatim from the stored frame that produced elasticity -1.432.
    assert comparative_spans("a third below the current rate") == ["third below", "current"]
    assert comparative_spans("two thirds above the current rate") == ["above", "current"]
    assert comparative_spans("the rate Pureloft actually charges") == ["actually"]


def test_passes_neutral_wording():
    assert comparative_spans("the nightly rate for these dates") == []
    assert comparative_spans("MYR 300 per night") == []
    assert comparative_spans("") == []


def test_matching_is_word_boundary_not_substring():
    # "aboveboard" must not match "above"; "discounted" is its own listed term.
    assert comparative_spans("an aboveboard arrangement") == []
    assert comparative_spans("a discounted rate") == ["discount"] or comparative_spans(
        "a discounted rate"
    ) == ["discounted"]


def test_audit_reports_per_variant_and_per_key():
    variants = [
        {"id": "p300", "label": "MYR 300", "subject": {"rate_note": "the current rate"}},
        {"id": "p500", "label": "MYR 500", "subject": {"rate_note": "well above market"}},
    ]
    assert audit_variants(variants) == [
        {"variant": "p300", "key": "rate_note", "terms": ["current"]},
        {"variant": "p500", "key": "rate_note", "terms": ["well above"]},
    ]


def test_audit_is_quiet_when_options_differ_only_in_the_quantity():
    variants = [
        {"id": "a", "label": "MYR 300", "subject": {"nightly_rate_myr": 300}},
        {"id": "b", "label": "MYR 500", "subject": {"nightly_rate_myr": 500}},
    ]
    assert audit_variants(variants) == []


def test_audit_ignores_non_string_values_and_missing_subjects():
    variants = [
        {"id": "a", "label": "A", "subject": {"rate": 300, "flag": True, "list": ["above"]}},
        {"id": "b", "label": "B"},
    ]
    assert audit_variants(variants) == []


# --- neutralising it -------------------------------------------------------


def test_neutralise_drops_offending_keys_and_keeps_the_quantity():
    frame = {
        "subject": {"property": "a 4-bedroom apartment"},
        "variants": [
            {
                "id": "p300",
                "label": "MYR 300 (current)",
                "subject": {"nightly_rate_myr": 300, "rate_note": "the current rate"},
            },
            {
                "id": "p500",
                "label": "MYR 500",
                "subject": {
                    "nightly_rate_myr": 500,
                    "rate_note": "two thirds above the current rate",
                },
            },
        ],
    }
    out = neutralise(frame)
    assert out["variants"][0]["subject"] == {"nightly_rate_myr": 300}
    assert out["variants"][1]["subject"] == {"nightly_rate_myr": 500}
    assert out["variants"][0]["label"] == "MYR 300"
    # the input must not be mutated
    assert frame["variants"][0]["subject"]["rate_note"] == "the current rate"
    assert frame["variants"][0]["label"] == "MYR 300 (current)"


def test_neutralise_drops_the_key_from_every_variant_not_just_the_guilty_one():
    # Otherwise the options stop being comparable, which is worse than the original problem.
    frame = {
        "subject": {},
        "variants": [
            {"id": "a", "label": "A", "subject": {"rate": 1, "note": "plain text"}},
            {"id": "b", "label": "B", "subject": {"rate": 2, "note": "well above market"}},
        ],
    }
    out = neutralise(frame)
    assert out["variants"][0]["subject"] == {"rate": 1}
    assert out["variants"][1]["subject"] == {"rate": 2}


def test_neutralise_is_a_no_op_on_a_clean_frame():
    frame = {"subject": {}, "variants": [{"id": "a", "label": "A", "subject": {"price": 1}}]}
    assert neutralise(frame) == frame


# --- reporting whether the result survives ---------------------------------


def test_agreeing_curves_pass():
    v = sensitivity_verdict(
        {"a": 0.55, "b": 0.53, "c": 0.52}, {"a": 0.554, "b": 0.534, "c": 0.527}
    )
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
    with pytest.raises(ValueError):
        sensitivity_verdict({"a": 0.5}, {"b": 0.5})


def test_a_rank_change_alone_fails_even_within_tolerance():
    # Shifts are tiny but the top option swaps, which is the decision-relevant failure.
    v = sensitivity_verdict({"a": 0.501, "b": 0.499}, {"a": 0.499, "b": 0.501})
    assert v["agrees"] is False
    assert v["rank_agreement"] < 1.0


# --- refusing impossible curves --------------------------------------------


def test_a_plausible_downward_curve_passes():
    v = curve_check(
        {200: 0.69, 250: 0.67, 300: 0.57, 400: 0.40, 500: 0.33},
        expect="decreasing",
        max_abs_elasticity=2.0,
    )
    assert v["ok"] is True
    assert v["elasticity"] == pytest.approx(-0.8731, abs=0.001)  # verified by hand


def test_a_curve_steeper_than_the_stated_ceiling_is_blocked():
    # the synthetic run that produced -3.29. Fitted value on these shares is -4.35.
    v = curve_check(
        {200: 0.95, 250: 0.80, 300: 0.45, 400: 0.09, 500: 0.02},
        expect="decreasing",
        max_abs_elasticity=2.0,
    )
    assert v["ok"] is False
    assert "steeper" in v["message"]
    assert "2.0" in v["message"]  # the ceiling must be stated, not hidden


def test_the_ceiling_is_required_and_has_no_default():
    # A silent default would smuggle in an unsourced benchmark, which is how we got burned.
    with pytest.raises(TypeError):
        curve_check({200: 0.6, 300: 0.5, 400: 0.4}, expect="decreasing")


def test_a_curve_going_the_wrong_way_is_blocked():
    v = curve_check(
        {200: 0.30, 250: 0.40, 300: 0.50, 400: 0.60, 500: 0.70},
        expect="decreasing",
        max_abs_elasticity=2.0,
    )
    assert v["ok"] is False
    assert "wrong direction" in v["message"]


def test_a_flat_curve_is_reported_as_no_signal_not_as_a_pass():
    v = curve_check(
        {200: 0.501, 250: 0.500, 300: 0.500, 400: 0.499, 500: 0.499},
        expect="decreasing",
        max_abs_elasticity=2.0,
    )
    assert v["ok"] is False
    assert "no measurable response" in v["message"]


def test_an_increasing_expectation_is_honoured():
    v = curve_check(
        {1: 0.30, 2: 0.45, 3: 0.60}, expect="increasing", max_abs_elasticity=2.0
    )
    assert v["ok"] is True
    assert v["elasticity"] > 0


def test_curve_check_needs_at_least_three_levels():
    with pytest.raises(ValueError):
        curve_check({200: 0.6, 300: 0.5}, expect="decreasing", max_abs_elasticity=2.0)
