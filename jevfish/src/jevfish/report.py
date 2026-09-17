"""Stage 4: the report.

Numbers come from Jev polls and the platform. The LLM then writes the narrative from a
data bundle, and may only use numbers that are in it.
"""

from __future__ import annotations

import json
import re

from .graph import digest
from .llm import LLM

SYSTEM = """You write the prediction report for a simulation in which a synthetic crowd reacted to a question.
The numbers were produced by a calibrated decision model polling every simulated person. Use only numbers from DATA; do not invent any.
Write clear markdown for a busy founder, with these sections:
## Prediction
One paragraph: the answer to the question, with the expected share saying yes and its 90% range, and how it moved from the first poll to the last.
## Why
The main reasons, citing the talking points that spread and quoting one or two top posts.
## Who moves
Which groups are most and least likely to say yes, with their numbers.
## Options compared
Only if there is more than one variant: which does better, and whether the difference is outside the 90% range.
## Risks and unknowns
What could make this wrong. Always say that the crowd is synthetic and the ranges only cover sampling noise.
## Recommendation
One or two concrete next steps.
No em dashes. No emojis. Keep it under 700 words."""


def bundle(summary: dict, graph: dict | None, crowd: dict) -> dict:
    variants = []
    for v in summary["variants"]:
        final, base = v.get("final") or {}, v.get("baseline") or {}
        variants.append({
            "id": v["id"],
            "label": v["label"],
            "subject": v["subject"],
            "final_poll": {k: round(final.get(k, 0), 3) for k in ("n", "mean_outcome", "expected_yes", "low", "high", "likely_yes", "stance_mean")} if final else None,
            "first_poll": {k: round(base.get(k, 0), 3) for k in ("mean_outcome", "expected_yes", "stance_mean")} if base else None,
            "poll_trajectory": [{"after_round": p["round"], "mean_outcome": round(p["mean_outcome"], 3)} for p in v["polls"]],
            "by_group": [{"group": r["value"], "n": r["n"], "mean_outcome": round(r["mean_outcome"], 3)} for r in v["segments"].get("group", [])][:10],
            "by_kind": [{"kind": r["value"], "n": r["n"], "mean_outcome": round(r["mean_outcome"], 3)} for r in v["segments"].get("kind", [])],
            "talking_points": [p for p in v["points"] if p["total"]][:8],
            "top_posts": [{"author": p["author"], "content": p["content"][:280], "engagement": p["engagement"]} for p in v["top_posts"][:5]],
            "activity": v["action_counts"],
        })
    return {
        "question": summary["question"],
        "outcome_question": summary["outcome_instructions"],
        "stance_levels": summary["stance_levels"],
        "crowd": summary["crowd"],
        "rounds": summary["config"]["rounds"],
        "platform": summary["config"]["platform"],
        "headline": {v["id"]: v["final_poll"] for v in variants},
        "variants": variants,
        "comparisons": [{k: (round(x, 3) if isinstance(x, float) else x) for k, x in c.items()} for c in summary["comparisons"]],
        "partial_run": summary.get("partial"),
        "background": digest(graph, 15, 20) if graph else "",
    }


def write_report(llm: LLM, summary: dict, graph: dict | None, crowd: dict) -> dict:
    data = bundle(summary, graph, crowd)
    text = llm.chat(
        "report",
        [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": "DATA:" + json.dumps(data, ensure_ascii=False)},
        ],
        temperature=0.4,
    )
    text = re.sub(r"(?m)^(\s*>?\s*)[\u2014\u2013]\s*", r"\1", text)  # attribution dashes at line start
    text = re.sub(r"\s*[\u2014\u2013]\s*", ", ", text)
    return {"markdown": text, "data": data}
