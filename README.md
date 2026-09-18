# JevFish

**Ask how a population will react. JevFish builds a synthetic crowd, polls every single person, and tells you when the answer came from your prompt instead of from the world.**

[![Licence: AGPL v3](https://img.shields.io/badge/licence-AGPL--3.0--or--later-blue.svg)](LICENSE)
[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue.svg)](https://www.python.org/)
[![Install size 27 MB](https://img.shields.io/badge/install-27%20MB-brightgreen.svg)](#install)

## See it work before you sign up for anything

```bash
uv tool install "git+https://github.com/markiewee/jevfish#subdirectory=jevfish"
JEVFISH_FAKE_JUDGE=1 JEVFISH_FAKE_LLM=1 jevfish demo --platform lite
```

About ten seconds, no API keys, no account. It runs all five stages on deterministic
stand-in answers and prints a real report. Then, with keys:

```bash
jevfish serve
```

It opens in your browser and asks for the two keys on screen. No clone, no Node, no
Homebrew, 27 MB.

> `uvx jevfish` will be the install line once the PyPI name is published. The name is
> reserved but not yet claimed, so until then use the `git+` form above, which is the one
> tested on every commit.

## What it does

Give it a yes-or-no question and the documents behind it.

1. **Graph** reads the documents and pulls out the people, places and facts.
2. **Crowd** writes a segmented synthetic public plus the real named stakeholders.
3. **Simulate** lets them argue on a social feed, then polls every one of them.
4. **Report** gives you the number, the segments behind it, and what moved.
5. **Ask** lets you interview any single simulated person afterwards.

Every person's judgment comes from a typed decision model rather than free text, so polling
a thousand people costs cents instead of dollars.

## What it will not do

This section is above the screenshots on purpose.

- **The number is not a real-world rate.** It is an acceptance rate within the crowd you
  described, or a share of the option set you described. A listing with a 22 percent choice
  share can sit in a flat running at 89 percent occupancy, because occupancy is arrival
  volume over supply. JevFish names which quantity it is reporting, every time.
- **With no resolved outcomes on file it reports no interval worth trusting, and says so.**
  On our own backtest the naive interval was 11.5 times too narrow, and it got *narrower*
  as we added people, because sampling noise shrinks while model bias does not move. Record
  one real outcome with `jevfish anchor add` and it fits a calibration map. Nine outcomes
  buys a distribution-free 90 percent interval. Below four it prints the raw errors instead
  of inventing a range.
- **It checks whether it is quoting your own prompt.** On one real price ladder, the wording
  the frame generator wrote into the options gave an elasticity of -1.43 and said cut the
  rate, while neutral wording of the same length gave -0.09 and said raise it, on identical
  inputs. JevFish now refuses frames that describe one option in terms of another, and
  reports whether a comparison survives neutral wording.

The full write-up, including the experiments that failed, is in
[jevfish/docs/research/calibration-experiment.md](jevfish/docs/research/calibration-experiment.md).

## Install

Write `GH=git+https://github.com/markiewee/jevfish#subdirectory=jevfish` and then:

| | Command | Size |
|---|---|---|
| Just the predictor | `uv tool install "$GH"` | **27 MB** |
| With PDF seed upload | `uv tool install "jevfish[pdf] @ $GH"` | plus 5 MB |
| With the OASIS social feed | `uv tool install "jevfish[oasis] @ $GH"` | about 1 GB |
| Everything | `uv tool install "jevfish[all] @ $GH"` | about 1 GB |

Once the package is on PyPI these shorten to `uvx jevfish serve` and
`uv tool install 'jevfish[oasis]'`.

The OASIS extra is large because it pulls a machine-learning stack that the prediction
itself never uses. The default `lite` platform gives the same prediction without the
simulated social feed, so start there.

No `uv`? `curl -LsSf https://astral.sh/uv/install.sh | sh`, or use `pipx install jevfish`.

You need a [TypeSafe](https://console.typesafe.ai/settings/keys) key and any
OpenAI-compatible key (a free Google Gemini key works). The app asks for both on first run
and checks them before spending anything.

### Mac, without a terminal

Download `JevFish-macos.dmg` from the
[latest release](https://github.com/markiewee/jevfish/releases/latest), drag it to
Applications and open it. It is not code-signed, so the first launch needs System Settings,
Privacy and Security, Open Anyway. If that annoys you, `uvx jevfish serve` does the same
thing in one line with no dialog.

## Recording what actually happened

This is the part that turns a plausible number into a trustworthy one.

```bash
jevfish anchor add --question "..." --option "MYR 300" \
  --predicted 0.568 --actual 0.892 --n 801
jevfish anchor list
```

| Outcomes on file | What you get |
|---|---|
| 0 | an uncalibrated number, labelled as such |
| 1 | a fitted level shift |
| 5 | level plus scale, so the shape is corrected too |
| 9 | a distribution-free 90 percent interval |
| about 70 | near-optimal decisions, by the published evidence |

Anchors record the model version they were fitted against, because the same prompt gives
different answers across versions and a calibration must not silently transfer.

## Developing

```bash
git clone https://github.com/markiewee/jevfish
cd jevfish/jevfish
uv sync
uv run pytest -q          # 158 pass, 4 skip without the optional extras
uv sync --all-extras && uv run pytest -q   # 175 pass
```

Nothing in the test suite needs API keys. See [CONTRIBUTING.md](CONTRIBUTING.md).

## Credits and licence

JevFish is a rebuild of the five-stage pipeline from
**[MiroFish](https://github.com/666ghj/MiroFish)** by 666ghj, running on a different
decision engine.

**Modifications by Mark Wee, from 17 September 2026.** The `jevfish/` tree is new work. The
upstream `backend/`, `frontend/`, `locales/`, `scripts/` and `static/` trees are unmodified
and kept for reference. MiroFish's own README is preserved at
[docs/UPSTREAM-README.md](docs/UPSTREAM-README.md).

### Licence

JevFish is licensed **AGPL-3.0-or-later**, inherited from MiroFish. In plain terms:

- You may use, study, change and redistribute it.
- If you distribute a modified version you must release your changes under the same
  licence, with a dated notice of what you changed.
- **Section 13:** if you run a modified JevFish as a service that others reach over a
  network, you must offer those users the corresponding source of your version. A static
  replay of a finished run is not covered, because nothing is accepting requests.

Full text in [LICENSE](LICENSE). Third-party components are listed in
[THIRD_PARTY.md](THIRD_PARTY.md), and the copyright notice is in [NOTICE](NOTICE).
