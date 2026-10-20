"""Deterministic evaluation harness for DataPilot's local agent router.

Run from backend/: python evaluation/run_evaluation.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.agent import offline_analysis
from app.sample import sample_sales

CASES = [
    ("Give me a summary of this dataset", "dataset_summary"),
    ("How many rows and columns are here?", "dataset_summary"),
    ("Tell me about the dataset", "dataset_summary"),
    ("Check missing values and duplicates", "data_quality"),
    ("How complete is this data?", "data_quality"),
    ("Run a data quality check", "data_quality"),
    ("Show monthly revenue trend", "trend"),
    ("Show revenue over time", "trend"),
    ("What is the daily revenue trend?", "trend"),
    ("Which category has the highest revenue?", "group_by"),
    ("Which region has the lowest revenue?", "group_by"),
    ("Give me the product revenue breakdown", "group_by"),
    ("Which category has the highest average profit?", "group_by"),
    ("What is the average profit by region?", "group_by"),
    ("Show statistics for revenue", "describe_metric"),
    ("Describe profit", "describe_metric"),
    ("What is the median revenue?", "describe_metric"),
    ("Find outliers in profit", "outliers"),
    ("Are there unusual revenue values?", "outliers"),
    ("Detect revenue anomalies", "outliers"),
    ("What is the correlation between revenue and profit?", "correlation"),
    ("Show the relationship between quantity and revenue", "correlation"),
    ("Compare March revenue with February", "compare_months"),
    ("How did revenue change in 2026-04?", "compare_months"),
    ("Compare June profit versus May", "compare_months"),
    ("Why did revenue decrease in March?", "compare_months"),
    ("What drove the March revenue change?", "compare_months"),
    ("Explain the reason for the April profit change", "compare_months"),
    ("Which region has the worst average profit?", "group_by"),
    ("Which product has the best revenue?", "group_by"),
]


def evaluate() -> dict:
    df = sample_sales()
    rows = []
    tool_hits = 0
    grounded_hits = 0
    for question, expected_tool in CASES:
        result = offline_analysis(df, question)
        steps = result.get("steps") or []
        actual_tool = steps[0].get("tool") if steps else None
        tool_ok = actual_tool == expected_tool
        grounded_ok = bool(steps) and "couldn't calculate" not in result.get("answer", "").lower()
        tool_hits += int(tool_ok)
        grounded_hits += int(grounded_ok)
        rows.append(
            {
                "question": question,
                "expected_tool": expected_tool,
                "actual_tool": actual_tool,
                "tool_ok": tool_ok,
                "grounded_ok": grounded_ok,
                "steps": len(steps),
            }
        )
    total = len(rows)
    return {
        "cases": total,
        "tool_selection_accuracy_pct": round(tool_hits / total * 100, 2),
        "grounded_completion_pct": round(grounded_hits / total * 100, 2),
        "results": rows,
    }


def main() -> None:
    report = evaluate()
    print(json.dumps({k: v for k, v in report.items() if k != "results"}, indent=2))
    root = Path(__file__).resolve().parents[2]
    out = root / "EVALUATION.md"
    lines = [
        "# DataPilot Evaluation",
        "",
        "This benchmark evaluates the deterministic local agent router against 30 natural-language questions on the bundled synthetic e-commerce dataset.",
        "",
        f"- Cases: **{report['cases']}**",
        f"- Tool-selection accuracy: **{report['tool_selection_accuracy_pct']:.2f}%**",
        f"- Grounded completion: **{report['grounded_completion_pct']:.2f}%**",
        "",
        "`Grounded completion` means the answer completed with at least one deterministic calculation step and did not return a calculation failure. This benchmark does not claim general language-model accuracy.",
        "",
        "| # | Question | Expected | Actual | Tool | Grounded |",
        "|---:|---|---|---|:---:|:---:|",
    ]
    for index, item in enumerate(report["results"], start=1):
        question = item["question"].replace("|", "\\|")
        lines.append(
            f"| {index} | {question} | `{item['expected_tool']}` | `{item['actual_tool']}` | "
            f"{'✅' if item['tool_ok'] else '❌'} | {'✅' if item['grounded_ok'] else '❌'} |"
        )
    lines += [
        "",
        "## Reproduce",
        "",
        "```bash",
        "cd backend",
        "python evaluation/run_evaluation.py",
        "```",
        "",
        "The dataset is synthetic and generated deterministically by `app/sample.py`.",
    ]
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()