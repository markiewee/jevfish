# JevFish Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Our own version of MiroFish's five-stage "predict anything" pipeline, with TypeSafe Jev making every decision the simulated people make.

**Architecture:** We keep MiroFish's architecture and write our own code for it, in a new `jevfish/` package inside the fork. The upstream `backend/` and `frontend/` folders stay untouched as reference.

- **Stage 1, seed to knowledge graph.** An LLM extracts entities and relations. The graph is stored locally, with no Zep.
- **Stage 2, graph to crowd and frame.** Stakeholder personas come from the graph, and public personas are sampled from LLM-proposed segments. The frame holds the prediction question, stance scale, outcome question, talking points, opening posts and optional variants.
- **Stage 3, simulation.** It runs on the same social platform MiroFish uses (CAMEL-AI OASIS, Reddit or Twitter), with a lightweight in-memory platform for tests. Each active person's turn is one Jev request, carried out as an OASIS `ManualAction`. The LLM only writes the words of a post or comment once Jev has decided to post one. Whole-crowd Jev polls at set rounds produce the calibrated prediction.
- **Stage 4, report.** Jev numbers (expected yes with a 90% range, stance shift, segments, spread of talking points) plus an LLM narrative that may only use those numbers.
- **Stage 5, interaction.** Chat with any simulated person (LLM plus their persona and history), and ask the whole crowd any yes/no question (Jev).

**Tech stack:** The same pieces MiroFish uses.
- Python 3.12 with Flask.
- The OpenAI SDK against any OpenAI-compatible LLM (default: Gemini `gemini-flash-latest` via Google's OpenAI endpoint, on Mark's existing key, free tier).
- `camel-oasis` 0.2.5 and `camel-ai` 0.2.78.
- Vue 3 and Vite for the UI.
- New: `typesafe-sdk` 0.6.0 for Jev.
- pytest.

**Approval:** Mark, 17 Sep 2026. He said "fork the mirofish github and actually build our own predictive model using the same stuff they use but built on Jev", then "basically understand the architecture and build our own version" and "based on Jev". The session goal is "build me a fully functioning version". That counts as approval to build; the PRD and PR summary go to Mark inline with the result.

---

## PRD

### Problem
MiroFish (666ghj/MiroFish, AGPL-3.0, 73.8k stars) makes an LLM call for every simulated person's turn, and it needs a Zep Cloud account. Its prediction is a narrative written by an LLM, with no calibrated numbers behind it. Mark wants the same capability on Jev: cheap, fast and quantitative.

### What MiroFish does, and what JevFish does instead

| Stage | MiroFish | JevFish |
| --- | --- | --- |
| 1 Graph | Zep Cloud builds the graph from seed text, using an LLM ontology | An LLM builds the ontology and extracts entities per chunk; the graph is stored locally as JSON with keyword search; no signup |
| 2 Setup | LLM writes OASIS profiles and a simulation config | LLM writes stakeholder personas, public segments and the frame; code samples the crowd and follow graph |
| 3 Simulate | OASIS with `LLMAction` for every active agent | OASIS with Jev-decided `ManualAction`; the LLM only phrases posts Jev chose to write; whole-crowd Jev polls |
| 4 Report | A ReportAgent with Zep search tools writes the prediction | Jev numbers first, then an LLM narrative grounded in those numbers and sample posts |
| 5 Interact | Interview agents through OASIS and the LLM | Chat with any person through the LLM, plus "ask the crowd" through Jev polls |

### Requirements
1. **Projects.** Create a project with a name, a prediction requirement, and seed text (pasted, or uploaded as .txt, .md or .pdf). Projects persist on disk.
2. **Graph (async task).**
   - Build an ontology of at most 10 entity types and 10 relation types.
   - Chunk the seed, extract entities and relations in parallel, and merge them by normalised name.
   - Expose nodes, edges and search.
3. **Prepare (async task).**
   - **Frame:** question, subject facts, outcome (a yes/no about `agent` and `subject`), 5 stance levels, 12 to 30 talking points, 1 to 3 opening posts by named stakeholders, and 0 to 3 variants.
   - **Crowd:** stakeholders from the graph, plus public members sampled from segments.
   - **Settings:** activity levels, and a follow graph where influence attracts followers.
   - The frame is editable through the API.
4. **Run (async task).**
   - **Platform:** `reddit` (the default, and needs no model download), `twitter` (downloads twhin-bert on first use), or `lite`.
   - **Schedule:** rounds, minutes per round, and agents per round, with peak and off-peak multipliers as in MiroFish.
   - **Injections:** news posts at chosen rounds.
   - **Variants:** each variant runs against the same crowd with its own platform database.
   - **Budget:** a request cap and an answer cache.
   - **Logs:** every Jev request and answer, every action, and every poll.
   - **Progress:** live status and a feed of posts.
