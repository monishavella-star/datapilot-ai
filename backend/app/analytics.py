"""Deterministic, explainable analytics tools used by DataPilot AI."""
from __future__ import annotations

import math
import sqlite3
from typing import Any

import numpy as np
import pandas as pd


def plain(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (list, dict)):
        return value
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating, float)):
        number = float(value)
        return round(number, 4) if math.isfinite(number) else None
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if isinstance(value, pd.Timedelta):
        return str(value)
    return value


def numeric_columns(df: pd.DataFrame) -> list[str]:
    return [str(c) for c in df.select_dtypes(include="number").columns]


def date_columns(df: pd.DataFrame) -> list[str]:
    found: list[str] = []
    for col in df.columns:
        series = df[col]
        if pd.api.types.is_datetime64_any_dtype(series):
            found.append(str(col))
            continue
        name = str(col).lower()
        if not any(token in name for token in ("date", "time", "day", "month", "year")):
            continue
        non_null = int(series.notna().sum())
        if not non_null:
            continue
        parsed = pd.to_datetime(series, errors="coerce")
        if int(parsed.notna().sum()) >= max(1, int(non_null * 0.75)):
            found.append(str(col))
    return found


def category_columns(df: pd.DataFrame) -> list[str]:
    nums = set(numeric_columns(df))
    dates = set(date_columns(df))
    result: list[str] = []
    for col in df.columns:
        name = str(col)
        if name in nums or name in dates:
            continue
        unique = int(df[col].nunique(dropna=True))
        if 1 <= unique <= 100:
            result.append(name)
    return result


def metric_col(df: pd.DataFrame) -> str | None:
    nums = numeric_columns(df)
    preferred = ("revenue", "sales", "amount", "profit", "price", "score", "value")
    for target in preferred:
        match = next((c for c in nums if c.lower() == target), None)
        if match:
            return match
    return nums[0] if nums else None


def quality(df: pd.DataFrame) -> dict[str, Any]:
    missing_series = df.isna().sum()
    missing = {str(k): int(v) for k, v in missing_series.items() if int(v) > 0}
    total_cells = max(int(df.size), 1)
    missing_cells = int(missing_series.sum())
    duplicate_rows = int(df.duplicated().sum())
    constant_columns = [str(c) for c in df.columns if int(df[c].nunique(dropna=True)) <= 1]
    return {
        "missing_cells": missing_cells,
        "missing_by_column": missing,
        "duplicate_rows": duplicate_rows,
        "constant_columns": constant_columns,
        "completeness_pct": round(100 * (1 - missing_cells / total_cells), 1),
    }


def _require_col(df: pd.DataFrame, name: str, numeric: bool = False) -> str:
    if name not in df.columns:
        raise ValueError(f"Unknown column '{name}'. Available columns: {', '.join(map(str, df.columns))}")
    if numeric and name not in numeric_columns(df):
        raise ValueError(f"'{name}' is not a numeric column.")
    return name


def quote_ident(value: str) -> str:
    return '"' + str(value).replace('"', '""') + '"'


def group_by(
    df: pd.DataFrame,
    dimension: str,
    metric: str,
    operation: str = "sum",
    order: str = "desc",
    limit: int = 8,
) -> dict[str, Any]:
    _require_col(df, dimension)
    _require_col(df, metric, numeric=True)
    if operation not in ("sum", "avg", "count"):
        raise ValueError("operation must be sum, avg, or count")
    if order not in ("asc", "desc"):
        raise ValueError("order must be asc or desc")
    limit = max(1, min(int(limit), 15))
    agg = {"sum": "SUM", "avg": "AVG", "count": "COUNT"}[operation]
    direction = "ASC" if order == "asc" else "DESC"
    sql = (
        f"SELECT {quote_ident(dimension)} AS label, {agg}({quote_ident(metric)}) AS value "
        f"FROM records WHERE {quote_ident(dimension)} IS NOT NULL "
        f"GROUP BY {quote_ident(dimension)} ORDER BY value {direction} LIMIT ?"
    )
    with sqlite3.connect(":memory:") as conn:
        df.to_sql("records", conn, index=False)
        rows = conn.execute(sql, (limit,)).fetchall()
    data = [
        {"label": str(label), "value": round(float(value), 2)}
        for label, value in rows
        if value is not None
    ]
    operation_name = {"sum": "Total", "avg": "Average", "count": "Count"}[operation]
    return {
        "summary": f"{operation_name} {metric} by {dimension}",
        "rows": data,
        "sql": sql.replace("?", str(limit)),
        "chart": {
            "type": "bar",
            "title": f"{operation_name} {metric.title()} by {dimension.title()}",
            "xKey": "label",
            "data": data,
            "series": [{"key": "value", "name": metric.title()}],
        },
    }


