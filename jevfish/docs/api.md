# JevFish HTTP API

Base URL: `http://127.0.0.1:5055`. All bodies are JSON unless noted.
- **Errors:** `{"error": "message"}` with status 400 (bad input or a missing earlier step), 404 (unknown id) or 503 (LLM or Jev unavailable).
- **Long jobs:** these return a **task** with status 202. Poll `GET /api/tasks/<id>` until `status` is `done`, `failed` or `cancelled`.

```ts
type Task = { id: string; kind: "graph"|"prepare"|"run"|"report"; project_id: string;
  status: "queued"|"running"|"done"|"failed"|"cancelled"; progress: number /*0..1*/; message: string;
  result: any; error: string|null; created_at: string; updated_at: string }
```

## Meta
- `GET /api/health` returns `{ok, judge: "jev"|"fake"|"missing TYPESAFE_API_KEY", jev_model, llm: "<model>"|"fake"|"missing LLM_API_KEY", llm_fallbacks: string[], llm_base_url, data_dir}`.
- `GET /api/tasks/<tid>` returns a Task. `POST /api/tasks/<tid>/cancel` cancels it and returns the Task.

## Projects
```ts
type Project = { id: string; name: string; requirement: string; created_at: string; updated_at: string;
  stage: "new"|"seeded"|"graph"|"prepared"; sources: {name: string; chars: number; added_at: string}[] }
type Overview = Project & { seed_chars: number; graph_stats: GraphStats|null; has_frame: boolean;
  crowd_stats: {size: number; stakeholders: number; public: number}|null; runs: Run[]; tasks: Task[] }
```
- `GET /api/projects` returns `Project[]`, newest first.
- `POST /api/projects` takes `{name, requirement, seed_text?}` and returns a Project (201). `requirement` is the prediction question and is required.
- `GET /api/projects/<pid>` returns an Overview.
- `PATCH /api/projects/<pid>` takes `{name?, requirement?}` and returns a Project.
- `DELETE /api/projects/<pid>` returns `{ok: true}`.
- `GET /api/projects/<pid>/seed` returns `{text}`.
- `POST /api/projects/<pid>/seed` takes `{text, source?}` and returns a Project.
- `POST /api/projects/<pid>/files` takes multipart field `file` (one or more of .txt, .md or .pdf, 25 MB maximum) and returns a Project.

## Stage 1: knowledge graph
- `POST /api/projects/<pid>/graph` returns a Task (202). It needs seed text.
- `GET /api/projects/<pid>/graph` returns a Graph.
- `GET /api/projects/<pid>/graph/search?q=...&limit=10` returns `{kind: "node"|"edge", score, item}[]`.
```ts
type Graph = { ontology: {entity_types: {name, description, is_actor}[]; relation_types: {name, description}[]};
  nodes: {id: string; name: string; type: string; summary: string; mentions: number; degree: number}[];
  edges: {id: string; source: string /*node id*/; target: string; type: string; fact: string}[];
  stats: GraphStats; errors: string[] }
type GraphStats = { chunks: number; failed_chunks: number; nodes: number; edges: number; types: Record<string, number> }
```

## Stage 2: frame and crowd
- `POST /api/projects/<pid>/prepare` takes `{public_size?: 60, max_stakeholders?: 20, seed?: 0}` and returns a Task (202). It needs the graph.
- `GET /api/projects/<pid>/frame` returns a Frame.
- `PUT /api/projects/<pid>/frame` takes a Frame (validated and normalised) and returns the Frame. Use it to edit talking points and variants.
- `GET /api/projects/<pid>/crowd` returns a Crowd.
```ts
type Frame = { question: string; subject: Record<string, string>;
  outcome: {instructions: string; criteria: {true: string; false: string}|null};
  stance: {instructions: string; levels: string[] /*2..10, most negative first*/};
  talking_points: {id: string; text: string; side: "pro"|"con"|"neutral"}[];
  opening_posts: {author: string; text: string; talking_point: string|null}[];
  variants: {id: string; label: string; subject: Record<string, string> /*overrides*/}[] }
type Agent = { agent_id: number; kind: "stakeholder"|"public"; name: string; username: string; bio: string; persona: string;
  segment: string; attributes: Record<string, string>; entity_id: string|null; stance_hint: "for"|"against"|"neutral"|"mixed";
  influence: number; activity: number; follows: number[] }
type Crowd = { agents: Agent[]; segments: {name, share, description, activity, attributes}[]; stats: {stakeholders, public} }
```

