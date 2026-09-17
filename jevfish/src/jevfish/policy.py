"""Jev's side of a turn: what a person sees, the typed questions, and how answers become an action.

One request per person per turn:
  stance          Score   how they now feel about the subject
  outcome         Noul    probability of the predicted behaviour (the prediction itself)
  action          Choice  what they do next, from the actions the feed allows
  point           Choice  speculative: which talking point a post or comment would make
  target_post     Choice  speculative: which feed post a reaction would pick
  target_comment  Choice  speculative: which comment a like would pick
  followee        Choice  speculative: whose account a follow would pick
Code samples from the probabilities and uses only the answers the chosen action needs.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any

from .judge import ChoiceA, ChoiceQ, NoulA, NoulQ, Question, ScoreA, ScoreQ, Verdict
from .platforms.base import POST_TARGET_ACTIONS, TEXT_ACTIONS, FeedPost

NO_OPINION = "has not formed a view yet"
NO_POINT = "none"

ACTION_INSTRUCTIONS = (
    "Given the posts in `feed`, what would the person described in `agent` most likely do next "
    "on this platform about `subject`?"
)
ACTION_TEXT = {
    "do_nothing": "Read the feed and move on without reacting",
    "like_post": "Like or upvote one post in `feed`",
    "dislike_post": "Dislike or downvote one post in `feed`",
    "create_comment": "Reply with a comment under one post in `feed`",
    "like_comment": "Like one of the comments shown under the posts in `feed`",
    "repost": "Reshare one post in `feed` to their followers without adding words",
    "quote_post": "Reshare one post in `feed` with a comment of their own",
    "create_post": "Write a new post of their own about `subject`",
    "follow": "Follow the author of one post in `feed`",
}
POINT_INSTRUCTIONS = (
    "Suppose the person described in `agent` writes a post or comment about `subject`. "
    "Which point would they most likely make?"
)
POINT_NONE = "None of these points matches what they would say"
TARGET_POST_INSTRUCTIONS = (
    "Suppose the person described in `agent` reacts to one post in `feed` (a like, dislike, reply or reshare). "
    "Which post would it be?"
)
TARGET_COMMENT_INSTRUCTIONS = "Suppose the person described in `agent` likes one comment in `feed`. Which comment would it be?"
FOLLOW_INSTRUCTIONS = "Suppose the person described in `agent` follows one author from `feed`. Whose account would it be?"


@dataclass
class Mind:
    """What code remembers about a person between turns."""

    agent: dict
    stance: float | None = None
    recent: list[str] = field(default_factory=list)
    following: set[int] = field(default_factory=set)
    liked_posts: set[int] = field(default_factory=set)
    disliked_posts: set[int] = field(default_factory=set)
    liked_comments: set[int] = field(default_factory=set)

    def exclusions(self) -> dict[str, set[int]]:
        """Targets a platform would reject because this person already reacted to them."""
        return {"like_post": self.liked_posts, "dislike_post": self.disliked_posts, "like_comment": self.liked_comments}

    def remember(self, line: str) -> None:
        self.recent = (self.recent + [line])[-3:]


def stance_label(levels: list, stance: float | None) -> Any:
    if stance is None:
        return NO_OPINION
    return levels[min(len(levels) - 1, max(0, int(stance + 0.5)))]


def agent_view(mind: Mind, levels: list) -> dict:
    a = mind.agent
    view: dict[str, Any] = {"name": a["name"], "bio": a.get("bio", ""), "persona": a.get("persona", ""), "group": a.get("segment", "")}
    view.update(a.get("attributes") or {})
    if a.get("stance_hint") and a["stance_hint"] != "neutral":
        view["known_position"] = a["stance_hint"]
    view["current_view"] = stance_label(levels, mind.stance)
    if mind.recent:
        view["their_recent_activity"] = mind.recent
    return view


def feed_view(feed: list[FeedPost], labels: dict[int, str], following: set[int]) -> list[dict]:
    items = []
    for p in feed:
        item = {
            "post_id": f"p{p.post_id}",
            "author": labels.get(p.author_id, f"user {p.author_id}"),
            "author_is_followed": p.author_id in following,
            "type": p.kind,
            "text": p.content[:600],
            "likes": p.likes,
            "dislikes": p.dislikes,
            "reshares": p.shares,
        }
        if p.quote:
            item["quote"] = p.quote[:300]
        if p.comments:
            item["comments"] = [
                {"comment_id": f"c{c.comment_id}", "author": labels.get(c.author_id, f"user {c.author_id}"), "text": c.content[:300], "likes": c.likes}
                for c in p.comments[-3:]
            ]
        items.append(item)
    return items


def allowed_actions(platform_actions: list[str], feed: list[FeedPost], mind: Mind, self_id: int, blocked_authors: set[int]) -> list[str]:
    post_ids = {p.post_id for p in feed}
    comment_ids = {c.comment_id for p in feed for c in p.comments}
    followable = {p.author_id for p in feed} - mind.following - {self_id} - blocked_authors
    excluded = mind.exclusions()
    out = []
    for a in platform_actions:
        if a in POST_TARGET_ACTIONS and not (post_ids - excluded.get(a, set())):
            continue
        if a == "like_comment" and not (comment_ids - excluded["like_comment"]):
            continue
        if a == "follow" and not followable:
            continue
        out.append(a)
    return out or ["do_nothing"]


def build_questions(frame: dict, feed: list[FeedPost], actions: list[str], labels: dict[int, str], mind: Mind, self_id: int, blocked: set[int]) -> dict[str, Question]:
    qs: dict[str, Question] = {
        "stance": ScoreQ(frame["stance"]["instructions"], list(frame["stance"]["levels"])),
        "outcome": NoulQ(frame["outcome"]["instructions"], frame["outcome"].get("criteria")),
    }
    if actions == ["do_nothing"]:
        return qs
    qs["action"] = ChoiceQ(ACTION_INSTRUCTIONS, {a: ACTION_TEXT[a] for a in actions})
    if TEXT_ACTIONS & set(actions):
        points = {p["id"]: p["text"] for p in frame["talking_points"]}
        points[NO_POINT] = POINT_NONE
        qs["point"] = ChoiceQ(POINT_INSTRUCTIONS, points)
    if POST_TARGET_ACTIONS & set(actions):
        qs["target_post"] = ChoiceQ(TARGET_POST_INSTRUCTIONS, {f"p{p.post_id}": p.content[:300] or "(empty)" for p in feed})
    if "like_comment" in actions:
        qs["target_comment"] = ChoiceQ(
            TARGET_COMMENT_INSTRUCTIONS,
            {f"c{c.comment_id}": c.content[:300] or "(empty)" for p in feed for c in p.comments[-3:]},
        )
    if "follow" in actions:
        authors = {p.author_id for p in feed} - mind.following - {self_id} - blocked
        qs["followee"] = ChoiceQ(FOLLOW_INSTRUCTIONS, {f"u{a}": labels.get(a, f"user {a}") for a in sorted(authors)})
    return qs


def poll_questions(frame: dict) -> dict[str, Question]:
    return {
        "stance": ScoreQ(frame["stance"]["instructions"], list(frame["stance"]["levels"])),
        "outcome": NoulQ(frame["outcome"]["instructions"], frame["outcome"].get("criteria")),
    }


def sample(rng: random.Random, answer: ChoiceA, exclude: set[str] = frozenset()) -> str | None:
    options = [k for k, v in answer.probabilities.items() if v > 0 and k not in exclude]
    if not options:
        remaining = [k for k in answer.probabilities if k not in exclude]
        return remaining[0] if remaining else None
    return rng.choices(options, weights=[answer.probabilities[k] for k in options])[0]


@dataclass
class Decision:
    agent_id: int
    stance: float
    stance_confidence: float
    stance_probabilities: dict[int, float]
    outcome_p: float
    action: str
    action_probabilities: dict[str, float]
    point: str | None = None
    target_post: int | None = None
    target_comment: int | None = None
    followee: int | None = None
    cached: bool = False

    def to_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items()}


def decide(verdict: Verdict, rng: random.Random, agent_id: int, exclusions: dict[str, set[int]] | None = None) -> Decision:
    a = verdict.answers
    stance, outcome = a["stance"], a["outcome"]
    assert isinstance(stance, ScoreA) and isinstance(outcome, NoulA)
    action_answer = a.get("action")
    if isinstance(action_answer, ChoiceA):
        action, probs = sample(rng, action_answer), action_answer.probabilities
    else:
        action, probs = "do_nothing", {"do_nothing": 1.0}
    d = Decision(agent_id, stance.score, stance.confidence, stance.probabilities, outcome.p, action, probs, cached=verdict.cached)
    if action in TEXT_ACTIONS and isinstance(a.get("point"), ChoiceA):
        d.point = sample(rng, a["point"])
    exclusions = exclusions or {}
    if action in POST_TARGET_ACTIONS and isinstance(a.get("target_post"), ChoiceA):
        pick = sample(rng, a["target_post"], {f"p{i}" for i in exclusions.get(action, set())})
        d.target_post = int(pick[1:]) if pick else None
    if action == "like_comment" and isinstance(a.get("target_comment"), ChoiceA):
        pick = sample(rng, a["target_comment"], {f"c{i}" for i in exclusions.get(action, set())})
        d.target_comment = int(pick[1:]) if pick else None
    if action == "follow" and isinstance(a.get("followee"), ChoiceA):
        pick = sample(rng, a["followee"])
        d.followee = int(pick[1:]) if pick else None
    return d
