# DataPilot AI Architecture

## Request flow

```text
Browser dashboard
      |
      v
FastAPI API + static UI
      |
      +--> CSV validation/storage ---------> local CSV files
      |
      +--> profile + automatic insights ---> Pandas calculations
      |
      +--> question router
               |
               +--> deterministic allow-listed tools
               |      +--> Pandas analytics
               |      +--> constrained SQLite GROUP BY queries
               |
               +--> optional OpenAI tool selection
                        |
                        +--> same deterministic tools

Analysis metadata/history ----------------> SQLite
```

## Core design choices

1. **Evidence first** — numeric claims are produced by deterministic analytics functions rather than free-form model generation.
2. **No arbitrary code execution** — the agent can only call approved functions. Generated SQL is a constrained aggregation query assembled from validated column identifiers.
3. **Local-first reliability** — every core demo workflow works without an API key. Optional provider failure falls back to local rules.
4. **Inspectable reasoning surface** — the UI exposes tool names, arguments, summaries and aggregation SQL where relevant.
5. **Bounded uploads** — CSV size, row count, column count and header validity are checked before storage.
6. **Deploy as one service** — FastAPI serves both API and static dashboard, avoiding a second frontend deployment and CORS complexity.

## Storage model

- Uploaded/demo CSVs: `DATA_DIR`
- Dataset metadata/history: SQLite at `STATE_DB`
- Render free deployment: treat both as ephemeral demo state
- Future SaaS version: object storage for datasets + PostgreSQL for durable application state

## Agent evaluation

`backend/evaluation/run_evaluation.py` runs 30 natural-language benchmark questions against the synthetic dataset. It measures intended tool selection and grounded completion. This is a bounded routing benchmark, not a claim of universal natural-language accuracy.
