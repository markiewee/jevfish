"""Resolved outcomes, which are the only thing that makes calibration possible.

One anchor buys a level shift. About five buys level plus scale. Nine buys a 90 percent
conformal interval (four buys 80 percent, nineteen buys 95). About seventy buys
near-optimal decisions: the one published LLM-persona pricing system that beats a real
baseline reached 90 percent of optimal revenue on roughly 73 observations, about 3 per
product (arxiv.org/html/2606.16183v1).

Without anchors JevFish cannot state an accuracy, and should not pretend to.

`model_version` and `frame_hash` are not bookkeeping. The same prompt gives significantly
different distributions across model versions and across a few months, so a calibration
fitted on one version does not transfer to another. An anchor without its model version is
not reusable, and silently mixing versions in one fit is a way to produce a confidently
wrong number.

`estimand` must match between an anchor and the run being calibrated. The NoulQ path
yields `acceptance_rate_independent`, where each person is judged on their own. The ChoiceQ
path yields `choice_share_of_described_set`, where people are allocated across a fixed
option set. These are different quantities and one map cannot serve both.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

ESTIMANDS = (
    "acceptance_rate_independent",
    "choice_share_of_described_set",
    "event_probability",
)


@dataclass
class Anchor:
    question: str
    option: str
    predicted: float
    actual: float
    n: int
    estimand: str = "acceptance_rate_independent"
    model_version: str = ""
    frame_hash: str = ""
    note: str = ""
    recorded_at: str = field(default="")

    def __post_init__(self) -> None:
        for name in ("predicted", "actual"):
            value = float(getattr(self, name))
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{name} must be a probability in [0, 1], got {value}")
            setattr(self, name, value)
        if int(self.n) < 1:
            raise ValueError("n must be at least 1")
        if self.estimand not in ESTIMANDS:
            raise ValueError(
                f"unknown estimand '{self.estimand}'; use one of {', '.join(ESTIMANDS)}. "
                "A real-world rate such as occupancy is not an estimand, it is what a "
                "calibration map converts an estimand into."
            )
        if not self.recorded_at:
            self.recorded_at = datetime.now(timezone.utc).isoformat(timespec="seconds")

    @property
    def residual(self) -> float:
        """Absolute error, which is the non-conformity score split conformal needs."""
        return abs(self.actual - self.predicted)


def load_anchors(
    path: str | Path,
    question: str | None = None,
    *,
    estimand: str | None = None,
    model_version: str | None = None,
) -> list[Anchor]:
    """Anchors on disk, optionally narrowed. Narrow before fitting, always."""
    p = Path(path)
    if not p.exists():
        return []
    text = p.read_text().strip()
    if not text:
        return []
    out = [Anchor(**row) for row in json.loads(text)]
    return [
        a
        for a in out
        if (question is None or a.question == question)
        and (estimand is None or a.estimand == estimand)
        and (model_version is None or a.model_version == model_version)
    ]


def save_anchor(path: str | Path, anchor: Anchor) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    text = p.read_text().strip() if p.exists() else ""
    rows = json.loads(text) if text else []
    rows.append(asdict(anchor))
    p.write_text(json.dumps(rows, indent=1, ensure_ascii=False))
