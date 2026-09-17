"""Canned LLM output for tests and key-free demos, keyed by task name.

Each handler reads what it needs from the prompt so the whole pipeline produces
consistent, deterministic data without a model.
"""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any

STOP = {"The", "A", "An", "In", "On", "At", "This", "That", "It", "We", "They", "He", "She", "If", "But", "And", "Source", "Prediction", "Chunk"}


def _user(messages) -> str:
    return next((m["content"] for m in reversed(messages) if m["role"] == "user"), "")


def _pick(seed: str, options: list, n: int = 1):
    h = int(hashlib.sha256(seed.encode()).hexdigest(), 16)
    return [options[(h >> (i * 7)) % len(options)] for i in range(n)]


def _names(text: str) -> list[str]:
    found = re.findall(r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b", text)
    out: list[str] = []
    for f in found:
        if f.split()[0] not in STOP and f not in out:
            out.append(f)
    return out


def ontology(messages) -> dict:
    return {
        "entity_types": [
            {"name": "Person", "description": "An individual", "is_actor": True},
            {"name": "Organization", "description": "A company or body", "is_actor": True},
            {"name": "Place", "description": "A location", "is_actor": False},
        ],
        "relation_types": [
            {"name": "WORKS_WITH", "description": "Works with"},
            {"name": "LOCATED_IN", "description": "Located in"},
        ],
    }


def extract(messages) -> dict:
    chunk = _user(messages).split("Chunk:", 1)[-1]
    names = _names(chunk)[:8]
    types = ["Person", "Organization", "Place"]
    entities = [{"name": n, "type": _pick(n, types)[0], "summary": f"{n} appears in the seed document."} for n in names]
    relations = [
        {"source": a, "target": b, "type": "WORKS_WITH", "fact": f"{a} is connected to {b}."}
        for a, b in zip(names, names[1:])
    ]
    return {"entities": entities, "relations": relations}


def frame(messages) -> dict:
    text = _user(messages)
    q = re.search(r"Prediction question:\s*(.+)", text)
    question = q.group(1).strip() if q else "Will people support the proposal?"
    return {
        "question": question,
        "subject": {"proposal": question, "source": "seed documents"},
        "outcome": {
            "instructions": "Would the person described in `agent` support the proposal in `subject`?",
            "criteria": {"true": "They would support it", "false": "They would not support it"},
        },
        "stance": {
            "instructions": "After reading `feed`, how does the person described in `agent` feel about `subject`?",
            "levels": [
                "Strongly against it",
                "Leaning against it",
                "Undecided or indifferent",
                "Leaning in favour",
                "Strongly in favour",
            ],
        },
        "talking_points": [
            {"id": f"tp{i:02d}", "text": t, "side": s}
            for i, (t, s) in enumerate(
                [
                    ("It costs too much for what it gives", "con"),
                    ("It fixes a problem people have complained about for years", "pro"),
                    ("The people affected were not consulted", "con"),
                    ("Early results elsewhere look promising", "pro"),
                    ("Nobody has explained how it will be paid for", "con"),
                    ("It is a fair compromise", "pro"),
                    ("Wait and see before judging it", "neutral"),
                    ("It helps newcomers most", "pro"),
                ]
            )
        ],
        "opening_posts": [
            {"author": m, "text": f"{m} here. Let us talk about: {question}", "talking_point": "tp01"}
            for m in re.findall(r"^- (.+?) \((?:Person|Organization)\):", text, flags=re.M)[:1]
        ],
        "variants": [],
    }


def crowd_plan(messages) -> dict:
    return {
        "stakeholders": [],
        "segments": [
            {"name": "young professionals", "share": 0.4, "description": "Working adults in their twenties and thirties",
             "attributes": {"income": {"middle": 0.7, "high": 0.3}, "priority": {"price": 0.5, "convenience": 0.5}}},
            {"name": "students", "share": 0.3, "description": "University students on tight budgets",
             "attributes": {"income": {"low": 1.0}, "priority": {"price": 0.8, "community": 0.2}}},
            {"name": "families", "share": 0.3, "description": "Parents with children at home",
             "attributes": {"income": {"middle": 0.6, "high": 0.4}, "priority": {"safety": 0.6, "price": 0.4}}},
        ],
    }


def personas(messages) -> dict:
    text = _user(messages)
    names = re.findall(r"^- id=(\S+) name=(.+?) type=", text, flags=re.M)
    out = []
    for i, (eid, name) in enumerate(names):
        out.append(
            {
                "entity_id": eid,
                "include": True,
                "username": re.sub(r"\W+", "_", name.lower()).strip("_")[:20] or f"user{i}",
                "bio": f"{name}, as described in the seed documents.",
                "persona": f"{name} speaks for their own interests and reacts to the proposal accordingly.",
                "stance_hint": _pick(name, ["against", "neutral", "for"])[0],
                "influence": round(0.3 + (i % 5) / 10, 2),
                "activity": 0.7,
            }
        )
    return {"personas": out}


def post(messages) -> str:
    text = _user(messages)
    point = re.search(r"Point to make:\s*(.+)", text)
    return (point.group(1).strip() if point else "Here is what I think.")[:280]


def report(messages) -> str:
    data = _user(messages)
    try:
        bundle = json.loads(data.split("DATA:", 1)[1])
        head = bundle.get("headline", {})
    except (IndexError, ValueError):
        head = {}
    return (
        "## Prediction\n\n"
        f"The simulated crowd leans towards: {json.dumps(head)}.\n\n"
        "## Why\n\nThis is a fake-LLM report used for testing.\n"
    )


def chat(messages) -> str:
    return "Honestly, it depends on the price and whether it actually works for people like me."


def poll_question(messages) -> dict:
    return {"instructions": "Would the person described in `agent` agree?", "criteria": {"true": "Yes", "false": "No"}}


HANDLERS: dict[str, Any] = {
    "ontology": ontology,
    "extract": extract,
    "frame": frame,
    "crowd_plan": crowd_plan,
    "personas": personas,
    "post": post,
    "report": report,
    "chat": chat,
    "poll_question": poll_question,
}
