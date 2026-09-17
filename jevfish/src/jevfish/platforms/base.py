"""Platform protocol shared by the in-memory platform and the OASIS adapter."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Protocol

# Actions Jev may choose on each platform. Text-bearing actions get their words from the writer.
ACTIONS: dict[str, list[str]] = {
    "reddit": ["do_nothing", "like_post", "dislike_post", "create_comment", "like_comment", "create_post", "follow"],
    "twitter": ["do_nothing", "like_post", "repost", "quote_post", "create_post", "follow"],
    "lite": ["do_nothing", "like_post", "dislike_post", "create_comment", "repost", "create_post", "follow"],
}
TEXT_ACTIONS = {"create_post", "create_comment", "quote_post"}
POST_TARGET_ACTIONS = {"like_post", "dislike_post", "create_comment", "repost", "quote_post"}


@dataclass
class FeedComment:
    comment_id: int
    author_id: int
    content: str
    likes: int = 0


@dataclass
class FeedPost:
    post_id: int
    author_id: int
    content: str
    likes: int = 0
    dislikes: int = 0
    shares: int = 0
    kind: str = "post"  # post, repost, quote
    original_post_id: int | None = None
    quote: str | None = None
    comments: list[FeedComment] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Act:
    agent_id: int
    action: str
    args: dict[str, Any] = field(default_factory=dict)


class Platform(Protocol):
    name: str
    actions: list[str]

    async def start(self, agents: list[dict]) -> None: ...

    async def refresh_recommendations(self) -> None: ...

    async def feed(self, agent_id: int) -> list[FeedPost]: ...

    async def apply(self, acts: list[Act]) -> list[dict]: ...

    async def posts(self) -> list[dict]: ...

    async def close(self) -> None: ...


def make_platform(kind: str, workdir, *, feed_size: int = 6) -> Platform:
    if kind == "lite":
        from .lite import LitePlatform

        return LitePlatform(feed_size=feed_size)
    if kind in ("reddit", "twitter"):
        from .oasis_platform import OasisPlatform

        return OasisPlatform(kind, workdir)
    raise ValueError(f"unknown platform '{kind}'; use reddit, twitter or lite")