def trend(df: pd.DataFrame, date_column: str, metric: str, frequency: str = "month") -> dict[str, Any]:
    _require_col(df, date_column)
    _require_col(df, metric, numeric=True)
    if frequency not in ("month", "day"):
        raise ValueError("frequency must be 'month' or 'day'")
    temp = df[[date_column, metric]].copy()
    temp[date_column] = pd.to_datetime(temp[date_column], errors="coerce")
    temp = temp.dropna(subset=[date_column, metric])
    if temp.empty:
        raise ValueError("No valid dates and numeric values found.")
    temp["period"] = temp[date_column].dt.to_period("M" if frequency == "month" else "D").astype(str)
    values = temp.groupby("period", sort=True)[metric].sum()
    data = [{"label": str(k), "value": round(float(v), 2)} for k, v in values.items()]
    return {
        "summary": f"{metric} totals by {frequency}, based on valid dates",
        "rows": data,
        "chart": {
            "type": "line",
            "title": f"{metric.title()} over time",
            "xKey": "label",
            "data": data,
            "series": [{"key": "value", "name": metric.title()}],
        },
    }


def compare_months(df: pd.DataFrame, date_column: str, metric: str, month: str) -> dict[str, Any]:
    _require_col(df, date_column)
    _require_col(df, metric, numeric=True)
    temp = df[[date_column, metric]].copy()
    temp[date_column] = pd.to_datetime(temp[date_column], errors="coerce")
    temp = temp.dropna(subset=[date_column, metric])
    try:
        current = pd.Period(month, freq="M")
    except (ValueError, TypeError) as exc:
        raise ValueError("month must use YYYY-MM format") from exc
    previous = current - 1
    periods = temp[date_column].dt.to_period("M")
    current_rows = periods == current
    previous_rows = periods == previous
    if not int(current_rows.sum()) or not int(previous_rows.sum()):
        raise ValueError(f"Both {previous} and {current} need data for a comparison.")
    current_value = float(temp.loc[current_rows, metric].sum())
    previous_value = float(temp.loc[previous_rows, metric].sum())
    change = current_value - previous_value
    pct = round(change / abs(previous_value) * 100, 2) if previous_value else None
    data = [
        {"label": str(previous), "value": round(previous_value, 2)},
        {"label": str(current), "value": round(current_value, 2)},
    ]
    return {
        "current_month": str(current),
        "previous_month": str(previous),
        "current": round(current_value, 2),
        "previous": round(previous_value, 2),
        "change": round(change, 2),
        "change_pct": pct,
        "note": "Month-on-month change is descriptive, not proof of causation.",
        "chart": {
            "type": "bar",
            "title": f"{metric.title()}: {previous} vs {current}",
            "xKey": "label",
            "data": data,
            "series": [{"key": "value", "name": metric.title()}],
        },
    }


def month_drivers(
    df: pd.DataFrame, date_column: str, metric: str, month: str, dimension: str, limit: int = 6
) -> dict[str, Any]:
    _require_col(df, date_column)
    _require_col(df, metric, numeric=True)
    _require_col(df, dimension)
    try:
        current = pd.Period(month, freq="M")
    except (ValueError, TypeError) as exc:
        raise ValueError("month must use YYYY-MM format") from exc
    previous = current - 1
    temp = df[[date_column, dimension, metric]].copy()
    temp[date_column] = pd.to_datetime(temp[date_column], errors="coerce")
    temp = temp.dropna(subset=[date_column, dimension, metric])
    temp["period"] = temp[date_column].dt.to_period("M")
    scoped = temp[temp["period"].isin([previous, current])]
    if scoped.empty or previous not in set(scoped["period"]) or current not in set(scoped["period"]):
        raise ValueError(f"Both {previous} and {current} need data for driver analysis.")
    pivot = scoped.pivot_table(index=dimension, columns="period", values=metric, aggfunc="sum", fill_value=0)
    if previous not in pivot.columns:
        pivot[previous] = 0.0
    if current not in pivot.columns:
        pivot[current] = 0.0
    rows = []
    total_change = float(pivot[current].sum() - pivot[previous].sum())
    for label, row in pivot.iterrows():
        prev_value = float(row[previous])
        cur_value = float(row[current])
        change = cur_value - prev_value
        rows.append(
            {
                "label": str(label),
                "previous": round(prev_value, 2),
                "current": round(cur_value, 2),
                "change": round(change, 2),
                "share_of_total_change_pct": round(change / total_change * 100, 2) if total_change else None,
            }
        )
    rows.sort(key=lambda r: abs(r["change"]), reverse=True)
    rows = rows[: max(1, min(int(limit), 12))]
    chart_data = [{"label": r["label"], "value": r["change"]} for r in rows]
    return {
        "summary": f"Largest {dimension} changes in {metric} from {previous} to {current}",
        "previous_month": str(previous),
        "current_month": str(current),
        "total_change": round(total_change, 2),
        "rows": rows,
        "note": "These are contribution patterns, not proof of root cause.",
        "chart": {
            "type": "bar",
            "title": f"Change in {metric.title()} by {dimension.title()}",
            "xKey": "label",
            "data": chart_data,
            "series": [{"key": "value", "name": "Change"}],
        },
    }