## Stage 3: runs
```ts
type RunConfig = { platform?: "reddit"|"twitter"|"lite" /*reddit default*/; variants?: string[] /*empty = all*/;
  rounds?: 12; minutes_per_round?: 60; start_hour?: 8; agents_per_round_min?: 8; agents_per_round_max?: 20;
  peak_hours?: number[]; peak_multiplier?: 1.5; quiet_hours?: number[]; quiet_multiplier?: 0.3;
  poll_rounds?: number[]|null /*default [0, rounds/2, rounds]; 0 = before round 1*/;
  injections?: {round: number /*1..rounds*/; text: string; author?: string /*agent name; default News desk*/}[];
  seed?: 0; concurrency?: 16; max_requests?: number|null; feed_size?: 6; log_requests?: true }
type Run = { id: string; project_id: string; config: RunConfig; created_at: string; updated_at?: string;
  status: "queued"|"running"|"done"|"partial"|"failed"|"cancelled"; progress?: number; message?: string;
  requests?: number; cache_hits?: number; planned_requests?: number; variants?: string[]; task_id?: string;
  started_at?: string; finished_at?: string; error?: string;
  summary?: Summary|null; report_ready?: boolean }
```
- `POST /api/projects/<pid>/estimate` takes a RunConfig and returns `{planned_requests, cap, est_input_tokens, est_cost_usd, polls}`.
- `GET /api/projects/<pid>/runs` returns `Run[]`, newest first.
- `POST /api/projects/<pid>/runs` takes a RunConfig and returns `{run: Run, task: Task}` (202).
- `GET /api/projects/<pid>/runs/<rid>` returns a Run with `summary` (null until finished) and `report_ready`. While running, `progress` and `message` update every round.
- `POST /api/projects/<pid>/runs/<rid>/cancel` returns a Run.
- `GET /api/projects/<pid>/runs/<rid>/actions?since=0&limit=200` returns `Action[]`. This is the live feed: poll with `since = number already received`.
- `GET /api/projects/<pid>/runs/<rid>/polls` returns `{variant, round, agent_id, stance, stance_confidence, outcome_p, cached}[]`.
```ts
type Action = { variant: string; round: number /*0 = opening posts*/; hour: number; at: string; agent_id: number; agent_name: string;
  action: "create_post"|"create_comment"|"quote_post"|"like_post"|"dislike_post"|"repost"|"like_comment"|"follow"|"do_nothing";
  args: Record<string, any>; ok: boolean; error?: string;
  content?: string /*text of posts, comments and quotes*/; target_excerpt?: string; target_author?: string;
  point?: string|null /*talking point id*/; stance?: number; outcome_p?: number; jev_action?: string;
  action_probabilities?: Record<string, number>; opening?: true; injection?: true; llm_text?: boolean }
type PollSummary = { round: number; n: number; mean_outcome: number; expected_yes: number; variance: number;
  low: number; high: number /*90% range*/; likely_yes: number; stance_mean: number; stance_hist: number[] }
type SegmentRow = { value: string; n: number; mean_outcome: number; expected_yes: number; mean_stance: number }
type VariantSummary = { id: string; label: string; subject: Record<string, string>; polls: PollSummary[];
  baseline: PollSummary|null; final: PollSummary|null;
  segments: Record<string /*"kind" | "group" | attribute name*/, SegmentRow[]>;
  points: {id, text, side, posts, comments, quotes, total}[];
  top_posts: {post_id, author, content, likes, dislikes, shares, comments: {author, content, likes}[], engagement}[];
  most_engaged: {agent_id, name, posts, engagement}[];
  timeline: ({round: number} & Record<string, number>)[]; action_counts: Record<string, number>; posts_total: number; partial: boolean }
type Summary = { run_id; project_id; created_at; question: string; outcome_instructions: string; stance_levels: string[];
  config: RunConfig; crowd: {size, stakeholders, public}; variants: VariantSummary[];
  comparisons: {variant, baseline, diff_expected_yes, low, high, diff_mean_outcome, verdict: "higher"|"lower"|"within noise"}[];
  judge: {model, fake, requests, cache_hits, input_tokens, est_cost_usd}; llm: {calls, prompt_tokens, completion_tokens, failures, by_task}|null;
  partial: string|null }
```

## Stage 4: report
- `POST /api/projects/<pid>/runs/<rid>/report` returns a Task (202). It needs a finished run.
- `GET /api/projects/<pid>/runs/<rid>/report` returns `{markdown: string, data: object, created_at}`, or 400 if there is no report yet.

## Stage 5: interaction
- `POST /api/projects/<pid>/runs/<rid>/chat` takes `{agent_id: number, message: string, variant?: string}` and returns `{agent_id, variant, reply, history: {role: "user"|"assistant", content, at}[]}`.
- `GET /api/projects/<pid>/runs/<rid>/chat/<agent_id>?variant=A` returns the history array.
- `POST /api/projects/<pid>/runs/<rid>/ask` takes `{question: string, variant?: string}` and returns an Ask. This polls every person with Jev; it takes a few seconds.
- `GET /api/projects/<pid>/runs/<rid>/ask` returns the previous asks, `Ask[]`.
```ts
type Ask = { question; instructions; variant; at;
  summary: {n, mean_outcome, expected_yes, low, high, likely_yes};
  segments: Record<string, SegmentRow[]>; most_yes: {name, p}[]; most_no: {name, p}[]; requests: number; cache_hits: number }
```
