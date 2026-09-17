"""Stage 2b: the crowd.

Stakeholders come from actor entities in the graph (the LLM writes their persona and
decides whether each would take part online). The public is sampled in code from
segments the LLM proposes, so a crowd of hundreds costs one LLM call. A follow graph
gives influential people more followers.
"""

from __future__ import annotations

import random
import re
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor

from .graph import digest
from .llm import LLM, LLMError

Progress = Callable[[float, str], None]
BATCH = 12

PLAN_SYSTEM = """You design the simulated public for a prediction simulation.
Describe 2 to 6 segments of ordinary people who would react to the question, with their share of the crowd and 2 to 4 categorical attributes each.
Reply with JSON only:
{"segments": [{"name": "short plural noun phrase", "share": 0.3, "description": "one sentence",
  "activity": 0.5, "attributes": {"attribute_name": {"value": weight, "value": weight}}}]}
Shares add up to about 1. activity is how often they engage online, 0 to 1. Weights are relative."""

PERSONA_SYSTEM = """You write personas for real actors from a knowledge graph who might take part in an online discussion.
For each entity decide whether it would plausibly post or react online about the question (include true or false).
Reply with JSON only:
{"personas": [{"entity_id": "the given id", "include": true, "username": "short_handle", "bio": "one sentence public bio",
  "persona": "2 to 4 sentences: who they are, what they care about, how they talk", "stance_hint": "for|against|neutral|mixed",
  "influence": 0.0, "activity": 0.0}]}
influence and activity are 0 to 1. Base stance_hint on the documents only; use neutral when unknown."""


def handle(text: str, fallback: str) -> str:
    h = re.sub(r"[^a-z0-9_]+", "_", text.lower()).strip("_")[:24]
    return h or fallback


def _clip(x, lo=0.0, hi=1.0, default=0.5) -> float:
    try:
        return max(lo, min(hi, float(x)))
    except (TypeError, ValueError):
        return default


def plan_public(llm: LLM, requirement: str, graph: dict) -> list[dict]:
    data = llm.json(
        "crowd_plan",
        [
            {"role": "system", "content": PLAN_SYSTEM},
            {"role": "user", "content": f"Prediction question: {requirement}\n\nKnowledge graph:\n{digest(graph, 25, 30)}"},
        ],
    )
    segments = []
    for s in data.get("segments") or []:
        attrs = {}
        for name, dist in (s.get("attributes") or {}).items():
            if isinstance(dist, dict):
                weights = {str(k): _clip(v, 0, 1e9, 0) for k, v in dist.items()}
                if sum(weights.values()) > 0:
                    attrs[str(name)] = weights
        share = _clip(s.get("share"), 0, 1, 0)
        if s.get("name") and share > 0:
            segments.append({
                "name": str(s["name"]),
                "share": share,
                "description": str(s.get("description", "")),
                "activity": _clip(s.get("activity")),
                "attributes": attrs,
            })
    if not segments:
        raise LLMError("the crowd plan had no usable segments")
    return segments


def actor_entities(graph: dict, limit: int) -> list[dict]:
    actor_types = {e["name"] for e in graph["ontology"]["entity_types"] if e.get("is_actor")}
    actors = [n for n in graph["nodes"] if n["type"] in actor_types]
    actors.sort(key=lambda n: (-(n.get("degree", 0) + n.get("mentions", 0)), n["name"]))
    return actors[:limit]


def write_personas(llm: LLM, requirement: str, graph: dict, entities: list[dict], progress: Progress, workers: int) -> list[dict]:
    by_id = {n["id"]: n for n in graph["nodes"]}
    batches = [entities[i : i + BATCH] for i in range(0, len(entities), BATCH)]

    def one(batch):
        facts = []
        for e in graph["edges"]:
            if e["source"] in {b["id"] for b in batch} or e["target"] in {b["id"] for b in batch}:
                facts.append(f"- {by_id[e['source']]['name']} {e['type']} {by_id[e['target']]['name']}: {e['fact']}")
        listing = "\n".join(f"- id={b['id']} name={b['name']} type={b['type']} summary={b['summary']}" for b in batch)
        data = llm.json(
            "personas",
            [
                {"role": "system", "content": PERSONA_SYSTEM},
                {"role": "user", "content": f"Question: {requirement}\n\nEntities:\n{listing}\n\nRelated facts:\n" + "\n".join(facts[:40])},
            ],
        )
        return data.get("personas") or []

    out: list[dict] = []
    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        for i, personas in enumerate(pool.map(one, batches), start=1):
            out.extend(personas)
            progress(0.35 + 0.35 * i / max(1, len(batches)), f"Wrote personas for batch {i}/{len(batches)}")
    return out


