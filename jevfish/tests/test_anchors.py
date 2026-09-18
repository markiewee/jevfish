import pytest

from jevfish.anchors import Anchor, load_anchors, save_anchor


def test_save_then_load_roundtrips(tmp_path):
    path = tmp_path / "anchors.json"
    a = Anchor(
        question="pureloft nightly rate",
        option="MYR 300",
        predicted=0.568,
        actual=0.892,
        n=801,
        note="610 resolved nights",
        model_version="jev-latest",
    )
    save_anchor(path, a)
    got = load_anchors(path)
    assert len(got) == 1
    assert got[0].predicted == 0.568
    assert got[0].actual == 0.892
    assert got[0].question == "pureloft nightly rate"
    assert got[0].recorded_at  # stamped automatically


def test_load_is_empty_when_the_file_does_not_exist(tmp_path):
    assert load_anchors(tmp_path / "missing.json") == []


def test_anchors_append_and_filter(tmp_path):
    path = tmp_path / "anchors.json"
    save_anchor(path, Anchor("rates", "MYR 300", 0.568, 0.892, 801, model_version="v1"))
    save_anchor(path, Anchor("rates", "MYR 400", 0.395, 0.700, 801, model_version="v2"))
    save_anchor(path, Anchor("cleaning", "plus S$100", 0.45, 0.30, 48))
    assert len(load_anchors(path)) == 3
    assert len(load_anchors(path, question="rates")) == 2
    assert len(load_anchors(path, model_version="v1")) == 1
    assert len(load_anchors(path, estimand="choice_share_of_described_set")) == 0


def test_residual_is_the_absolute_error():
    assert Anchor("q", "o", 0.568, 0.892, 801).residual == pytest.approx(0.324)


def test_anchor_rejects_a_probability_outside_zero_to_one():
    with pytest.raises(ValueError):
        Anchor("q", "o", 1.2, 0.5, 10)
    with pytest.raises(ValueError):
        Anchor("q", "o", 0.5, -0.1, 10)
    with pytest.raises(ValueError):
        Anchor("q", "o", 0.5, 0.5, 0)


def test_anchor_rejects_an_estimand_that_is_really_a_real_world_rate():
    with pytest.raises(ValueError) as e:
        Anchor("q", "o", 0.5, 0.5, 10, estimand="occupancy")
    assert "occupancy is not an estimand" in str(e.value)
