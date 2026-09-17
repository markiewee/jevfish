"""Stage 3: the simulation.

For every variant: start a platform with the crowd plus a news desk account, run
the baseline poll, publish the opening posts, then run the rounds. In each round the
scheduled people read their feed, Jev decides their turn, the writer phrases any text,
and all actions are applied together. Whole-crowd polls at the chosen rounds produce the
prediction.
"""

from __future__ import annotations

import asyncio
import random
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from . import metrics
from .frame import variant_subject
from .judge import BudgetExceeded, answer_to_json, build_judge, question_to_json
from .llm import LLM
from .platforms import Act, make_platform
from .platforms.base import POST_TARGET_ACTIONS, TEXT_ACTIONS
from .policy import Mind, agent_view, allowed_actions, build_questions, decide, feed_view, poll_questions, stance_label
from .store import Store, now
from .writer import write

PLATFORMS = {"reddit", "twitter", "lite"}


class RunConfigError(ValueError):
    pass


@dataclass
class RunConfig:
    platform: str = "reddit"
    variants: list[str] = field(default_factory=list)
    rounds: int = 12
    minutes_per_round: int = 60
    start_hour: int = 8
    agents_per_round_min: int = 8
    agents_per_round_max: int = 20
    peak_hours: list[int] = field(default_factory=lambda: [9, 10, 11, 12, 19, 20, 21, 22])
    peak_multiplier: float = 1.5
    quiet_hours: list[int] = field(default_factory=lambda: [0, 1, 2, 3, 4, 5, 6])
    quiet_multiplier: float = 0.3
    poll_rounds: list[int] | None = None
    injections: list[dict] = field(default_factory=list)
    seed: int = 0
    concurrency: int = 16
    max_requests: int | None = None
    feed_size: int = 6
    log_requests: bool = True

    @classmethod
    def from_dict(cls, data: dict | None) -> "RunConfig":
        data = dict(data or {})
        known = {f for f in cls.__dataclass_fields__}
        unknown = set(data) - known
        if unknown:
            raise RunConfigError(f"unknown run settings: {', '.join(sorted(unknown))}")
        cfg = cls(**data)
        if cfg.platform not in PLATFORMS:
            raise RunConfigError("platform must be reddit, twitter or lite")
        if not 1 <= cfg.rounds <= 500:
            raise RunConfigError("rounds must be between 1 and 500")
        if not 1 <= cfg.agents_per_round_min <= cfg.agents_per_round_max:
            raise RunConfigError("agents per round: need 1 <= min <= max")
        if cfg.concurrency < 1:
            raise RunConfigError("concurrency must be at least 1")
        if cfg.minutes_per_round < 1:
            raise RunConfigError("minutes_per_round must be at least 1")
        for inj in cfg.injections:
            if not str(inj.get("text", "")).strip() or not 1 <= int(inj.get("round", 0)) <= cfg.rounds:
                raise RunConfigError("each injection needs text and a round between 1 and the number of rounds")
        return cfg

    def polls(self) -> list[int]:
        if self.poll_rounds is None:
            return sorted({0, self.rounds // 2, self.rounds})
        rounds = sorted({int(r) for r in self.poll_rounds if 0 <= int(r) <= self.rounds})
        return rounds or [self.rounds]

    def planned_requests(self, crowd_size: int, n_variants: int) -> int:
        peak = int(self.agents_per_round_max * max(1.0, self.peak_multiplier))
        per_variant = self.rounds * min(crowd_size, peak) + len(self.polls()) * crowd_size
        return per_variant * n_variants

    def to_dict(self) -> dict:
        return asdict(self)


Progress = Callable[[float, str], None]


class RunContext:
    def __init__(self, store: Store, pid: str, rid: str, llm: LLM, settings, progress: Progress):
        self.store = store
        self.pid = pid
        self.rid = rid
        self.llm = llm
        self.settings = settings
        self.progress = progress
        self.run_dir = store.run_dir(pid, rid)
        project_dir = store.project_dir(pid)
        self.frame = store.read(project_dir / "frame.json")
        self.crowd = store.read(project_dir / "crowd.json")
        if not self.frame or not self.crowd:
            raise RunConfigError("prepare the project (frame and crowd) before running")
        run = store.get_run(pid, rid)
        self.config = RunConfig.from_dict(run["config"])
        all_ids = [v["id"] for v in self.frame["variants"]]
        self.variants = self.config.variants or all_ids
        missing = [v for v in self.variants if v not in all_ids]
        if missing:
            raise RunConfigError(f"unknown variants: {', '.join(missing)}")
        self.agents = self.crowd["agents"]
        self.levels = self.frame["stance"]["levels"]
        self.points = {p["id"]: p["text"] for p in self.frame["talking_points"]}
        self.cache_path = project_dir / "verdicts.sqlite"
        self.judge = None
        self.meter = None
        self.writer_gate = asyncio.Semaphore(max(1, settings.llm_workers))
        self.judge_gate = asyncio.Semaphore(self.config.concurrency)
        self.polls = self.config.polls()
        self.units_total = len(self.variants) * (self.config.rounds + len(self.polls) + 1)
        self.units_done = 0

    def tick(self, message: str) -> None:
        self.units_done += 1
        fraction = min(0.99, self.units_done / self.units_total)
        self.progress(fraction, message)
        self.store.update_run(
            self.pid,
            self.rid,
            status="running",
            progress=round(fraction, 4),
            message=message,
            requests=self.meter.requests if self.meter else 0,
            cache_hits=self.judge.hits if self.judge else 0,
        )

    def log(self, name: str, record: dict) -> None:
        self.store.append_jsonl(self.run_dir / name, record)


class VariantRun:
    def __init__(self, ctx: RunContext, variant_id: str):
        self.ctx = ctx
        self.vid = variant_id
        self.cfg = ctx.config
        self.subject = variant_subject(ctx.frame, variant_id)
        self.label = next(v["label"] for v in ctx.frame["variants"] if v["id"] == variant_id)
        self.news_id = len(ctx.agents)
        self.labels = {a["agent_id"]: f"{a['name']} ({a.get('segment') or a['kind']})" for a in ctx.agents}
        self.labels[self.news_id] = "News desk"
        self.minds = {a["agent_id"]: Mind(a, following=set(a.get("follows", []))) for a in ctx.agents}
        self.rng = random.Random(f"{self.cfg.seed}:{variant_id}:schedule")
        self.actions: list[dict] = []
        self.poll_records: dict[int, list[dict]] = {}
        self.platform = make_platform(self.cfg.platform, ctx.run_dir / variant_id, feed_size=self.cfg.feed_size)

    # -- helpers ---------------------------------------------------------
    def platform_agents(self) -> list[dict]:
        news = {"agent_id": self.news_id, "username": "newsdesk", "name": "News desk",
                "bio": "News and announcements", "persona": "A neutral news account", "follows": []}
        agents = []
        for a in self.ctx.agents:
            follows = list(a.get("follows", []))
            if self.cfg.platform == "twitter":
                follows.append(self.news_id)
            agents.append({**a, "follows": follows})
        return agents + [news]

    def author_id(self, name: str | None) -> int:
        if name:
            key = name.strip().lower()
            for a in self.ctx.agents:
                if key in (a["name"].lower(), a["username"].lower()):
                    return a["agent_id"]
        return self.news_id

    def state(self, mind: Mind, feed) -> dict:
        return {
            "topic": self.ctx.frame["question"],
            "subject": self.subject,
            "agent": agent_view(mind, self.ctx.levels),
            "feed": feed_view(feed, self.labels, mind.following),
        }

    def hour(self, round_no: int) -> int:
        return (self.cfg.start_hour + ((round_no - 1) * self.cfg.minutes_per_round) // 60) % 24

    def schedule(self, round_no: int) -> list[int]:
        hour = self.hour(round_no)
        mult = self.cfg.peak_multiplier if hour in self.cfg.peak_hours else (
            self.cfg.quiet_multiplier if hour in self.cfg.quiet_hours else 1.0)
        target = max(1, int(self.rng.uniform(self.cfg.agents_per_round_min, self.cfg.agents_per_round_max) * mult))
        candidates = [a["agent_id"] for a in self.ctx.agents if self.rng.random() < a.get("activity", 0.5)]
        return sorted(self.rng.sample(candidates, min(target, len(candidates))))

    async def ask(self, state: dict, questions: dict, kind: str, round_no: int, agent_id: int):
        async with self.ctx.judge_gate:
            verdict = await self.ctx.judge.ask(state, questions)
        if self.cfg.log_requests:
            self.ctx.log("requests.jsonl", {
                "variant": self.vid, "round": round_no, "agent_id": agent_id, "kind": kind, "cached": verdict.cached,
                "input_tokens": verdict.input_tokens, "state": state,
                "questions": {k: question_to_json(q) for k, q in questions.items()},
                "answers": {k: answer_to_json(a) for k, a in verdict.answers.items()},
            })
        return verdict

    async def gather(self, coros):
        results = await asyncio.gather(*coros, return_exceptions=True)
        errors = [r for r in results if isinstance(r, BaseException)]
        if errors:
            raise errors[0]
        return results

    # -- phases ----------------------------------------------------------
    async def poll(self, round_no: int) -> None:
        await self.platform.refresh_recommendations()
        questions = poll_questions(self.ctx.frame)

        async def one(agent_id: int):
            mind = self.minds[agent_id]
            feed = await self.platform.feed(agent_id)
            verdict = await self.ask(self.state(mind, feed), questions, "poll", round_no, agent_id)
            stance, outcome = verdict.answers["stance"], verdict.answers["outcome"]
            mind.stance = stance.score
            return {"variant": self.vid, "round": round_no, "agent_id": agent_id, "stance": stance.score,
                    "stance_confidence": stance.confidence, "outcome_p": outcome.p, "cached": verdict.cached}

        records = await self.gather([one(a["agent_id"]) for a in self.ctx.agents])
        self.poll_records[round_no] = records
        for r in records:
            self.ctx.log("polls.jsonl", r)
        s = metrics.summarize_poll(records, len(self.ctx.levels))
        self.ctx.tick(f"{self.vid}: poll after round {round_no}: {s['expected_yes']:.1f} of {s['n']} expected yes")

    async def apply(self, round_no: int, acts: list[Act], extras: list[dict]) -> None:
        if not acts:
            return
        results = await self.platform.apply(acts)
        for res, extra in zip(results, extras):
            record = {
                "variant": self.vid, "round": round_no, "hour": self.hour(max(1, round_no)), "at": now(),
                "agent_id": res["agent_id"], "agent_name": self.labels.get(res["agent_id"], str(res["agent_id"])),
                "action": res["action"], "args": res["args"], "ok": res["ok"],
                **extra,
            }
            if not res["ok"]:
                record["error"] = str(res["info"])[:300]
            elif isinstance(res["info"], dict):
                for key in ("post_id", "comment_id"):
                    if res["info"].get(key) is not None and key not in res["args"]:
                        record[f"created_{key}"] = res["info"][key]
            self.actions.append(record)
            self.ctx.log("actions.jsonl", record)
            mind = self.minds.get(res["agent_id"])
            if mind and res["ok"] and res["action"] != "do_nothing":
                if res["action"] == "follow":
                    mind.following.add(res["args"]["followee_id"])
                elif res["action"] == "like_post":
                    mind.liked_posts.add(res["args"]["post_id"])
                elif res["action"] == "dislike_post":
                    mind.disliked_posts.add(res["args"]["post_id"])
                elif res["action"] == "like_comment":
                    mind.liked_comments.add(res["args"]["comment_id"])
                snippet = extra.get("content") or extra.get("target_excerpt") or ""
                mind.remember(f"{res['action']}: {snippet[:120]}".strip())

    async def turn(self, round_no: int, agent_id: int):
        mind = self.minds[agent_id]
        feed = await self.platform.feed(agent_id)
        actions = allowed_actions(self.platform.actions, feed, mind, agent_id, {self.news_id})
        questions = build_questions(self.ctx.frame, feed, actions, self.labels, mind, agent_id, {self.news_id})
        verdict = await self.ask(self.state(mind, feed), questions, "turn", round_no, agent_id)
        rng = random.Random(f"{self.cfg.seed}:{self.vid}:{round_no}:{agent_id}")
        d = decide(verdict, rng, agent_id, mind.exclusions())
        mind.stance = d.stance
        posts = {p.post_id: p for p in feed}
        comments = {c.comment_id: c for p in feed for c in p.comments}
        extra: dict[str, Any] = {"stance": d.stance, "outcome_p": d.outcome_p, "point": d.point}
        action, args = d.action, {}
        target = None
        if action in POST_TARGET_ACTIONS:
            eligible = [p for p in feed if p.post_id not in mind.exclusions().get(action, set())]
            target = posts.get(d.target_post) if d.target_post in {p.post_id for p in eligible} else (eligible[0] if eligible else None)
            if target is None:
                action = "do_nothing"
            else:
                args["post_id"] = target.post_id
                extra["target_excerpt"] = target.content[:200]
                extra["target_author"] = self.labels.get(target.author_id)
        if action == "like_comment":
            open_comments = [c for c in comments.values() if c.comment_id not in mind.liked_comments]
            comment = comments.get(d.target_comment) if d.target_comment in {c.comment_id for c in open_comments} else (open_comments[0] if open_comments else None)
            if comment is None:
                action = "do_nothing"
            else:
                args["comment_id"] = comment.comment_id
                extra["target_excerpt"] = comment.content[:200]
                extra["target_author"] = self.labels.get(comment.author_id)
        if action == "follow":
            if d.followee is None:
                action = "do_nothing"
            else:
                args["followee_id"] = d.followee
                extra["target_author"] = self.labels.get(d.followee)
        if action in TEXT_ACTIONS:
            point_text = self.ctx.points.get(d.point) if d.point else None
            async with self.ctx.writer_gate:
                content, used_llm = await asyncio.to_thread(
                    write, self.ctx.llm, action, mind.agent, str(stance_label(self.ctx.levels, d.stance)),
                    self.subject, point_text, target.content if target is not None and action != "create_post" else None,
                )
            extra["content"] = content
            extra["llm_text"] = used_llm
            args["quote_content" if action == "quote_post" else "content"] = content
        if action == "do_nothing":
            args = {}
        extra["jev_action"] = d.action
        extra["action_probabilities"] = d.action_probabilities
        return Act(agent_id, action, args), extra

    async def run(self) -> dict:
        ctx, cfg = self.ctx, self.cfg
        # OASIS samples feeds with the global random module; seed it so reruns see the same feeds.
        random.seed(f"{cfg.seed}:{self.vid}:platform")
        await self.platform.start(self.platform_agents())
        try:
            if 0 in ctx.polls:
                await self.poll(0)
            openings = ctx.frame.get("opening_posts") or []
            acts, extras = [], []
            for o in openings:
                author = self.author_id(o.get("author"))
                text = o["text"]
                if author == self.news_id and o.get("author"):
                    text = f"{o['author']} said: {text}"  # author is not in the crowd; the news desk reports it
                acts.append(Act(author, "create_post", {"content": text}))
                extras.append({"content": text, "point": o.get("talking_point"), "opening": True})
            await self.apply(0, acts, extras)
            ctx.tick(f"{self.vid}: {len(acts)} opening post(s) published")
            for r in range(1, cfg.rounds + 1):
                ctx.progress(ctx.units_done / ctx.units_total, f"{self.vid}: round {r}/{cfg.rounds}")
                injections = [i for i in cfg.injections if int(i["round"]) == r]
                if injections:
                    await self.apply(
                        r,
                        [Act(self.author_id(i.get("author")), "create_post", {"content": i["text"]}) for i in injections],
                        [{"content": i["text"], "injection": True} for i in injections],
                    )
                await self.platform.refresh_recommendations()
                active = self.schedule(r)
                turns = await self.gather([self.turn(r, a) for a in active])
                await self.apply(r, [t[0] for t in turns], [t[1] for t in turns])
                ctx.tick(f"{self.vid}: round {r}/{cfg.rounds} done, {len(active)} people acted")
                if r in ctx.polls:
                    await self.poll(r)
            posts = await self.platform.posts()
        finally:
            await self.platform.close()
        return self.summarize(posts)

    def summarize(self, posts: list[dict], partial: bool = False) -> dict:
        n_levels = len(self.ctx.levels)
        polls = [{"round": r, **metrics.summarize_poll(recs, n_levels)} for r, recs in sorted(self.poll_records.items())]
        final_round = max(self.poll_records) if self.poll_records else None
        final_records = self.poll_records.get(final_round, []) if final_round is not None else []
        counts = {}
        for a in self.actions:
            if a["ok"] and a["round"] > 0:
                counts[a["action"]] = counts.get(a["action"], 0) + 1
        return {
            "id": self.vid,
            "label": self.label,
            "subject": self.subject,
            "polls": polls,
            "baseline": polls[0] if polls else None,
            "final": polls[-1] if polls else None,
            "segments": metrics.segment_breakdown(final_records, self.ctx.agents),
            "points": metrics.point_spread(self.actions, self.ctx.frame),
            "top_posts": metrics.top_posts(posts, self.labels),
            "most_engaged": metrics.most_engaged(posts, self.labels),
            "timeline": metrics.action_timeline(self.actions),
            "action_counts": counts,
            "posts_total": len(posts),
            "partial": partial,
        }


async def _run(ctx: RunContext) -> dict:
    ctx.judge, ctx.meter = build_judge(ctx.settings, ctx.cache_path, ctx.config.max_requests)
    variant_summaries = []
    partial = None
    try:
        for vid in ctx.variants:
            vr = VariantRun(ctx, vid)
            try:
                variant_summaries.append(await vr.run())
            except BudgetExceeded as e:
                partial = f"{e}. Answers already paid for are cached, so a rerun only pays for the rest."
                try:
                    posts = await vr.platform.posts()
                except Exception:
                    posts = []
                variant_summaries.append(vr.summarize(posts, partial=True))
                break
    finally:
        await ctx.judge.aclose()
    finals = {v["id"]: v["final"] for v in variant_summaries if v["final"] and not v["partial"]}
    usage = getattr(ctx.llm, "usage", None)
    summary = {
        "run_id": ctx.rid,
        "project_id": ctx.pid,
        "created_at": now(),
        "question": ctx.frame["question"],
        "outcome_instructions": ctx.frame["outcome"]["instructions"],
        "stance_levels": ctx.levels,
        "config": ctx.config.to_dict(),
        "crowd": {"size": len(ctx.agents), **(ctx.crowd.get("stats") or {})},
        "variants": variant_summaries,
        "comparisons": metrics.compare(finals),
        "judge": {
            "model": ctx.meter.inner.model,
            "fake": ctx.settings.fake_judge,
            "requests": ctx.meter.requests,
            "cache_hits": ctx.judge.hits,
            "input_tokens": ctx.meter.input_tokens,
            "est_cost_usd": ctx.meter.input_tokens / 1_000_000 * 0.042,
        },
        "llm": usage.to_dict() if usage else None,
        "partial": partial,
    }
    ctx.store.write(ctx.run_dir / "summary.json", summary)
    return summary


def run_simulation(store: Store, settings, llm: LLM, pid: str, rid: str, progress: Progress) -> dict:
    ctx = RunContext(store, pid, rid, llm, settings, progress)
    store.update_run(pid, rid, status="running", started_at=now(), progress=0.0, variants=ctx.variants)
    try:
        summary = asyncio.run(_run(ctx))
    except BaseException as e:
        store.update_run(pid, rid, status="cancelled" if type(e).__name__ == "Cancelled" else "failed",
                         error=f"{type(e).__name__}: {e}", finished_at=now())
        raise
    store.update_run(pid, rid, status="partial" if summary["partial"] else "done", progress=1.0,
                     finished_at=now(), requests=summary["judge"]["requests"], cache_hits=summary["judge"]["cache_hits"])
    return summary


def planned_requests(frame: dict, crowd: dict, config: RunConfig) -> int:
    n_variants = len(config.variants or frame["variants"])
    return config.planned_requests(len(crowd["agents"]), n_variants)


def load_actions(run_dir: Path, store: Store, since: int = 0, limit: int = 200) -> list[dict]:
    return store.read_jsonl(Path(run_dir) / "actions.jsonl", since=since, limit=limit)
