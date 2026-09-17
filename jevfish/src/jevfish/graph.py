"""Stage 1: seed documents to a knowledge graph.

MiroFish hands this to Zep Cloud. Here the LLM designs a small ontology for the
prediction question, extracts entities and relations chunk by chunk, and code merges them
into a local graph with keyword search.
"""

from __future__ import annotations

import math
import re
from collections import Counter, defaultdict
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from .llm import LLM, LLMError

MAX_TYPES = 10
Progress = Callable[[float, str], None]

ONTOLOGY_SYSTEM = """You design the schema of a knowledge graph that will seed a social simulation used to answer a prediction question.
Pick the entity types that matter for who would react and why: people, organisations, groups of the public, places, products, policies, events.
Pick relation types that connect them in ways that affect opinions or behaviour.
Reply with JSON only:
{"entity_types": [{"name": "PascalCase", "description": "one sentence", "is_actor": true}],
 "relation_types": [{"name": "UPPER_SNAKE_CASE", "description": "one sentence"}]}
Use at most 10 of each. is_actor is true when members of that type could post or react online."""

EXTRACT_SYSTEM = """You extract a knowledge graph from a document chunk. Use only the given entity and relation types.
Only include entities and facts stated or clearly implied by the chunk. Use each entity's full proper name.
Reply with JSON only:
{"entities": [{"name": "...", "type": "one of the entity types", "summary": "who or what it is and why it matters here, max 2 sentences"}],
 "relations": [{"source": "entity name", "target": "entity name", "type": "one of the relation types", "fact": "the fact in one sentence"}]}"""


def pascal(name: str) -> str:
    parts = re.split(r"[^0-9A-Za-z]+", name.strip())
    return "".join(p[:1].upper() + p[1:] for p in parts if p) or "Entity"


def upper_snake(name: str) -> str:
    return re.sub(r"[^0-9A-Z]+", "_", name.strip().upper()).strip("_") or "RELATED_TO"


def norm(name: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s&]", "", name.lower())).strip()


def tokens(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]{2,}", text.lower())


def chunk_text(text: str, size: int = 3000, overlap: int = 300) -> list[str]:
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    chunks: list[str] = []
    current = ""
    for p in paragraphs:
        while len(p) > size:  # hard-split giant paragraphs
            head, p = p[:size], p[size - overlap :]
            if current:
                chunks.append(current)
                current = ""
            chunks.append(head)
        if len(current) + len(p) + 2 > size and current:
            chunks.append(current)
            current = current[-overlap:] + "\n\n" + p if overlap else p
        else:
            current = f"{current}\n\n{p}" if current else p
    if current.strip():
        chunks.append(current)
    return chunks


def build_ontology(llm: LLM, requirement: str, sample: str) -> dict:
    data = llm.json(
        "ontology",
        [
            {"role": "system", "content": ONTOLOGY_SYSTEM},
            {"role": "user", "content": f"Prediction question:\n{requirement}\n\nDocument excerpt:\n{sample[:6000]}"},
        ],
    )
    entities, seen = [], set()
    for e in (data.get("entity_types") or [])[:MAX_TYPES]:
        name = pascal(str(e.get("name", "")))
        if name not in seen:
            seen.add(name)
            entities.append({"name": name, "description": str(e.get("description", "")), "is_actor": bool(e.get("is_actor", False))})
    for fallback, actor in (("Person", True), ("Organization", True)):
        if fallback not in seen:
            entities.append({"name": fallback, "description": f"Any {fallback.lower()} mentioned", "is_actor": actor})
            seen.add(fallback)
    relations, seen_r = [], set()
    for r in (data.get("relation_types") or [])[:MAX_TYPES]:
        name = upper_snake(str(r.get("name", "")))
        if name not in seen_r:
            seen_r.add(name)
            relations.append({"name": name, "description": str(r.get("description", ""))})
    if "RELATED_TO" not in seen_r:
        relations.append({"name": "RELATED_TO", "description": "Any other stated connection"})
    return {"entity_types": entities, "relation_types": relations}


def extract_chunk(llm: LLM, ontology: dict, requirement: str, chunk: str) -> dict:
    types = ", ".join(e["name"] for e in ontology["entity_types"])
    rels = ", ".join(r["name"] for r in ontology["relation_types"])
    data = llm.json(
        "extract",
        [
            {"role": "system", "content": EXTRACT_SYSTEM},
            {
                "role": "user",
                "content": f"Entity types: {types}\nRelation types: {rels}\nPrediction question: {requirement}\n\nChunk:\n{chunk}",
            },
        ],
    )
    return {"entities": data.get("entities") or [], "relations": data.get("relations") or []}


