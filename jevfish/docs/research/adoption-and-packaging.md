# JevFish: adoption and packaging research

Compiled 18 September 2026. Star counts and release figures pulled live from the GitHub REST API on that date. Local measurements were run on this machine against `/Users/mark/Desktop/claudine/projects/mirofish-jev`.

Two corrections to the brief before anything else, both measured:

1. The committed frontend is **332 KB**, not 39 MB. `jevfish/web/dist` is 3 tracked files (332 KB); the 39 MB is `jevfish/web/node_modules`, which is gitignored (`jevfish/.gitignore:6`). Only 34 files are tracked under `jevfish/web`.
2. The backend is **Flask**, not FastAPI. `jevfish/src/jevfish/api.py:1` reads `"""HTTP API (Flask). Serves the Vue app from web/dist at /."""`, and `pyproject.toml` lists `flask>=3.0`. This matters for the Vercel and PyInstaller sections below.

Emoji have been removed from the quoted README excerpts below. They are otherwise verbatim.

---

## Executive summary, ranked by impact per unit of effort

1. **The repo is a GitHub fork, so it does not exist in GitHub search.** `search/repositories?q=mirofish-jev` returns **0**; with `fork:true` it returns **1**. Forks are excluded from repository search and from topic pages by default. Leaving the fork network is self-service and free, and costs nothing here (0 stars, 0 issues, 0 child forks). Natural experiment in the same ecosystem: `nikmcfly/MiroFish-Offline` (detached, 10 topics) has **2,522 stars** while `EleutheroiEdge/mirofish-offline` (a fork, 0 topics) has **0**, on a byte-identical description.
2. **The repo still presents itself as MiroFish.** Description is MiroFish's Chinese-and-English tagline, the homepage field points at `mirofish.ai`, topics are **zero of a permitted 20**, and three badges plus a whole 18 KB workflow report upstream's star count. Every shared link unfurls as MiroFish. Fix: about 40 minutes.
3. **A one-line install already works and nobody knows.** Verified live: `uv` clones the public repo, finds the package via `git+https://github.com/markiewee/mirofish-jev#subdirectory=jevfish` and resolves all 140 packages, with the commit SHA pinned for free.
4. **But the wheel ships no UI.** `uv build --wheel` gives 34 files / 168,620 bytes and **no `web/dist`**, because `PACKAGE_ROOT = Path(__file__).resolve().parents[2]` (`config.py:19`) resolves to `lib/python3.12` once installed. I applied the two-line fix and verified the wheel then serves `GET /` at 200 with the real index and the 301 KB JS bundle.
5. **The install is 1.1 GB and about 940 MB of that is never used.** `camel-oasis==0.2.5` hard-depends on `sentence-transformers`, dragging torch 2.14.0 (553 MB), transformers (59 MB), scipy (82 MB), scikit-learn (34 MB), sympy (41 MB), plus `pre-commit` and `pytest` as runtime deps. Measured: **1.1 GB / 161 packages** today, **118 MB / 59** without `camel-oasis`, **66 MB** if `pymupdf` also goes. Cold install drops from 27.4 s to 4.4 s.
6. **PyMuPDF is itself AGPL** ("Dual Licensed, GNU AFFERO GPL 3.0 or Artifex Commercial License"), used in exactly one already-lazy import at `service.py:59`. So `jevfish/` carries a copyleft obligation independent of MiroFish, and a hosted demo triggers AGPL Section 13 through it. Swapping to `pypdf` (BSD-3-Clause) is five lines, removes that obligation and saves 54 MB. Best value-per-line change in the report.
7. **The keyless demo already exists and is undiscoverable.** With `JEVFISH_FAKE_JUDGE=1 JEVFISH_FAKE_LLM=1` the full five-stage pipeline runs in about ten seconds with no API keys and returns a real calibrated prediction with a 90% range. No competitor in this market lets anyone see output without a signup. This belongs as the first command in the README.
8. **The unsigned `.app` is the weakest part of the funnel, and signing it would certify nothing.** `spctl` reports `rejected, source=no usable signature`. The right-click-Open bypass was removed in macOS 15.0, so the only path is System Settings, Open Anyway, which needs an admin password and expires after about an hour. Notarization costs USD 99/yr and would seal a 148 KB shell around 1 GB downloaded after launch. Switching the ZIP to a DMG is near-free and strictly better today.
9. **The README buries the install and the numbers.** First fenced block is at **line 112** against a 46-repo median of 60 and Ollama's 15, the brand ratio is 37 MiroFish mentions to 4 JevFish, and 44 of 46 high-star adjacent repos put media at a median of line 3. Target hero GIF: 300 to 900 KB, the band lazygit (665 KB) and zoxide (627 KB) sit in.
10. **The name is clear, the vocabulary is not.** `jevfish` is free on PyPI, npm and GitHub (0 repos, 0 users), and all four of `jevfish.com/.ai/.dev/.app` have no DNS records. But the README uses none of the words the audience types: silicon sampling, generative agents, synthetic respondents, AI focus group, social simulation.

---

## 1. Comparable projects and what their repos look like

### 1.1 Live figures, 18 September 2026

| Repo | Stars | Forks | Lang | Licence | README lines | First install command at line | Position |
|---|---|---|---|---|---|---|---|
| ollama/ollama | 181,191 | 17,922 | Go | MIT | 356 | 16 | 4% |
| langflow-ai/langflow | 154,960 | | Python | MIT | | | |
| open-webui/open-webui | 152,442 | 22,304 | Python | custom | 261 | 116 | 44% |
| AUTOMATIC1111/stable-diffusion-webui | 164,994 | 30,938 | Python | AGPL-3.0 | 205 | 154 | 75% |
| Comfy-Org/ComfyUI | 133,718 | 15,829 | Python | GPL-3.0 | 437 | 185 | 42% |
| tauri-apps/tauri | 111,148 | | Rust | Apache-2.0 | | | |
| astral-sh/uv | 89,946 | 3,591 | Rust | Apache-2.0 | 326 | 50 | 15% |
| **666ghj/MiroFish (upstream)** | **73,886** | **11,362** | Python | **AGPL-3.0** | 203 | 172 | **84%** |
| openinterpreter/openinterpreter | 68,378 | 5,884 | Rust | Apache-2.0 | 147 | 34 | 23% |
| Mintplex-Labs/anything-llm | 66,164 | 7,348 | JS | MIT | 326 | none (download button) | |
| lllyasviel/Fooocus | 53,098 | 8,612 | Python | GPL-3.0 | 486 | 132 | 27% |
| Aider-AI/aider | 49,036 | | Python | Apache-2.0 | 180 | none (docs link) | |
| oobabooga/textgen | 47,681 | | Python | AGPL-3.0 | | | |
| janhq/jan | 44,517 | 3,032 | TS | custom | 204 | 114 | 55% |
| danny-avila/LibreChat | 44,264 | 9,099 | TS | MIT | 264 | none | |
| khoj-ai/khoj | 37,399 | 2,484 | Python | **AGPL-3.0** | **107** | none (docs link) | |
| ItzCrazyKns/Vane (ex-Perplexica) | 36,867 | 4,092 | TS | MIT | 251 | 71 | 28% |
| Genesis-Embodied-AI/genesis-world | 29,963 | | Python | Apache-2.0 | | | |
| assafelovic/gpt-researcher | 29,503 | 4,014 | Python | Apache-2.0 | 369 | 102 | 27% |
| marimo-team/marimo | 22,821 | 1,275 | Python | Apache-2.0 | 350 | 60 | 17% |
| joonspk-research/generative_agents | 22,121 | 3,107 | - | Apache-2.0 | 141 | 45 | 31% |
| camel-ai/camel | 17,741 | 2,083 | Python | Apache-2.0 | | | |
| Nuitka/Nuitka | 15,129 | | Python | AGPL-3.0 | | | |
| SakanaAI/AI-Scientist | 14,574 | 2,056 | Notebook | custom | | | |
| pyinstaller/pyinstaller | 13,095 | | Python | custom | | | |
| pypa/pipx | 12,967 | | Python | MIT | | | |
| simonw/llm | 12,526 | | Python | Apache-2.0 | | | |
| darrenburns/posting | 12,424 | | Python | Apache-2.0 | 60 | 34 | 56% |
| **microsoft/TinyTroupe** | **7,571** | | Notebook | MIT | 844 | 237 | 28% |
| tconbeer/harlequin | 6,403 | | Python | MIT | 179 | 23 | 12% |
| **camel-ai/oasis** | **5,156** | 631 | Python | Apache-2.0 | 369 | 115 | 31% |
| OpenBMB/AgentVerse | 5,132 | | JS | Apache-2.0 | | | |
| mesa/mesa | 3,846 | 1,313 | Python | Apache-2.0 | 142 | 37 | 26% |
| beeware/briefcase | 3,348 | | Python | BSD-3 | | | |
| google-deepmind/concordia | 1,709 | 368 | Python | Apache-2.0 | 187 | 80 | 42% |
| tsinghua-fib-lab/AgentSociety | 1,293 | | Python | Apache-2.0 | | | |
| AgentTorch/AgentTorch | 649 | 98 | Notebook | **AGPL-3.0** | 127 | none | |
| sotopia-lab/sotopia | 332 | | Python | MIT | | | |

LM Studio is closed source and has no public repo, so it is out of scope for README study; it is an Electron (reportedly now Tauri) signed installer distributed from lmstudio.ai.

Two patterns worth naming. The projects with the highest adoption relative to their niche put the install command in the **top 20% of the README** (Ollama 4%, harlequin 12%, uv 15%, marimo 17%). The upstream MiroFish, despite 73,886 stars, buries its first command at **84%**, which tells you stars came from a trending-list spike and Chinese social distribution, not from README conversion. Note also that MiroFish's Discord has only **800 members** (65 online) against 73,886 stars: a 0.011 ratio. Compare ComfyUI Discord at **60,973** members and Open WebUI at **35,077**. Stars are not users.

### 1.2 The most instructive READMEs, first 30 lines

**Ollama, 181,191 stars. The gold standard for "download and it works".** First install command at line 16 of 356.

```
<p align="center">
  <a href="https://ollama.com">
    <img src="https://github.com/ollama/ollama/assets/3325447/0d0b44e2-8f4a-4e99-9b52-a5c1c741c8f7" alt="ollama" width="200"/>
  </a>
</p>

# Ollama

Start building with open models.

## Download

### macOS

```shell
curl -fsSL https://ollama.com/install.sh | sh
```

or [download manually](https://ollama.com/download/Ollama.dmg)

### Windows

```shell
irm https://ollama.com/install.ps1 | iex
```

or [download manually](https://ollama.com/download/OllamaSetup.exe)

### Linux

```shell
curl -fsSL https://ollama.com/install.sh | sh
```

Nine lines of prose total before the heading `## Download`. One sentence of positioning ("Start building with open models"). No badges at all. Both a script and a manual download per platform. Release evidence that this works: `Ollama-darwin.zip` 188 MB with **59,719 downloads** and `OllamaSetup.exe` 1,497 MB with **58,282 downloads** on the latest tag alone, while the bare `install.sh` asset shows 9,110.

**nikmcfly/MiroFish-Offline, 2,522 stars. The single most relevant comparable: a MiroFish derivative that got adopted.** First install command at line 56 of 205.

```
<div align="center">

<img src="./static/image/mirofish-offline-banner.png" alt="MiroFish Offline" width="100%"/>

# MiroFish-Offline

**Fully local fork of [MiroFish](https://github.com/666ghj/MiroFish) - no cloud APIs required. English UI.**

*A multi-agent swarm intelligence engine that simulates public opinion, market sentiment, and social dynamics. Entirely on your hardware.*

[![GitHub Stars](https://img.shields.io/github/stars/nikmcfly/MiroFish-Offline?style=flat-square&color=DAA520)](https://github.com/nikmcfly/MiroFish-Offline/stargazers)
[![GitHub Forks](https://img.shields.io/github/forks/nikmcfly/MiroFish-Offline?style=flat-square)](https://github.com/nikmcfly/MiroFish-Offline/network)
[![Docker](https://img.shields.io/badge/Docker-Build-2496ED?style=flat-square&logo=docker&logoColor=white)](https://hub.docker.com/)
[![License: AGPL-3.0](https://img.shields.io/badge/License-AGPL--3.0-blue?style=flat-square)](./LICENSE)

</div>

## What is this?

MiroFish is a multi-agent simulation engine: upload any document (press release, policy draft, financial report), and it generates hundreds of AI agents with unique personalities that simulate the public reaction on social media. Posts, arguments, opinion shifts, hour by hour.

The [original MiroFish](https://github.com/666ghj/MiroFish) was built for the Chinese market (Chinese UI, Zep Cloud for knowledge graphs, DashScope API). This fork makes it **fully local and fully English**:

| Original MiroFish | MiroFish-Offline |
|---|---|
| Chinese UI | **English UI** (1,000+ strings translated) |
| Zep Cloud (graph memory) | **Neo4j Community Edition 5.15** |
| DashScope / OpenAI API (LLM) | **Ollama** (qwen2.5, llama3, etc.) |
| Zep Cloud embeddings | **nomic-embed-text** via Ollama |
| Cloud API keys required | **Zero cloud dependencies** |
```

The structure is a template JevFish can copy line for line: banner, H1, one bold line saying "fork of X, and here is the one thing that is different", one italic line saying what the thing is, four badges including an AGPL badge, then a two-column **original versus this fork** table before any install instruction. Its attribution section (line 197) reads:

```
## Credits & Attribution

This is a modified fork of [MiroFish](https://github.com/666ghj/MiroFish) by [666ghj](https://github.com/666ghj), originally supported by [Shanda Group](https://www.shanda.com/). The simulation engine is powered by [OASIS](https://github.com/camel-ai/oasis) from the CAMEL-AI team.
```

**khoj-ai/khoj, 37,399 stars. AGPL-3.0, Python, local-first, hosted demo: the closest legal and architectural analog.** 107 lines, and **no install command in the README at all**.

```
<p align="center"><img src="https://assets.khoj.dev/khoj-logo-sideways-1200x540.png" width="230" alt="Khoj Logo"></p>

<div align="center">

[![test](https://github.com/khoj-ai/khoj/actions/workflows/test.yml/badge.svg)](https://github.com/khoj-ai/khoj/actions/workflows/test.yml)
[![docker](https://github.com/khoj-ai/khoj/actions/workflows/dockerize.yml/badge.svg)](https://github.com/khoj-ai/khoj/pkgs/container/khoj)
[![pypi](https://github.com/khoj-ai/khoj/actions/workflows/pypi.yml/badge.svg)](https://pypi.org/project/khoj/)
[![discord](https://img.shields.io/discord/1112065956647284756?style=plastic&label=discord)](https://discord.gg/BDgyabRM6e)

</div>

<div align="center">
<b>Your AI second brain</b>
</div>

<br />

<div align="center">

[Docs](https://docs.khoj.dev)
<span>&nbsp;&nbsp;•&nbsp;&nbsp;</span>
[Web](https://khoj.dev)
<span>&nbsp;&nbsp;•&nbsp;&nbsp;</span>
[App](https://app.khoj.dev)
<span>&nbsp;&nbsp;•&nbsp;&nbsp;</span>
[Discord](https://discord.gg/BDgyabRM6e)
<span>&nbsp;&nbsp;•&nbsp;&nbsp;</span>
[Blog](https://blog.khoj.dev)

</div>
```

Khoj's whole self-host section is three lines: `## Self-Host` / "To get started with self-hosting Khoj, [read the docs](https://docs.khoj.dev/get-started/setup)." The README's job is reduced to: logo, three CI badges that prove the thing builds, one-line positioning, five links, a 19.2 MB demo GIF, a feature bullet list, an FAQ. This is the right model if you intend to run a docs site. It is the wrong model if you do not, because the README then dead-ends.

**Open WebUI, 152,442 stars. The counter-example on badges.** Nine shields badges before a single word of prose, first install at line 116 of 261, and the hero is a **281 KB PNG at the repo root** (`./demo.png`), not a GIF.

```
# Open WebUI

![GitHub stars](https://img.shields.io/github/stars/open-webui/open-webui?style=social)
![GitHub forks](https://img.shields.io/github/forks/open-webui/open-webui?style=social)
![GitHub watchers](https://img.shields.io/github/watchers/open-webui/open-webui?style=social)
![GitHub repo size](https://img.shields.io/github/repo-size/open-webui/open-webui)
![GitHub language count](https://img.shields.io/github/languages/count/open-webui/open-webui)
![GitHub top language](https://img.shields.io/github/languages/top/open-webui/open-webui)
![GitHub last commit](https://img.shields.io/github/last-commit/open-webui/open-webui?color=red)
[![Discord](https://img.shields.io/badge/Discord-Open_WebUI-blue?logo=discord&logoColor=white)](https://discord.gg/5rJgQTnV4s)
[![](https://img.shields.io/static/v1?label=Sponsor&message=%E2%9D%A4&logo=GitHub&color=%23fe8e86)](https://github.com/sponsors/open-webui)

Open WebUI is **a home for AI**, a self-hosted AI platform that's **[extensible](...)**, **[feature-rich](...)**, user-friendly, and built to run **[entirely offline](...)**.

Passionate about open-source AI? [Join our team →](https://careers.openwebui.com/)

![Open WebUI Demo](./demo.png)
```

Note that six of those nine badges are vanity metrics (repo size, language count, top language) that carry no information for a visitor. Do not copy this part.

**microsoft/TinyTroupe, 7,571 stars. The closest project by subject matter: LLM persona simulation for business insight.** 844 lines, first install at 237. Its opening is worth reading because it is the vocabulary JevFish's audience already uses:

```
# TinyTroupe
[![Core Tests](.../core-tests.yml/badge.svg)](...)

*LLM-powered multiagent persona simulation for imagination enhancement and business insights.*

<p align="center">
  <img src="./docs/tinytroupe_stage.png" alt="A tiny office with tiny people doing some tiny jobs.">
</p>

>[!TIP]
>**New Paper Released!** Check out our [TinyTroupe paper (preprint)](https://arxiv.org/abs/2507.09788) ...

*TinyTroupe* is an experimental Python library that allows the **simulation** of people with specific personalities, interests, and goals. ... Here are some application ideas to **enhance human imagination**:

  - **Advertisement:** TinyTroupe can **evaluate digital ads (e.g., Bing Ads)** offline with a simulated audience before spending money on them!
  - **Software Testing:** TinyTroupe can **provide test input** to systems ...
  - **Training and exploratory data:** TinyTroupe can generate realistic **synthetic data** ...
  - **Product and project management:** TinyTroupe can **read project or product proposals** and **give feedback** from the perspective of **specific personas** ...
  - **Brainstorming:** TinyTroupe can simulate **focus groups** and deliver great product feedback at a fraction of the cost!
```

Five named use cases in five bullets, each with a concrete example and a named product. That is what JevFish's README is missing: it explains the mechanism (five stages, seven typed Jev questions) and never says what a buyer would use it for.

**MiroShark, 1,451 stars. An AGPL MiroFish derivative that is purely a marketing exercise, and it works.** First install at line 57 of 184. Its hero is an **11,393-byte animated SVG** with keyword-loaded alt text:

