"""In-memory platform with Reddit-style posts, comments, likes, reposts and follows.

Fast and dependency-free; used by tests and quick runs."""

from __future__ import annotations

from .base import ACTIONS, Act, FeedComment, FeedPost


class LitePlatform:
    name = "lite"

    def __init__(self, feed_size: int = 6):
        self.actions = list(ACTIONS["lite"])
        self.feed_size = feed_size
        self.follows: dict[int, set[int]] = {}
        self._posts: list[FeedPost] = []
        self._round = 0
        self._created: dict[int, int] = {}  # post_id -> round created
        self._visible_round: dict[int, int] = {}
        self._reactions: set[tuple] = set()  # (agent, action, target) pairs; duplicates are rejected like OASIS

    async def start(self, agents: list[dict]) -> None:
        self.follows = {a["agent_id"]: set(a.get("follows", [])) for a in agents}

    async def refresh_recommendations(self) -> None:
        # Posts made before this call become visible; mirrors OASIS updating its rec table per step.
        for p in self._posts:
            self._visible_round.setdefault(p.post_id, self._round)
        self._round += 1

    def _post(self, pid: int) -> FeedPost | None:
        return next((p for p in self._posts if p.post_id == pid), None)

    async def feed(self, agent_id: int) -> list[FeedPost]:
        visible = [p for p in self._posts if p.post_id in self._visible_round and p.author_id != agent_id]
        mine = self.follows.get(agent_id, set())
        followed = sorted((p for p in visible if p.author_id in mine), key=lambda p: -p.post_id)
        hot = sorted((p for p in visible if p.author_id not in mine), key=lambda p: (-(p.likes - p.dislikes + 2 * p.shares + len(p.comments)), -p.post_id))
        out, roots = [], set()
        for p in [*followed, *hot]:
            root = p.original_post_id or p.post_id
            if root in roots:
                continue
            roots.add(root)
            out.append(p)
            if len(out) >= self.feed_size:
                break
        return out

    async def apply(self, acts: list[Act]) -> list[dict]:
        results = []
        for act in acts:
            ok, info = True, {}
            a = act.args
            key = (act.agent_id, act.action, a.get("post_id", a.get("comment_id")))
            if act.action in ("like_post", "dislike_post", "like_comment"):
                if key in self._reactions:
                    results.append({"agent_id": act.agent_id, "action": act.action, "args": a, "ok": False,
                                    "info": {"error": "reaction already exists"}})
                    continue
                self._reactions.add(key)
            if act.action == "create_post":
                pid = len(self._posts) + 1
                self._posts.append(FeedPost(pid, act.agent_id, a["content"]))
                info = {"post_id": pid}
            elif act.action in ("like_post", "dislike_post", "repost", "quote_post", "create_comment"):
                post = self._post(a.get("post_id", -1))
                if post is None:
                    ok, info = False, {"error": "no such post"}
                elif act.action == "like_post":
                    post.likes += 1
                elif act.action == "dislike_post":
                    post.dislikes += 1
                elif act.action in ("repost", "quote_post"):
                    root = self._post(post.original_post_id) if post.original_post_id else post
                    root.shares += 1
                    pid = len(self._posts) + 1
                    kind = "repost" if act.action == "repost" else "quote"
                    self._posts.append(FeedPost(pid, act.agent_id, root.content, kind=kind, original_post_id=root.post_id, quote=a.get("quote_content")))
                    info = {"post_id": pid}
                else:
                    cid = sum(len(p.comments) for p in self._posts) + 1
                    post.comments.append(FeedComment(cid, act.agent_id, a["content"]))
                    info = {"comment_id": cid}
            elif act.action == "like_comment":
                comment = next((c for p in self._posts for c in p.comments if c.comment_id == a.get("comment_id")), None)
                if comment is None:
                    ok, info = False, {"error": "no such comment"}
                else:
                    comment.likes += 1
            elif act.action == "follow":
                self.follows.setdefault(act.agent_id, set()).add(a["followee_id"])
            elif act.action != "do_nothing":
                ok, info = False, {"error": f"unsupported action {act.action}"}
            results.append({"agent_id": act.agent_id, "action": act.action, "args": a, "ok": ok, "info": info})
        return results

    async def posts(self) -> list[dict]:
        return [p.to_dict() for p in self._posts]

    async def close(self) -> None:
        pass