def merge(extractions: list[dict], ontology: dict) -> dict:
    valid_types = {e["name"] for e in ontology["entity_types"]}
    valid_rels = {r["name"] for r in ontology["relation_types"]}
    names: dict[str, Counter] = defaultdict(Counter)
    types: dict[str, Counter] = defaultdict(Counter)
    summaries: dict[str, list[str]] = defaultdict(list)
    for ex in extractions:
        for e in ex["entities"]:
            name = str(e.get("name", "")).strip()
            key = norm(name)
            if not key:
                continue
            names[key][name] += 1
            t = pascal(str(e.get("type", "")))
            types[key][t if t in valid_types else "Entity"] += 1
            s = str(e.get("summary", "")).strip()
            if s and s not in summaries[key]:
                summaries[key].append(s)

    edges, seen_edges = [], set()
    for ex in extractions:
        for r in ex["relations"]:
            src, dst = norm(str(r.get("source", ""))), norm(str(r.get("target", "")))
            if not src or not dst or src == dst:
                continue
            for key, raw in ((src, r.get("source")), (dst, r.get("target"))):
                if key not in names:
                    names[key][str(raw).strip()] += 1
                    types[key]["Entity"] += 1
            rtype = upper_snake(str(r.get("type", "")))
            rtype = rtype if rtype in valid_rels else "RELATED_TO"
            fact = str(r.get("fact", "")).strip()
            sig = (src, dst, rtype, norm(fact))
            if sig in seen_edges:
                continue
            seen_edges.add(sig)
            edges.append({"source": src, "target": dst, "type": rtype, "fact": fact})

    ids = {key: f"n{i:04d}" for i, key in enumerate(sorted(names))}
    nodes = []
    for key in sorted(names):
        nodes.append(
            {
                "id": ids[key],
                "name": names[key].most_common(1)[0][0],
                "type": types[key].most_common(1)[0][0],
                "summary": " ".join(summaries[key][:3])[:700],
                "mentions": sum(names[key].values()),
            }
        )
    for i, e in enumerate(edges):
        e["id"] = f"e{i:05d}"
        e["source"], e["target"] = ids[e["source"]], ids[e["target"]]
    degree = Counter([e["source"] for e in edges] + [e["target"] for e in edges])
    for n in nodes:
        n["degree"] = degree[n["id"]]
    return {"ontology": ontology, "nodes": nodes, "edges": edges}


def build_graph(llm: LLM, requirement: str, seed_text: str, progress: Progress = lambda p, m: None, workers: int = 4) -> dict:
    if not seed_text.strip():
        raise ValueError("the project has no seed text yet")
    progress(0.02, "Designing the ontology")
    ontology = build_ontology(llm, requirement, seed_text)
    chunks = chunk_text(seed_text)
    progress(0.1, f"Extracting entities from {len(chunks)} chunk(s)")
    results: list[dict | None] = [None] * len(chunks)
    errors: list[str] = []
    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        futures = {pool.submit(extract_chunk, llm, ontology, requirement, c): i for i, c in enumerate(chunks)}
        for done, fut in enumerate(as_completed(futures), start=1):
            i = futures[fut]
            try:
                results[i] = fut.result()
            except LLMError as e:
                errors.append(f"chunk {i + 1}: {e}")
            progress(0.1 + 0.8 * done / len(chunks), f"Extracted {done}/{len(chunks)} chunks")
    extracted = [r for r in results if r]
    if not extracted:
        raise LLMError("entity extraction failed for every chunk: " + "; ".join(errors[:3]))
    graph = merge(extracted, ontology)
    graph["stats"] = {
        "chunks": len(chunks),
        "failed_chunks": len(errors),
        "nodes": len(graph["nodes"]),
        "edges": len(graph["edges"]),
        "types": dict(Counter(n["type"] for n in graph["nodes"])),
    }
    graph["errors"] = errors
    progress(1.0, f"Graph ready: {len(graph['nodes'])} entities, {len(graph['edges'])} relations")
    return graph


def search(graph: dict, query: str, limit: int = 10) -> list[dict[str, Any]]:
    """Rank nodes and edges by IDF-weighted token overlap with the query."""
    by_id = {n["id"]: n for n in graph["nodes"]}
    docs: list[tuple[str, dict, list[str]]] = []
    for n in graph["nodes"]:
        docs.append(("node", n, tokens(f"{n['name']} {n['name']} {n['type']} {n['summary']}")))
    for e in graph["edges"]:
        text = f"{by_id[e['source']]['name']} {e['type']} {by_id[e['target']]['name']} {e['fact']}"
        docs.append(("edge", e, tokens(text)))
    df = Counter(t for _, _, toks in docs for t in set(toks))
    total = len(docs) or 1
    q = set(tokens(query))
    scored = []
    for kind, item, toks in docs:
        counts = Counter(toks)
        score = sum((1 + math.log(counts[t])) * math.log(1 + total / df[t]) for t in q if t in counts)
        if score > 0:
            scored.append({"kind": kind, "score": round(score, 3), "item": item})
    scored.sort(key=lambda s: -s["score"])
    return scored[:limit]


def digest(graph: dict, max_nodes: int = 40, max_edges: int = 60) -> str:
    """Compact text version of the most connected part of the graph, for prompts."""
    by_id = {n["id"]: n for n in graph["nodes"]}
    nodes = sorted(graph["nodes"], key=lambda n: (-(n.get("degree", 0) + n.get("mentions", 0)), n["name"]))[:max_nodes]
    lines = ["Entities:"]
    lines += [f"- {n['name']} ({n['type']}): {n['summary']}" for n in nodes]
    keep = {n["id"] for n in nodes}
    facts = [e for e in graph["edges"] if e["source"] in keep or e["target"] in keep][:max_edges]
    lines.append("Facts:")
    lines += [f"- {by_id[e['source']]['name']} {e['type']} {by_id[e['target']]['name']}: {e['fact']}" for e in facts]
    return "\n".join(lines)
