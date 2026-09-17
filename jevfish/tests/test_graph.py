import pytest

from jevfish.graph import build_graph, build_ontology, chunk_text, digest, merge, norm, search
from jevfish.llm import FakeLLM, LLMError

SEED = """Lazybee runs co-living homes in Thomson.

Mark Wee founded Lazybee with Jason Park. Thomson Grove is one of the homes.

Renters in Singapore compare rooms on price and cleanliness."""


def test_chunking_respects_size_and_keeps_everything():
    text = "\n\n".join(f"Paragraph {i} " + "word " * 100 for i in range(20))
    chunks = chunk_text(text, size=1500, overlap=100)
    assert len(chunks) > 1
    assert all(len(c) <= 1500 + 700 for c in chunks)
    for i in range(20):
        assert any(f"Paragraph {i} " in c for c in chunks)
    giant = "x" * 7000
    assert all(len(c) <= 3000 for c in chunk_text(giant, size=3000, overlap=300))


def test_ontology_normalises_names_and_adds_fallbacks():
    fake = FakeLLM({"ontology": lambda m: {
        "entity_types": [{"name": "tenant group", "description": "d", "is_actor": True}] * 2 + [{"name": f"t{i}"} for i in range(15)],
        "relation_types": [{"name": "lives in"}],
    }})
    onto = build_ontology(fake, "q", "text")
    names = [e["name"] for e in onto["entity_types"]]
    assert names[0] == "TenantGroup"
    assert names.count("TenantGroup") == 1
    assert "Person" in names and "Organization" in names
    assert [r["name"] for r in onto["relation_types"]] == ["LIVES_IN", "RELATED_TO"]


def test_merge_dedupes_names_types_and_edges():
    onto = {"entity_types": [{"name": "Person"}, {"name": "Organization"}], "relation_types": [{"name": "FOUNDED"}, {"name": "RELATED_TO"}]}
    ex = [
        {"entities": [{"name": "Mark Wee", "type": "person", "summary": "Founder"}, {"name": "Lazybee", "type": "Organization"}],
         "relations": [{"source": "Mark Wee", "target": "Lazybee", "type": "founded", "fact": "Mark founded Lazybee."}]},
        {"entities": [{"name": "mark wee", "type": "Person", "summary": "Runs ops"}, {"name": "Lazybee", "type": "Spaceship"}],
         "relations": [{"source": "Mark Wee", "target": "Lazybee", "type": "FOUNDED", "fact": "Mark founded Lazybee."},
                       {"source": "Lazybee", "target": "Thomson Grove", "type": "owns", "fact": "Runs it."},
                       {"source": "X", "target": "X", "type": "self", "fact": "loop"}]},
    ]
    g = merge(ex, onto)
    by_name = {n["name"]: n for n in g["nodes"]}
    assert set(by_name) == {"Mark Wee", "Lazybee", "Thomson Grove"}
    assert by_name["Mark Wee"]["mentions"] == 2
    assert by_name["Mark Wee"]["summary"] == "Founder Runs ops"
    assert by_name["Thomson Grove"]["type"] == "Entity"
    assert len(g["edges"]) == 2
    assert {e["type"] for e in g["edges"]} == {"FOUNDED", "RELATED_TO"}
    ids = {n["id"] for n in g["nodes"]}
    assert all(e["source"] in ids and e["target"] in ids for e in g["edges"])
    assert by_name["Lazybee"]["degree"] == 2


def test_build_graph_end_to_end_with_progress():
    steps = []
    g = build_graph(FakeLLM(), "Will renters book?", SEED, progress=lambda p, m: steps.append((p, m)))
    names = {n["name"] for n in g["nodes"]}
    assert {"Lazybee", "Mark Wee", "Thomson Grove"} <= names
    assert g["stats"]["nodes"] == len(g["nodes"]) and g["stats"]["chunks"] == 1
    assert steps[-1][0] == 1.0 and "Graph ready" in steps[-1][1]
    assert [p for p, _ in steps] == sorted(p for p, _ in steps)


def test_build_graph_survives_some_failed_chunks_but_not_all():
    calls = {"n": 0}

    def flaky(messages):
        calls["n"] += 1
        if calls["n"] % 2:
            raise LLMError("boom")
        return {"entities": [{"name": "Alpha Co", "type": "Organization"}], "relations": []}

    seed = "\n\n".join(("Paragraph " + "text " * 700) for _ in range(4))
    g = build_graph(FakeLLM({"extract": flaky}), "q", seed, workers=1)
    assert g["stats"]["failed_chunks"] >= 1 and g["nodes"]

    def always(messages):
        raise LLMError("down")

    with pytest.raises(LLMError, match="every chunk"):
        build_graph(FakeLLM({"extract": always}), "q", seed, workers=1)
    with pytest.raises(ValueError):
        build_graph(FakeLLM(), "q", "   ")


def test_search_and_digest():
    g = build_graph(FakeLLM(), "q", SEED)
    hits = search(g, "Thomson Grove home")
    assert hits and hits[0]["kind"] in {"node", "edge"}
    assert "Thomson" in str(hits[0]["item"])
    assert search(g, "zzzz") == []
    text = digest(g)
    assert text.startswith("Entities:") and "Facts:" in text


def test_norm():
    assert norm("  Mark   WEE! ") == "mark wee"
