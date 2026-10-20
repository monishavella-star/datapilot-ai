# DataPilot AI — Portfolio & Interview Guide

## One-line pitch

DataPilot is an evidence-first AI data analyst that turns arbitrary CSV files into deterministic analytics, charts, data-quality checks and explainable natural-language answers.

## Resume bullets

- Built a FastAPI/Pandas analytics agent that profiles CSV datasets, routes natural-language questions to constrained tools, generates validated SQLite aggregations and exposes calculation traces to reduce hallucinated numeric answers.
- Implemented trend analysis, month-over-month driver decomposition, descriptive statistics, outlier detection, correlation analysis, automatic findings, report export and persistent local analysis history.
- Added Docker/Render deployment, security headers, CI tests and a 30-question evaluation benchmark achieving 100% intended tool selection and 100% grounded completion on the bundled synthetic dataset.

## 60-second interview explanation

“DataPilot separates reasoning from calculation. The browser sends a natural-language question to FastAPI. The agent layer maps that question to an allow-listed analytics tool such as group-by, trend, correlation or month-driver analysis. Pandas and constrained SQLite calculate the numbers. DataPilot then returns the answer together with the tool arguments, calculation summary and generated aggregation SQL where relevant. That means the app can work without an LLM and the optional LLM can never execute arbitrary code. I also built a deterministic evaluation harness so I can measure routing behavior instead of claiming that the agent is accurate without evidence.”

## Demo sequence for a recruiter

1. Open the app and point out the automatic findings.
2. Ask: **Why did revenue decrease in March?**
3. Expand the calculation trace and show the month comparison plus driver tools.
4. Ask: **What is the correlation between revenue and profit?**
5. Open Data Quality.
6. Export the Markdown report.
7. Briefly show `EVALUATION.md`, tests and `render.yaml` in the repository.

## Be ready to discuss

- Why deterministic tools reduce hallucination risk.
- Why arbitrary generated SQL/Python is not executed.
- Why an LLM is optional rather than required.
- Why correlation is not causation.
- Why Render free storage is only suitable for a demo.
- How you would add PostgreSQL/object storage/authentication for a multi-user system.
