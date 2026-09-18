import copy
import random

import pytest

from jevfish.crowd import build_crowd, build_follows, sample_public
from jevfish.fakes import frame as fake_frame
from jevfish.frame import FrameError, build_frame, normalize_frame, variant_subject
from jevfish.graph import build_graph
from jevfish.llm import FakeLLM

SEED = """Lazybee runs co-living homes in Thomson.

Mark Wee founded Lazybee with Jason Park. Thomson Grove is one of the homes.

Renters in Singapore compare rooms on price and cleanliness. Acme Realty competes with Lazybee."""


@pytest.fixture(scope="module")
def graph():
    return build_graph(FakeLLM(), "Will renters book a viewing?", SEED)


def test_build_frame_from_graph(graph):
    f = build_frame(FakeLLM(), "Will renters book a viewing?", graph)
    assert f["question"] == "Will renters book a viewing?"
    assert len(f["stance"]["levels"]) == 5
    assert f["variants"] == [{"id": "base", "label": "As described", "subject": {}}]
    assert f["opening_posts"] and f["opening_posts"][0]["author"] in {n["name"] for n in graph["nodes"]}
    assert f["opening_posts"][0]["talking_point"] == "tp01"


def test_normalize_frame_cleans_points_and_variants():
    raw = fake_frame([{"role": "user", "content": "Prediction question: X?"}])
    raw["talking_points"] += [
        {"id": "tp00", "text": "duplicate id", "side": "pro"},
        {"id": "none", "text": "reserved id", "side": "sideways"},
        {"id": "x", "text": "   "},
    ]
    raw["variants"] = [{"id": "A", "label": "Now", "subject": {}}, {"id": "B!", "label": "Cheaper", "subject": {"price": "$1"}},
                       {"id": "A", "label": "dup"}]
    f = normalize_frame(raw)
    ids = [p["id"] for p in f["talking_points"]]
    assert len(ids) == len(set(ids)) and "tp00_2" in ids and "point_none" in ids
    assert {p["side"] for p in f["talking_points"]} <= {"pro", "con", "neutral"}
    assert [v["id"] for v in f["variants"]] == ["A", "B"]
    assert variant_subject(f, "B")["price"] == "$1"
    assert variant_subject(f, "B")["source"] == "seed documents"
    with pytest.raises(FrameError):
        variant_subject(f, "Z")


@pytest.mark.parametrize("mutate", [
    lambda f: f["outcome"].update(instructions=""),
    lambda f: f["stance"].update(levels=["one"]),
    lambda f: f.update(talking_points=[]),
    lambda f: f.update(stance=None),
])
def test_normalize_frame_rejects_unusable_frames(mutate):
    raw = fake_frame([{"role": "user", "content": "Prediction question: X?"}])
    mutate(raw)
    with pytest.raises(FrameError):
        normalize_frame(raw)


def test_build_crowd(graph):
    progress = []
    crowd = build_crowd(FakeLLM(), "q", graph, public_size=30, max_stakeholders=3, progress=lambda p, m: progress.append(m))
    agents = crowd["agents"]
    assert [a["agent_id"] for a in agents] == list(range(len(agents)))
    stake = [a for a in agents if a["kind"] == "stakeholder"]
    public = [a for a in agents if a["kind"] == "public"]
    assert 1 <= len(stake) <= 3 and len(public) == 30
    assert all(a["entity_id"] for a in stake)
    assert {a["segment"] for a in public} <= {"young professionals", "students", "families"}
    assert all(a["follows"] and a["agent_id"] not in a["follows"] for a in agents)
    assert "Crowd ready" in progress[-1]
    again = build_crowd(FakeLLM(), "q", graph, public_size=30, max_stakeholders=3)
    assert again["agents"] == agents


def test_personas_can_exclude_entities(graph):
    def exclude_all(messages):
        import re
        ids = re.findall(r"^- id=(\S+) ", messages[-1]["content"], flags=re.M)
        return {"personas": [{"entity_id": i, "include": False} for i in ids] + [{"entity_id": "n9999", "include": True}]}

    crowd = build_crowd(FakeLLM({"personas": exclude_all}), "q", graph, public_size=5)
    assert crowd["stats"]["stakeholders"] == 0 and len(crowd["agents"]) == 5


def test_follow_graph_favours_influence():
    rng = random.Random(1)
    segs = [{"name": "people", "share": 1, "description": "d", "activity": 0.5, "attributes": {"x": {"a": 1}}}]
    agents = sample_public(segs, 200, rng, start_id=0)
    for a in agents[:5]:
        a["influence"] = 1.0
    build_follows(agents, {"edges": []}, 5, rng)
    from collections import Counter
    counts = Counter(f for a in agents for f in a["follows"])
    top = sum(counts[i] for i in range(5)) / 5
    rest = sum(counts[i] for i in range(5, 200)) / 195
    assert top > 5 * rest


