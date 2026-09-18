"""The example project: made-up figures for a Singapore co-living brand."""

from __future__ import annotations

from .assets import example_seed

PATH = example_seed()
NAME = "Lazybee cleaning upgrade (example)"
QUESTION = ("If Lazybee adds weekly professional cleaning for S$100 more a month (example figure), "
            "will more Singapore renters book a viewing?")


def example() -> dict:
    return {"name": NAME, "requirement": QUESTION, "seed_text": PATH.read_text()}
