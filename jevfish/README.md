# JevFish

A MiroFish-style swarm prediction engine in which TypeSafe's **Jev** makes every decision a simulated person makes. You feed it documents and a question. It builds a knowledge graph and a crowd, runs the crowd on a simulated social platform, and reports a calibrated prediction you can question afterwards.

It lives inside our fork of [666ghj/MiroFish](https://github.com/666ghj/MiroFish). The upstream `backend/` and `frontend/` folders are left as reference; JevFish is new code in this folder.

## How it works

| Stage | What happens | Who does it |
| --- | --- | --- |
| 1. Graph | Designs an ontology for the question, extracts entities and relations chunk by chunk, merges them into a local graph with search | LLM for extraction, code for merging. No Zep account needed |
| 2. Crowd | Writes the frame: outcome question, stance scale, talking points, opening posts, variants to compare. Builds stakeholder personas from the graph, samples the public from segments, and wires a follow graph | LLM writes, code samples |
| 3. Simulate | Runs every variant on CAMEL-AI OASIS (Reddit or Twitter, the platform MiroFish uses) or a fast in-memory platform. Each scheduled person reads their feed, and **Jev** answers one request per turn. News can be injected at any round. **Jev** polls the whole crowd at chosen rounds | Jev decides; the LLM only phrases posts Jev chose to write |
| 4. Report | Numbers first: expected yes with a 90% range, shift over time, groups, talking points, top posts, variant comparison. Then a narrative that may only cite those numbers | Jev numbers, LLM narrative |
| 5. Ask | Chat with any simulated person, or ask the whole crowd a new yes/no question and get a calibrated count back | LLM chat, Jev crowd poll |

Each simulated turn is a single Jev request containing seven typed questions:
- **stance** (Score): how the person now feels.
- **outcome** (Noul): the probability of the predicted behaviour.
- **action** (Choice): what the person does. The options are limited to what the feed allows.
- Four speculative Choices, which code uses only when the chosen action needs them: which talking point to make, which post to react to, which comment to like, and whom to follow.

## Differences from MiroFish

- **Agent turns.** MiroFish makes one LLM call per turn and parses free text. JevFish makes one Jev request per turn with typed answers and probabilities. At launch pricing that is about US$0.00006 a turn, and it takes about 1 second from Singapore.
- **The prediction.** In MiroFish it is a narrative from a report agent. In JevFish it is the sum of calibrated probabilities from a poll of every person, with a range.
- **Knowledge graph.** MiroFish needs a Zep Cloud key; JevFish builds a local graph.
- **Interviews.** MiroFish's interviews only work while its simulation process is still alive. JevFish chat works any time after a run.
- **Variants.** JevFish can compare variants of a decision on the same crowd.

## Run it

Double-click **JevFish.app** in this folder. Nothing else is needed: no terminal, no Homebrew, no Node.

- The first start installs uv and the Python packages (about 1 GB) with no admin password, then opens JevFish in your browser. It took 30 seconds on a fast connection and can take a few minutes on a slow one.
- Later starts take a few seconds, and reuse a JevFish that is already running.
- It uses the first free port from 5055 to 5064. Logs are in `~/Library/Logs/JevFish/`.
- If something goes wrong, a dialog says what, with a button that opens the log.

Then the app asks for two keys on its Setup screen:
- **Jev** from [console.typesafe.ai](https://console.typesafe.ai). A typical run costs about US$0.04.
- **A language model**: a free [Gemini key](https://aistudio.google.com/apikey), or any OpenAI-compatible service (address, model, key).

"Save and check" stores them in `jevfish/.env` (readable only by you) and checks both with calls that cost nothing. There is also a **test mode** that runs every screen on deterministic fakes, so you can look around without keys. Every number it shows is made up.

**If macOS blocks the app**, it came from a downloaded ZIP, which macOS quarantines. Open System Settings, Privacy & Security, scroll to the JevFish message and click Open Anyway. A `git clone` has no such block.

### From the terminal

```sh
cd jevfish
uv sync
cd web && npm install && npm run build && cd ..   # only if you change the web app; the built one is committed

export TYPESAFE_API_KEY=...          # or set the keys in the app
export GEMINI_API_KEY=...            # or LLM_API_KEY + LLM_BASE_URL + LLM_MODEL for any OpenAI-compatible model
uv run jevfish serve                 # http://127.0.0.1:5055
```

- **Whole pipeline from the terminal:** `uv run jevfish demo` runs it on `examples/lazybee-cleaning.md`. That file uses example figures, not real Lazybee data.
- **No keys:** `JEVFISH_FAKE_JUDGE=1 JEVFISH_FAKE_LLM=1 uv run jevfish serve` runs everything on deterministic fakes, the same as test mode.
- The API answers only requests addressed to this computer, and refuses changing requests sent from another website. `serve --host 0.0.0.0` turns that off and warns, which also exposes the key screen to your network.

Settings:
- `JEVFISH_DATA_DIR` sets where data is stored (default `jevfish/data`).
- `JEVFISH_MAX_REQUESTS` caps Jev requests per run (default 5000).
- `JEVFISH_LLM_WORKERS` sets parallel LLM calls (default 4).
- `LLM_FALLBACK_MODELS` lists models to rotate to on 429 or 503 errors. For Gemini the default is `gemini-2.5-flash,gemini-flash-lite-latest`.

Data is stored on disk. Each project has a folder under `data/projects/<id>` containing:
- `seed.md`, `graph.json`, `frame.json` and `crowd.json`
- an answer cache, `verdicts.sqlite`
- `runs/<id>/`, which holds `summary.json`, `actions.jsonl`, `polls.jsonl`, `requests.jsonl` (every Jev state, question and answer), `report.json`, chats and asks, plus a platform database per variant

## Cost and speed

Jev costs US$0.042 per million input tokens, and output is free. A turn is about 1,200 to 1,400 tokens.

A default run of 80 people and 12 rounds sends about 600 requests:
- 12 rounds of up to 30 active people.
- Three polls of all 80 people.

That comes to roughly US$0.04 per variant. The estimate endpoint shows the figure before you start. Reruns with the same settings are answered from the cache for free.

## Tests

```sh
uv run pytest -q          # offline: fake LLM and fake Jev, lite platform and real OASIS Reddit
```

## Limits

- The crowd is synthetic. It is built from the documents and the LLM's idea of the public.
- The 90% range only covers the chance element of who says yes. It does not cover model error.
- Jev's calibration has no published metric. Before trusting a forecast, backtest on a decision whose outcome you know.
- Jev is hosted in the US, and TypeSafe's terms allow it to keep telemetry. Do not put personal data in the seed documents.
- Twitter mode downloads the `Twitter/twhin-bert-base` model (about 500 MB) on first use. Reddit mode needs no model.

## Licence

The fork is AGPL-3.0. JevFish is new code that copies no MiroFish source. While it lives in this repo it is distributed under the repo's licence.