def correlations(df: pd.DataFrame, left: str, right: str) -> dict[str, Any]:
    _require_col(df, left, numeric=True)
    _require_col(df, right, numeric=True)
    if left == right:
        raise ValueError("Choose two different numeric columns.")
    valid = df[[left, right]].dropna()
    if len(valid) < 3:
        raise ValueError("Not enough complete rows for correlation.")
    value = valid[left].corr(valid[right])
    if pd.isna(value):
        raise ValueError("Correlation is undefined for constant values.")
    return {
        "columns": [left, right],
        "pearson_r": round(float(value), 3),
        "sample_size": int(len(valid)),
        "note": "Correlation does not imply causation.",
    }


def describe_metric(df: pd.DataFrame, metric: str) -> dict[str, Any]:
    _require_col(df, metric, numeric=True)
    series = pd.to_numeric(df[metric], errors="coerce").dropna()
    if series.empty:
        raise ValueError(f"'{metric}' has no valid numeric values.")
    stats = {
        "count": int(series.count()),
        "missing": int(df[metric].isna().sum()),
        "mean": round(float(series.mean()), 3),
        "median": round(float(series.median()), 3),
        "std": round(float(series.std(ddof=1)), 3) if len(series) > 1 else 0.0,
        "min": round(float(series.min()), 3),
        "q1": round(float(series.quantile(0.25)), 3),
        "q3": round(float(series.quantile(0.75)), 3),
        "max": round(float(series.max()), 3),
    }
    return {"metric": metric, "statistics": stats}


def outliers(df: pd.DataFrame, metric: str) -> dict[str, Any]:
    _require_col(df, metric, numeric=True)
    series = pd.to_numeric(df[metric], errors="coerce")
    valid = series.dropna()
    if len(valid) < 4:
        raise ValueError("At least four numeric values are required for IQR outlier detection.")
    q1 = float(valid.quantile(0.25))
    q3 = float(valid.quantile(0.75))
    iqr = q3 - q1
    lower = q1 - 1.5 * iqr
    upper = q3 + 1.5 * iqr
    mask = (series < lower) | (series > upper)
    flagged = df.loc[mask, metric].dropna()
    examples = sorted((float(v) for v in flagged), key=abs, reverse=True)[:10]
    return {
        "metric": metric,
        "method": "IQR 1.5x",
        "lower_bound": round(lower, 3),
        "upper_bound": round(upper, 3),
        "outlier_count": int(mask.fillna(False).sum()),
        "outlier_pct": round(float(mask.fillna(False).mean() * 100), 2),
        "example_values": [round(v, 3) for v in examples],
        "note": "Statistical outliers can be valid observations; investigate before removing them.",
    }


def overview(df: pd.DataFrame) -> dict[str, Any]:
    nums = numeric_columns(df)
    return {
        "rows": int(len(df)),
        "columns": int(len(df.columns)),
        "numeric_columns": nums,
        "category_columns": category_columns(df),
        "date_columns": date_columns(df),
        "quality": quality(df),
        "suggested_metric": metric_col(df),
    }


def suggested_questions(df: pd.DataFrame) -> list[str]:
    nums = numeric_columns(df)
    cats = category_columns(df)
    dates = date_columns(df)
    metric = metric_col(df)
    items = ["Summarize this dataset", "Check missing values and duplicates"]
    if metric and dates:
        items.append(f"Show monthly {metric} trend")
    if metric and cats:
        items.append(f"Which {cats[0]} has the highest {metric}?")
    if len(nums) >= 2:
        items.append(f"What is the correlation between {nums[0]} and {nums[1]}?")
    if metric:
        items.append(f"Show statistics for {metric}")
        items.append(f"Find outliers in {metric}")
    deduped: list[str] = []
    for item in items:
        if item not in deduped:
            deduped.append(item)
    return deduped[:6]


