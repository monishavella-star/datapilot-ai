"""Automatic evidence-backed findings for DataPilot datasets."""
from __future__ import annotations

from itertools import combinations
from typing import Any

import pandas as pd

from .analytics import (
    category_columns,
    correlations,
    date_columns,
    group_by,
    metric_col,
    numeric_columns,
    outliers,
    quality,
    trend,
)


def _fmt(value: float) -> str:
    return f"{value:,.2f}"


def automatic_insights(df: pd.DataFrame, limit: int = 6) -> list[dict[str, Any]]:
    """Return a compact set of deterministic findings with explicit evidence.

    This intentionally avoids LLM generation. Every finding is calculated from the
    dataframe so it is safe to show immediately after upload.
    """
    items: list[dict[str, Any]] = []
    q = quality(df)
    items.append(
        {
            "kind": "quality",
            "title": "Data quality",
            "text": (
                f"{q['completeness_pct']:.2f}% complete with {q['missing_cells']:,} missing cells "
                f"and {q['duplicate_rows']:,} duplicate rows."
            ),
            "evidence": {
                "completeness_pct": q["completeness_pct"],
                "missing_cells": q["missing_cells"],
                "duplicate_rows": q["duplicate_rows"],
            },
        }
    )

    metric = metric_col(df)
    cats = category_columns(df)
    dates = date_columns(df)
    nums = numeric_columns(df)

    if metric and cats:
        try:
            result = group_by(df, cats[0], metric, operation="sum", order="desc", limit=5)
            rows = result.get("rows") or []
            if rows:
                total = float(pd.to_numeric(df[metric], errors="coerce").sum())
                lead = rows[0]
                share = (float(lead["value"]) / total * 100) if total else None
                share_text = f" ({share:.1f}% of total)" if share is not None else ""
                items.append(
                    {
                        "kind": "ranking",
                        "title": f"Top {cats[0]}",
                        "text": f"{lead['label']} leads {metric} with {_fmt(float(lead['value']))}{share_text}.",
                        "evidence": {"dimension": cats[0], "metric": metric, "leader": lead, "share_pct": round(share, 2) if share is not None else None},
                    }
                )
        except (ValueError, TypeError, KeyError):
            pass

    if metric and dates:
        try:
            result = trend(df, dates[0], metric, frequency="month")
            rows = result.get("rows") or []
            if len(rows) >= 2:
                previous, current = rows[-2], rows[-1]
                prev_value, cur_value = float(previous["value"]), float(current["value"])
                change = cur_value - prev_value
                pct = (change / abs(prev_value) * 100) if prev_value else None
                direction = "increased" if change >= 0 else "decreased"
                pct_text = f" {abs(pct):.1f}%" if pct is not None else ""
                items.append(
                    {
                        "kind": "trend",
                        "title": "Latest monthly movement",
                        "text": f"{metric.title()} {direction}{pct_text} from {previous['label']} to {current['label']}.",
                        "evidence": {"previous": previous, "current": current, "change": round(change, 2), "change_pct": round(pct, 2) if pct is not None else None},
                    }
                )
        except (ValueError, TypeError, KeyError):
            pass

    if metric:
        try:
            result = outliers(df, metric)
            if result["outlier_count"]:
                items.append(
                    {
                        "kind": "outlier",
                        "title": "Potential outliers",
                        "text": f"{result['outlier_count']:,} {metric} values ({result['outlier_pct']:.2f}%) fall outside the 1.5× IQR bounds.",
                        "evidence": result,
                    }
                )
        except (ValueError, TypeError, KeyError):
            pass

    # Correlation search is intentionally bounded so wide CSVs remain responsive.
    candidate_nums = nums[:8]
    strongest: tuple[float, dict[str, Any]] | None = None
    for left, right in combinations(candidate_nums, 2):
        try:
            result = correlations(df, left, right)
        except (ValueError, TypeError, KeyError):
            continue
        score = abs(float(result["pearson_r"]))
        if strongest is None or score > strongest[0]:
            strongest = (score, result)
    if strongest and strongest[0] >= 0.35:
        result = strongest[1]
        strength = "strong" if strongest[0] >= 0.7 else "moderate"
        direction = "positive" if float(result["pearson_r"]) >= 0 else "negative"
        items.append(
            {
                "kind": "correlation",
                "title": "Notable correlation",
                "text": f"{result['columns'][0]} and {result['columns'][1]} have a {strength} {direction} correlation (r={result['pearson_r']:.3f}).",
                "evidence": result,
                "note": "Correlation does not imply causation.",
            }
        )

    return items[: max(1, min(int(limit), 10))]