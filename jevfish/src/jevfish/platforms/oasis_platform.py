"""CAMEL-AI OASIS, the social platform MiroFish simulates on, driven by Jev decisions.

Agents are built on camel's StubModel, so OASIS never calls an LLM. Every action is
executed with `perform_action_by_data`, which is what OASIS runs for a ManualAction.
"""

from __future__ import annotations

import asyncio
import csv
import json
import logging
import sqlite3
from pathlib import Path

from .base import ACTIONS, Act, FeedComment, FeedPost

_OASIS_LOGGERS = ["oasis.env", "social.agent", "social.twitter", "social.rec", "table", "camel", "camel.agents", "camel.models"]


def _import_oasis():
    try:
        import oasis  # noqa: F401  (import creates ./log and file handlers)
    except ModuleNotFoundError as e:
        from .base import OASIS_HINT

        raise RuntimeError(OASIS_HINT.format(kind="reddit or twitter")) from e

    for name in _OASIS_LOGGERS:
        logger = logging.getLogger(name)
        for handler in list(logger.handlers):
            if isinstance(handler, logging.FileHandler):
                logger.removeHandler(handler)
                handler.close()
        logger.setLevel(logging.WARNING)
    return oasis


class OasisPlatform:
    def __init__(self, kind: str, workdir):
        if kind not in ("reddit", "twitter"):
            raise ValueError(kind)
        self.name = kind
        self.actions = list(ACTIONS[kind])
        self.workdir = Path(workdir)
        self.db_path = self.workdir / f"{kind}.db"
        self.env = None

    def _write_profiles(self, agents: list[dict]) -> Path:
        self.workdir.mkdir(parents=True, exist_ok=True)
        if self.name == "reddit":
            path = self.workdir / "reddit_profiles.json"
            rows = [
                {
                    "username": a["username"],
                    "bio": a.get("bio", ""),
                    "persona": a.get("persona", ""),
                    "mbti": a.get("mbti", "unknown"),
                    "gender": a.get("gender", "unknown"),
                    "age": a.get("age", 30),
                    "country": a.get("country", "unknown"),
                }
                for a in agents
            ]
            path.write_text(json.dumps(rows, ensure_ascii=False))
        else:
            path = self.workdir / "twitter_profiles.csv"
            with path.open("w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["username", "description", "user_char"])
                for a in agents:
                    writer.writerow([a["username"], a.get("bio", ""), a.get("persona", "")])
        return path

    async def start(self, agents: list[dict]) -> None:
        ids = [a["agent_id"] for a in agents]
        if ids != list(range(len(agents))):
            raise ValueError("OASIS needs agent ids 0..N-1 in order")
        oasis = _import_oasis()
        from camel.models import ModelFactory
        from camel.types import ModelPlatformType, ModelType
        from oasis import ActionType, generate_reddit_agent_graph, generate_twitter_agent_graph

        model = ModelFactory.create(model_platform=ModelPlatformType.OPENAI, model_type=ModelType.STUB)
        profile_path = self._write_profiles(agents)
        available = [ActionType(a) for a in self.actions]
        generate = generate_reddit_agent_graph if self.name == "reddit" else generate_twitter_agent_graph
        graph = await generate(profile_path=str(profile_path), model=model, available_actions=available)
        if self.db_path.exists():
            self.db_path.unlink()
        platform_type = oasis.DefaultPlatformType.REDDIT if self.name == "reddit" else oasis.DefaultPlatformType.TWITTER
        self.env = oasis.make(agent_graph=graph, platform=platform_type, database_path=str(self.db_path))
        await self.env.reset()
        follows = [Act(a["agent_id"], "follow", {"followee_id": f}) for a in agents for f in a.get("follows", [])]
        if follows:
            await self.apply(follows, tick=False)

    def _agent(self, agent_id: int):
        return self.env.agent_graph.get_agent(agent_id)

    async def refresh_recommendations(self) -> None:
        await self.env.platform.update_rec_table()

    async def feed(self, agent_id: int) -> list[FeedPost]:
        result = await self._agent(agent_id).env.action.refresh()
        if not result.get("success"):
            return []
        out = []
        for p in result.get("posts", []):
            if p.get("user_id") == agent_id:
                continue
            likes, dislikes = p.get("num_likes"), p.get("num_dislikes", 0)
            if likes is None:
                score = p.get("score", 0) or 0
                likes, dislikes = max(score, 0), max(-score, 0)
            comments = []
            for c in p.get("comments") or []:
                c_likes = c.get("num_likes")
                if c_likes is None:
                    c_likes = max(c.get("score", 0) or 0, 0)
                comments.append(FeedComment(c["comment_id"], c["user_id"], c.get("content", ""), c_likes))
            original = p.get("original_post_id")
            kind = "post" if not original else ("quote" if p.get("quote_content") else "repost")
            out.append(
                FeedPost(
                    post_id=p["post_id"],
                    author_id=p["user_id"],
                    content=p.get("content") or "",
                    likes=likes or 0,
                    dislikes=dislikes or 0,
                    shares=p.get("num_shares", 0) or 0,
                    kind=kind,
                    original_post_id=original,
                    quote=p.get("quote_content"),
                    comments=comments,
                )
            )
        return out

    async def apply(self, acts: list[Act], tick: bool = True) -> list[dict]:
        async def one(act: Act):
            return await self._agent(act.agent_id).perform_action_by_data(act.action, **act.args)

        raw = await asyncio.gather(*(one(a) for a in acts), return_exceptions=True)
        if tick and self.name == "twitter":
            self.env.platform.sandbox_clock.time_step += 1
        results = []
        for act, r in zip(acts, raw):
            if isinstance(r, BaseException):
                ok, info = False, {"error": f"{type(r).__name__}: {r}"}
            else:
                ok = bool(r.get("success", False)) if isinstance(r, dict) else False
                info = r if isinstance(r, dict) else {"result": str(r)}
            results.append({"agent_id": act.agent_id, "action": act.action, "args": act.args, "ok": ok, "info": info})
        return results

    async def posts(self) -> list[dict]:
        con = sqlite3.connect(self.db_path)
        try:
            con.row_factory = sqlite3.Row
            posts = {
                r["post_id"]: {
                    "post_id": r["post_id"],
                    "author_id": r["user_id"],
                    "content": r["content"] or "",
                    "likes": r["num_likes"] or 0,
                    "dislikes": r["num_dislikes"] or 0,
                    "shares": r["num_shares"] or 0,
                    "kind": "post" if not r["original_post_id"] else ("quote" if r["quote_content"] else "repost"),
                    "original_post_id": r["original_post_id"],
                    "quote": r["quote_content"],
                    "comments": [],
                }
                for r in con.execute(
                    "SELECT post_id, user_id, original_post_id, content, quote_content, num_likes, num_dislikes, num_shares FROM post ORDER BY post_id"
                )
            }
            for c in con.execute("SELECT comment_id, post_id, user_id, content, num_likes FROM comment ORDER BY comment_id"):
                if c["post_id"] in posts:
                    posts[c["post_id"]]["comments"].append(
                        {"comment_id": c["comment_id"], "author_id": c["user_id"], "content": c["content"], "likes": c["num_likes"] or 0}
                    )
            return list(posts.values())
        finally:
            con.close()

    async def close(self) -> None:
        if self.env is not None:
            await self.env.close()
            self.env = None
