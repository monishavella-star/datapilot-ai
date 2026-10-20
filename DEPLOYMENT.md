# DataPilot AI — Deployment Guide

## Recommended portfolio deployment: Render

DataPilot is a single Dockerized FastAPI web service. The static dashboard is served by FastAPI, so there is no separate frontend deployment and no Node/npm build step.

### Render configuration

The repository root includes `render.yaml` with:

- service type: web
- runtime: Docker
- free compute plan
- region: Singapore
- health check: `/api/health`
- automatic deploys from commits
- 5 MB / 50,000-row / 80-column upload limits

The Docker image binds to `0.0.0.0` and uses Render's `PORT` variable automatically.

### Deploy with Blueprint

1. Push this project to a dedicated GitHub repository, ideally named `datapilot-ai`.
2. In Render, choose **New → Blueprint**.
3. Select the repository that contains this `render.yaml` at the root.
4. Review the service name `datapilot-ai`, free plan and Singapore region.
5. Apply the Blueprint.
6. Wait for the deploy to become live.
7. Open `/api/health` on the public URL and confirm `"status":"ok"`.
8. Open the root URL and test the bundled demo plus a small CSV upload.

### Optional OpenAI mode

The public demo does not require an API key. If you intentionally enable optional model tool-calling, add these secrets in Render's environment-variable UI rather than committing them:

- `OPENAI_API_KEY`
- `OPENAI_MODEL` (optional)

Never commit `.env` or API keys.

### Free-plan storage limitation

The service writes uploaded CSVs and SQLite history to `/app/data`. On a free Render web service this should be treated as ephemeral demo storage. A restart/redeploy can remove it. Do not upload confidential data to the public demo.

For a real multi-user product, move dataset objects to durable object storage and application state to PostgreSQL, then add authentication/authorization and per-user access controls.

### Post-deploy acceptance test

- `GET /api/health` returns HTTP 200.
- Home page loads without console-breaking JavaScript syntax errors.
- Demo dataset loads automatically.
- “Why did revenue decrease in March?” returns calculation steps.
- “Check missing values and duplicates” returns the data-quality tool.
- Export report downloads Markdown.
- Uploading a non-CSV is rejected.
- Uploading a valid small UTF-8 CSV succeeds.

## Local Docker smoke test

```bash
docker build -t datapilot-ai .
docker run --rm -p 8000:8000 datapilot-ai
```

Then open `http://127.0.0.1:8000`.
