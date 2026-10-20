# DataPilot Evaluation

This benchmark evaluates the deterministic local agent router against 30 natural-language questions on the bundled synthetic e-commerce dataset.

- Cases: **30**
- Tool-selection accuracy: **100.00%**
- Grounded completion: **100.00%**

`Grounded completion` means the answer completed with at least one deterministic calculation step and did not return a calculation failure. This benchmark does not claim general language-model accuracy.

| # | Question | Expected | Actual | Tool | Grounded |
|---:|---|---|---|:---:|:---:|
| 1 | Give me a summary of this dataset | `dataset_summary` | `dataset_summary` | ✅ | ✅ |
| 2 | How many rows and columns are here? | `dataset_summary` | `dataset_summary` | ✅ | ✅ |
| 3 | Tell me about the dataset | `dataset_summary` | `dataset_summary` | ✅ | ✅ |
| 4 | Check missing values and duplicates | `data_quality` | `data_quality` | ✅ | ✅ |
| 5 | How complete is this data? | `data_quality` | `data_quality` | ✅ | ✅ |
| 6 | Run a data quality check | `data_quality` | `data_quality` | ✅ | ✅ |
| 7 | Show monthly revenue trend | `trend` | `trend` | ✅ | ✅ |
| 8 | Show revenue over time | `trend` | `trend` | ✅ | ✅ |
| 9 | What is the daily revenue trend? | `trend` | `trend` | ✅ | ✅ |
| 10 | Which category has the highest revenue? | `group_by` | `group_by` | ✅ | ✅ |
| 11 | Which region has the lowest revenue? | `group_by` | `group_by` | ✅ | ✅ |
| 12 | Give me the product revenue breakdown | `group_by` | `group_by` | ✅ | ✅ |
| 13 | Which category has the highest average profit? | `group_by` | `group_by` | ✅ | ✅ |
| 14 | What is the average profit by region? | `group_by` | `group_by` | ✅ | ✅ |
| 15 | Show statistics for revenue | `describe_metric` | `describe_metric` | ✅ | ✅ |
| 16 | Describe profit | `describe_metric` | `describe_metric` | ✅ | ✅ |
| 17 | What is the median revenue? | `describe_metric` | `describe_metric` | ✅ | ✅ |
| 18 | Find outliers in profit | `outliers` | `outliers` | ✅ | ✅ |
| 19 | Are there unusual revenue values? | `outliers` | `outliers` | ✅ | ✅ |
| 20 | Detect revenue anomalies | `outliers` | `outliers` | ✅ | ✅ |
| 21 | What is the correlation between revenue and profit? | `correlation` | `correlation` | ✅ | ✅ |
| 22 | Show the relationship between quantity and revenue | `correlation` | `correlation` | ✅ | ✅ |
| 23 | Compare March revenue with February | `compare_months` | `compare_months` | ✅ | ✅ |
| 24 | How did revenue change in 2026-04? | `compare_months` | `compare_months` | ✅ | ✅ |
| 25 | Compare June profit versus May | `compare_months` | `compare_months` | ✅ | ✅ |
| 26 | Why did revenue decrease in March? | `compare_months` | `compare_months` | ✅ | ✅ |
| 27 | What drove the March revenue change? | `compare_months` | `compare_months` | ✅ | ✅ |
| 28 | Explain the reason for the April profit change | `compare_months` | `compare_months` | ✅ | ✅ |
| 29 | Which region has the worst average profit? | `group_by` | `group_by` | ✅ | ✅ |
| 30 | Which product has the best revenue? | `group_by` | `group_by` | ✅ | ✅ |

## Reproduce

```bash
cd backend
python evaluation/run_evaluation.py
```

The dataset is synthetic and generated deterministically by `app/sample.py`.
