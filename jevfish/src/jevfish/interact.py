"""Stage 5: talk to the simulation.

Chat: the LLM answers as one simulated person, using their persona, their final stance and
what they did during the run.
Ask the crowd: any yes/no question becomes a Jev poll of every person, reusing their final
state, so the answer is a calibrated count rather than a guess.
"""

from __future__ import annotations

import asyncio

from . import metrics
from .frame import variant_subject
from .judge import NoulQ, build_judge
from .llm import LLM
from .policy import Mind, agent_view, stance_label

CHAT_SYSTEM = """You are role-playing a simulated person in a prediction simulation. Stay in character.
Answer in the first person, as they would talk, in 1 to 4 sentences. Base your answer on their persona,
their current view and what they did in the simulation. If asked something they would not know, say so in character.
No em dashes, no emojis."""


def agent_history(actions: list[dict], agent_id: int, variant: str, limit: int = 12) -> list[str]:
    lines = []
    for a in actions:
        if a["agent_id"] != agent_id or a["variant"] != variant or not a.get("ok") or a["action"] == "do_nothing":
            continue
        what = a.get("content") or a.get("target_excerpt") or ""
        target = f" ({a['target_author']})" if a.get("target_author") else ""
        lines.append(f"round {a['round']}: {a['action']}{target}: {what[:160]}")
    return lines[-limit:]


def last_poll(polls: list[dict], agent_id: int, variant: str) -> dict | None:
    mine = [p for p in polls if p["agent_id"] == agent_id and p["variant"] == variant]
    return mine[-1] if mine else None


def chat(llm: LLM, frame: dict, agent: dict, variant: str, actions: list[dict], polls: list[dict], history: list[dict], message: str) -> str:
    poll = last_poll(polls, agent["agent_id"], variant)
    stance = stance_label(frame["stance"]["levels"], poll["stance"] if poll else None)
    facts = "; ".join(f"{k}: {v}" for k, v in variant_subject(frame, variant).items())
    lines = [
        f"You are {agent['name']}. {agent.get('bio', '')}",
        f"Persona: {agent.get('persona', '')}",
        f"Topic: {frame['question']}",
        f"Facts you were shown: {facts}",
        f"Your current view: {stance}",
    ]
    if poll:
        lines.append(f"Your likelihood of the predicted behaviour, from the simulation: {poll['outcome_p']:.0%}")
    hist = agent_history(actions, agent["agent_id"], variant)
    if hist:
        lines.append("What you did in the simulation:\n" + "\n".join(hist))
    messages = [{"role": "system", "content": CHAT_SYSTEM + "\n\n" + "\n".join(lines)}]
    for turn in history[-10:]:
        if turn.get("role") in ("user", "assistant") and turn.get("content"):
            messages.append({"role": turn["role"], "content": str(turn["content"])[:2000]})
    messages.append({"role": "user", "content": message})
    return llm.chat("chat", messages, temperature=0.8, max_tokens=300)


def ask_crowd(settings, cache_path, frame: dict, agents: list[dict], variant: str, polls: list[dict], actions: list[dict], question: str, criteria: dict | None = None) -> dict:
    """Poll every person with a yes/no question about `agent` and `subject`."""
    instructions = question.strip()
    if "`agent`" not in instructions:
        instructions = f"For the person described in `agent`, considering `subject`: {instructions}"
    subject = variant_subject(frame, variant)
    levels = frame["stance"]["levels"]

    async def go():
        judge, meter = build_judge(settings, cache_path, max_requests=len(agents) + 5)
        try:
            gate = asyncio.Semaphore(16)

            async def one(agent):
                mind = Mind(agent)
                poll = last_poll(polls, agent["agent_id"], variant)
                mind.stance = poll["stance"] if poll else None
                mind.recent = agent_history(actions, agent["agent_id"], variant, limit=3)
                state = {"topic": frame["question"], "subject": subject, "agent": agent_view(mind, levels)}
                async with gate:
                    v = await judge.ask(state, {"answer": NoulQ(instructions, criteria)})
                return {"agent_id": agent["agent_id"], "outcome_p": v.answers["answer"].p, "stance": mind.stance or 0.0}

            records = await asyncio.gather(*(one(a) for a in agents))
            return records, meter.requests, judge.hits
        finally:
            await judge.aclose()

    records, requests, hits = asyncio.run(go())
    summary = metrics.summarize_poll(records, len(levels))
    by_id = {a["agent_id"]: a for a in agents}
    ranked = sorted(records, key=lambda r: -r["outcome_p"])
    return {
        "question": question,
        "instructions": instructions,
        "variant": variant,
        "summary": {k: summary[k] for k in ("n", "mean_outcome", "expected_yes", "low", "high", "likely_yes")},
        "segments": metrics.segment_breakdown(records, agents),
        "most_yes": [{"name": by_id[r["agent_id"]]["name"], "p": r["outcome_p"]} for r in ranked[:5]],
        "most_no": [{"name": by_id[r["agent_id"]]["name"], "p": r["outcome_p"]} for r in ranked[-5:][::-1]],
        "requests": requests,
        "cache_hits": hits,
    }
