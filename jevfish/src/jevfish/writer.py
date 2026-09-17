"""Words for the posts and comments Jev decided a person makes.

Jev picks the action and the talking point; the LLM only phrases it in the person's voice.
If the LLM fails, the talking point itself is posted so the run never stalls.
"""

from __future__ import annotations

from .llm import LLM, LLMError

LIMITS = {"create_post": 280, "quote_post": 200, "create_comment": 220}
KIND = {"create_post": "post", "quote_post": "quote comment", "create_comment": "reply"}

SYSTEM = """You write one short social media {kind} in the voice of a simulated person.
First person, plain text, no hashtags, no emojis, no quotation marks around it, at most {limit} characters.
Sound like a real person on a forum, not a press release. Reply with the text only."""


def fallback_text(point_text: str | None, stance_label: str) -> str:
    return point_text or f"My take: {stance_label}"


def write(
    llm: LLM,
    action: str,
    agent: dict,
    stance_label: str,
    subject: dict,
    point_text: str | None,
    replying_to: str | None = None,
) -> tuple[str, bool]:
    """Returns (text, used_llm)."""
    limit = LIMITS.get(action, 280)
    lines = [
        f"Person: {agent['name']}. {agent.get('bio', '')}",
        f"About them: {agent.get('persona', '')}",
        f"Their current view: {stance_label}",
        "Topic facts: " + "; ".join(f"{k}: {v}" for k, v in subject.items()),
        f"Point to make: {point_text or 'their own honest take, in line with their current view'}",
    ]
    if replying_to:
        lines.append(f"Replying to this post: {replying_to[:500]}")
    try:
        text = llm.chat(
            "post",
            [
                {"role": "system", "content": SYSTEM.format(kind=KIND.get(action, "post"), limit=limit)},
                {"role": "user", "content": "\n".join(lines)},
            ],
            temperature=0.9,
            max_tokens=200,
        )
        text = text.strip().strip('"').strip()
        if not text:
            raise LLMError("empty text")
        return text[:limit], True
    except LLMError:
        return fallback_text(point_text, str(stance_label))[:limit], False