```
<p align="center">
  <img src="../docs/images/hero-animated.svg" alt="MiroShark - Simulate anything for $1 in under 10 minutes with 100+ grounded agents. The pipeline flows input → build world → swarm → report. Keywords: multi-agent simulation, social simulation, swarm intelligence, agent-based modeling, LLM agents, prediction market, scenario testing." width="100%" />
</p>

<h1 align="center">Simulate <em>anything.</em></h1>

<p align="center">
  <b>$1</b> · per simulation &nbsp;·&nbsp; <b>10 min</b> · first result &nbsp;·&nbsp; <b>100+</b> · grounded agents
</p>
```

Three numbers above the fold: price per run, time to first result, agent count. JevFish already has the equivalent numbers and buries them in prose at line 22 of `jevfish/README.md` ("about US$0.00006 a turn, and it takes about 1 second from Singapore"). Those belong above the fold: **$0.00006 per agent turn, about 1 second per turn**.

### 1.3 The fork versus detached natural experiment

This is the most important finding in the report because it is free to act on and the evidence is unusually clean.

Two repositories, byte-identical description ("Offline multi-agent simulation & prediction engine. English fork of MiroFish with Neo4j + Ollama local stack."):

| Repo | `fork` flag | Topics | Stars |
|---|---|---|---|
| `nikmcfly/MiroFish-Offline` | false | 10 | **2,522** |
| `EleutheroiEdge/mirofish-offline` | true | 0 | **0** |

Across the top 40 MiroFish derivatives by stars, **36 are detached and 4 are forks**. The highest-starred fork in the whole set is `ByeongkiJeong/MiroFish-Ko` at 222 stars; the highest-starred detached derivative is 2,522. Across the first 100 results, medians are close (forks 12, detached 9), so the effect is not on the median repo, it is on the ceiling: a fork cannot break out.

Other derivatives to note, all detached: `MiroShark/MiroShark` 1,451, `jangles-byte/Pythia` 1,102, `D2I-CUHKSZ/MicroWorld` 1,039, `SCTY-Inc/mirofish-cli` 310, `tt-a1i/MiroFish-local` 152, `nativ3ai/hermes-geopolitical-market-sim` 130, `ChinmayShringi/MicroFish-En` 118, `luis212/NovaShoal-Swarm-Sim` 117. The derivative market is real, crowded, and JevFish's differentiator (typed calibrated decisions rather than parsed free text) is genuinely unoccupied in it.

### 1.4 Distribution mechanics of the comparables

Latest-release assets and download counts, live from the API:

| Project | Assets | Sizes | Downloads on latest tag |
|---|---|---|---|
| ollama/ollama v0.34.2 | 17 | `Ollama-darwin.zip` 188 MB, `Ollama.dmg` 188 MB, `OllamaSetup.exe` 1,497 MB | zip 59,719; exe 58,282; dmg 2,060; `install.sh` 9,110 |
| janhq/jan v0.8.4 | 11 | `Jan_0.8.4_universal.dmg` 97 MB, `jan-mac-universal-0.8.4.zip` 97 MB, `Jan_0.8.4_x64-setup.exe` 55 MB | exe 91,746; mac zip 77,361; dmg 19,630; `latest.json` 313,061 (auto-updater polling) |
| Comfy-Org/ComfyUI v0.36.0 | 4 | `ComfyUI_windows_portable_nvidia.7z` 1,828 MB | nvidia 29,088 |
| Mintplex-Labs/anything-llm v1.16.1 | 7 | `AnythingLLMDesktop.exe` 391 MB, `AnythingLLMDesktop-Silicon.dmg` 522 MB | exe 9,111; AppImage 1,178; Silicon dmg 613 |
| khoj-ai/khoj 2.0.0-beta.28 | 3 | Obsidian plugin files only (`main.js`, `manifest.json`, `styles.css`) | 7,264 / 7,858 / 6,989 |
| marimo-team/marimo 0.24.2 | 0 | none (PyPI only) | |
| **666ghj/MiroFish v0.1.2** | **0** | **none** | |

Three lessons. Windows is where the download volume is (Jan: 91,746 exe against 19,630 dmg plus 77,361 mac zip; Ollama: 58,282 exe against 59,719 mac zip, so roughly even). `latest.json` at 313,061 downloads is Jan's Tauri auto-updater and is the clearest signal of real retained users in the whole table. And a project can be enormous with zero release assets (marimo, MiroFish) if the install path is a package manager.

### 1.5 Docs sites, detected by fetching each site

| Project | Docs URL | Generator | Host |
|---|---|---|---|
| astral-sh/uv | docs.astral.sh/uv | **Material for MkDocs** | Cloudflare |
| marimo-team/marimo | docs.marimo.io | **MkDocs** | Vercel |
| khoj-ai/khoj | docs.khoj.dev | **Docusaurus** | GitHub Pages |
| open-webui/open-webui | docs.openwebui.com | **Docusaurus** | GitHub Pages |
| camel-ai/oasis | docs.oasis.camel-ai.org | **Mintlify** | Vercel |
| Comfy-Org/ComfyUI | docs.comfy.org | **Mintlify + Starlight** | Vercel |
| mesa/mesa | mesa.readthedocs.io | **Sphinx** | ReadTheDocs |

Two free-and-good defaults emerge: Material for MkDocs (what uv uses, single `mkdocs.yml`, one Action) and Docusaurus (what both AGPL/Python local-first projects use, on GitHub Pages). MiroFish has **no docs site** (`has_pages: false`), which is part of why its README is 203 lines of everything.

### 1.6 Hosted demos

Upstream MiroFish has one, and it is the cheapest possible version: `https://666ghj.github.io/mirofish-demo/` is a **Vue SPA on GitHub Pages** (confirmed: `server: GitHub.com`, 1,359-byte `index.html`, module script at `/mirofish-demo/assets/index-BnqFA15a.js`, no API calls, Cloudflare Insights beacon). It is a static replay of a pre-computed simulation. No backend, no API keys, no bill, and no AGPL Section 13 network-interaction exposure.

CAMEL-AI runs interactive Hugging Face Spaces instead (`huggingface.co/spaces/camel-ai/agent-trust-Trust-Game-Demo`, `camel-ai/camel-agents`), and the camel-agents Space requires the **visitor** to paste their own API key, which is the pattern that avoids paying for strangers' inference.

Note that the large self-hosted projects mostly do not run official hosted demos: LibreChat and AnythingLLM only have third-party community mirrors on HF Spaces. They lead with Docker.

---

## 2. The "download and it works" problem for Python apps

### 2.0 JevFish's measured baseline

| Check | Result |
|---|---|
| `JevFish.app` size | 148 KB, 3 files (`Info.plist`, `MacOS/JevFish`, `Resources/AppIcon.icns`) |
| `codesign -dv --verbose=4` | `code object is not signed at all` |
| `spctl -a -vvv` | `rejected`, `source=no usable signature` |
| `.venv` | **1.1 GB**, 161 packages |
| `uv build --wheel` output | 34 files, **168,620 bytes**, **no `web/dist`** |
| Tracked files under `jevfish/web` | 34 (dist is 332 KB) |

So today the `.app` is a script-only wrapper with no signature, which is both the worst case for Gatekeeper and the hardest thing to notarize meaningfully.

### 2.1 The dependency tree is the biggest single lever

Traced from `jevfish/uv.lock`:

```
camel-oasis==0.2.5
  -> sentence-transformers==3.0.0
       -> torch==2.14.0           553 MB
       -> transformers==4.57.6     59 MB
       -> scikit-learn==1.9.1      34 MB
       -> scipy==1.18.1            82 MB
       -> sympy (via torch)        41 MB
  -> pandas, pillow, neo4j, cairocffi, igraph, slack-sdk,
     unstructured (-> lxml 21 MB), prance, openapi-spec-validator,
     requests-oauthlib, AND pre-commit + pytest + pytest-asyncio
```

`camel-oasis` ships dev tools (`pre-commit`, `pytest`) as runtime dependencies, which is a packaging bug on their side that you inherit.

Measured by actually installing each variant into a fresh venv on this machine:

| Variant | Size | Packages |
|---|---|---|
| Current `jevfish/.venv` | **1.1 GB** | 161 |
| Drop `camel-oasis` (keep `camel-ai`) | **118 MB** | 59 |
| Drop `camel-oasis`, swap `pymupdf` (54 MB) for `pypdf` | **66 MB** | |
| Drop `camel-ai` too (Jev + LLM + Flask + pypdf) | **27 MB** | |

JevFish already has "a fast in-memory platform" as an alternative to OASIS (`jevfish/README.md`, stage 3). So `camel-oasis` belongs in `[project.optional-dependencies] oasis = ["camel-oasis==0.2.5"]`, imported lazily, and the default install drops from 1.1 GB to 118 MB (17x if pymupdf also goes). That single change does more for the download experience than any packaging technology in this section.

### 2.2 `uv tool install` and `uvx`: this already works, verified live

I ran a real resolution against the live public repo:

```
$ echo 'jevfish @ git+https://github.com/markiewee/mirofish-jev#subdirectory=jevfish' > gittest.txt
$ uv pip compile gittest.txt -o gitresolved.txt --python-version 3.12
resolved packages: 140
jevfish @ git+https://github.com/markiewee/mirofish-jev@77bbedc7ff62ac125953de0c89e79b25996fb3f0#subdirectory=jevfish
torch==2.14.0
camel-oasis==0.2.5
typesafe-sdk==0.6.0
```

uv cloned the repo, found the `jevfish` package inside the `jevfish/` subdirectory via the `#subdirectory=` fragment, and pinned the resolved commit SHA for free. So these commands work **today**:

```
uv tool install "git+https://github.com/markiewee/mirofish-jev#subdirectory=jevfish"
jevfish serve

# or, without installing anything permanently
uvx --from "git+https://github.com/markiewee/mirofish-jev#subdirectory=jevfish" jevfish serve
```

`pyproject.toml` already declares `[project.scripts] jevfish = "jevfish.cli:main"` and `cli.py` already has a `serve` subcommand that prints `Open http://{host}:{port}`.

**Three defects stop this being the headline install path.** All are small:

1. **`web/dist` is not in the wheel.** `uv build --wheel` yields 34 files and no web assets. `api.py:20` does `WEB_DIST = PACKAGE_ROOT / "web" / "dist"`, and `config.py:19` sets `PACKAGE_ROOT = Path(__file__).resolve().parents[2]`. Installed into site-packages, `parents[2]` is `lib/python3.12`, so the UI 404s. Fix: move the built assets to `src/jevfish/web/dist/` and resolve them relative to the module, and let the uv build backend ship them.
2. **`.env` and `data/` resolve to the same wrong place** (`config.py:28`, `config.py:91`). Fix: `platformdirs.user_data_dir("JevFish")` with the current path kept as a fallback when running from a checkout.
3. **Nothing opens a browser.** `grep -rn "webbrowser" src/` returns nothing. `cmd_serve` prints a URL and blocks. Fix: after the port binds, `webbrowser.open(f"http://127.0.0.1:{port}")`, plus a `--headless` flag, which is exactly what marimo does.

Install syntax reference, from https://docs.astral.sh/uv/guides/tools/:

```
uv tool install ruff
uvx ruff                                    # ephemeral, = uv tool run ruff
uvx --from httpie http                      # command name differs from package
uvx --from git+https://github.com/httpie/cli httpie
uvx --from git+https://github.com/httpie/cli@v3.0.0 httpie
```

