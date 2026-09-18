"""Numbers from polls, decisions and the platform.

A poll asks every person the outcome question. With calibrated probabilities the expected
number who say yes is the sum of their probabilities, and its spread is Poisson-binomial
with variance sum p(1 - p). The 90% range covers only that chance element, not model error.
"""

from __future__ import annotations

import math
from collections import Counter, defaultdict

Z90 = 1.6449


ESTIMANDS = {
    "acceptance_rate_independent": "acceptance rate among the described crowd",
    "choice_share_of_described_set": "share of the described option set",
    "event_probability": "probability of the event",
}


def summarize_poll(
    records: list[dict],
    n_levels: int,
    *,
    calibration=None,
    honest_half_width: float | None = None,
    estimand: str = "acceptance_rate_independent",
) -> dict:
    """Summarise one poll.

    `mean_outcome` is NOT a real-world rate, and which quantity it is depends on how the
    question was asked. A NoulQ judges each person on their own
    (`acceptance_rate_independent`); a ChoiceQ allocates people across a fixed option set
    (`choice_share_of_described_set`). One calibration map cannot serve both.

    Neither is occupancy. A listing with a 22 percent choice share can sit in a flat
    running at 89 percent occupancy, because occupancy is arrival volume over supply. The
    market-research trade has known this for decades: share of preference assumes equal
    awareness and equal distribution, and reaching market share needs availability,
    awareness, a scale exponent and a share adjustment. JevFish has none of those inputs,
    so a calibration map fitted on resolved outcomes is the only honest bridge.

    With no `honest_half_width` the interval is Poisson-binomial, which covers sampling
    noise inside a synthetic crowd and NOT model, frame or crowd-composition error. On the
    Pureloft backtest the real error was 11.5x that half-width, and it shrinks as
    1/sqrt(n) while the real error does not move, so more people means more confidence and
    the same error. `interval_covers` always says which of the two you are looking at.
    """
    from .calibrate import apply_map

    if estimand not in ESTIMANDS:
        raise ValueError(
            f"unknown estimand '{estimand}'; use one of {', '.join(ESTIMANDS)}. "
            "A real-world rate such as occupancy is not an estimand JevFish produces; "
            "it is what a calibration map converts an estimand into."
        )
    n = len(records)
    raw = [r["outcome_p"] for r in records]
    ps = apply_map(raw, calibration) if calibration is not None else raw
    calibrated = calibration is not None and not calibration.is_identity

    expected = sum(ps)
    variance = sum(p * (1 - p) for p in ps)
    mean_outcome = expected / n if n else 0.0

    if honest_half_width is not None:
        low = max(0.0, mean_outcome - honest_half_width) * n
        high = min(1.0, mean_outcome + honest_half_width) * n
        covers = "our own past errors on resolved outcomes"
    else:
        half = Z90 * math.sqrt(variance)
        low, high = max(0.0, expected - half), min(float(n), expected + half)
        covers = "sampling noise in the synthetic crowd only"

    hist = [0] * n_levels
    for r in records:
        hist[min(n_levels - 1, max(0, int(r["stance"] + 0.5)))] += 1

    out = {
        "n": n,
        "mean_outcome": mean_outcome,
        "expected_yes": expected,
        "variance": variance,
        "low": low,
        "high": high,
        "likely_yes": sum(p >= 0.5 for p in ps),
        "stance_mean": sum(r["stance"] for r in records) / n if n else 0.0,
        "stance_hist": hist,
        "estimand": estimand,
        "estimand_label": ESTIMANDS[estimand],
        "calibrated": calibrated,
        "interval_covers": covers,
    }
    if calibration is not None:
        out["mean_outcome_raw"] = sum(raw) / n if n else 0.0
        out["calibration_note"] = calibration.describe()
    return out


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