def profile(df: pd.DataFrame, dataset_id: str, filename: str, source: str = "upload") -> dict[str, Any]:
    nums = numeric_columns(df)
    dates = date_columns(df)
    cats = category_columns(df)
    q = quality(df)
    kpis: list[dict[str, Any]] = [
        {"label": "Rows", "value": int(len(df)), "format": "integer"},
        {"label": "Columns", "value": int(len(df.columns)), "format": "integer"},
    ]
    preferred_metrics = ["revenue", "profit"]
    for target in preferred_metrics:
        col = next((c for c in nums if c.lower() == target), None)
        if col:
            kpis.append(
                {
                    "label": f"Total {col.title()}",
                    "value": round(float(pd.to_numeric(df[col], errors="coerce").sum()), 2),
                    "format": "currency" if source == "demo" else "number",
                }
            )
    if len(kpis) == 2 and nums:
        col = metric_col(df)
        if col:
            kpis.append(
                {
                    "label": f"Total {col.title()}",
                    "value": round(float(pd.to_numeric(df[col], errors="coerce").sum()), 2),
                    "format": "number",
                }
            )
    columns = [
        {
            "name": str(c),
            "type": "number" if str(c) in nums else "date" if str(c) in dates else "text",
            "missing": int(df[c].isna().sum()),
            "unique": int(df[c].nunique(dropna=True)),
        }
        for c in df.columns
    ]
    preview = [{str(k): plain(v) for k, v in row.items()} for row in df.head(10).to_dict("records")]
    output: dict[str, Any] = {
        "dataset_id": dataset_id,
        "filename": filename,
        "source": source,
        "rows": int(len(df)),
        "columns": columns,
        "numeric_columns": nums,
        "category_columns": cats,
        "date_columns": dates,
        "kpis": kpis,
        "quality": q,
        "preview": preview,
        "suggested_questions": suggested_questions(df),
    }
    group = next((c for c in ("category", "region", "product") if c in df.columns), None) or (cats[0] if cats else None)
    metric = metric_col(df)
    if group and metric:
        output["category_chart"] = group_by(df, group, metric)["chart"]
    if dates and metric:
        output["trend_chart"] = trend(df, dates[0], metric)["chart"]
    return output


def execute_tool(df: pd.DataFrame, name: str, args: dict[str, Any]) -> dict[str, Any]:
    if name == "dataset_summary":
        return overview(df)
    if name == "data_quality":
        return quality(df)
    if name == "group_by":
        return group_by(
            df,
            args["dimension"],
            args["metric"],
            args.get("operation", "sum"),
            args.get("order", "desc"),
            args.get("limit", 8),
        )
    if name == "trend":
        return trend(df, args["date_column"], args["metric"], args.get("frequency", "month"))
    if name == "compare_months":
        return compare_months(df, args["date_column"], args["metric"], args["month"])
    if name == "month_drivers":
        return month_drivers(df, args["date_column"], args["metric"], args["month"], args["dimension"])
    if name == "correlation":
        return correlations(df, args["left"], args["right"])
    if name == "describe_metric":
        return describe_metric(df, args["metric"])
    if name == "outliers":
        return outliers(df, args["metric"])
    raise ValueError("Tool not allowed")


def create_report(df: pd.DataFrame, filename: str, analyses: list[dict[str, Any]] | None = None) -> str:
    info = overview(df)
    q = info["quality"]
    lines = [
        f"# DataPilot AI Report — {filename}",
        "",
        "## Dataset overview",
        f"- Rows: {len(df):,}",
        f"- Columns: {len(df.columns)}",
        f"- Numeric columns: {', '.join(info['numeric_columns']) or 'none'}",
        f"- Categorical columns: {', '.join(info['category_columns']) or 'none'}",
        f"- Date columns: {', '.join(info['date_columns']) or 'none'}",
        "",
        "## Data quality",
        f"- Completeness: {q['completeness_pct']}%",
        f"- Missing cells: {q['missing_cells']:,}",
        f"- Duplicate rows: {q['duplicate_rows']:,}",
        f"- Constant columns: {', '.join(q['constant_columns']) or 'none'}",
        "",
        "## Descriptive findings",
    ]
    metric = metric_col(df)
    if metric:
        metric_series = pd.to_numeric(df[metric], errors="coerce")
        lines.append(f"- Total {metric}: {metric_series.sum():,.2f} (units follow the source data)")
        stats = describe_metric(df, metric)["statistics"]
        lines.append(f"- {metric} mean: {stats['mean']:,.2f}; median: {stats['median']:,.2f}")
        cats = category_columns(df)
        if cats:
            grouped = group_by(df, cats[0], metric)
            if grouped["rows"]:
                top = grouped["rows"][0]
                lines.append(f"- Top {cats[0]} by {metric}: {top['label']} ({top['value']:,.2f})")
    if analyses:
        lines += ["", "## Recent questions"]
        for entry in analyses[:10]:
            lines.append(f"- **Q:** {entry.get('question', '')}")
            lines.append(f"  - **A:** {entry.get('answer', '')}")
    lines += [
        "",
        "## Notes",
        "- Findings describe this dataset only and do not establish causation.",
        "- Statistical outliers can still be legitimate records.",
        "- Check source accuracy, units and business definitions before decisions.",
        "- The bundled demo dataset is fully synthetic.",
    ]
    return "\n".join(lines) + "\n"