def sample_public(segments: list[dict], size: int, rng: random.Random, start_id: int) -> list[dict]:
    total = sum(s["share"] for s in segments)
    people = []
    for i in range(size):
        seg = rng.choices(segments, weights=[s["share"] / total for s in segments])[0]
        attrs = {name: rng.choices(list(dist), weights=list(dist.values()))[0] for name, dist in seg["attributes"].items()}
        detail = "; ".join(f"{k.replace('_', ' ')}: {v}" for k, v in attrs.items())
        people.append({
            "agent_id": start_id + i,
            "kind": "public",
            "name": f"{seg['name']} #{i + 1}",
            "username": f"{handle(seg['name'], 'public')}_{i + 1}",
            "bio": seg["description"],
            "persona": f"One of the {seg['name']}. {seg['description']} {detail}.".strip(),
            "segment": seg["name"],
            "attributes": attrs,
            "entity_id": None,
            "stance_hint": "neutral",
            "influence": 0.1,
            "activity": seg["activity"],
        })
    return people


def build_follows(agents: list[dict], graph: dict, per_agent: int, rng: random.Random) -> None:
    ids = [a["agent_id"] for a in agents]
    weight = {a["agent_id"]: 1.0 + 9.0 * a["influence"] for a in agents}
    by_entity = {a["entity_id"]: a["agent_id"] for a in agents if a["entity_id"]}
    linked: dict[int, set[int]] = {i: set() for i in ids}
    for e in graph["edges"]:
        s, t = by_entity.get(e["source"]), by_entity.get(e["target"])
        if s is not None and t is not None and s != t:
            linked[s].add(t)
            linked[t].add(s)
    k = min(per_agent, len(ids) - 1)
    for a in agents:
        me = a["agent_id"]
        keyed = sorted((rng.random() ** (1.0 / weight[o]), o) for o in ids if o != me)
        follows = set(linked[me]) | {o for _, o in keyed[-k:]}
        a["follows"] = sorted(follows)


def build_crowd(
    llm: LLM,
    requirement: str,
    graph: dict,
    *,
    public_size: int = 60,
    max_stakeholders: int = 20,
    follows_per_agent: int = 6,
    seed: int = 0,
    workers: int = 4,
    progress: Progress = lambda p, m: None,
) -> dict:
    rng = random.Random(f"crowd:{seed}")
    progress(0.3, "Planning the public")
    segments = plan_public(llm, requirement, graph)
    entities = actor_entities(graph, max_stakeholders * 2)
    progress(0.35, f"Writing personas for {len(entities)} candidate stakeholders")
    personas = write_personas(llm, requirement, graph, entities, progress, workers) if entities else []
    by_id = {n["id"]: n for n in graph["nodes"]}
    stakeholders, used = [], set()
    for p in personas:
        eid = p.get("entity_id")
        if eid not in by_id or eid in used or not p.get("include", True):
            continue
        used.add(eid)
        node = by_id[eid]
        stance = str(p.get("stance_hint", "neutral")).lower()
        stakeholders.append({
            "agent_id": len(stakeholders),
            "kind": "stakeholder",
            "name": node["name"],
            "username": handle(str(p.get("username") or node["name"]), f"actor_{len(stakeholders)}"),
            "bio": str(p.get("bio") or node["summary"])[:300],
            "persona": str(p.get("persona") or node["summary"])[:1200],
            "segment": node["type"],
            "attributes": {},
            "entity_id": eid,
            "stance_hint": stance if stance in {"for", "against", "neutral", "mixed"} else "neutral",
            "influence": _clip(p.get("influence")),
            "activity": _clip(p.get("activity"), default=0.6),
        })
        if len(stakeholders) >= max_stakeholders:
            break
    public = sample_public(segments, public_size, rng, start_id=len(stakeholders))
    agents = stakeholders + public
    if len(agents) < 2:
        raise LLMError("the crowd needs at least 2 people")
    build_follows(agents, graph, follows_per_agent, rng)
    progress(0.95, f"Crowd ready: {len(stakeholders)} stakeholders and {len(public)} members of the public")
    return {"agents": agents, "segments": segments, "stats": {"stakeholders": len(stakeholders), "public": len(public)}}
