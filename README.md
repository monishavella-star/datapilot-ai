# DataPilot AI v1.1

**Evidence-first AI data analyst for CSV files.** DataPilot turns an uploaded dataset into a profile, charts, data-quality checks, natural-language analysis, saved history, and a downloadable report. It works fully without a paid AI key; optional OpenAI tool-calling can be enabled later.

## Why this is a strong portfolio project

DataPilot is not a chatbot wrapped around a CSV. Numeric answers come from deterministic analytics tools. The optional LLM is allowed to choose tools and explain results, but it cannot execute arbitrary SQL/Python or invent dataset values. The app also exposes calculation steps and generated aggregation SQL so an interviewer can inspect how an answer was produced.

### Implemented features

- CSV upload and validation: UTF-8, maximum 5 MB, 50,000 rows and 80 columns by default.
- Automatic schema discovery: numeric, categorical and date-like columns.
- Dashboard KPIs, responsive SVG line/bar charts, automatic evidence-backed findings and a data preview table.
- Data-quality diagnostics: completeness, missing cells, duplicates and constant columns.
- Deterministic natural-language analysis for:
  - dataset summaries;
  - grouped total/average ranking;
  - monthly/daily trends;
  - month-over-month comparisons;
  - month-change driver decomposition by dimensions such as region/category;
  - descriptive statistics;
  - Pearson correlation;
  - IQR-based potential outlier detection.
- Calculation trace for every answer, including generated safe group-by SQL where applicable.
- SQLite-backed analysis history per dataset.
- Markdown report export including recent questions.
- Dataset delete API and history-clear API.
- Synthetic 960-row e-commerce demo dataset.
- Optional OpenAI Responses API function-calling mode with automatic deterministic fallback.
- FastAPI interactive API documentation at `/docs`.
- Dockerfile, Docker Compose and GitHub Actions CI.
- 17 automated API/integration/evaluation tests.
- 30-question deterministic agent benchmark with measured tool-selection and grounded-completion scores.
- Security headers (CSP, frame denial, no-sniff, permissions policy) and no-store API caching.
- Render-ready `render.yaml` for a free Docker web service in Singapore.

## Fastest Windows setup

### Requirements

- Python **3.11 or newer**
- Internet access only for the first dependency installation

### Run

1. Extract this project.
2. Double-click `setup-windows.bat` once.
3. Double-click `start-windows.bat`.
4. Your browser opens `http://127.0.0.1:8000`.

The application automatically loads fictional demo data. Click **Upload CSV** to analyze your own file.

## macOS / Linux

```bash
chmod +x run.sh
./run.sh
```

Then open `http://127.0.0.1:8000`.

## Manual setup

```bash
cd backend
python -m venv .venv
```

Activate it:

```bash
# Windows CMD
.venv\Scripts\activate

# macOS/Linux
source .venv/bin/activate
```

Install and run:

```bash
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

## Questions to try

With the bundled demo dataset:

```text
Why did revenue decrease in March?
Show monthly revenue trend
Which category has the highest revenue?
Which region has the lowest average profit?
Show statistics for revenue
Find outliers in profit
What is the correlation between revenue and profit?
Check missing values and duplicates
```

For uploaded data, the dashboard generates suggestions from the detected columns.

## Optional AI mode

**You do not need this to run DataPilot.** Local mode already performs real calculations.

On Windows, run `setup-ai-windows.bat`. Then copy/edit `backend/.env` and set:

```env
OPENAI_API_KEY=your_key_here
OPENAI_MODEL=gpt-5.4-mini
```

Restart the server. In AI mode, the model receives dataset metadata and derived tool output, not the complete raw CSV. Column names and aggregate results can still be sent to the provider, so do not use sensitive data without reviewing your privacy requirements.

If AI configuration, networking or the provider fails, DataPilot automatically returns to deterministic local calculations so the application remains usable.

## Tests

```bash
cd backend
python -m pip install -r requirements-dev.txt
python -m pytest -q
python -m compileall -q app
```

Expected test result for this release:

```text
17 passed
```

Run the agent benchmark:

```bash
python evaluation/run_evaluation.py
```

Current bundled benchmark: **30 cases, 100% intended tool selection, 100% grounded completion**. See `EVALUATION.md` for scope and limitations.

## Docker

```bash
docker compose up --build
```

Open `http://127.0.0.1:8000`. Docker Compose stores datasets/history in a persistent named volume.

## API

| Method | Endpoint | Purpose |
| --- | --- | --- |
| GET | `/api/health` | Health, version, limits and analysis mode |
| POST | `/api/demo` | Create the synthetic demo dataset |
| POST | `/api/upload` | Upload CSV multipart field `file` |
| GET | `/api/datasets/{id}` | Dataset profile |
| GET | `/api/datasets/{id}/insights` | Deterministic automatic findings |
| DELETE | `/api/datasets/{id}` | Delete local dataset + history |
| POST | `/api/ask` | Ask a natural-language data question |
| GET | `/api/datasets/{id}/history` | Read saved analysis history |
| DELETE | `/api/datasets/{id}/history` | Clear analysis history |
| GET | `/api/datasets/{id}/report` | Download Markdown report |

Interactive OpenAPI docs: `http://127.0.0.1:8000/docs`.

## Project structure

```text
datapilot-ai/
├── README.md
├── ARCHITECTURE.md
├── DEPLOYMENT.md
├── EVALUATION.md
├── PORTFOLIO_GUIDE.md
├── SECURITY.md
├── render.yaml
├── Dockerfile
├── docker-compose.yml
├── setup-windows.bat
├── setup-ai-windows.bat
├── start-windows.bat
├── run.sh
├── sample_data/
│   └── sample_sales_2026.csv
├── .github/workflows/ci.yml
└── backend/
    ├── requirements.txt
    ├── requirements-ai.txt
    ├── requirements-dev.txt
    ├── .env.example
    ├── app/
    │   ├── main.py
    │   ├── agent.py
    │   ├── analytics.py
    │   ├── repository.py
    │   ├── store.py
    │   ├── sample.py
    │   └── static/
    │       ├── index.html
    │       ├── styles.css
    │       └── standalone.js
    └── tests/
        └── test_api.py
```

## Deploy to Render

The repository includes a current `render.yaml` and a Dockerfile that honors Render's `PORT` environment variable. After this folder is pushed to its own GitHub repository, either create a Blueprint from the repo or create one Docker web service with the root Dockerfile. The health check is `/api/health`.

The free Render service has an ephemeral filesystem: uploaded datasets and SQLite history can disappear after restarts or redeploys. That is appropriate for the public portfolio demo using synthetic/non-sensitive data. For durable user data, add a persistent database/object store before treating the app as a production SaaS.

See `DEPLOYMENT.md` for the exact deployment checklist.

## Important production boundary

This release is a **complete single-user portfolio demo**, not a public multi-tenant SaaS. It intentionally does not pretend dataset IDs are authentication. Before hosting confidential uploads for multiple users, add real authentication/authorization, rate limiting, encrypted storage, retention policies, secret management, observability and deployment-specific security headers.

For a recruiter demo, running it locally or deploying it with non-sensitive synthetic/sample data is appropriate.

## Good interview explanation

A concise explanation you should be able to give yourself:

> “DataPilot separates reasoning from calculation. The analytics layer computes the facts with Pandas and constrained SQLite aggregation. The agent layer only routes natural-language questions to approved functions and explains the returned evidence. That design reduces hallucinated numbers, makes answers inspectable, and still works without an LLM.”

## License

MIT — see `LICENSE`.