5. **Report (async task).**
   - Numbers: the final-poll expected yes with a 90% range per variant, the shift from baseline to final, stance histograms, and a breakdown by segment and by stakeholder versus public.
   - Talking-point spread, the most-engaged people, and variant differences with a range.
   - An LLM narrative in markdown that may only use numbers from the bundle it is given.
6. **Interact.**
   - Chat with a simulated person, keeping a history per person.
   - Ask the crowd a yes/no question, answered as a Jev poll of every person, with expected yes and a segment breakdown.
7. **UI.** A Vue 3 single page served by Flask at `/`. It has a project list and a workspace with 5 steps (Graph, Crowd, Simulate, Report, Ask), a graph view, a live simulation feed, a round chart and a report view.
8. **Ops.**
   - `uv run jevfish serve` starts everything.
   - `/api/health` reports which keys are present.
   - The app refuses to run without `TYPESAFE_API_KEY` unless `JEVFISH_FAKE_JUDGE=1` is set.
   - The LLM client retries and falls back across models on 429 and 503 errors.

### Non-goals
- Zep Cloud, Neo4j and multi-user auth.
- Running MiroFish's original backend.
- Real tenant or guest data.

### Licence note
The fork is AGPL-3.0. JevFish is new code written for this repo, and it copies no MiroFish source, so it could be relicensed later. As long as it sits in the fork, it ships under the repo's AGPL.

### Success criteria
- Offline tests pass, using a fake LLM, a fake judge, and both the lite platform and real OASIS.
- A live end-to-end run on a real seed document works through the API and the UI: graph, prepare, run on Reddit OASIS with real Jev and Gemini, report, chat and ask.

---

## File map (`jevfish/`)

| File | Responsibility |
| --- | --- |
| `pyproject.toml` | uv project and `jevfish` script |
| `jevfish/config.py` | Environment settings and data dir |
| `jevfish/llm.py` | OpenAI-compatible chat and JSON calls with retries and model fallback; `FakeLLM` for tests |
| `jevfish/judge.py` | Jev judge, fake judge, cache and budget meter (from jev-swarm) |
| `jevfish/store.py` | Project and run folders, JSON read and write |
| `jevfish/tasks.py` | Background tasks with progress and status |
| `jevfish/graph.py` | Stage 1: ontology, chunking, extraction, merge, search |
| `jevfish/frame.py` | Stage 2: prediction frame |
| `jevfish/crowd.py` | Stage 2: stakeholder and public personas, follow graph, activity |
| `jevfish/policy.py` | Stage 3: Jev state and questions per agent, sampling, mapping to platform actions |
| `jevfish/writer.py` | Post and comment wording (LLM, with a talking-point fallback) |
| `jevfish/platforms/base.py` | Platform protocol and shared types (`FeedPost`, `Act`) |
| `jevfish/platforms/lite.py` | In-memory platform |
| `jevfish/platforms/oasis_platform.py` | OASIS Reddit and Twitter adapter |
| `jevfish/simulate.py` | Round loop, schedule, injections, polls, logs, cancellation |
| `jevfish/metrics.py` | Aggregation and intervals |
| `jevfish/report.py` | Stage 4 numbers and narrative |
| `jevfish/interact.py` | Stage 5 chat and crowd poll |
| `jevfish/api.py` | Flask app and routes; serves `web/dist` |
| `jevfish/cli.py` | `serve`, `demo` |
| `web/` | Vue 3 and Vite UI |
| `tests/` | One file per module, plus an API end-to-end test on fakes |

## Tasks
- [ ] 1. Scaffold the uv project, config, store and tasks (with tests).
- [ ] 2. `llm.py` with retry, fallback and FakeLLM (with tests).
- [ ] 3. Port `judge.py` and `metrics.py` from jev-swarm (with tests).
- [ ] 4. `graph.py` (tests with FakeLLM).
- [ ] 5. `frame.py` and `crowd.py` (tests).
- [ ] 6. Platform base, lite and OASIS adapter (tests; OASIS runs locally with no network).
- [ ] 7. `policy.py`, `writer.py` and `simulate.py` (tests on the lite platform and on OASIS Reddit).
- [ ] 8. `report.py` and `interact.py` (tests).
- [ ] 9. `api.py` and `cli.py` (Flask test client end to end on fakes).
- [ ] 10. Vue UI (build, served by Flask, browser QA).
- [ ] 11. A live end-to-end run with real Jev and Gemini on a real seed, then fix what breaks.
- [ ] 12. README, push to the fork, log everything.
