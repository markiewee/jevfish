"""Numbers from polls, decisions and the platform.

A poll asks every person the outcome question. With calibrated probabilities the expected
number who say yes is the sum of their probabilities, and its spread is Poisson-binomial
with variance sum p(1 - p). The 90% range covers only that chance element, not model error.
"""

from __future__ import annotations

import math
from collections import Counter, defaultdict

Z90 = 1.6449


def summarize_poll(records: list[dict], n_levels: int) -> dict:
    n = len(records)
    ps = [r["outcome_p"] for r in records]
    expected = sum(ps)
    variance = sum(p * (1 - p) for p in ps)
    half = Z90 * math.sqrt(variance)
    hist = [0] * n_levels
    for r in records:
        hist[min(n_levels - 1, max(0, int(r["stance"] + 0.5)))] += 1
    return {
        "n": n,
        "mean_outcome": expected / n if n else 0.0,
        "expected_yes": expected,
        "variance": variance,
        "low": max(0.0, expected - half),
        "high": min(float(n), expected + half),
        "likely_yes": sum(p >= 0.5 for p in ps),
        "stance_mean": sum(r["stance"] for r in records) / n if n else 0.0,
        "stance_hist": hist,
    }


def compare(finals: dict[str, dict]) -> list[dict]:
    ids = list(finals)
    if len(ids) < 2:
        return []
    base = finals[ids[0]]
    out = []
    for vid in ids[1:]:
        v = finals[vid]
        diff = v["expected_yes"] - base["expected_yes"]
        half = Z90 * math.sqrt(v["variance"] + base["variance"])
        out.append({
            "variant": vid,
            "baseline": ids[0],
            "diff_expected_yes": diff,
            "low": diff - half,
            "high": diff + half,
            "diff_mean_outcome": v["mean_outcome"] - base["mean_outcome"],
            "verdict": "higher" if diff - half > 0 else ("lower" if diff + half < 0 else "within noise"),
        })
    return out


def segment_breakdown(records: list[dict], agents: list[dict]) -> dict[str, list[dict]]:
    by_id = {a["agent_id"]: a for a in agents}
    keys: dict[str, dict[str, list[dict]]] = defaultdict(lambda: defaultdict(list))
    for r in records:
        a = by_id.get(r["agent_id"])
        if not a:
            continue
        keys["kind"][a["kind"]].append(r)
        keys["group"][a.get("segment") or "unknown"].append(r)
        for k, v in (a.get("attributes") or {}).items():
            keys[k][str(v)].append(r)
    out = {}
    for attr, groups in keys.items():
        rows = [
            {
                "value": value,
                "n": len(rs),
                "mean_outcome": sum(r["outcome_p"] for r in rs) / len(rs),
                "expected_yes": sum(r["outcome_p"] for r in rs),
                "mean_stance": sum(r["stance"] for r in rs) / len(rs),
            }
            for value, rs in groups.items()
        ]
        out[attr] = sorted(rows, key=lambda r: (-r["mean_outcome"], r["value"]))
    return out


def point_spread(actions: list[dict], frame: dict) -> list[dict]:
    counts: dict[str, Counter] = defaultdict(Counter)
    for a in actions:
        if a.get("ok") and a.get("point") and a["point"] != "none":
            counts[a["point"]][a["action"]] += 1
    rows = []
    for p in frame["talking_points"]:
        c = counts.get(p["id"], Counter())
        rows.append({
            "id": p["id"],
            "text": p["text"],
            "side": p["side"],
            "posts": c["create_post"],
            "comments": c["create_comment"],
            "quotes": c["quote_post"],
            "total": sum(c.values()),
        })
    return sorted(rows, key=lambda r: (-r["total"], r["id"]))


def engagement(post: dict) -> int:
    return post["likes"] + post["dislikes"] + 2 * post["shares"] + len(post["comments"])


def top_posts(posts: list[dict], labels: dict[int, str], limit: int = 10) -> list[dict]:
    originals = [p for p in posts if p["kind"] != "repost"]
    ranked = sorted(originals, key=lambda p: (-engagement(p), p["post_id"]))[:limit]
    return [
        {
            "post_id": p["post_id"],
            "author": labels.get(p["author_id"], str(p["author_id"])),
            "content": p["content"],
            "likes": p["likes"],
            "dislikes": p["dislikes"],
            "shares": p["shares"],
            "comments": [{"author": labels.get(c["author_id"], str(c["author_id"])), "content": c["content"], "likes": c["likes"]} for c in p["comments"][:5]],
            "engagement": engagement(p),
        }
        for p in ranked
    ]


def most_engaged(posts: list[dict], labels: dict[int, str], limit: int = 10) -> list[dict]:
    score: Counter = Counter()
    count: Counter = Counter()
    for p in posts:
        if p["kind"] == "repost":
            continue
        score[p["author_id"]] += engagement(p)
        count[p["author_id"]] += 1
    return [
        {"agent_id": a, "name": labels.get(a, str(a)), "posts": count[a], "engagement": s}
        for a, s in score.most_common(limit)
        if s > 0
    ]


def action_timeline(actions: list[dict]) -> list[dict]:
    by_round: dict[int, Counter] = defaultdict(Counter)
    for a in actions:
        if a.get("ok"):
            by_round[a["round"]][a["action"]] += 1
    return [{"round": r, **dict(c)} for r, c in sorted(by_round.items())]