def test_attribute_shapes_are_tolerated():
    from jevfish.crowd import _attributes

    assert _attributes({"age": {"20s": 0.6, "30s": 0.4}}) == {"age": {"20s": 0.6, "30s": 0.4}}
    assert _attributes({"age": ["20s", "30s"]}) == {"age": {"20s": 1.0, "30s": 1.0}}
    assert _attributes({"age": {"20s": "young adults"}}) == {"age": {"20s": 1.0}}
    assert _attributes([{"name": "budget", "values": [{"value": "low", "weight": 2}, {"value": "high", "weight": 1}]}]) == {
        "budget": {"low": 2.0, "high": 1.0}}
    assert _attributes({"x": {"a": 0}, "y": None}) == {}


# --- the frame must not dictate the answer (Finding 7) ----------------------

_GOOD_BASE = {
    "question": "would they book?",
    "outcome": {"instructions": "would `agent` book `subject`?"},
    "stance": {"levels": ["rules it out", "unsure", "books it"]},
    "talking_points": [{"id": "p", "text": "a point", "side": "pro"}],
}


def test_normalize_frame_rejects_comparative_variant_wording():
    from jevfish.frame import FrameError, normalize_frame

    data = {
        **_GOOD_BASE,
        "variants": [
            {"id": "a", "label": "MYR 300", "subject": {"rate": 300, "note": "the current rate"}},
            {"id": "b", "label": "MYR 500", "subject": {"rate": 500, "note": "well above market"}},
        ],
    }
    with pytest.raises(FrameError) as e:
        normalize_frame(data, "q")
    msg = str(e.value)
    assert "note" in msg
    assert "current" in msg
    assert "-1.432" in msg          # the message must carry the evidence


def test_normalize_frame_accepts_options_differing_only_in_the_quantity():
    from jevfish.frame import normalize_frame

    data = {
        **_GOOD_BASE,
        "variants": [
            {"id": "a", "label": "MYR 300", "subject": {"rate": 300}},
            {"id": "b", "label": "MYR 500", "subject": {"rate": 500}},
        ],
    }
    frame = normalize_frame(data, "q")
    assert [v["subject"] for v in frame["variants"]] == [{"rate": 300}, {"rate": 500}]


def test_normalize_frame_still_accepts_a_frame_with_no_variants():
    from jevfish.frame import normalize_frame

    frame = normalize_frame({**_GOOD_BASE, "variants": []}, "q")
    assert frame["variants"] == [{"id": "base", "label": "As described", "subject": {}}]


def test_build_frame_retries_then_self_heals_rather_than_breaking_a_run():
    """A sampling model must not randomly break prepare. Retry, then strip and warn."""
    from jevfish.frame import build_frame

    bad = {
        **_GOOD_BASE,
        "opening_posts": [],
        "variants": [
            {"id": "A", "label": "Now", "subject": {"rate": 300, "note": "the current rate"}},
            {"id": "B", "label": "Up", "subject": {"rate": 500, "note": "well above market"}},
        ],
    }

    class AlwaysBad:
        def __init__(self):
            self.calls = 0

        def json(self, task, messages, **kw):
            self.calls += 1
            return bad

        def chat(self, task, messages, **kw):
            return ""

    llm = AlwaysBad()
    graph = {"ontology": {"entity_types": []}, "nodes": [], "edges": []}
    frame = build_frame(llm, "q", graph)
    assert llm.calls == 2, "must retry exactly once before self-healing"
    assert [v["subject"] for v in frame["variants"]] == [{"rate": 300}, {"rate": 500}]
    assert frame["warnings"]
    assert "removed automatically" in frame["warnings"][0]


def test_build_frame_accepts_a_clean_frame_without_retrying():
    from jevfish.frame import build_frame

    good = {
        **_GOOD_BASE,
        "opening_posts": [],
        "variants": [
            {"id": "A", "label": "MYR 300", "subject": {"rate": 300}},
            {"id": "B", "label": "MYR 500", "subject": {"rate": 500}},
        ],
    }

    class Good:
        def __init__(self):
            self.calls = 0

        def json(self, task, messages, **kw):
            self.calls += 1
            return good

        def chat(self, task, messages, **kw):
            return ""

    llm = Good()
    frame = build_frame(llm, "q", {"ontology": {"entity_types": []}, "nodes": [], "edges": []})
    assert llm.calls == 1
    assert "warnings" not in frame