How a user gets uv (https://docs.astral.sh/uv/getting-started/installation/):

```
curl -LsSf https://astral.sh/uv/install.sh | sh
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
brew install uv
winget install --id=astral-sh.uv -e
```

uv 0.12.16 asset sizes: `uv-aarch64-apple-darwin.tar.gz` 16 MB, `uv-x86_64-apple-darwin.tar.gz` 19 MB, `uv-x86_64-pc-windows-msvc.zip` 16 MB. No Python is needed beforehand; uv fetches its own managed CPython. That last fact is the whole reason to prefer uv over pipx.

Measured install speeds on a subagent's run of the same machine class: `fastapi uvicorn` cold with `--no-cache` was 1.05 s for a 10 MB venv; an eight-package scientific set was 15.22 s for 305 MB. Extrapolated, a 1.1 GB venv is roughly 45 to 60 s on a good connection, and a 118 MB venv is roughly 6 to 10 s.

**Who distributes this way:** Aider-AI/aider (49,036 stars) whose `curl -LsSf https://aider.chat/install.sh | sh` is uv's own installer plus one `uv tool install --python python3.12 aider-chat` line; marimo (22,821) `uvx marimo edit --sandbox`; simonw/llm (12,526) `uv tool install llm`; darrenburns/posting (12,424) `uv tool install --python 3.13 posting`; tconbeer/harlequin (6,403); ml-explore/mlx-lm (7,044); simonw/files-to-prompt (2,790) `uvx files-to-prompt`.

Friction for a non-technical Mac user: open Terminal, paste two lines. No Gatekeeper dialog, no admin password, no "damaged" scare. The cliff is Terminal itself. Cost: **USD 0**, roughly 4 to 8 hours including a hosted `install.sh`.

### 2.3 pipx

Same shapes, smaller reach:

```
pipx install jevfish
pipx run jevfish
pipx install --spec "git+https://github.com/markiewee/mirofish-jev#subdirectory=jevfish" jevfish
pipx install pipx[uv]      # uv-backed venv creation, same CLI
```

pypa/pipx has **12,967 stars** against uv's 89,946 and is actively maintained (last push 2026-09-18), so it is superseded in practice rather than legacy. pipx's own comparison page (https://pipx.pypa.io/latest/explanation/comparisons.html) frames them as peers and names the real difference: "uv tool ships a smaller per-tool surface, then reuses the rest of uv for free: managed Python, content-addressed cache, lockfiles, PEP 723 script handling." The decisive gap for a non-technical installer is that pipx needs a working Python 3 first. Document it as a one-line fallback; about 30 minutes of README.

### 2.4 Frozen bundles: PyInstaller, Nuitka, Briefcase, py2app

| Tool | Stars | Reported sizes | Notes |
|---|---|---|---|
| pyinstaller/pyinstaller | 13,095 | FastAPI + uvicorn exe roughly 35 to 40 MB on Windows (https://aiechoes.substack.com/p/building-production-ready-desktop); a plain PyQt5 app hitting 800 MB is "a common experience", trimmable under 200 MB (https://www.pythonguis.com/faq/pyinstaller-on-macos-frustration/) | onefile extracts to temp on every launch, slow cold start |
| Nuitka/Nuitka | 15,129 (AGPL-3.0) | a TensorFlow app bundle measured **2.84 GB**, `_pywrap_tensorflow_internal.so` alone 1.3 GB (https://github.com/Nuitka/Nuitka/issues/2359) | compiles to C, longest build times |
| beeware/briefcase | 3,348 | default scaffold roughly 190 MB on macOS | signs and notarizes for you |
| ronaldoussoren/py2app | **425** | comparable to PyInstaller | macOS only, tiny community, maintenance risk |

Known breakage, all of which JevFish would hit:

- **Dynamic imports.** Static analysis cannot see `importlib.import_module()`, `__import__()`, `exec()`. Flask and Werkzeug are milder than uvicorn here, but `camel-ai` and `mcp` both dispatch dynamically. Diagnose with `--debug=imports` (https://pyinstaller.org/en/stable/when-things-go-wrong.html).
- **`importlib.metadata`.** `importlib.metadata.version("pkg")` raises `PackageNotFoundError` in a frozen app; needs a hook with `from PyInstaller.utils.hooks import copy_metadata` (https://pyinstaller.org/en/stable/hooks.html, https://github.com/pyinstaller/pyinstaller/issues/5814). Anything resolving entry points at runtime breaks here.
- **Data files.** `web/dist` has to go in via `--add-data` and be resolved at runtime through `sys._MEIPASS`, not `__file__`. This is the same bug class as defect 1 in section 2.2.
- **Hardened runtime collision.** `codesign --deep -s $ID -o runtime` on a PyInstaller macOS binary has crashed at startup with `MemoryError` and `[6159] Failed to execute script pyiboot01_bootstrap` in `ctypes/__init__.py line 273 in _reset_cache` (https://github.com/pyinstaller/pyinstaller/issues/4629). Hardened runtime is mandatory for notarization, so this is on the critical path.

Who actually ships PyInstaller builds: **spesmilo/electrum** (8,591 stars), whose own docs note that from macOS 10.15 the output "also need to be notarized by Apple's central server" (https://github.com/spesmilo/electrum/blob/master/contrib/osx/README.md); **Ultimaker/Cura** (7,041), which produces both the macOS DMG and the Linux AppImage. Both are single-binary GUI apps, the easier case.

For JevFish, freezing a Flask app plus a static bundle plus a 1.1 GB tree realistically lands at 300 to 700 MB per platform after trimming, at an estimated **30 to 60 hours**, and you still owe Apple USD 99. Skip until there is demand pull. Note also: cut the tree to 66 MB first (section 2.1) and the frozen bundle becomes a far more tractable 90 to 150 MB.

### 2.5 macOS signing and notarization, since our `.app` is unsigned

**What the user sees on macOS 15 Sequoia and macOS 26 Tahoe.** Apple's own page (https://support.apple.com/en-us/102445) lists the dialog **"Apple cannot check 'Example App' for malware"** with only **Move to Trash** and **Done** as buttons, and describes exactly one recovery path: System Settings, Privacy and Security, scroll to Security, **Open Anyway**, confirm again. The page does not mention right-clicking at all.

**The right-click Open workaround is gone.** Removed in macOS 15.0: "Before macOS 15.0, you could ctrl+right-click an unsigned application and force it to run. In macOS 15.0, Apple removed the ability to do this" (https://www.osnews.com/story/141055/). Confirmed at announcement (https://www.idownloadblog.com/2024/08/07/apple-macos-sequoia-gatekeeper-change-install-unsigned-apps-mac/) and still gone in Tahoe (https://swissmacuser.ch/fix-macos-tahoe-app-is-damaged-and-cant-be-opened-move-trash/).

Two extra cruelties: the Open Anyway button "is available for about an hour after you try to open the app" (https://support.apple.com/en-ca/guide/mac-help/mh40617/mac), and it requires an administrator username and password. On a managed or corporate Mac that is a hard stop.

The current README's instruction ("If macOS blocks the app because you downloaded the ZIP, open System Settings, Privacy & Security, and click Open Anyway") is factually correct for 15 and 26, which is good. What it understates is that this is a six-step, password-gated, one-hour-windowed flow whose default button is Move to Trash.

**Which message means what:**

| Message | Trigger |
|---|---|
| "unidentified developer" | Signed, but not with a Developer ID traceable to Apple, or not notarized |
| "Apple could not verify / cannot check for malware" | Quarantined with no notarization ticket. This is our case on Sequoia and Tahoe |
| "is damaged and can't be opened" | Quarantine plus failed signature or ticket validation; also the standard Apple-silicon result for a broken or absent arm64 signature (https://blog.margrop.net/en/post/macos-gatekeeper-unsigned-app-fix/) |

All three run on the `com.apple.quarantine` xattr, applied by browsers and inherited by everything extracted from a quarantined ZIP. `xattr -dr com.apple.quarantine /path/to/JevFish.app` clears it and the app launches silently. Do not put that in a README: it trains users to defeat Gatekeeper on request.

**The notarization flow.** Cost: **Apple Developer Program USD 99 per year** (https://developer.apple.com/help/account/membership/program-enrollment/). Certificate: **Developer ID Application**, issued only to Program members (https://developer.apple.com/support/developer-id). **There is no free notarization path**, because notarization is gated on a Developer ID which is gated on the paid membership.

```
security find-identity -v -p codesigning

# sign bottom up; do NOT use --deep, it is unreliable
codesign -f -s "$ID" -o runtime JevFish.app/Contents/MacOS/JevFish
codesign -f -s "$ID" -o runtime JevFish.app

xcrun notarytool store-credentials jevfish-profile \
  --team-id XXXXXXXXXX --apple-id "you@example.com" --password "APP_SPECIFIC_PASSWORD"

ditto -c -k --keepParent JevFish.app JevFish.app.zip   # `zip -qr` FAILS notarization
xcrun notarytool submit JevFish.app.zip --keychain-profile jevfish-profile --wait
xcrun stapler staple JevFish.app
spctl -a -vvv -t install JevFish.app       # expect: accepted, source=Notarized Developer ID
xcrun notarytool log <submission-uuid> --keychain-profile jevfish-profile log.json
```

Two CI traps: `notarytool` **exits 0 even on failure**, so the pipeline must parse output, and it writes informational output to stderr not stdout. Turnaround is typically 2 to 15 minutes (https://www.forasoft.com/blog/article/the-pain-of-publishing-electron-apps-on-macos-303), but the tail is real: 3.5 to 4.5 hours consistently in one thread (https://developer.apple.com/forums/thread/813586), "stuck In Progress for 2+ days" in another (https://developer.apple.com/forums/thread/819403), and 24h+ for first submissions held for in-depth analysis (https://developer.apple.com/forums/thread/814827). Tauri and `electron/notarize` both have open issues about `--wait` hanging for hours (https://github.com/orgs/tauri-apps/discussions/8630, https://github.com/electron/notarize/issues/179). Budget 90-minute CI timeouts.

**Can you notarize a shell-script `.app` bundle? Technically yes, meaningfully no.** Scripts carry no signature of their own; only the bundle seal covers them, and the seal covers only what exists **at sign time**. JevFish's script downloads uv and installs roughly 1 GB **after** launch, so a ticket would certify an empty shell around unverified downloaded code. Any post-install edit to the script invalidates the bundle. Bundled helper scripts are also a known rejection cause (Apple Developer Forums thread 127403).

**Does hardened runtime break shelling out to a downloaded uv?** The distinction matters. Library validation constrains what loads **into your process**: "if library validation is enabled on an executable, the trusted execution system only allows the process to load code signed by Apple or with the same Team ID" (https://developer.apple.com/forums/thread/706437). A separate `fork/exec` of `uv` is its own process, so that part is fine. What bites is a 1 GB scientific venv full of third-party `.so` files being loaded into a signed process, which needs `com.apple.security.cs.disable-library-validation`, and Apple's own advice is to leave library validation on because disabling it makes Gatekeeper harder to pass. Separately, files fetched by curl inside a script generally do not get quarantined (curl does not set the xattr the way a browser does), which is why the current wrapper works at all. That is a loophole, not a guarantee.

**Cheaper alternatives, honestly:**

- **Ad-hoc or self-signed: worthless.** An ad-hoc signature works only on the machine that built it and "fails silently when copied to another computer" (https://gist.github.com/rsms/929c9c2fec231f0cf843a1a746a416f5). A self-signed CA cert is worse than useless because almost all the value of code signing requires traceability to a CA.
- **DMG over ZIP: do this now.** ZIP is the worst container. It cannot be code-signed at all, every extracted file inherits quarantine, and it triggers **App Translocation**, where the app runs from a read-only `/private/var/folders/.../AppTranslocation/` path. The JevFish launcher already fights this: `JevFish.app/Contents/MacOS/JevFish` contains the comment "A downloaded copy can run from a temporary path (App Translocation). Ask Spotlight." and falls back to `mdfind -name jevfish-folder-marker`. A DMG can be signed, does not translocate, makes the Gatekeeper dialog's default button **Open** rather than Move to Trash, and dragging to `/Applications` drops quarantine. Stapling only works on `.dmg`, `.pkg` and `.app`, never on a `.zip`.
- **Homebrew cask: this door closed on 1 September 2026.** Homebrew is removing `--no-quarantine` and will "end support for all casks that fail Gatekeeper checks on September 1st, 2026" (https://github.com/Homebrew/brew/issues/20755). Today is 18 September 2026, so the official-cask route for an un-notarized app is already past its deadline. A private tap with a `postflight` `xattr -dr` still works but is unsupported and teaches users to defeat Gatekeeper.

Signing route cost: **USD 99/yr**, roughly 10 to 20 hours for a first signed-and-notarized DMG, plus 10 to 25 hours more if the bundle has to become a real self-contained app for the seal to mean anything.

### 2.6 Tauri v2 or Electron around a local Python server

Who actually does this:

| Project | Stars | Shape |
|---|---|---|
| open-webui/open-webui | 152,442 | Python backend, no desktop shell. Docker first, then `pip install open-webui` and `open-webui serve`. Pins Python 3.11 explicitly |
| Mintplex-Labs/anything-llm | 66,164 | Node backend, separate Electron desktop app plus Docker |
| janhq/jan | 44,517 | llama.cpp backend, **Tauri** wrapper, auto-updater (`latest.json`: 313,061 downloads) |
| danny-avila/LibreChat | 44,264 | `docker compose up`, localhost:3080 |
| khoj-ai/khoj | 37,399, AGPL-3.0 | FastAPI backend, `pip install khoj` or docker compose, `--full` also installs desktop and Obsidian clients |
| pinokiocomputer/pinokio | 8,106 | Electron whose entire purpose is installing and babysitting other people's local servers |

The pattern across all of them: **nobody ships an unsigned script-in-a-bundle.** They ship Docker plus pip, or a real signed desktop app.

Tauri v2 has a first-class sidecar mechanism (https://v2.tauri.app/develop/sidecar/):

```json
{ "bundle": { "externalBin": ["binaries/my-sidecar"] } }
```

with a target-triple suffix per binary (`my-sidecar-aarch64-apple-darwin`; find yours with `rustc --print host-tuple`), invoked via `Command.sidecar('binaries/my-sidecar')` in JS or `app.shell().sidecar("my-sidecar")` in Rust, and gated by a capability grant. The canonical FastAPI reference is `dieharders/example-tauri-v2-python-server-sidecar` (only **126 stars**), whose README flags the killer caveat: "we cannot use process.kill() for one-file Python executables since Tauri only knows the pid of the PyInstaller bootloader process and not its' child process". You inherit a hand-rolled shutdown protocol.

Measured shell sizes (N=1, https://www.gethopp.app/blog/tauri-vs-electron): Tauri bundle **8.6 MiB** versus Electron **244 MiB**; memory across 6 windows 172 MB versus 409 MB; build time 81 s versus 16 s. But the shell size is irrelevant here, because the payload is the frozen Python: realistically **350 to 700 MB per architecture** at today's dependency tree, and you own every problem from section 2.4 plus a Rust toolchain plus the same USD 99. Estimated **60 to 120 hours**. Tauri also uses the platform WebView (WKWebView on macOS), so the existing Vue bundle needs a fresh cross-browser QA pass.

### 2.7 Docker one-liner

Open WebUI's actual line, verbatim:

```
docker run -d -p 3000:8080 --add-host=host.docker.internal:host-gateway -v open-webui:/app/backend/data --name open-webui --restart always ghcr.io/open-webui/open-webui:main
```

The JevFish analogue, given two keys and a port:

```
docker run -d -p 8000:8000 \
  -e TYPESAFE_API_KEY=... -e GEMINI_API_KEY=... \
  -v jevfish:/app/data --name jevfish --restart always \
  ghcr.io/markiewee/jevfish:latest
```

LibreChat (44,264) and Vane/Perplexica (36,867) both lead with `docker compose up -d` after editing `.env`. The repo already has a root `Dockerfile` and `docker-compose.yml` from upstream, plus a `.github/workflows/docker-image.yml`, so this is mostly plumbing a JevFish-specific image.

Friction, which is easy to underrate because it looks like one line: **Docker Desktop is a prerequisite install of roughly 6 GB** (about 1.5 GB for Docker.app plus the Linux VM image), 4 GB RAM minimum and 8 GB recommended (https://docs.docker.com/desktop/troubleshoot-and-support/faqs/macfaqs/). And the licence tripwire: free for personal use, education, non-commercial open source, and small business under **250 employees AND under USD 10 million annual revenue**; either threshold alone triggers payment, at roughly Pro USD 9, Team 15, Business 24 per user per month (https://docs.docker.com/subscription/desktop-license/). Every enterprise evaluator either already has a licence or cannot legally follow the README.

Cost to us: 4 to 8 hours, **USD 0** (GHCR is free for public images), and it doubles as the deploy artifact for the hosted demo. Ship it as the power-user and Linux path, never as the headline.

### 2.8 Hosted demo as the try-before-download path

| Platform | Free reality in 2026 | Key server-side? | Cost at low traffic | Cold start |
|---|---|---|---|---|
| **HF Spaces** | CPU Basic is 2 vCPU / 16 GB / 50 GB non-persistent at USD 0/hr. But Gradio and Docker Spaces "require a paid plan to create: PRO for personal accounts". Static Spaces stay free for everyone. Free `cpu-basic` Spaces sleep after **48 h** idle, not configurable. Outbound restricted to ports 80, 443, 8080 | **Yes**, proper Secrets (value unreadable after set, not copied on duplication) versus public Variables, both as env vars. Secrets scanner flags hard-coded keys | **USD 0** on CPU Basic, else **USD 9/mo** PRO. CPU Upgrade (8 vCPU / 32 GB) USD 0.03/hr, about USD 22/mo running | roughly 2 min for a paused Space to start booting, plus app startup |
| **Streamlit Community Cloud** | 0.078 to 2 CPU cores, 690 MB to 2.7 GB RAM, up to 50 GB storage. Sleeps after **12 h** without traffic. Deployer needs admin on the repo. US-only. Unlimited public apps, 1 private | Yes, `st.secrets` from a TOML blob | **USD 0** | wake-on-visit prompt plus container boot |
| **Vercel** | Hosts Flask and FastAPI natively (WSGI and ASGI are both first class); entrypoint must be `app.py`, `index.py`, `server.py`, `main.py`, `wsgi.py` or `asgi.py` exposing a top-level `app`, or set `[tool.vercel] entrypoint`. Python 3.12 default. Bundle limit **500 MB uncompressed** (raised from 250 MB on 24 Feb 2026), 5 GB on Fluid large beta. Timeout 300 s default, 800 s on Pro with Fluid. **No automatic tree-shaking for Python** | Yes, project env vars | USD 0 on Hobby | per-invocation cold start |
| **Fly.io** | **The free tier is gone** (ended for new orgs 7 Oct 2024; new signups get 2 VM-hours or 7 days). `shared-cpu-1x`: 256 MB USD 2.02/mo, 512 MB 3.32, 1 GB 5.92, 2 GB 11.11. Egress USD 0.02/GB. Volumes USD 0.15/GB/mo even stopped. New apps default to `auto_stop_machines = "stop"`, `min_machines_running = 0` | Yes, `fly secrets set` | roughly **USD 3 to 6/mo** at 1 GB with scale-to-zero | no published number; community reports 5-min idle stop then cold boot |
| **GitHub Pages static replay** | Free, unlimited, no sleep | N/A (no keys, no backend) | **USD 0** | none, it is static |

The Vercel blocker for JevFish as-is: a 1.1 GB dependency tree against a 500 MB uncompressed limit, with no Python tree-shaking. Cut the tree to 66 MB (section 2.1) and Vercel becomes viable for a thin demo API. Flask is directly supported, so the entrypoint work is small.

The cheapest credible option, and what upstream already does, is the **static replay** described in 1.6: export one completed run to JSON, point the existing Vue app at it, publish to GitHub Pages. USD 0, no keys at risk, no Section 13 exposure, no sleep, and it can be linked from a "See a finished run" button above the fold.

If an interactive demo is wanted later, copy CAMEL-AI's `camel-agents` Space and make the visitor paste their own keys. That removes both the inference bill and the key-exposure risk.

### 2.9 The keyless demo already exists and nobody knows

This is the single largest unexploited adoption asset in the repo. `config.py` supports `JEVFISH_FAKE_JUDGE=1` and `JEVFISH_FAKE_LLM=1`. I ran the full five-stage pipeline with no API keys, no `camel-oasis`, in the 117 MB slim venv:

```
$ JEVFISH_FAKE_JUDGE=1 JEVFISH_FAKE_LLM=1 python -m jevfish.cli demo \
    --seed examples/lazybee-cleaning.md --platform lite --rounds 3 --public 12 --stakeholders 3
project p_9f7e9085bf
graph: {'chunks': 1, 'failed_chunks': 0, 'nodes': 8, 'edges': 7, 'types': {'Place': 4, 'Organization': 2, 'Person': 2}}
prepare: {'talking_points': 8, 'variants': 1, 'stakeholders': 3, 'public': 12}
run: {'run_id': 'r_0a66d40ea4', 'partial': None, 'requests': 67}
  base As described: 7.1 of 15 (90% 4.6 to 9.6), first poll 6.8
  jev: {'model': 'fake', 'fake': True, 'requests': 67, 'input_tokens': 37880, 'est_cost_usd': 0.00159096}
  llm: {'calls': 10, 'prompt_tokens': 3918, 'completion_tokens': 500, 'failures': 0}

## Prediction
The simulated crowd leans towards: {"base": {"n": 15, "mean_outcome": 0.475, "expected_yes": 7.118,
"low": 4.612, "high": 9.624, "likely_yes": 7, "stance_mean": 2.459}}
```

Roughly ten seconds, zero keys, zero signup, zero cost, and a real calibrated output with a 90% range. That is the "it works" moment and it should be the first command in the README, ahead of any key setup. Four example seeds already ship in `jevfish/examples/` (`hotel-rate-ladder.md`, `hotel-rate-ladder-v2.md`, `lazybee-cleaning.md`, `pureloft-suasana-kl.md`), so if one is bundled into the package the whole thing is a single copy-paste with no local files needed.

### 2.10 Verified proof that the recommended install path works

I applied the three fixes from 2.2 to a copy of the tree and rebuilt:

| Step | Result |
|---|---|
| Move `web/dist` to `src/jevfish/web/dist` and change `api.py:20` to `Path(__file__).resolve().parent / "web" / "dist"` | wheel goes from 34 files / 168,620 B to **40 files / 502,428 B uncompressed (174,808 B compressed)** and now contains `jevfish/web/dist/index.html` (1,102 B), `assets/index-BX2Ou-8v.js` (301,083 B), `assets/index-BHsORouT.css` (31,320 B) |
| Install that wheel into a venv with **no `camel-oasis`** | 117 MB venv, imports cleanly (so the OASIS import is already lazy, no code restructuring needed) |
| `create_app()` then `GET /` | **200, `text/html`, 1,102 bytes**, the real Vue shell |
| `GET /assets/index-BX2Ou-8v.js` | **200, 301,083 bytes** |

Before the fix, the same test gave `WEB_DIST = .../lib/python3.12/web/dist`, `index.html present: False`, and a 150-byte fallback response. So the one-line install works after roughly a two-line change plus the `platformdirs` change for `.env` and `data/`.

Cold install timings measured with `--no-cache` on this machine:

| Tree | Time | Size |
|---|---|---|
| Slim (7 direct deps, no `camel-oasis`) | **4.35 s** | 68 MB |
| `camel-oasis==0.2.5` alone (today's default) | **27.44 s** | 978 MB |

---

## 3. GitHub repo presentation mechanics

### 3.0 What the fork measures today

| Field | Current value |
|---|---|
| Stars / forks / watchers | 0 / 0 / 0 |
| `fork` | **true**, parent `666ghj/MiroFish` |
| Description | `A Simple and Universal Swarm Intelligence Engine, Predicting Anything. 简洁通用的群体智能引擎，预测万物` (upstream's) |
| Homepage | **`https://mirofish.ai`** (upstream's site) |
| Topics | **0** of a permitted 20 |
| Releases | **0**, although tag `v0.1.2` exists |
| `has_pages` | false |
| Root README | 9,902 bytes, 208 lines |
| First fenced code block | **line 112** |
| Badges | **11**, of which the Stars, Watchers and Forks badges report `666ghj/MiroFish`'s numbers and the Trendshift badge is upstream repo id 16144 |
| Brand references in README | **37** for `666ghj|mirofish.ai|MiroFish` versus **4** for `JevFish` |
| Community health files | none (no CONTRIBUTING, CODE_OF_CONDUCT, SECURITY, ISSUE_TEMPLATE, PULL_REQUEST_TEMPLATE) |
| `.github/workflows` | `docker-image.yml` (1,557 B), `jevfish-web.yml` (606 B), `update-star-history.yml` (**18,211 B, charting upstream's stars**) |
| `og:image` | auto-generated `opengraph.githubassets.com/...`, no custom social preview |
| `og:description` | upstream's Chinese-and-English tagline, so every shared link unfurls as MiroFish |

Upstream by contrast has a custom social preview at `repository-images.githubusercontent.com/1104332987/...`.

Two mechanical consequences of the `fork: true` flag, both verified:

- `gh api "search/repositories?q=mirofish-jev"` returns **0**. With `+fork:true` it returns **1**. GitHub docs: "By default, forks are not shown in search results" (https://docs.github.com/en/search-github/searching-on-github/searching-in-forks). Topics pages are built from the same index.
- Code search only indexes forks with more stars than the parent, which at 73,886 is never.

**Leaving the fork network** is self-service (Settings, Danger Zone, "Leave fork network") and requires the fork to be public, under 1 GB, and free of child forks (https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/working-with-forks/detaching-a-fork). The fork is public, 17,291 KB and has 0 child forks, so all three conditions hold. It is permanent and does not retain "issues, pull requests, wikis, stars, watchers, comments, child forks, or other metadata", all of which are currently zero, so the cost is nil. Git commit metadata is preserved, which keeps the AGPL provenance intact.

### 3.1 README structure: the actual evidence

**Prana et al., "Categorizing the Content of GitHub README Files"**, Empirical Software Engineering 24(3), 2019. https://arxiv.org/abs/1802.06997 and https://link.springer.com/article/10.1007/s10664-018-9660-3. Manual annotation of **4,226 sections across 393 randomly sampled repositories**, plus an 8-category classifier at F1 0.746.

| Category | Sections | % of sections | Files containing it | % of files |
|---|---|---|---|---|
| What | 707 | 16.7% | 381 | **97.0%** |
| How | 2,467 | **58.4%** | 348 | 88.5% |
| References | 858 | 20.3% | 239 | 60.8% |
| Who | 322 | 7.6% | 208 | 52.9% |
| Contribution | 122 | 2.9% | 109 | 27.8% |
| Why | 116 | 2.7% | 101 | **25.7%** |
| When (status) | 180 | 4.3% | 84 | **21.4%** |
| Other | 58 | 1.4% | 27 | 6.9% |

The median README has **7 sections**, with the middle 50% between 5 and 12. Long is not the norm. Only 25.7% explain why the project exists and only 21.4% state status, so those are the two cheapest differentiators. The paper's practitioner survey (n=20) ranked usage and installation instructions first, license second, known bugs third.

**Venigalla and Chimalakonda, "An Empirical Study On Correlation between Readme Content and Project Popularity"**, arXiv:2206.10772 (https://arxiv.org/abs/2206.10772), 1,950 READMEs across 10 languages: "readme files in majority of the popular projects are well organised using lists and images", they "comprise links to external sources", and "repositories with readme files containing contribution guidelines and references were observed to be associated with higher popularity." Popularity is a composite of stars, forks, watchers and PR count. Follow-on in Software: Practice and Experience 2025, https://onlinelibrary.wiley.com/doi/10.1002/spe.3390

**GitHub Open Source Survey 2017** (https://opensourcesurvey.org/2017/), 5,500 respondents from 3,800+ repositories: "Incomplete or outdated documentation is a pervasive problem, observed by 93% of respondents"; "60% of contributors say they rarely or never contribute to documentation"; and the one that bears directly on AGPL, "**64% say an open source license is very important in deciding whether to use a project, and 67% say it is very important in deciding whether to contribute**". Two thirds of evaluators will look for the licence, so AGPL-3.0 belongs stated plainly near the top rather than left to the sidebar.

**Badges: the one study with a regression behind it.** Trockman, Zhou, Kästner, Vasilescu, "Adding Sparkle to Social Coding: An Empirical Study of Repository Badges in the npm Ecosystem", ICSE 2018, https://cmustrudel.github.io/papers/icse18badges.pdf. 294,941 npm packages plus a maintainer survey and regression-discontinuity time series on 1,762 packages.

| Badge | Count | Share of 294,941 |
|---|---|---|
| Travis CI (build status) | 92,789 | **31.5%** |
| David DM | 23,601 | 8.0% |
| Coveralls | 17,603 | 6.0% |
| npm Downloads | 15,552 | 5.3% |
| CodeClimate | 6,652 | 2.3% |
| GitHub Stars | 630 | **0.2%** |

- Badge adoption correlates with "a sizeable positive discontinuity in download counts at badge adoption (**33% increase on average**)", then "a small negative slope after the intervention". The boost decays; quality-assurance badges decay slower (8.8%).
- **H8 is supported**: a negative binomial model "suggests a nonlinear relationship in popular packages, with a predicted inflection point at **5 badges**, which supports H8: Packages with many badges tend to have fewer downloads."
- **H5**: "The adoption of a link-related badge does not correlate with either popularity or code quality." Discord, X and Instagram badges are link badges.

So badges work only as assessment signals (CI, coverage, version), and more than about five is associated with worse outcomes. JevFish currently has 11, mostly link and vanity badges, three of which report another repo's numbers.

**Measured across 46 high-star adjacent repos** (3,846 to 191,838 stars, selected for adjacency: local-first AI apps, Python tooling, agent frameworks, simulation, CLI tools):

| Metric | n | min | p25 | median | mean | p75 | max |
|---|---|---|---|---|---|---|---|
| First fenced code block (line) | 39 | **15** | 39 | **60** | 86.4 | 115 | 261 |
| First install command (line) | 35 | 16 | 51 | **90** | 105.8 | 122 | 262 |
| First image or video (line) | 44 | 1 | 3 | **3** | 5.4 | 5 | 35 |
| Total lines | 46 | 1 | 151 | 327 | 412.6 | 473 | 2,505 |
| Badges in first 45 lines | 36 | 1 | 3 | **5** | 4.4 | 6 | 9 |
| Headings (h1 to h3) | 45 | 2 | 10 | 17 | 26.0 | 30 | 137 |
| Topics | 46 | 0 | 6 | 11 | - | 15 | **20** |

Two convergences: the measured median badge count (5) lands exactly on Trockman's modelled inflection point, and the hero image sits at **line 3 in the median repo** (44 of 46 have media). Ten of 46 carry zero badges, including ollama (181,191), streamlit, lazygit, vllm and stable-diffusion-webui.

JevFish's first fenced code block at **line 112** is worse than the p75 of this sample (115 is close, but the sample p25 is 39 and ollama is 15).

**Recommended section order**, synthesised from the Prana ranking, the sample medians and the exemplars in 1.2:

1. Logo or wordmark, name (lines 1 to 8)
2. One sentence of what it is, plus **3 assessment badges maximum**
3. **Hero media by line 3 to 10**
4. **The Why in two or three lines** (only 25.7% of READMEs do this)
5. **One runnable command by line 15 to 30**
6. Status and maturity, plus the AGPL statement (only 21.4% state status; 64% of evaluators care about licence)
7. Highlights as a short bullet list
8. Fuller usage, config, docs link
9. Fork provenance and attribution, contributing, licence

Target 7 to 12 sections, under 200 lines.

### 3.2 Hero GIF or video: hosting, limits and real sizes

| Route | Per-file limit | Docs |
|---|---|---|
| Committed to the repo | Git **warns at 50 MiB**, **hard blocks at 100 MiB**; repos "ideally less than 1 GB" | https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-large-files-on-github |
| Drag-drop attachment (issue, PR, discussion, web editor) | "**10MB for images and gifs**"; "**10MB for videos** ... on a **free** GitHub plan"; "**100MB for videos** ... on a **paid** GitHub plan"; "25MB for all other files" | https://docs.github.com/en/get-started/writing-on-github/working-with-advanced-formatting/attaching-files |
| Release asset | "Each file included in a release must be **under 2 GiB**"; "Up to **1000** release assets"; "**no limit on the total size of a release, nor bandwidth usage**" | https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases |
| Git LFS | **10 GiB storage and 10 GiB bandwidth per month** on Free and Pro | https://docs.github.com/en/billing/concepts/product-billing/git-lfs |

Supported attachment types: "PNG (`.png`), GIF (`.gif`), JPEG (`.jpg`, `.jpeg`), SVG (`.svg`), Video (`.mp4`, `.mov`, `.webm`)", with "we recommend using H.264 for greatest compatibility". Attachment URLs moved from `user-images.githubusercontent.com` to `github.com/user-attachments/assets/{uuid}` on 9 May 2023 (https://github.blog/changelog/2023-05-09-more-secure-private-attachments/); legacy URLs still resolve.

The asymmetry that matters: **a 10.8 MB GIF cannot be drag-dropped (10 MB cap) but can be committed (100 MiB cap)**. AnythingLLM sidesteps both by putting its 30.4 MB hero GIF in a **release asset** (`releases/download/v1.11.2/AnythingLLM720p.gif`), where there is no size or bandwidth limit.

**Does GitHub render `<video>` in a README?** Tested both renderers.

The REST Markdown API (`POST /markdown`, `mode: gfm`) **strips `<video>` entirely**, turns `![demo](x.mp4)` into a broken `<img>`, and leaves a bare mp4 URL as a plain link. But the live github.com renderer does render it, verified by counting `<video>` elements in the served HTML: `zai-org/GLM-4` has 3, `Tencent-Hunyuan/HunyuanVideo-1.5` has 17, `11cafe/jaaz` has 2, `esimov/caire` has 2. The served markup for `11cafe/jaaz`:

```html
<video src="https://github.com/user-attachments/assets/1c15e792-098a-4557-b310-d9c223f73442"
  data-canonical-src="https://github.com/user-attachments/assets/1c15e792-098a-4557-b310-d9c223f73442"
  controls="controls" muted="muted"
  class="d-block rounded-bottom-2 border-top width-fit"
  style="max-height:640px; min-height: 200px">
```

with the `src` rewritten on first paint to a short-lived signed `private-user-images.githubusercontent.com/...?jwt=...` URL. The rules:

1. `<video src="...">` renders on github.com **only** when the src is a GitHub attachment URL (`github.com/user-attachments/assets/{uuid}` or legacy `user-images.githubusercontent.com/{id}/{uuid}.mp4`).
2. GitHub injects `controls` and `muted` and imposes `max-height:640px`. Your `autoplay`, `loop` and `playsinline` are dropped.
3. A **repo-committed** mp4 path does not work. Community discussion #19403 records exactly this (https://github.com/orgs/community/discussions/19403).
4. `![](x.mp4)` never becomes a player on either renderer.
5. `<iframe>` is blocked, so no YouTube embed. Use a thumbnail image linked to the video (which is what MiroFish does with its Bilibili links).
6. Anywhere other than github.com (PyPI project description, npm, mirrors, IDE previews) drops the `<video>`. **A GIF via `<img>` is the only thing that renders everywhere.**

What does render, confirmed: `<img>` (GitHub adds `data-animated-image` for GIFs), `<picture>` with `prefers-color-scheme` sources (wrapped in `<themed-picture>`), `<details>`/`<summary>`, `<div align="center">`.

So: **GIF as the hero, video as a second-position deep dive.** Since JevFish is a Python package that will also render on PyPI, the `<img>` GIF is the only correct choice for the hero.

**Recording tools, with verified star counts:**

| Tool | Repo | Stars | Output |
|---|---|---|---|
| vhs | charmbracelet/vhs | **20,924** | GIF, MP4, WebM, PNG frames |
| ScreenToGif | NickeManarin/ScreenToGif | 27,661 | GIF, APNG, video (Windows) |
| Kap | wulkano/Kap | 19,356 | GIF, MP4, WebM, APNG (macOS) |
| asciinema | asciinema/asciinema | 17,815 | `.cast` text, streams |
| terminalizer | faressoft/terminalizer | 16,163 | GIF, web player |
| Peek | phw/peek | 10,552 | GIF, APNG, WebM (Linux) |
| Gifski (Mac GUI) | sindresorhus/Gifski | 8,556 | GIF from video |
| gifski (CLI, library) | ImageOptim/gifski | 5,635 | high-quality GIF |
| freeze (static code images) | charmbracelet/freeze | 4,844 | PNG, SVG |
| agg (asciinema to GIF) | asciinema/agg | 1,724 | GIF via gifski |
| t-rec | sassman/t-rec-rs | 1,253 | GIF, MP4 |

asciinema plus agg produces the smallest terminal GIFs because agg "uses Kornel Lesiński's excellent gifski library to produce optimized, high quality GIF output with accurate frame timing" (https://docs.asciinema.org/manual/agg/), though the same docs warn that "while gifski produces great-looking GIFs, this often comes at a cost in file size, though gifsicle can be used to shrink the produced GIF files". asciinema and vhs only record TTYs, so for the **web UI** the path is Kap then a `gifski` or `gifsicle` pass. For the **CLI** half, vhs is right because the recording is a committed, diffable `.tape` file that CI can regenerate. The key pair in the tape language is `Hide` and `Show`, which lets you hide the `cd`, venv and key export and show only the one command you want copied. On this machine none of vhs, asciinema, agg, gifski or svgo are installed; `ffmpeg` is, with `palettegen` and `paletteuse` available, so a decent GIF is possible today with ffmpeg alone.

**Real hero sizes, fetched byte-exact:**

| Project | Asset | Bytes | Hosting |
|---|---|---|---|
| Mintplex-Labs/anything-llm | `AnythingLLM720p.gif` | **31,146,000** (30.4 MB) | **release asset** |
| khoj-ai/khoj | `quadratic_equation_khoj_web.gif` | **19,703,000** (19.2 MB) | committed, `documentation/assets/img/` |
| marimo-team/marimo | `docs-intro.gif` | 8,984,335 | committed, `docs/_static/` |
| Textualize/rich | `downloader.gif` | 2,636,646 | committed |
| open-webui/open-webui | `demo.png` | **287,744** (281 KB) | committed, repo root |
| ajeetdsouza/zoxide | `contrib/tutorial.gif` | 627,065 | committed |
| jesseduffield/lazygit | `commit_graph-compressed.gif` | **665,089** | committed on an orphan `assets` branch |
| junegunn/fzf | `fzf-color.png` | 93,402 | **a separate repo** (`junegunn/i`) |
| charmbracelet/vhs | `examples/demo.gif` | **25,403** | Git LFS |
| MiroShark/MiroShark | `docs/images/hero-animated.svg` | **11,393** | committed animated SVG |
| camel-ai/oasis | `assets/banner.png` | 1,044,480 | committed |
| microsoft/TinyTroupe | `docs/tinytroupe_stage.png` | 1,397,760 | committed |
| 666ghj/MiroFish | `MiroFish_logo_compressed.jpeg` | 180,224 | committed |

lazygit keeps both raw and `-compressed` variants and references only the compressed ones. Across 15 matched pairs: raw min 2,005,422 and max 11,363,958; compressed min **307,837**, median **453,269**, max **985,118**; median compression **6.7x**.

The GIF-versus-MP4 tax, from 22 exact marimo triples: **GIF is a median 14.1x the size of the equivalent MP4** (min 0.7x, max 20.7x) and 2.3x the WebM. In aggregate marimo's GIFs total 72,118,080 bytes against 45,344,274 bytes of MP4s covering more clips.

**Target for JevFish: 300 KB to 900 KB**, which is the lazygit and zoxide band. Achievable at 1200x600 with a capped framerate and a clip under 12 seconds, then `gifski` or `gifsicle -O3 --lossy=80`. Commit it rather than drag-dropping (100 MiB cap versus 10 MB, and it survives forks). Do **not** use Git LFS: on a Free plan the 10 GiB monthly bandwidth is consumed by every README view. Path convention: the three live ones are `docs/assets/` or `docs/_static/` (marimo, uv), `assets/` on an orphan branch (lazygit), and `.github/assets/`. For a Python package, **`docs/assets/`** is right because `pyproject.toml` already knows how to leave `docs/` out of the wheel.

One more cheap trick worth stealing: MiroShark's **11 KB animated SVG** carries keyword-loaded alt text ("Keywords: multi-agent simulation, social simulation, swarm intelligence, agent-based modeling, LLM agents, prediction market, scenario testing"). An SVG hero is diffable, tiny, and the alt text is indexed.

And a specific idea from uv: its hero is not a screenshot but a **benchmark chart with a one-line caption stating what was measured** ("Installing Trio's dependencies with a warm cache"). For a calibrated predictor, the strongest possible hero is a **calibration plot**, captioned, not a UI screenshot.

### 3.3 Releases with attached binaries, automated on tag

`softprops/action-gh-release` has **5,763 stars** and a version warning that invalidates most tutorials: "`v2.6.2` is the final `v2` release and is no longer maintained or supported. It uses the Node 20 runtime deprecated by GitHub Actions. Upgrade to `v3`, which runs on Node 24." Current tag is **v3.0.3**.

Minimal working pattern:

```yaml
name: Release
on:
  push:
    tags: ["v*.*.*"]
jobs:
  release:
    runs-on: macos-latest
    permissions:
      contents: write
    steps:
      - uses: actions/checkout@v7
      - uses: astral-sh/setup-uv@v10
      - name: Build the app bundle and DMG
        run: |
          ./jevfish/launcher/make-icon.sh
          mkdir -p dist/JevFish && cp -R JevFish.app jevfish dist/JevFish/
          hdiutil create -volname JevFish -srcfolder dist/JevFish -ov -format UDZO dist/JevFish-macos.dmg
      - uses: softprops/action-gh-release@v3
        with:
          files: dist/JevFish-macos.dmg
```

`hdiutil` is built into macOS (verified at `/usr/bin/hdiutil`), so a basic DMG needs zero dependencies. For a prettier one, `create-dmg/create-dmg` (2,623 stars, MIT, shell) or `sindresorhus/create-dmg` (5,373 stars, JS). Current action versions: `actions/checkout` v7.0.1, `actions/setup-python` v7.0.0, `astral-sh/setup-uv` v10.1.0, `actions/upload-pages-artifact` v5.0.0, `actions/deploy-pages` v5.0.1, `peaceiris/actions-gh-pages` v4.1.0.

The production pattern to copy is `yt-dlp/yt-dlp`, the closest real reference for a Python project shipping native binaries. Its `build.yml` is 598 lines and the structure is:

```yaml
permissions: {}          # deny everything at workflow level
jobs:
  macos:
    permissions:
      contents: read     # build jobs only read
    runs-on: macos-14
    steps:
      - run: |
          python3 -m bundle.pyinstaller --target-architecture universal2 --onedir
          (cd ./dist/yt-dlp_macos && zip -r ../yt-dlp_macos.zip .)
      - uses: actions/upload-artifact@043fb46d1a93c77aae656e7c1c64a875d1fc6a0a  # v7.0.1
```

and in `release.yml`:

```yaml
  publish:
    permissions:
      contents: write  # Needed by gh to publish release to Github
    steps:
      - name: Push tag
        run: |
          git tag "${TARGET_TAG}" "${HEAD_SHA}"
          git push origin "refs/tags/${TARGET_TAG}"
          sleep 5  # Enough time to cover git-push vs gh-release-create race condition
      - name: Publish release
        env:
          GH_TOKEN: ${{ github.token }}
        run: gh release create --verify-tag --notes-file "${NOTES_FILE}" "${TARGET_TAG}" artifact/*
```

Four things worth copying: `permissions: {}` at workflow level with `contents: write` on only the publish job; actions pinned by commit SHA with the version in a trailing comment; `--verify-tag` so a typo fails instead of creating a phantom release; and the explicit `sleep 5` for the push-versus-create race. Missing `contents: write` produces "Resource not accessible by integration".

Runner labels have changed: `macos-latest` is now Apple Silicon, so an Intel build needs `macos-15-intel` explicitly. `sharkdp/bat`'s matrix is the current reference, and it sets `fail-fast: false` so one platform failing does not cancel the rest and ship a partial release. PyInstaller cannot cross-compile, so each artifact builds on its native runner; `--target-architecture universal2` removes the need for a second macOS runner.

**One-line curl install mechanics.** `https://github.com/{owner}/{repo}/releases/latest/download/{asset}` is a permanent alias, verified:

```
$ curl -sI https://github.com/astral-sh/uv/releases/latest/download/uv-aarch64-apple-darwin.tar.gz
HTTP/2 302
location: https://github.com/astral-sh/uv/releases/download/0.12.16/uv-aarch64-apple-darwin.tar.gz
```

So the asset filename must be **version-free** for the alias to work. `uv-aarch64-apple-darwin.tar.gz` works; `uv-0.12.16-...` would not.

How the three reference installers are actually built:

| | Lines | Bytes | Provenance | Binary source | Checksums |
|---|---|---|---|---|---|
| uv, `https://astral.sh/uv/install.sh` | 2,191 | 71,308 | **generated by cargo-dist 0.32.0** | GitHub Releases, dual-mirrored | **yes, per-target sha256 inlined** |
| ollama, `https://ollama.com/install.sh` | 455 | 15,902 | hand-written | own CDN | no |
| rustup, `https://sh.rustup.rs` | 930 | 29,915 | hand-written | own CDN | no (`rustup-init` self-verifies) |

uv's script carries its generator manifest inline at line 69 (`"provider":{"source":"cargo-dist","version":"0.32.0"}`), resolves about 20 target triples, falls back across mirrors (`ARTIFACT_DOWNLOAD_URLS="https://releases.astral.sh/github/uv/releases/download/0.12.16 https://github.com/astral-sh/uv/releases/download/0.12.16"`), and inlines a sha256 per target. rustup's own comment is the honest summary of the genre: "This is just a little script that can be downloaded from the internet to install rustup. It just does platform detection, downloads the installer and runs it."

**Recommendation: do not hand-write an installer.** Publish to PyPI (the name is free, see section 5) so the one-liner is `uvx jevfish` or `uv tool install jevfish`, which is zero infrastructure. Reserve GitHub Releases for the macOS DMG under a version-free asset name, so `releases/latest/download/JevFish-macos.dmg` is a stable link for line 15 of the README. Tag `v0.1.2` already exists with no release attached, so the first job is just attaching an asset to it.

### 3.4 Repo metadata mechanics

**Social preview** (https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/customizing-your-repositorys-social-media-preview): "PNG, JPG, or GIF file", "**under 1 MB in size**", "at least 640 by 320 pixels (**1280 by 640 pixels for best display**)". Set in Settings, Social preview, Edit. This is the highest-leverage single asset on the list because it is what renders on X, LinkedIn, Slack, Discord and Hacker News unfurls. JevFish has none, so it falls back to the generic card, and its `og:description` is still MiroFish's tagline.

**About section:** description limit is **350 characters**, enforced server side (`desktop/desktop` issue #19465). The longest real description in a 46-repo sample was 302 characters, so nobody is near the cap. The Website field populates the clickable link under About; JevFish's still points at `mirofish.ai`.

**Topics** (https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/classifying-your-repository-with-topics): "**Add no more than 20 topics**", "Use lowercase letters, numbers, and hyphens", "Use **50 characters or less**", and "Topic names are always public, even if you create the topic from within a private repository." Corroborated empirically: of 46 sampled repos, 4 sit at exactly 20 (`langchain-ai/langchain`, `fastapi/fastapi`, `vllm-project/vllm`, `khoj-ai/khoj`) and none exceed it; median 11. Each topic gets a `github.com/topics/{name}` page and feeds `topic:` search. Zero topics means zero inbound discovery.

**Pinned repositories:** **6 is the cap**, "up to six repositories and gists, combined", hard-coded in the UI and not liftable by Pro (https://docs.github.com/en/account-and-profile/how-tos/profile-customization/pinning-items-to-your-profile; docs gap tracked at github/docs#31159, feature request at community discussion #28350).

**Profile READMEs:** a personal one is a repository named exactly the username (`markiewee/markiewee`) with a root `README.md`, rendered above the pinned repos. An organization one is a repo named `.github` with the file at **`profile/README.md`** (member-only variant `profile/README-MEMBER.md`, added April 2022, https://github.blog/changelog/2022-04-20-organization-profile-updates-member-only-readmes-and-pinned-private-repositories/). The same `.github` repo serves org-wide default community health files.

### 3.5 Community health files, and whether they measurably help

The checklist lives at `github.com/{owner}/{repo}/community`, reached via Insights, then Community Standards (https://docs.github.com/en/communities/setting-up-your-project-for-healthy-contributions/accessing-a-projects-community-profile). `GET /repos/{owner}/{repo}/community/profile` returns a machine-readable `health_percentage`. Measured today:

| Repo | Stars | health_percentage | Missing |
|---|---|---|---|
| ollama/ollama | 181,191 | **62** | code_of_conduct, issue_template, pull_request_template |
| open-webui/open-webui | 152,443 | 87 | contributing, issue_template |
| astral-sh/uv | 89,946 | 87 | issue_template |
| jesseduffield/lazygit | 82,436 | 85 | issue_template |
| marimo-team/marimo | 22,821 | 87 | issue_template |
| charmbracelet/vhs | 20,924 | 75 | code_of_conduct, issue_template |
| camel-ai/camel | 17,741 | 75 | code_of_conduct, issue_template |
| mesa/mesa | 3,846 | 75 | issue_template |

The most-starred project in the set has the **lowest** score, so the percentage is not a proxy for adoption, and all eight are missing `issue_template`. Worth getting to roughly 87 because it takes an hour and removes visible orange circles, not because it converts anyone. The endpoint returns 404 on `markiewee/mirofish-jev`.

What the evidence does support: state the **licence** plainly (64% of evaluators say it decides use, 67% contribution), and include a **contribution section** (only 27.8% of READMEs have one, and Venigalla found it correlates with popularity). What it does not support: community link badges (Trockman H5).

**Issue forms** (https://docs.github.com/en/communities/using-templates-to-encourage-useful-issues-and-pull-requests/syntax-for-issue-forms), in `/.github/ISSUE_TEMPLATE/*.yml`, still marked "currently in public preview". Required top-level keys `name`, `description`, `body`; optional `title`, `labels` (must already exist), `assignees`, `projects`, `type`. Body element types: `markdown`, `input`, `textarea`, `dropdown`, `checkboxes`, `upload`.

```yaml
name: Bug Report
description: File a bug report.
title: "[Bug]: "
labels: ["bug", "triage"]
body:
  - type: markdown
    attributes:
      value: Thanks for reporting!
```

`config.yml` in the same directory controls `blank_issues_enabled` and `contact_links`. For JevFish the fields that would otherwise cost a round trip are: LLM provider and model, whether `TYPESAFE_API_KEY` is set, OS and Python version, and **how the app was launched** (the `.app` bundle versus a terminal), since the macOS Desktop/Documents/Downloads restriction is a known recurring failure that the launcher already works around. `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md` and `SECURITY.md` are recognised in the root, `.github/` or `docs/`.

### 3.6 Docs sites

| Generator | Repo | Stars | Official Pages action | Setup effort |
|---|---|---|---|---|
| Docusaurus | facebook/docusaurus | **66,274** | none first-party, documented recipe | Node, React, heaviest |
| MkDocs Material | squidfunk/mkdocs-material | **27,457** | none needed, `mkdocs gh-deploy` is built in | **lowest: one `mkdocs.yml`, pip install** |
| mdBook | rust-lang/mdBook | 22,155 | none first-party | low, but book-shaped |
| VitePress | vuejs/vitepress | **18,333** | none first-party, documented recipe | Node, Vue, medium |
| Starlight (Astro) | withastro/starlight | 9,254 | **yes, `withastro/action`** (259 stars) | medium, Node toolchain |

Generic Pages plumbing if a generator has no dedicated action: `actions/deploy-pages` (953), `actions/upload-pages-artifact` (512), `peaceiris/actions-gh-pages` (5,362), `JamesIves/github-pages-deploy-action` (4,606). The official path needs `pages: write` **and** `id-token: write` plus a job targeting the `github-pages` environment.

What the comparables actually run, fingerprinted from each live page's `<meta name="generator">` and response headers:

| Project | Docs URL | Generator | Host |
|---|---|---|---|
| **uv (astral-sh)** | docs.astral.sh/uv | **`mkdocs-1.6.1, mkdocs-material-9.7.6`** | Cloudflare |
| **marimo** | docs.marimo.io | **`mkdocs-1.6.1, mkdocs-material-9.7.7`** | Vercel |
| Open WebUI | docs.openwebui.com | **Docusaurus v3.9.2** | GitHub Pages |
| Khoj | docs.khoj.dev | Docusaurus | GitHub Pages |
| Ollama | docs.ollama.com | Mintlify | |
| LangChain | python.langchain.com | Mintlify | |
| CAMEL-AI | docs.camel-ai.org | Mintlify | Vercel |
| ComfyUI | docs.comfy.org | Mintlify (with Starlight strings, likely mid-migration) | Vercel |
| Mesa | mesa.readthedocs.io | Sphinx | Read the Docs |

The pattern is clean: funded AI and agent projects have moved to **Mintlify**, a hosted commercial product. The two closest structural analogs to JevFish, both Python and both self-funded when they set up docs, run **MkDocs Material**. Mesa runs Sphinx because it needs autodoc for a Python API.

**Recommendation: MkDocs Material**, free, pip-installable into the environment that already exists, and Mintlify would violate the free-first constraint while Docusaurus and Starlight drag a Node toolchain into a Python project for no gain at this size. The official workflow (https://squidfunk.github.io/mkdocs-material/publishing-your-site/) is short:

```yaml
name: ci
on:
  push:
    branches: [main]
permissions:
  contents: write
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Configure Git Credentials
        run: |
          git config user.name github-actions[bot]
          git config user.email 41898282+github-actions[bot]@users.noreply.github.com
      - uses: actions/setup-python@v5
        with:
          python-version: 3.x
      - run: echo "cache_id=$(date --utc '+%V')" >> $GITHUB_ENV
      - uses: actions/cache@v4
        with:
          key: mkdocs-material-${{ env.cache_id }}
          path: ~/.cache
          restore-keys: |
            mkdocs-material-
      - run: pip install mkdocs-material
      - run: mkdocs gh-deploy --force
```

This uses the older `gh-pages`-branch mode, which needs no `id-token` and no environment, so it is the shortest path to a live site. Switch to `mkdocs build` plus `upload-pages-artifact` plus `deploy-pages` later if deployment protection rules are wanted. `has_pages` is currently false, so nothing is set up.

### 3.7 Launch-day evidence

Obada Kraishan, **"Launch-Day Diffusion: Tracking Hacker News Impact on GitHub Stars for AI Tools"**, arXiv:2511.04453 (https://arxiv.org/abs/2511.04453), 6 November 2025. **138 repository launches, 2024 to 2025.** Average stars gained: **121 within 24 hours, 189 within 48 hours, 289 within one week**. Elastic Net and Gradient Boosting models found "posting timing appears as key factor, launching at optimal hours can mean hundreds of additional stars", and notably the **"Show HN" tag showed no statistical advantage** after controlling for other variables.

One widely quoted claim deserves a caveat: the assertion that "adding a single demo GIF moved a project's visual proof score from 18 to 62 out of 100" comes from a vendor blog (screencli.sh), based on that vendor's own scoring rubric over 116 READMEs. Treat it as a plausible directional claim, not evidence. The defensible version of the same point is the measurement above: 44 of 46 high-star adjacent repos have media, at a median of line 3.

---

## 4. The AGPL constraint

### 4.0 The finding that changes the licence picture: PyMuPDF is itself AGPL

Verified independently from two sources:

```
$ curl -s https://pypi.org/pypi/pymupdf/json | jq -r '.info.license'
Dual Licensed - GNU AFFERO GPL 3.0 or Artifex Commercial License

$ grep -i '^License' jevfish/.venv/.../pymupdf-1.28.2.dist-info/METADATA
License: Dual Licensed - GNU AFFERO GPL 3.0 or Artifex Commercial License
```

`jevfish/pyproject.toml` declares `pymupdf>=1.24` as a direct runtime dependency. So `jevfish/` carries an AGPL copyleft obligation that is completely **independent of MiroFish**. Every argument below about MiroFish separability is correct and currently pointless, because PyMuPDF re-imposes the same duties.

It is used in exactly one place, and the import is already lazy (`jevfish/src/jevfish/service.py:56-63`):

```python
    def add_file(self, pid: str, filename: str, data: bytes) -> dict:
        suffix = Path(filename).suffix.lower()
        if suffix == ".pdf":
            import fitz

            with fitz.open(stream=data, filetype="pdf") as doc:
                text = "\n\n".join(page.get_text() for page in doc)
```

Replacements: `pypdf` 6.19.0 is **BSD-3-Clause** (`license_expression: 'BSD-3-Clause'`, 10,208 stars) and `pdfminer.six` is **MIT** (7,025 stars). The swap is about five lines in one function:

```python
        if suffix == ".pdf":
            from io import BytesIO
            from pypdf import PdfReader

            reader = PdfReader(BytesIO(data))
            text = "\n\n".join((p.extract_text() or "") for p in reader.pages)
```

That single change removes an entire independent copyleft obligation **and** cuts 54 MB off the install (section 2.1). It is the best value-per-line change in this whole report.

### 4.1 Verbatim operative licence text

Source: https://www.gnu.org/licenses/agpl-3.0.txt (HTML mirror https://www.gnu.org/licenses/agpl-3.0.en.html), version 3, 19 November 2007.

**Section 0, the definitions that decide everything:**

> To "modify" a work means to copy from or adapt all or part of the work in a fashion requiring copyright permission, other than the making of an exact copy. The resulting work is called a "modified version" of the earlier work or a work "based on" the earlier work.

> To "convey" a work means any kind of propagation that enables other parties to make or receive copies. **Mere interaction with a user through a computer network, with no transfer of a copy, is not conveying.**

> An interactive user interface displays "Appropriate Legal Notices" to the extent that it includes a convenient and prominently visible feature that (1) displays an appropriate copyright notice, and (2) tells the user that there is no warranty for the work (except to the extent that warranties are provided), that licensees may convey the work under this License, and how to view a copy of this License. If the interface presents a list of user commands or options, such as a menu, a prominent item in the list meets this criterion.

That last one **defines when an interface displays the notices**. It is not itself an obligation. The obligation comes only from Section 5(d).

**Section 1, Corresponding Source:**

> The "Corresponding Source" for a work in object code form means all the source code needed to generate, install, and (for an executable work) run the object code and to modify the work, including scripts to control those activities. However, it does not include the work's System Libraries, or general-purpose tools or generally available free programs which are used unmodified in performing those activities but which are not part of the work.

> The Corresponding Source for a work in source code form is that same work.

**Section 4:**

> You may convey verbatim copies of the Program's source code as you receive it, in any medium, provided that you conspicuously and appropriately publish on each copy an appropriate copyright notice; keep intact all notices stating that this License and any non-permissive terms added in accord with section 7 apply to the code; keep intact all notices of the absence of any warranty; and give all recipients a copy of this License along with the Program.

**Section 5, the fork clause:**

> a) The work must carry prominent notices stating that you modified it, and giving a relevant date.
>
> b) The work must carry prominent notices stating that it is released under this License and any conditions added under section 7. This requirement modifies the requirement in section 4 to "keep intact all notices".
>
> c) You must license the entire work, as a whole, under this License to anyone who comes into possession of a copy. This License will therefore apply, along with any applicable section 7 additional terms, to the whole of the work, and all its parts, regardless of how they are packaged. This License gives no permission to license the work in any other way, but it does not invalidate such permission if you have separately received it.
>
> d) If the work has interactive user interfaces, each must display Appropriate Legal Notices; however, **if the Program has interactive interfaces that do not display Appropriate Legal Notices, your work need not make them do so.**

**Section 5, the aggregate carve-out:**

> A compilation of a covered work with other separate and independent works, which are not by their nature extensions of the covered work, and which are not combined with it such as to form a larger program, in or on a volume of a storage or distribution medium, is called an "aggregate" if the compilation and its resulting copyright are not used to limit the access or legal rights of the compilation's users beyond what the individual works permit. **Inclusion of a covered work in an aggregate does not cause this License to apply to the other parts of the aggregate.**

**Section 6(d), the option that applies to a downloaded binary:**

> d) Convey the object code by offering access from a designated place (gratis or for a charge), and offer equivalent access to the Corresponding Source in the same way through the same place at no further charge. You need not require recipients to copy the Corresponding Source along with the object code. If the place to copy the object code is a network server, the Corresponding Source may be on a different server (operated by you or a third party) that supports equivalent copying facilities, provided you maintain clear directions next to the object code saying where to find the Corresponding Source. Regardless of what server hosts the Corresponding Source, you remain obligated to ensure that it is available for as long as needed to satisfy these requirements.

Also from Section 6, load-bearing for a `.app`:

> Corresponding Source conveyed, and Installation Information provided, in accord with this section must be in a format that is publicly documented (and with an implementation available to the public in source code form), and must require no special password or key for unpacking, reading or copying.

6(a) and 6(b) are physical-media options. 6(c) is occasional noncommercial pass-along only. 6(e) is peer-to-peer.

**Section 7, additional terms.** The six things you may add, for material you contributed yourself, are (a) different warranty or liability terms, (b) "Requiring preservation of specified reasonable legal notices or author attributions in that material or in the Appropriate Legal Notices displayed by works containing it", (c) "Prohibiting misrepresentation of the origin of that material", (d) limiting publicity use of authors' names, (e) "Declining to grant rights under trademark law for use of some trade names, trademarks, or service marks", and (f) indemnification. Anything else is a "further restriction" and void under Section 10. Practically, only **7(b)** (require downstream to preserve JevFish attribution) and **7(e)** (reserve the JevFish name) matter, and both apply only to material we added.

**Section 13, Remote Network Interaction, in full:**

> Notwithstanding any other provision of this License, if you modify the Program, your modified version must prominently offer all users interacting with it remotely through a computer network (if your version supports such interaction) an opportunity to receive the Corresponding Source of your version by providing access to the Corresponding Source from a network server at no charge, through some standard or customary means of facilitating copying of software. This Corresponding Source shall include the Corresponding Source for any work covered by version 3 of the GNU General Public License that is incorporated pursuant to the following paragraph.

**Section 2, the private-use clause:**

> You may make, run and propagate covered works that you do not convey, without conditions so long as your license otherwise remains in force.

**Section 8, the cure windows:**

> your license from a particular copyright holder is reinstated permanently if the copyright holder notifies you of the violation by some reasonable means, this is the first time you have received notice of violation of this License (for any work) from that copyright holder, and you cure the violation prior to 30 days after your receipt of the notice.

### 4.2 Source distribution on GitHub

Four gaps in the current state, all cheap:

| Requirement | Current state | Fix |
|---|---|---|
| **S4**: give recipients a copy of the licence | `LICENSE` present at root, byte-identical to upstream's (which is the verbatim unmodified AGPL text, diff against gnu.org is 2 lines of line-wrap in the appendix) | nothing to do, do not edit it |
| **S5(a)**: "prominent notices stating that you modified it, **and giving a relevant date**" | Root README line 1 does say "This fork adds JevFish... The original MiroFish code below is kept unchanged as reference", which is prominent and states modification. It carries **no date**, so 5(a) is not currently met | one line: "Modified from 666ghj/MiroFish; JevFish added September 2026." |
| **S5(b)**: prominent notice that the work is under this licence | GitHub's sidebar detects AGPL-3.0 but **neither README says so**. No licence section, no badge | add a `## License` heading plus an AGPL-3.0 badge to both READMEs |
| **S4**: "an appropriate copyright notice" | **There is no copyright holder line anywhere in the repo.** Upstream's `LICENSE` appendix is the unfilled `Copyright (C) <year> <name of author>` template, and upstream has no NOTICE, no AUTHORS, no CONTRIBUTING. So there is literally no upstream copyright line to keep intact | add a `NOTICE` file rather than editing `LICENSE` |

**What "prominent notices ... giving a relevant date" means in practice.** GPLv2 Section 2(a) said "cause the modified files to carry prominent notices stating that you changed the files and the date of any change". GPLv3 and AGPLv3 deliberately moved it from the files to the work: "**The work** must carry prominent notices." That is a real relaxation, and no project inspected stamps dated change notices into individual files. The FSF does separately recommend per-file licence headers, for an unrelated reason (https://www.gnu.org/licenses/gpl-faq.html#NoticeInSourceFile): "You should put a notice at the start of each source file, stating what license it carries, in order to avoid risk of the code's getting disconnected from its license."

**Four real AGPL forks and exactly what they say:**

`nikmcfly/MiroFish-Offline` (2,522 stars, AGPL-3.0) is the most directly useful, being a sibling fork of the same upstream. Subtitle: "Fully local fork of [MiroFish](https://github.com/666ghj/MiroFish), no cloud APIs required. English UI." Then:

> ## Credits & Attribution
>
> This is a modified fork of [MiroFish](https://github.com/666ghj/MiroFish) by [666ghj](https://github.com/666ghj), originally supported by [Shanda Group](https://www.shanda.com/). The simulation engine is powered by [OASIS](https://github.com/camel-ai/oasis) from the CAMEL-AI team.
>
> **Modifications in this fork:**
> - Backend migrated from Zep Cloud to local Neo4j CE 5.15 + Ollama
> - Entire frontend translated from Chinese to English (20 files, 1,000+ strings)
> - All Zep references replaced with Neo4j across the UI
> - Rebranded to MiroFish Offline

That enumerated list is exactly what a 5(a) notice should look like. It is still missing a date, which is the one thing to improve on.

`glitch-soc/mastodon` (AGPL-3.0, a real GitHub fork, 802 stars), line 13: "Mastodon Glitch Edition is a fork of [Mastodon](https://github.com/mastodon/mastodon). Upstream's README file is reproduced below." Bottom of README keeps the **upstream** copyright line unaltered: "Copyright (c) 2016-2026 Eugen Rochko (+ [`mastodon authors`](AUTHORS.md))". It does not add its own.

`hometown-fork/hometown` (AGPL-3.0, 823 stars) has the strongest practice: the H1 is literally "Hometown: a Mastodon fork", and the body says "This is _not_ the official version of Mastodon; this is a separate version (i.e. a fork) maintained by [Darius Kazemi]". That disclaimer is doing trademark work, not licence work, and is worth copying.

`nextcloud/server` (AGPL-3.0-or-later, 36,837 stars) is the mechanically airtight version, being fully REUSE-compliant (https://reuse.software). Its README opens with an SPDX header naming both copyright holders:

```
<!--
 - SPDX-FileCopyrightText: 2016-2024 Nextcloud GmbH and Nextcloud contributors
 - SPDX-FileCopyrightText: 2013-2016 ownCloud, Inc.
 - SPDX-License-Identifier: AGPL-3.0-or-later
-->
```

and every source file carries `SPDX-FileCopyrightText` plus `SPDX-License-Identifier`. The date ranges in those headers satisfy "giving a relevant date" continuously, with no prose change notice anywhere. If a mechanical answer to 5(a) is wanted, this is it.

**The most urgent item is not a licence item at all.** The repo description and homepage are still MiroFish's and point at `mirofish.ai`, and the `og:description` on every shared link reads as MiroFish. AGPL says nothing about repo metadata, so this is not a violation, but it is the exact opposite of Hometown's "this is _not_ the official version" disclaimer, and it is the one thing in the current state likely to annoy a brand owner with 73,886 stars and a commercial site.

### 4.3 A distributed binary (the `.app` or a frozen bundle)

**Option 6(d) is the one to use.** A link to the GitHub repo is sufficient, confirmed by the FSF at https://www.gnu.org/licenses/gpl-faq.html#SourceAndBinaryOnDifferentSites:

> Yes. Section 6(d) allows this. However, you must provide clear instructions people can follow to obtain the source, and you must take care to make sure that the source remains available for as long as you distribute the object code.

Three conditions in practice:

1. **Clear directions next to the object code.** The release page body must carry the pointer, not a README the downloader never sees. Concretely: "Source for this build: `github.com/markiewee/mirofish-jev` at tag `v0.1.3`, commit `abc1234`."
2. **The exact version.** Corresponding Source is the source *of that build*, so name the tag or commit. Bit-for-bit reproducibility is not required: https://www.gnu.org/licenses/gpl-faq.html#MustSourceBuildToMatchExactHashOfBinary, "Complete corresponding source means the source that the binaries were made from, but that does not imply your tools must be able to make a binary that is an exact hash of the binary you are distributing."
3. **"Including scripts to control those activities."** For `JevFish.app` this pulls in `jevfish/launcher/` (`launch.sh`, `make-icon.sh`), `jevfish/web/vite.config.js`, `package.json`, `package-lock.json`, and critically `jevfish/uv.lock`. The bundled `jevfish/web/dist/` is object code whose Corresponding Source is `jevfish/web/src/` plus the build config, all of which is in the repo, and the existing `.github/workflows/jevfish-web.yml` already enforces that `dist` matches `src`. A frozen bundle that vendors site-packages conveys object code for **every AGPL and GPL dependency in it**, which today includes PyMuPDF, so the lockfile is what makes those sources identifiable. Do not omit it.

Also: Corresponding Source "must require no special password or key for unpacking, reading or copying", so a public repo is fine and a private repo or a signup-gated zip is not. The `.app` is almost certainly not a "User Product", so the Installation Information and anti-tivoization paragraphs do not bite.

**Must a GUI app display a copyright notice and a licence notice?** The precise answer is **almost certainly no, because of the second half of Section 5(d), but do it anyway.**

The obligation is 5(d): "If the work has interactive user interfaces, each must display Appropriate Legal Notices". The classic vehicle is an About box, and GPLv3's own appendix says so: "for a GUI interface, you would use an 'about box'". But 5(d) carries an escape hatch: "however, if the Program has interactive interfaces that do not display Appropriate Legal Notices, your work need not make them do so." Code search across MiroFish's frontend returns **one** hit for "license" and it is `package-lock.json`. MiroFish has interactive interfaces and they display no Appropriate Legal Notices, so the escape clause applies squarely and the fork inherits the exemption. This is the most-missed detail in AGPL fork compliance: because upstream never bothered, we do not have to.

Two reasons to do it regardless. First, the PyMuPDF wrinkle: if PyMuPDF is "the Program" for the `jevfish` work, it is a library with **no** interactive interfaces at all, so the precondition "if the Program has interactive interfaces that do not display Appropriate Legal Notices" is arguably not satisfied and 5(d)'s main clause bites unrelieved. That is a reading, not settled law, and no FSF statement resolves it. One About dialog makes the question moot, and dropping PyMuPDF (4.0) makes it moot for free. Second, one About dialog satisfies 5(d), Section 13 and the hosted demo at once.

### 4.4 A hosted demo, and the real problem with it

Reading Section 13 element by element:

| Element | Text | Our case |
|---|---|---|
| Trigger | "if you modify the Program" | see below, this is the crux |
| Who is owed | "all users interacting with it remotely through a computer network" | every visitor, not just registered users, not just the copyright holder |
| What is owed | "the Corresponding Source **of your version**" | the exact build running, not upstream HEAD |
| How | "access ... from a network server at no charge, through some standard or customary means of facilitating copying of software" | a public git repo qualifies; a tarball qualifies |
| Manner | "must **prominently** offer" | a visible link in the running UI, not a README the user never sees |

Section 13 does **not** require publishing to the world at large (only offering to your users), does not require a tarball specifically, and does not require notifying anyone.

The FSF's canonical implementation, from the AGPL-3.0 appendix:

> If your software can interact with users remotely through a computer network, you should also make sure that it provides a way for users to get its source. For example, if your program is a web application, its interface could display a "Source" link that leads users to an archive of the code.

**Does it cover only modified versions? Yes, textually, and hosting an unmodified copy does not trigger it.** Three independent reputable sources agree. Jeffrey Robert Kaufman, Senior Commercial Counsel on Red Hat's open source legal team, https://opensource.com/article/17/1/providing-corresponding-source-agplv3-license: "the source code requirement in AGPLv3 Section 13 is triggered only where the AGPLv3 software has been modified by 'you'" and "many unmodified and standard deployments of software modules under AGPL simply do not trigger Section 13." Kyle E. Mitchell, https://writing.kemitchell.com/2021/01/24/Reading-AGPL: "we download it, put it on a server, run it, and open the ports... we're operating a network server, but we don't have to offer any source code. We didn't modify the program." And the FSF confirms the converse at https://www.gnu.org/licenses/gpl-faq.html#UnreleasedModsAGPL: "The GNU Affero GPL requires that modified versions of the software offer all users interacting with it over a computer network an opportunity to receive the source... the company must release the modified source code."

On what "interacting remotely" means, https://www.gnu.org/licenses/gpl-faq.html#AGPLv3InteractingRemotely: "If the program is expressly designed to accept user requests and send responses over a network, then it meets these criteria. Common examples... include web and mail servers, interactive web-based applications."

**The real problem, flagged.** If we host JevFish and not the upstream MiroFish backend, then as to MiroFish we are not running the Program at all, so MiroFish's Section 13 is not engaged. That part is clean. But **PyMuPDF is AGPL-3.0** and `jevfish/` declares it directly. Combining an AGPL library into a larger Python program is adapting it "in a fashion requiring copyright permission", which makes the combined work a modified version of PyMuPDF, and the hosted JevFish demo is exactly the "interactive web-based application" the FSF names. So **Section 13 is triggered via PyMuPDF even though we never touched a line of MiroFish or PyMuPDF code**, and the source we owe is the Corresponding Source of the whole combined work, meaning all of `jevfish/`. The FSF confirms that scope at https://www.gnu.org/licenses/gpl-faq.html#AGPLv3CorrespondingSource: "if your modified version depends on libraries under other licenses, such as the Expat license or GPLv3, the Corresponding Source should include those libraries (unless they are System Libraries)."

So the hosted demo needs a visible Source link regardless. Mitigation, if you ever want the hosted service free of AGPL: swap PyMuPDF for `pypdf` (BSD-3-Clause) or `pdfminer.six` (MIT). One dependency swap removes an entire independent copyleft obligation.

**Are private config and prompt files Corresponding Source?** Three-part honest answer.

The text is broad: Section 1 covers "all the source code needed to generate, install, and (for an executable work) run the object code and to modify the work". "Needed to run" plausibly reaches a config file the service cannot start without. Kyle Mitchell flags the adjacent question as unresolved and concludes "there are a lot more good questions about GPLv3 and AGPLv3 than there are good answers".

**Secrets are not source.** API keys and credentials are not copyrightable subject matter and no serious commentator reads AGPL as compelling their disclosure. Ship `.env.example` with every key present and blank, which the repo already does.

**Prompt files are where we actually have exposure.** JevFish's prompts are not configuration in the credentials sense, they are the program's behaviour: seven typed Jev questions per turn (stance, outcome, action, plus four speculative Choices) plus the framing text. Those schemas and their surrounding prompts are the thing "needed to run" the work and the thing you would need "to modify the work". A hosted demo whose prompt files are held back from the repo is the weakest link in the compliance story and the likeliest thing a complainant would point at. Keep prompt templates in the repo; keep only keys and hostnames out.

**The cheapest structural answer: make the demo serve its own source.** A route returning the running commit hash and a tarball of the deployed tree, linked from a footer reading "JevFish, AGPL-3.0. Source: github.com/markiewee/mirofish-jev at `<commit>`". That satisfies "prominently offer", makes "your version" mechanically true rather than aspirational, and sidesteps the config-drift question entirely because what you serve is what is running.

**The risk if you get it wrong.** Bradley M. Kuhn of the Software Freedom Conservancy, writing about Truth Social's use of Mastodon (https://sfconservancy.org/blog/2021/oct/21/trump-group-agplv3/): "when you put any site on the Internet licensed under AGPLv3, the AGPLv3 **requires** that you provide (to _every_ user) an opportunity to receive the entire Corresponding Source for the website... If they fail to do this within 30 days, their rights and permissions in the software are automatically and permanently terminated." That maps to Section 8's 30-day first-notice cure window.

**And the safest option of all: do not host an interactive demo.** Ship the static replay described in 1.6 and 2.8. A pre-computed run served as static JSON to a Vue SPA on GitHub Pages is not the Program accepting user requests, so Section 13 does not attach. Upstream already does exactly this. It is free, it never sleeps, it exposes no keys, and it carries no copyleft question.

### 4.5 Private forks, commercial layers, and whether our new code becomes AGPL

**A private fork is completely fine.** Section 2: "You may make, run and propagate covered works that you do not convey, without conditions." FSF, https://www.gnu.org/licenses/gpl-faq.html#GPLRequireSourcePostedPublic: "The GPL does not require you to release your modified version, or any part of it... an organization can make a modified version and use it internally without ever releasing it outside the organization." The catch is that Section 13 does not care about conveying: running a modified version as a public network service triggers the source offer with no copy transferred. So "private fork" means internally used, not publicly hosted.

Contractors matter. https://www.gnu.org/licenses/gpl-faq.html#InternalDistribution: "when the organization transfers copies to other organizations or individuals, that is distribution. In particular, providing copies to contractors for use off-site is distribution." Section 2's second paragraph gives a narrow exception for people "making modifications exclusively for you" working "exclusively on your behalf, under your direction and control", which is a work-for-hire posture rather than a general contractor posture. NDA development is fine (https://www.gnu.org/licenses/gpl-faq.html#DevelopChangesUnderNDA), because the client still gets the AGPL rights.

**A commercial layer: not over MiroFish code, yes over code we wrote.** Section 5(c) is absolute for the covered work, and Section 10 blocks the workarounds ("you may not impose a license fee, royalty, or other charge for exercise of rights granted under this License"). You may sell AGPL software (https://www.gnu.org/licenses/gpl-faq.html#GPLCommercially) but not fold it into a closed product (https://www.gnu.org/licenses/gpl-faq.html#GPLInProprietarySystem: "A system incorporating a GPL-covered program is an extended version of that program"). The three viable shapes:

1. **Hosting and support.** Sell the service, publish the source. Grafana's model, and Khoj's.
2. **Dual licensing, but only if you own all the copyright.** iText is the clean illustration: "dual-licensed, and available under open source (AGPLv3) or commercial license agreements", and "If you distribute your source code under a closed source license (e.g. a commercial license), then you can only use iText if you purchase a commercial iText license" (https://itextpdf.com/how-buy/AGPLv3-license). **We cannot do this with MiroFish code** (we do not own the copyright, there is no CLA). We could with `jevfish/` alone, but only after removing PyMuPDF, which is itself AGPL-or-Artifex-commercial.
3. A genuinely separate proprietary program talking to JevFish over HTTP. Thin, and it rests on the aggregate analysis below.

**Does our new code become AGPL?** There is a defensible answer in our favour, resting on three verified facts.

The test is Section 0's "based on the Program" versus Section 5's aggregate paragraph. The FSF's criterion, https://www.gnu.org/licenses/gpl-faq.html#MereAggregation:

> We believe that a proper criterion depends both on the mechanism of communication (exec, pipes, rpc, function calls within a shared address space, etc.) and the semantics of the communication (what kinds of information are interchanged). If the modules are included in the same executable file, they are definitely combined in one program. If modules are designed to run linked together in a shared address space, that almost surely means combining them into one program. By contrast, pipes, sockets and command-line arguments are communication mechanisms normally used between two separate programs.

Applied:

- **No shared address space.** `jevfish/` has its own `pyproject.toml`, `uv.lock`, `.python-version`, entry point (`jevfish = "jevfish.cli:main"`), Flask server and Vite frontend. Separate process.
- **No code copied.** GitHub code search for `from backend`, `import backend` and `sys.path` scoped to `path:jevfish` returns **0 hits**. It reaches OASIS directly through the public `camel-oasis` PyPI package, not through MiroFish's `backend/`.
- **No runtime communication with the covered work at all.** Not pipes, not sockets. The upstream `backend/` and `frontend/` are inert files in the same git tree.

That is about as strong an aggregate case as can be built: two programs sharing a directory and nothing else. `jevfish/README.md` already states it carefully: "The fork is AGPL-3.0. JevFish is new code that copies no MiroFish source. While it lives in this repo it is distributed under the repo's licence."

Three qualifications. **"MiroFish-style" is fine**: reimplementing the same five-stage pipeline copies an architecture, not expression, and Section 0's "modify" requires copying "in a fashion requiring copyright permission". Reading a design and writing your own code does not. (Caution: if any JevFish file was written by pasting upstream code and editing it, that file **is** a modified version and the aggregate argument fails for the whole thing. Worth a one-time honest audit.) **Distributing both together still leaves the MiroFish half AGPL**, so all of 4.2's notice duties still apply. And **PyMuPDF defeats the point anyway**, so if separability is the goal the order of operations is: drop PyMuPDF first, then split the trees.

### 4.6 The compliance checklist and copy-pasteable notices

Files a well-run AGPL fork should have:

| File | Status | Purpose |
|---|---|---|
| `LICENSE` | present, do not edit | S4 |
| `NOTICE` | **missing** | supplies the copyright notice S4 requires and that upstream never wrote |
| `## License` section in both READMEs | **missing** | S5(b), and 64% of evaluators say licence decides use |
| Dated modification notice | **partially present, no date** | S5(a) |
| `THIRD_PARTY.md` | missing | lists OASIS (Apache-2.0), PyMuPDF (AGPL or Artifex), typesafe-sdk (MIT), Flask (BSD-3), openai (Apache-2.0), mcp (MIT), python-dotenv (BSD-3) |
| Per-file SPDX headers | missing | optional, the Nextcloud/REUSE pattern; the cheapest mechanical answer to 5(a) |
| An About panel or footer in the web UI | missing | not required (5(d) escape clause applies) but satisfies 5(d), S13 and the hosted demo in one |

The FSF's recommended source-file block, from the AGPL-3.0 appendix ("How to Apply These Terms to Your New Programs"):

```
    JevFish: a swarm prediction engine
    Copyright (C) 2026  Mark Wee

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU Affero General Public License as published
    by the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Affero General Public License for more details.

    You should have received a copy of the GNU Affero General Public License
    along with this program.  If not, see <https://www.gnu.org/licenses/>.
```

The SPDX one-liner alternative, which is what Nextcloud actually uses per file:

```python
# SPDX-FileCopyrightText: 2026 Mark Wee
# SPDX-License-Identifier: AGPL-3.0-or-later
```

For the interactive program, the appendix's short notice (the Section 0 "Appropriate Legal Notices" content):

```
JevFish  Copyright (C) 2026  Mark Wee
This program comes with ABSOLUTELY NO WARRANTY.
This is free software, and you are welcome to redistribute it
under certain conditions; see <https://www.gnu.org/licenses/agpl-3.0.html>.
Source: https://github.com/markiewee/mirofish-jev
```

A `NOTICE` file covering the fork provenance, the third parties and the trademark position:

```
JevFish
Copyright (C) 2026 Mark Wee

This work is a modified version of MiroFish
(https://github.com/666ghj/MiroFish), Copyright (C) the MiroFish authors
(github.com/666ghj and contributors), which received support from Shanda Group.
Licensed under the GNU Affero General Public License v3.0; see LICENSE.

MODIFICATIONS (September 2026):
  - Added jevfish/, a new implementation of the five-stage pipeline in which
    TypeSafe Jev makes every simulated person's decision and the language model
    only writes text. Builds a local knowledge graph, so no Zep Cloud account
    is needed. Returns a calibrated probability with a 90% range from polling
    every simulated person, rather than a narrative from a report agent.
  - Added JevFish.app, a macOS launcher.
  - The upstream backend/ and frontend/ directories are retained unchanged as
    reference and are not executed by JevFish.

THIRD-PARTY COMPONENTS:
  - OASIS (camel-oasis), CAMEL-AI, Apache License 2.0.
    https://github.com/camel-ai/oasis
  - PyMuPDF, dual licensed GNU AGPL v3 or Artifex commercial licence.
    https://pymupdf.readthedocs.io
  - typesafe-sdk, MIT. Flask, BSD-3-Clause. openai, Apache-2.0. mcp, MIT.
    python-dotenv, BSD-3-Clause.

TRADEMARKS: "MiroFish" is a mark of its owners. "Jev" and "TypeSafe" are marks
of TypeSafe AI, Inc. "Gemini" and "Google" are marks of Google LLC. Use of
these names in this project is nominative, to identify the upstream project and
the interfaces this software works with. No affiliation or endorsement is
claimed. This licence does not grant rights in any of these marks.
```

Note on OASIS: it is **Apache-2.0**, not AGPL. If a distribution ever vendors OASIS source rather than pip-installing `camel-oasis`, Apache-2.0 Sections 4(b) and 4(c) add their own change-statement and NOTICE-propagation duties. We pip-install, so this is documentation only.

### 4.7 What MiroFish itself requires beyond AGPL: nothing

Verified against the actual files:

- `LICENSE` is the verbatim unmodified AGPL-3.0 text. No added clauses, no Section 7 additional terms, no trademark reservation, no attribution requirement.
- No `NOTICE`, no `CONTRIBUTING.md`, no `AUTHORS`, no CLA (all 404 on both `main` and `master`).
- The README has **no licence section at all**, no licence badge, no copyright line, no trademark statement, no required credit line.
- Code search across the whole upstream repo: 4 hits for "AGPL", 1 for "Affero", 3 for "copyright" (in `scripts/star_history.py`, `LICENSE`, and `.github/star-history/THIRD_PARTY_NOTICES.md`). **Zero per-file licence headers. Zero licence display in the frontend.**
- The only attribution-shaped content is upstream crediting **its** dependency: "MiroFish's simulation engine is powered by **[OASIS](https://github.com/camel-ai/oasis)**, We sincerely thank the CAMEL-AI team for their open-source contributions!" That is upstream crediting CAMEL-AI, not upstream requiring anything of us.
- **No copyright holder is identified anywhere.** This is unusual and is why the `NOTICE` block above attributes to "the MiroFish authors (github.com/666ghj and contributors)" rather than a named entity.

"MiroFish" is nonetheless a live commercial brand: `mirofish.ai`, `@mirofish_ai` on X and Instagram, a Discord, a Trendshift badge, recruiting at `mirofish@shanda.com`, and "strategic support and incubation from Shanda Group". No registered mark found, but common-law rights plainly exist at 73,886 stars, and AGPL grants no trademark rights (Section 7(e) exists precisely so a licensor *can* reserve marks, so the fact they have not expressly reserved anything does not give us the name).

The community norm is that forks keep the MiroFish name and nobody objects. GitHub repo search for `mirofish in:name` returns **506 repos**, all the notable ones AGPL-3.0: `nikmcfly/MiroFish-Offline` (2,522), `SCTY-Inc/mirofish-cli` (310, a company shipping under the name), `tt-a1i/MiroFish-local` (152), `enpixeles-ai/MiroFish-ESP` (51), `BEKO2210/MiroFish-DE` (26). Every one keeps "MiroFish" in the repo name with no visible pushback.

---

## 5. Naming and discoverability

### 5.1 "JevFish" collides with nothing

| Namespace | Result | Method |
|---|---|---|
| GitHub repos, `jevfish` | **0 results** | `gh api search/repositories?q=jevfish` |
| GitHub users/orgs, `jevfish` | **0 results** | `gh api search/users?q=jevfish` |
| PyPI, `jevfish` | **404, available** | `pypi.org/pypi/jevfish/json` |
| PyPI, `jev-fish`, `jevfish-cli`, `mirofish` | **all 404, available** | same |
| npm, `jevfish` | **404, available** | `registry.npmjs.org/jevfish` |
| npm text search, `jevfish` | 0 total | npm search API |
| DNS, `jevfish.com` / `.ai` / `.dev` / `.app` | **no A record, no NS record on any of the four** | `dig +short A` and `dig +short NS` |
| Web search, `"JevFish"` | only our own repo and PRs | WebSearch |
| Any company or product named JevFish | **none found** | WebSearch |

`jevfish/pyproject.toml` already declares `name = "jevfish"`, so `uv publish` would take it. Grab it on PyPI (and npm, defensively) now: both are free, the name is distinctive, and the PyPI name is what makes `uvx jevfish` possible.

One phonetic note: "JevFish" reads as "Jellyfish" at a glance, and Jellyfish is a real B2B engineering-analytics company (jellyfish.co). Not a legal problem (different goods, different spelling) but a discoverability tax, since people will mistype it.

### 5.2 "Jev" and "TypeSafe" as marks

TypeSafe's model **is** called Jev. The endpoint is `POST https://api.typesafe.ai/v1/systemone` with the early-access route `jev-latest`, described as a "System One model" answering typed questions (Choice, Score, Noul) with calibrated probabilities rather than text (https://docs.typesafe.ai/introduction, https://typesafe.ai/blog/introducing-system-one-models-and-jev). The name comes from William Stanley Jevons, of Jevons paradox.

**No evidence of any "Jev" registration, and the timing makes one very unlikely.** TypeSafe AI exited stealth on **16 September 2026**, two days before this research, with a USD 40m seed led by DCVC, founded by Diogo Almeida (ex-OpenAI) with Erik Gafni and Sasha Sheng (https://siliconangle.com/2026/09/16/typesafe-ai-exits-stealth-with-40m-to-build-ai-for-use-by-software/, https://www.theregister.com/ai-and-ml/2026/09/16/typesafe-ai-debuts-model-for-machines-that-plays-doom/5296711). Their Terms of Use is dated **14 September 2026**.

**Method caveat, stated plainly.** USPTO could not be queried directly: `tmsearch.uspto.gov` serves only a JavaScript app and its API endpoints returned S3 errors, while `trademarks.justia.com`, `uspto.report` and `trademarkia.com` all returned 403 to automated fetches. So "no registration" rests on press and absence of evidence, not a docket search. **Run `JEV` in classes 9 and 42 by hand at https://tmsearch.uspto.gov before the name goes on anything commercial.** An application filed in the last few weeks would also not be publicly searchable yet. Common-law rights in "Jev" for AI model services plainly exist regardless, given the launch publicity.

Pre-existing unrelated "Jev" uses, which weaken any claim to the bare syllable: npm has a placeholder package literally named `jev` (v0.0.0, published 16 June 2021, no description); `jevajs/Jeva` (220 stars); `GoldenGnu/jeveassets` (193 stars, an EVE Online asset manager). PyPI `jev` is free.

**The most useful evidence is what third parties actually do.** `jev in:name` returns **4,034 repos**, and within days of launch there is a whole ecosystem putting the bare mark in project names:

| Repo | Stars | What it is |
|---|---|---|
| `browser-use/jev-ultrafast` | 3,261 | an established project using the bare mark |
| `tamaratran/fast-jev-compaction` | 1,602 | Claude Code plugin scoring tool calls with Jev |
| `vinnylarouge/jevlike` | 759 | |
| `jarrodwatts/jev-trader` | 637 | "One AI trade decision every Monad block" |
| `Anil-matcha/awesome-jev-by-typesafe` | 436 | MIT; topics `jev`, `typesafe-ai`, `system-one-models` |
| `devagrawal09/jev-review` | 197 | "built with TypeSafe Jev" |

Topic counts: `jev` **113** repos, `typesafe` **524**, `typesafe-ai` 34, `system-one-models` 7, `typesafe-jev` 3.

**Read on risk:** using "Jev" in a project name is established, tolerated practice with no visible pushback, and TypeSafe is actively cultivating it (the awesome list is titled "awesome-jev-by-typesafe"). Their Terms of Use contains **no** trademark, brand-usage, publicity, attribution or naming clause at all, and no restriction on saying "powered by Jev", so there is no contractual constraint today, only trademark law. The residual risk is low but real and entirely within TypeSafe's gift to change: a company two days out of stealth with USD 40m and a coined mark will eventually publish a brand policy, and "Jev" plus suffix is the pattern such policies usually restrict. Contact points for written permission if wanted: `support@typesafe.ai`, `hello@typesafe.ai`.

**Does the old Typesafe Inc matter? No.** Typesafe Inc, the Scala and Akka company, **renamed itself Lightbend in February 2016** and kept the trademarks. A Justia owner page lists TYPESAFE, TYPESAFE ACTIVATOR and TYPESAFE CONDUCTR under Lightbend, Inc., covering "computer programs for creating other computer programs and computer programs for implementing a computer programming language" (https://trademarks.justia.com/owners/lightbend-inc-3265134; the page itself returned 403, so serial numbers and current status are unverified). The namespace is still live: topic `typesafe` has 524 repos, PyPI `typesafe` is taken, and `com.typesafe:config` remains one of the most-depended-on Java libraries in existence.

Why it does not touch us: we are not naming anything "TypeSafe". We use the word once, descriptively, to say whose model we call. The party with a potential problem is TypeSafe AI, Inc., who picked a name a live registrant already holds in class 9 software. That is their risk, not ours, but it has one practical consequence: **if TypeSafe AI is ever forced to rebrand, "JevFish" survives and every "TypeSafe" reference in our docs goes stale.** Another argument for keeping the vendor's name in prose rather than in the product name.

### 5.3 Nominative use: naming a project after the API it uses

The governing US test is nominative fair use from *New Kids on the Block v. News America Publishing*, 971 F.2d 302 (9th Cir. 1992). The Ninth Circuit's model jury instruction (https://www.ce9.uscourts.gov/jury-instructions/civil/chapter-15/15-26-defenses-nominative-fair-use/):

> First, the product or service in question must be one not readily identifiable without the use of the trademark; second, only so much of the mark or marks may be used as is reasonably necessary to identify the product or service; and third, the user must do nothing that would, in conjunction with the mark, suggest sponsorship or endorsement by the trademark holder.

Applied: prong 1 passes easily (there is no way to say "this uses TypeSafe's System One model" without saying "Jev"; Google's own open source casebook makes exactly this point, https://google.github.io/opencasebook/trademarks/). Prong 3 is fixable with a disclaimer. **Prong 2 is where "JevFish" is weakest**: using "Jev" in prose is necessary, building it into the product name is not.

Also worth knowing from the same casebook: **an open source licence grants no trademark rights.** It quotes Apache-2.0 ("This License does not grant permission to use the trade names, trademarks, service marks, or product names of the Licensor"); AGPL-3.0 is the same by omission, and Section 7(e) exists precisely so a licensor may decline to grant them. So forking MiroFish under AGPL gives us no right to the MiroFish name either.

The casebook records the PHP Group's formulation as the model, and it is directly on point:

> You may indicate that your software works in conjunction with PHP by saying "Foo for PHP" instead of calling it "PHP Foo" or "phpfoo"

"JevFish" is the `phpfoo` pattern. The approved pattern is `Foo for Jev`. In practice this is a matter of degree, and the community evidence in 5.2 shows the fused pattern is currently ubiquitous and unpoliced in AI tooling. Options, in descending order of safety:

1. Keep `JevFish` with a clear disclaimer and "built on TypeSafe Jev" in the subtitle. Defensible, and where we are.
2. Rename to something without "Jev" and describe it as "built on TypeSafe Jev". Strongest position, loses the launch-moment SEO that "Jev" currently buys (113 repos on the topic, two days old).
3. Keep `JevFish` but never use TypeSafe's logo, colours or wordmark styling, and never write it so it looks like a TypeSafe first-party release.

Recommendation: keep JevFish, add the disclaimer, do not build a logo lockup resembling TypeSafe's. The name is doing real discovery work right now and that window is worth more than the marginal risk.

**Google's Gemini brand rules: may you say "Gemini" in a project name? No.** Google's guidance for products using Google APIs (https://partnermarketinghub.withgoogle.com/brands/google/use-cases/product-co-branding/#referring-to-google-apis) says:

> Use plain text. For example, you could say your product or service "works with," "is compatible with," or "integrates with" a Google product.

> If you're using our trademarks, include a legal line in the footer or other appropriate area of your product, website, or other materials.

> Make sure the reference doesn't imply something bigger like an endorsement, affiliation, or official partnership with Google.

On icons: "Use product icons only when necessary" and "Don't use product icons by themselves". The app-naming rule is blunter in Google's app-identity guidance (https://support.google.com/cloud/answer/13804963 and the OAuth brand verification docs): application names should not include any Google product names or modified Google trademarks, and should not use Google icons or logos as part of your icon or logo.

Practical consequences, all easy: never name anything `GeminiFish`; "JevFish works with Google Gemini" is safe and "JevFish for Gemini" is borderline; do not use the Gemini spark logo anywhere; use the exact product name "Google Gemini", not "Gemini AI". Put a legal line in the footer (the `NOTICE` block in 4.6 already has one). And since the config layer accepts any OpenAI-compatible model, the least-entangled and most accurate framing is "**works with Google Gemini and any OpenAI-compatible model**". Also read the Gemini API Additional Terms of Service (https://ai.google.dev/gemini-api/terms) before a public demo ships, particularly on whether a free-tier key may serve a public endpoint.

### 5.4 GitHub topics: real counts and a ranked 20

GitHub's limit, verbatim: "Add no more than 20 topics", "Use lowercase letters, numbers, and hyphens", "Use 50 characters or less." Counts below are live from the search API on 18 September 2026 (page figures run 1 to 2 percent higher than API figures for the same slug).

| slug | repos | note |
|---|---|---|
| `python` | 885,086 | too generic to earn a slot |
| `llm` | 133,885 | curated topic |
| `ai-agents` | 93,660 | |
| `fastapi` | 93,565 | **we use Flask. Do not tag this.** |
| `flask` | 77,317 | the accurate one |
| `simulation` | 26,649 | curated; game-physics heavy (bullet3, JoltPhysics) |
| `gemini` | 24,218 | |
| `local-first` | 21,185 | tempting, but we still call two cloud APIs |
| `multi-agent` | 16,432 | MetaGPT, deer-flow |
| `knowledge-graph` | 8,840 | upstream uses it |
| `forecasting` | 6,853 | prophet, statsmodels, autogluon |
| `prediction` | 5,941 | |
| `llm-agents` | 5,558 | agenticSeek, nanobot |
| `synthetic-data` | 2,960 | contested vocabulary, pulls the privacy crowd |
| `survey` | 2,434 | **form builders (formbricks, heyform). Wrong intent.** |
| `agent-based-modeling` | 1,448 | mesa, AgentSociety |
| `market-research` | 1,281 | thin field, so rankable |
| `swarm-intelligence` | 773 | **MiroFish and MiroFish-Offline are both here.** Highest relevance per repo of any slug |
| `agent-based-simulation` | 678 | mesa, concordia, **camel-ai/oasis** |
| `social-simulation` | 134 | concordia, AgentSociety |
| `multi-agent-simulation` | 123 | upstream uses it |
| `jev` | 113 | the TypeSafe ecosystem tag, two days old |
| `generative-agents` | 98 | awesome-llm-powered-agent, concordia |
| `opinion-dynamics` | 72 | precise, academic, near-empty |
| `typesafe-ai` | 34 | |
| `synthetic-users` | 25 | no notable repos, an open field |
| `public-opinion-analysis` | 18 | upstream uses it |
| `persona-simulation` | 12 | TinyTroupe territory |
| `system-one-models` | 7 | |
| `focus-group` | 6 | nearly empty |
| `synthetic-respondents` | 6 | **the market's canonical noun, and nearly empty. Claim it.** |
| `mirofish` | 23 | the derivative ecosystem tag |

**Recommended 20, ranked.** The logic is a barbell: half the slots for high-volume ambient reach, half for near-empty precise tags where we can be the top result on day one, plus three that place us next to the exact repos our audience already browses (`swarm-intelligence` for MiroFish derivatives, `agent-based-simulation` for OASIS, `jev` for the TypeSafe ecosystem).

| # | topic | repos | why |
|---|---|---|---|
| 1 | `swarm-intelligence` | 773 | upstream and every sibling derivative live here; best signal-to-noise of any slug |
| 2 | `agent-based-simulation` | 678 | `camel-ai/oasis` is listed here and OASIS is our actual engine |
| 3 | `multi-agent` | 16,432 | best volume-to-relevance ratio in the high-volume tier |
| 4 | `llm-agents` | 5,558 | the developer-intent term |
| 5 | `generative-agents` | 98 | academically anchored (Park et al., UIST 2023); small enough to rank |
| 6 | `social-simulation` | 134 | the umbrella term the CS literature uses; next to concordia and AgentSociety |
| 7 | `forecasting` | 6,853 | the outcome word, cleaner intent than `prediction` |
| 8 | `llm` | 133,885 | ambient reach for one slot |
| 9 | `simulation` | 26,649 | curated, high volume, literally what it does |
| 10 | `prediction` | 5,941 | upstream-adjacent; MiroFish-Offline uses it |
| 11 | `jev` | 113 | free distribution inside a launch-moment ecosystem |
| 12 | `agent-based-modeling` | 1,448 | catches the Mesa and NetLogo crowd looking for the LLM version |
| 13 | `synthetic-respondents` | 6 | the market's canonical noun, topic empty, instant number one |
| 14 | `market-research` | 1,281 | the buyer word, thin field |
| 15 | `opinion-dynamics` | 72 | precise, academic, near-empty |
| 16 | `knowledge-graph` | 8,840 | stage 1 is a local knowledge graph; upstream tags it |
| 17 | `gemini` | 24,218 | real volume and accurate. Tag only, never in the name |
| 18 | `persona-simulation` | 12 | TinyTroupe's term, near-empty, exactly descriptive |
| 19 | `flask` | 77,317 | accurate stack tag. **Not `fastapi`** |
| 20 | `mirofish` | 23 | 23 repos, and every visitor browsing MiroFish derivatives sees us |

Swap candidates for more academic weight: drop `gemini` and `knowledge-graph`, add `system-one-models` (7) and `multi-agent-simulation` (123).

Deliberately excluded: `fastapi` (inaccurate, and puts us in front of the wrong audience), `survey` (form builders), `synthetic-data` (contested; one vendor in this market publishes a post arguing against the term, and it pulls the data-generation and privacy crowd), `python` (noise), `local-first` (misleading while two cloud APIs are required), `prediction-market` (reads as trading bots), `calibration` (camera calibration owns it), `ai-agents` (huge but `multi-agent` plus `llm-agents` already cover the intent).

**Also fix the description.** GitHub search weights it heavily and it is still MiroFish's. Suggested, under the 350-character cap: "Swarm prediction engine: simulate a crowd of LLM personas, poll every one of them with TypeSafe Jev, and get a calibrated forecast with a 90% range. Local-first, no Node needed. Fork of MiroFish."

### 5.5 The vocabulary the audience actually uses

**The commercial category exists, is well funded, and has settled on specific nouns.**

| Company | Their own words | Category noun |
|---|---|---|
| **Synthetic Users** (syntheticusers.com) | "User research at the speed of AI"; "Every brain is a synthetic respondent"; "generative agent simulations" | synthetic respondents, synthetic research |
| **Aaru** (aaru.com) | "Behavior simulation at the scale of the real world"; "Ask people, and they answer. Simulate them, and they act" | simulated populations, behavior simulation. Explicitly avoids "synthetic respondents". Series A at a USD 1bn headline valuation, Redpoint led, Accenture invested |
| **Simile** (simile.com) | "Simulate every decision at scale"; "Building a foundation model for human behavior" | Stanford spinout by Joon Sung Park, Michael Bernstein and Percy Liang, the *Generative Agents* authors. USD 100m Series A led by Index, Feb 2026. **The most important entrant** |
| **Viewpoints AI** (viewpoints.ai) | "AI market research with simulated personas"; "Stanford-validated: 88% match with real studies" | simulated personas |
| **Verve** (addverve.com) | "Verve Intelligent Personas & Simulations (VIPS)"; "synthetic populations/panels". Publishes "Why We Don't Talk About 'Synthetic Data' (And Why You Shouldn't Either)"; cites Gartner's category name "synthetic population and behavioral simulation" | personas and simulations |
| **Evidenza** (evidenza.ai) | "AI Market Research for Impossible Audiences"; "the world's first synthetic research platform"; "synthetic digital twins"; "impersonas" | synthetic customers |
| **Yabble** (yabble.com) | "Virtual Audiences", "AI Personas answering any business question" | virtual audiences |
| **Fairgen** (fairgen.ai) | "premium simulated audiences"; "directional research, not a replacement for field studies" | synthetic data, simulated audiences |
| **Roundtable** (roundtable.ai) | **gone, and inverted.** 301s to poh.org, "Proof of Human, PBC (formerly Roundtable AI)": "Prove every user is real in real time" | the counter-category: bot detection in survey panels |

Trade-body evidence that buyers exist: Greenbook runs a supplier directory titled "Top Suppliers of Synthetic/AI-Augmented Sample" listing 22 vendors (https://www.greenbook.org/market-research-firms/synthetic-sample-providers), plus a "Synthetic Qualitative Research with AI Probing" category.

Strength order of the terms: **synthetic respondents** is the industry's canonical noun (Synthetic Users, Fairgen, Greenbook, NIQ, SurveyMonkey, QuestionPro, Quirks all use it). **synthetic research** / **synthetic market research** is the strongest category phrase. **AI personas** / **simulated personas** is the most search-friendly because it is plain English. **digital twin of your customer** is the enterprise term. **simulated audiences** is marketer-facing where "respondent" is researcher-facing. **behavior simulation** / **synthetic population** is the frontier framing and closest to a forecasting tool.

**Search-demand evidence, phrase by phrase** (SERP composition rather than absolute volume, since that needs a paid tool; ranked listicles only get written where there is lead value):

- **"synthetic respondents"**: strongest. Full commercial SERP plus mainstream research brands (Greenbook, NIQ, SurveyMonkey, QuestionPro, Quirks), multiple ranked listicles. **The noun to lead with.**
- **"AI focus group"**: highest plain-language commercial intent. Dedicated domains and four-plus competing listicles. Caveat: about half the SERP is transcript-analysis software (ATLAS.ti, Looppanel), not simulated participants.
- **"synthetic panel"**, **"AI panel"**: solid. Qualtrics has a pillar page on it, which is itself a volume signal.
- **"LLM persona simulation"**: low volume, **near-pure developer intent**, SERP is entirely GitHub (microsoft/TinyTroupe, awesome-llm-human-simulation, and the live `persona-simulation` topic page). **The best phrase for a README.**
- **"generative agents simulation"**: medium, academically anchored, best bridge between the literature and the commercial category. Synthetic Users uses the exact phrase in its own copy.
- **"synthetic survey"**: medium and split. The SERP is dominated by critical academic work (Cambridge *Political Analysis*, PNAS). Good for credibility with researchers, weak for buyers.
- **"simulated respondents"**: the neutral sibling. Fewer vendors own it, so cheaper to rank for while still understood.
- **"synthetic users research"**: brand-dominated, and polluted by a second meaning (agents that QA your app). The real signal is that the establishment wrote rebuttals, which only happens for terms with reach: NN/g, "Synthetic Users: If, When, and How to Use AI-Generated 'Research'" (https://www.nngroup.com/articles/synthetic-users/).
- **"agent based prediction market"**: **weakest, avoid.** The SERP is trading bots and quantitative finance. Anyone reading that phrase in our README will think we built a Polymarket bot.

**The academic vocabulary that carries credibility:**

| Term | Source | Use it for |
|---|---|---|
| **generative agents** | Park, O'Brien, Cai, Morris, Liang, Bernstein, "Generative Agents: Interactive Simulacra of Human Behavior", UIST 2023, https://arxiv.org/pdf/2304.03442, code https://github.com/joonspk-research/generative_agents (22,121 stars) | the highest-traffic academic term, because the repo is a landmark |
| **silicon sampling** | Argyle, Busby, Fulda, Gubler, Rytting, Wingate, "Out of One, Many: Using Language Models to Simulate Human Samples", *Political Analysis* 31(3): 337-351, 2023, https://arxiv.org/abs/2209.06899 | the most-searched academic term, with teaching material built on it |
| **algorithmic fidelity** | coined in the same Argyle et al. paper | the term of art for "is the simulation any good". If JevFish claims calibration, this is the word that signals we know the literature |
| **homo silicus** | Horton, "Large Language Models as Simulated Economic Agents", NBER WP 31122, https://arxiv.org/abs/2301.07543 | a one-line framing device, not a keyword |
| **generative agent simulations of 1,000 people** | Park et al. 2024, arXiv 2411.10109, repo joonspk-research/genagents. 1,052 participants, two-hour interviews, roughly 85% accuracy on GSS replication | the number every vendor cites |
| counter-literature | Bisbee et al., "Synthetic Replacements for Human Survey Data? The Perils of Large Language Models", *Political Analysis*; "Social Simulations with Large Language Model Risk Utopian Illusion", https://arxiv.org/pdf/2510.21180 | a README that names the sceptics reads more credible than one that does not |

**The ten queries our actual user types.** Builders search mechanism words, buyers search product words, and the gap is that mechanism queries currently return awesome-lists rather than working tools.

1. `generative agents github` (lands on joonspk-research/generative_agents)
2. `llm agent based social simulation github` (lands on awesome-lists and `topics/social-simulation`)
3. `simulate survey responses with llm python` (lands on **expectedparrot/edsl**, the strongest existing open-source incumbent for this exact job)
4. `open source synthetic respondents` (**poorly served today. This is the gap.**)
5. `llm persona simulation framework` (lands on microsoft/TinyTroupe, 7,571 stars)
6. `predict public opinion llm agents github` (lands on ElectionSim, FudanDISC/SocioVerse)
7. `silicon sampling code` (lands on teaching notebooks)
8. `synthetic focus group open source` (**returns commercial listicles today. Second gap.**)
9. `agent based model llm population python` (the Mesa-literate user)
10. `multi agent llm forecasting open source` (**currently fails the searcher entirely**)

Closest existing open-source competitors to know: `expectedparrot/edsl`, `microsoft/TinyTroupe` (7,571), `google-deepmind/concordia` (1,709), `tsinghua-fib-lab/AgentSociety` (1,293), `FudanDISC/SocioVerse`, and `maisymylod/quorum`, which describes itself as a population simulation engine that synthesises a representative population from census marginals, predicts its answers, and scores against real published survey results. Quorum is the nearest match to JevFish's pitch and worth reading before the README is finalised.

**What to put in the README.** Lead with mechanism words, because that is what developers type and there is almost no competition for them: "LLM agent population simulation", "generative agents", "synthetic respondents", "silicon sampling", "social simulation", "opinion forecasting". Add buyer words as secondary aliases so the repo also surfaces in commercial searches: "AI focus group", "synthetic panel", "simulated audience", "concept testing", "AI market research". Name the papers explicitly, because the academic terms carry credibility the commercial ones have already burned through. Avoid "agent based prediction market" and "synthetic data". Mention "synthetic users" but do not build on it: a brand owns it and a second meaning competes for it.

And foreground the one differentiator none of the commercial vendors can claim: JevFish returns **a calibrated probability with a 90% range from polling every simulated person**, not a narrative from a report agent. Every vendor above hedges with "directional research". Calibration is the honest claim, and "algorithmic fidelity" is the phrase that signals you know what the claim costs.

---

## 6. Recommended plan for JevFish

Ranked by impact per unit of effort. Costs are engineering hours at the stated confidence, plus money where any is owed. Everything in tiers 1 and 2 is free in money terms.

### Tier 1: do today, under two hours total, zero money

| # | Change | Effort | Why |
|---|---|---|---|
| 1 | **Leave the fork network.** Settings, Danger Zone, "Leave fork network". All three preconditions hold (public, 17 MB, no child forks) and the fork has 0 stars, 0 issues, 0 watchers so nothing is lost. Git history is preserved, so AGPL provenance survives | **10 min** | The repo currently returns 0 results in GitHub search and appears on no topic page. Nothing else in this plan matters while `fork: true` is set. Evidence: `nikmcfly/MiroFish-Offline` (detached, 10 topics) 2,522 stars versus `EleutheroiEdge/mirofish-offline` (fork, 0 topics) 0 stars, identical description |
| 2 | **Rewrite the About block.** Description to the one in 5.4, Website to whatever we own (or blank, never `mirofish.ai`), and add the 20 topics from 5.4 | **15 min** | Zero topics means zero inbound discovery, and GitHub weights the description heavily in search. Every link currently unfurls as MiroFish |
| 3 | **Delete the three star/watcher/fork badges pointing at `666ghj/MiroFish`, the Trendshift badge for upstream repo 16144, and `.github/workflows/update-star-history.yml`** (18,211 bytes charting upstream's stars) | **15 min** | We are currently advertising someone else's numbers. Also drops the badge count toward Trockman's 5-badge inflection point |
| 4 | **Add the date to the fork notice** ("Modified from 666ghj/MiroFish; JevFish added September 2026") and a `## License` section with an AGPL-3.0 badge to both READMEs | **20 min** | AGPL Section 5(a) currently unmet (no date) and 5(b) unmet (no licence notice anywhere in prose). 64% of evaluators say licence decides whether they use a project |
| 5 | **Add the `NOTICE` file from 4.6** plus a `THIRD_PARTY.md` | **20 min** | Supplies the Section 4 copyright notice that neither we nor upstream has, and records the trademark position for MiroFish, Jev, TypeSafe and Gemini |
| 6 | **Claim `jevfish` on PyPI and npm** | **15 min** | Both free today. The PyPI name is what makes `uvx jevfish` possible and the whole install story depends on it |

### Tier 2: this week, roughly 12 to 20 hours, zero money

| # | Change | Effort | Why |
|---|---|---|---|
| 7 | **Swap PyMuPDF for `pypdf`.** Five lines in `service.py:56-63`, already a lazy import | **1 hr** | Best value-per-line change in the report. Removes an entire independent AGPL copyleft obligation (PyMuPDF is "Dual Licensed, GNU AFFERO GPL 3.0 or Artifex Commercial License") **and** cuts 54 MB off the install. pypdf is BSD-3-Clause, 10,208 stars |
| 8 | **Make `camel-oasis` an optional extra.** `[project.optional-dependencies] oasis = ["camel-oasis==0.2.5"]`, default to the existing `lite` platform, keep the import lazy (verified: it already is) | **2 hrs** | Measured: 1.1 GB / 161 packages becomes 118 MB / 59 packages, and 66 MB with change 7. Cold install 27.44 s becomes 4.35 s. `camel-oasis` drags `sentence-transformers`, which drags torch 2.14.0 (553 MB), transformers (59 MB), scikit-learn (34 MB), scipy (82 MB), sympy (41 MB), plus `pre-commit` and `pytest` as runtime deps |
| 9 | **Make `uvx` the primary install path.** Move `web/dist` to `src/jevfish/web/dist`, change `api.py:20` to resolve relative to the module, move `.env` and `data/` to `platformdirs.user_data_dir("JevFish")` with a checkout fallback, add `webbrowser.open()` plus a `--headless` flag to `cmd_serve`, bundle one example seed | **4 to 6 hrs** | Verified end to end: with those changes the wheel goes from 34 files with no UI to 40 files serving `GET /` at 200 with the real 1,102-byte index and the 301 KB JS bundle, in a 117 MB venv with no `camel-oasis`. Before the fix `WEB_DIST` resolves to `lib/python3.12/web/dist` and the UI 404s. The resolution from `git+...#subdirectory=jevfish` already works today, verified against the live repo |
| 10 | **Rewrite the top 30 lines of the README** to the structure in 3.1, with the keyless demo command as the first runnable line | **3 hrs** | First fenced block is currently at line 112 against a 46-repo median of 60 and Ollama's 15. Brand ratio is 37 MiroFish references to 4 JevFish. Copy `nikmcfly/MiroFish-Offline`'s structure: banner, H1, one bold "fork of X, here is what changed" line, one italic what-it-is line, 4 badges, then an original-versus-this-fork table. Lead with the numbers MiroShark puts above the fold: **$0.00006 per agent turn, about 1 second per turn**, and the calibrated 90% range |
| 11 | **Lead with the keyless demo.** `uvx --from "git+..." jevfish demo --platform lite --rounds 3` runs the whole five-stage pipeline in about ten seconds with no API keys and produces a real calibrated prediction. Verified | **included in 9 and 10** | This is the "it works" moment and it is currently undiscoverable. No competitor listed in 5.5 lets you see output without a signup |
| 12 | **Record a hero GIF**, 300 to 900 KB, committed to `docs/assets/`, referenced with `<img src>` so it renders on PyPI too. `ffmpeg` with `palettegen`/`paletteuse` is already installed; add `gifski` or `gifsicle -O3 --lossy=80` | **3 hrs** | 44 of 46 high-star adjacent repos have media, at a median of line 3. Real sizes: lazygit 665 KB compressed, zoxide 627 KB, Open WebUI 281 KB PNG. Following uv's example, consider a **calibration plot with a one-line caption** rather than a UI screenshot: it is the one claim no commercial vendor makes |
| 13 | **Attach a release to `v0.1.2`** (or cut `v0.1.3`) with a **DMG**, not a ZIP, under a version-free asset name so `releases/latest/download/JevFish-macos.dmg` is stable. `hdiutil create -volname JevFish -srcfolder ... -format UDZO` needs no dependencies. Put the AGPL 6(d) source pointer (repo plus tag plus commit) in the release body | **2 hrs** | ZIP cannot be signed, inherits quarantine on every extracted file, and triggers App Translocation, which the launcher already fights with `mdfind`. DMG makes the Gatekeeper dialog's default button **Open** instead of Move to Trash, and is the only container that can later carry a stapled ticket. 6(d) requires "clear directions next to the object code" |
| 14 | **Automate the release** with `softprops/action-gh-release@v3` (not v2, EOL on Node 20) on `tags: ["v*.*.*"]`, `permissions: {}` at workflow level with `contents: write` on the publish job only | **2 hrs** | See 3.3 for the working YAML |

### Tier 3: next two weeks, roughly 10 to 16 hours, zero money

| # | Change | Effort | Why |
|---|---|---|---|
| 15 | **Publish a static replay demo on GitHub Pages.** Export one completed run to JSON, point the existing Vue app at it, deploy. Upstream does exactly this at `666ghj.github.io/mirofish-demo/` (Vue SPA, 1,359-byte index, no backend) | **4 hrs** | Free forever, never sleeps, exposes no keys, and **carries no AGPL Section 13 obligation** because a static replay is not the Program accepting user requests over a network. Gives a "See a finished run" button above the fold |
| 16 | **Social preview image**, 1280x640, under 1 MB, PNG | **1 hr** | Currently the auto-generated card with MiroFish's description. This is what renders on X, LinkedIn, Slack, Discord and HN unfurls |
| 17 | **Community health files**: CONTRIBUTING, CODE_OF_CONDUCT, SECURITY, one issue form asking LLM provider and model, whether `TYPESAFE_API_KEY` is set, OS, Python version, and **how the app was launched** (bundle versus terminal) | **2 hrs** | Gets `health_percentage` to roughly 87, matching uv and marimo. Low conversion impact (ollama scores 62 at 181,191 stars) but the last field saves a round trip on the known macOS Desktop/Documents/Downloads failure |
| 18 | **A `## Why` and a `## Status` section**, and name the five use cases the way TinyTroupe does | **2 hrs** | Only 25.7% of READMEs explain why and 21.4% state status, so both differentiate cheaply. The current README explains the mechanism (five stages, seven typed questions) and never says what a buyer would use it for |
| 19 | **Publish to PyPI**, so the install line becomes `uvx jevfish` | **2 hrs** | Shortest possible install, and the `<img>` hero renders on the PyPI page too |
| 20 | **Docker image on GHCR**, documented as the power-user and Linux path, never the headline | **3 hrs** | Free on GHCR, and it doubles as the deploy artifact. Never lead with it: Docker Desktop costs the user roughly 6 GB and a licence question (free only under 250 employees **and** under USD 10m revenue) |
| 21 | **MkDocs Material docs site on GitHub Pages**, using the workflow in 3.6 | **4 hrs** | What both uv and marimo run, fingerprinted live. Free, pip-installable into the environment that already exists, no Node toolchain. Only worth doing once the README is doing its job |

### Tier 4: only if demand appears

| # | Change | Cost | Verdict |
|---|---|---|---|
| 22 | **An About panel or footer in the web UI** carrying the short notice from 4.6 plus a source link | 2 hrs, USD 0 | Not required (AGPL 5(d)'s escape clause applies, because upstream's UI displays no Appropriate Legal Notices) but it makes the PyMuPDF ambiguity moot and covers Section 13 if an interactive demo ever ships. Do it if an interactive demo ships |
| 23 | **Apple Developer Program, Developer ID signing, notarization** | **USD 99/yr** plus 10 to 20 hrs for a first signed DMG, plus 10 to 25 hrs more to make the bundle self-contained enough for the seal to mean something | **Defer.** Signing today's 148 KB script wrapper certifies an empty shell around 1 GB downloaded after launch. A script-only bundle is also the hardest thing to notarize cleanly, and notarization requires hardened runtime, which collides with a venv full of third-party `.so` files. There is no free notarization path |
| 24 | **PyInstaller or Nuitka freeze** | 30 to 60 hrs plus the USD 99 | **Defer.** Inherits hidden-import, `importlib.metadata` and hardened-runtime `MemoryError` failure classes. Worth revisiting **after** changes 7 and 8, because a 66 MB tree freezes to roughly 90 to 150 MB instead of 300 to 700 MB |
| 25 | **Tauri v2 sidecar** | 60 to 120 hrs plus the USD 99 | **Defer.** The 8.6 MiB shell is free; the frozen Python inside it is not, and the canonical FastAPI reference (`dieharders/example-tauri-v2-python-server-sidecar`, 126 stars) documents that you must hand-roll subprocess shutdown because Tauri only knows the PyInstaller bootloader's pid |
| 26 | **An interactive hosted demo** | HF Spaces USD 0 on CPU Basic (48-hour sleep, roughly 2-minute wake) or USD 9/mo PRO; Fly.io roughly USD 3 to 6/mo with scale-to-zero | **Defer in favour of change 15.** If it ever ships, copy CAMEL-AI's `camel-agents` Space and make the visitor paste their own keys, which removes both the inference bill and the key-exposure risk. It also triggers AGPL Section 13, so it needs the footer source link from change 22 |
| 27 | **Rename away from "Jev"** | 4 hrs plus lost launch-moment SEO | **Do not.** "JevFish" is the `phpfoo` pattern that Google's casebook advises against, but the practice is ubiquitous and unpoliced in the Jev ecosystem (`browser-use/jev-ultrafast` at 3,261 stars uses the bare mark), TypeSafe's Terms of Use contains no naming clause, and the `jev` topic is two days old with 113 repos. Keep the name, add the disclaimer, never use TypeSafe's logo or wordmark styling. Do run `JEV` in classes 9 and 42 by hand at tmsearch.uspto.gov before it goes on anything commercial |

### The one-line summary of the plan

Detach the fork and give it its own identity (tier 1, under two hours), cut the install from 1.1 GB to 66 MB and make `uvx` work (tier 2, about a day), then lead the README with the keyless ten-second demo that already exists. Everything expensive, signing, freezing, Tauri, hosted inference, stays deferred until those three prove demand.

