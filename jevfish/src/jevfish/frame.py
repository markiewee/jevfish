"""Stage 2a: the prediction frame.

The frame turns the prediction requirement into things Jev can answer: an outcome
question (yes/no), a stance scale, and a pool of talking points people can post. It also
names the opening posts that start the discussion and any variants to compare.
"""

from __future__ import annotations

import re
from typing import Any

from .graph import digest
from .llm import LLM

RESERVED = "none"
MAX_POINTS = 254

FRAME_SYSTEM = """You set up a prediction simulation. A crowd of simulated people will read a social feed and react.
A decision model judges each person. It can only choose among options you define and never writes text, so everything it needs must be spelled out here.
Reply with JSON only:
{"question": "the prediction question in plain words",
 "subject": {"short fact name": "value", "...": "3 to 10 facts about the thing people react to, taken from the documents"},
 "outcome": {"instructions": "a yes/no question about the person described in `agent` and `subject` whose yes-rate answers the prediction",
             "criteria": {"true": "what yes means", "false": "what no means"}},
 "stance": {"instructions": "After reading `feed`, how does the person described in `agent` feel about `subject`?",
            "levels": ["5 levels from most negative to most positive, each a concrete situation, not a degree word"]},
 "talking_points": [{"id": "snake_case_id", "text": "one sentence a person might post", "side": "pro|con|neutral"}],
 "opening_posts": [{"author": "exact entity name from the graph", "text": "a post of at most 280 characters", "talking_point": "id"}],
 "variants": [{"id": "A", "label": "short name", "subject": {"fact name": "value that differs"}}]}
Rules:
- 12 to 30 talking points, balanced between pro and con, grounded in the documents.
- 1 to 3 opening posts written by actors that appear in the graph.
- variants only when the question compares options; otherwise an empty list. The first variant is the status quo with an empty subject override.
- In instructions, refer to the inputs only as `agent`, `subject` and `feed`, with backticks.
- Never invent a number that is not in the documents."""


class FrameError(ValueError):
    pass


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")[:40] or "point"


def normalize_frame(data: dict[str, Any], requirement: str = "") -> dict:
    if not isinstance(data, dict):
        raise FrameError("frame must be an object")
    outcome = data.get("outcome") or {}
    if not str(outcome.get("instructions", "")).strip():
        raise FrameError("frame.outcome.instructions is required")
    stance = data.get("stance") or {}
    levels = [lv for lv in (stance.get("levels") or []) if str(lv).strip()]
    if not 2 <= len(levels) <= 10:
        raise FrameError("frame.stance needs 2 to 10 levels")
    points, seen = [], set()
    for p in data.get("talking_points") or []:
        text = str(p.get("text", "")).strip()
        if not text:
            continue
        pid = slug(str(p.get("id") or text))
        if pid == RESERVED:
            pid = "point_none"
        base, n = pid, 2
        while pid in seen:
            pid = f"{base}_{n}"
            n += 1
        seen.add(pid)
        side = str(p.get("side", "neutral")).lower()
        points.append({"id": pid, "text": text, "side": side if side in {"pro", "con", "neutral"} else "neutral"})
    if not points:
        raise FrameError("frame needs at least one talking point")
    points = points[:MAX_POINTS]
    subject = data.get("subject") if isinstance(data.get("subject"), dict) else {}
    variants, vids = [], set()
    for v in data.get("variants") or []:
        vid = re.sub(r"[^A-Za-z0-9_-]", "", str(v.get("id", "")))[:12] or f"V{len(variants) + 1}"
        if vid in vids:
            continue
        vids.add(vid)
        overrides = v.get("subject") if isinstance(v.get("subject"), dict) else {}
        variants.append({"id": vid, "label": str(v.get("label") or vid), "subject": overrides})
    if not variants:
        variants = [{"id": "base", "label": "As described", "subject": {}}]
    openings = []
    for o in data.get("opening_posts") or []:
        text = str(o.get("text", "")).strip()[:280]
        if text:
            tp = slug(str(o.get("talking_point", ""))) if o.get("talking_point") else None
            openings.append({"author": str(o.get("author", "")).strip(), "text": text, "talking_point": tp if tp in seen else None})
    return {
        "question": str(data.get("question") or requirement).strip(),
        "subject": subject,
        "outcome": {"instructions": outcome["instructions"], "criteria": outcome.get("criteria") or None},
        "stance": {
            "instructions": stance.get("instructions")
            or "After reading `feed`, how does the person described in `agent` feel about `subject`?",
            "levels": levels,
        },
        "talking_points": points,
        "opening_posts": openings[:3],
        "variants": variants,
    }


def variant_subject(frame: dict, variant_id: str) -> dict:
    for v in frame["variants"]:
        if v["id"] == variant_id:
            return {**frame["subject"], **v["subject"]}
    raise FrameError(f"no variant '{variant_id}'")


def build_frame(llm: LLM, requirement: str, graph: dict) -> dict:
    data = llm.json(
        "frame",
        [
            {"role": "system", "content": FRAME_SYSTEM},
            {"role": "user", "content": f"Prediction question: {requirement}\n\nKnowledge graph:\n{digest(graph)}"},
        ],
    )
    return normalize_frame(data, requirement)
