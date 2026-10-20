import io

import pytest
from fastapi.testclient import TestClient

from app import repository, store
from app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def isolated_storage(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "DATA_DIR", tmp_path / "datasets")
    monkeypatch.setattr(repository, "DB_PATH", tmp_path / "state" / "datapilot.db")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)


def demo_dataset():
    response = client.post("/api/demo")
    assert response.status_code == 200
    return response.json()


def test_health_reports_version_and_limits():
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert data["version"] == "1.1.0"
    assert data["analysis_mode"] == "local-rules"
    assert data["max_rows"] >= 20_000


def test_demo_profile_has_charts_and_suggestions():
    data = demo_dataset()
    assert data["rows"] == 960
    assert data["source"] == "demo"
    assert data["quality"]["missing_cells"] == 0
    assert data["trend_chart"]["type"] == "line"
    assert data["category_chart"]["type"] == "bar"
    assert len(data["suggested_questions"]) >= 4


def test_upload_profile_preserves_filename_and_no_currency_assumption():
    payload = b"date,segment,revenue\n2026-01-01,A,12\n2026-02-01,B,16\n"
    up = client.post("/api/upload", files={"file": ("metrics.csv", io.BytesIO(payload), "text/csv")})
    assert up.status_code == 200
    body = up.json()
    assert body["filename"] == "metrics.csv"
    assert body["source"] == "upload"
    revenue = next(k for k in body["kpis"] if k["label"] == "Total Revenue")
    assert revenue["format"] == "number"
    fetched = client.get(f"/api/datasets/{body['dataset_id']}")
    assert fetched.status_code == 200
    assert fetched.json()["filename"] == "metrics.csv"


def test_upload_validation_rejects_bad_files():
    assert client.post("/api/upload", files={"file": ("doc.txt", b"hello", "text/plain")}).status_code == 400
    assert client.post("/api/upload", files={"file": ("empty.csv", b"a,b\n", "text/csv")}).status_code == 400
    assert client.post("/api/upload", files={"file": ("blank.csv", b",\n1,2\n", "text/csv")}).status_code == 400


def test_group_by_and_generated_sql():
    payload = b"category,revenue\nA,50\nB,80\nA,25\n"
    up = client.post("/api/upload", files={"file": ("sales.csv", io.BytesIO(payload), "text/csv")}).json()
    answer = client.post("/api/ask", json={"dataset_id": up["dataset_id"], "question": "Which category has the highest revenue?"})
    assert answer.status_code == 200
    body = answer.json()
    assert body["steps"][0]["tool"] == "group_by"
    assert "SELECT" in body["steps"][0]["sql"]
    assert "B" in body["answer"]


def test_average_and_lowest_group_questions():
    payload = b"team,score\nA,10\nA,30\nB,15\nB,15\n"
    up = client.post("/api/upload", files={"file": ("scores.csv", io.BytesIO(payload), "text/csv")}).json()
    res = client.post("/api/ask", json={"dataset_id": up["dataset_id"], "question": "Which team has the lowest average score?"})
    assert res.status_code == 200
    step = res.json()["steps"][0]
    assert step["tool"] == "group_by"
    assert step["arguments"]["operation"] == "avg"
    assert step["arguments"]["order"] == "asc"
    assert "B" in res.json()["answer"]


def test_month_comparison_and_driver_analysis():
    payload = (
        b"date,region,category,revenue\n"
        b"2026-02-02,East,A,100\n2026-02-03,West,A,100\n"
        b"2026-03-02,East,A,20\n2026-03-03,West,A,80\n"
    )
    up = client.post("/api/upload", files={"file": ("sales.csv", io.BytesIO(payload), "text/csv")}).json()
    res = client.post("/api/ask", json={"dataset_id": up["dataset_id"], "question": "Why did revenue decrease in March?"})
    assert res.status_code == 200
    body = res.json()
    assert "50.00%" in body["answer"]
    tools = [step["tool"] for step in body["steps"]]
    assert tools[0] == "compare_months"
    assert "month_drivers" in tools
    assert "East" in body["answer"]


def test_statistics_outliers_and_correlation():
    payload = b"x,y\n1,2\n2,4\n3,6\n4,8\n100,200\n"
    up = client.post("/api/upload", files={"file": ("numbers.csv", io.BytesIO(payload), "text/csv")}).json()
    stats = client.post("/api/ask", json={"dataset_id": up["dataset_id"], "question": "Show statistics for x"}).json()
    assert stats["steps"][0]["tool"] == "describe_metric"
    outliers = client.post("/api/ask", json={"dataset_id": up["dataset_id"], "question": "Find outliers in x"}).json()
    assert outliers["steps"][0]["tool"] == "outliers"
    corr = client.post("/api/ask", json={"dataset_id": up["dataset_id"], "question": "Correlation between x and y"}).json()
    assert corr["steps"][0]["tool"] == "correlation"
    assert "1.0" in corr["answer"]


def test_history_is_persisted_and_can_be_cleared():
    data = demo_dataset()
    dataset_id = data["dataset_id"]
    client.post("/api/ask", json={"dataset_id": dataset_id, "question": "Show monthly revenue trend"})
    client.post("/api/ask", json={"dataset_id": dataset_id, "question": "Check data quality"})
    history = client.get(f"/api/datasets/{dataset_id}/history")
    assert history.status_code == 200
    assert len(history.json()["items"]) == 2
    assert history.json()["items"][0]["question"] == "Check data quality"
    cleared = client.delete(f"/api/datasets/{dataset_id}/history")
    assert cleared.status_code == 200
    assert client.get(f"/api/datasets/{dataset_id}/history").json()["items"] == []


def test_report_includes_recent_analysis():
    data = demo_dataset()
    dataset_id = data["dataset_id"]
    client.post("/api/ask", json={"dataset_id": dataset_id, "question": "Show monthly revenue trend"})
    report = client.get(f"/api/datasets/{dataset_id}/report")
    assert report.status_code == 200
    assert "DataPilot AI Report" in report.text
    assert "Recent questions" in report.text
    assert "Show monthly revenue trend" in report.text
    assert "attachment" in report.headers["content-disposition"]


def test_delete_dataset_removes_data_and_history():
    data = demo_dataset()
    dataset_id = data["dataset_id"]
    client.post("/api/ask", json={"dataset_id": dataset_id, "question": "Check data quality"})
    deleted = client.delete(f"/api/datasets/{dataset_id}")
    assert deleted.status_code == 200
    assert client.get(f"/api/datasets/{dataset_id}").status_code == 404
    assert repository.list_history(dataset_id) == []


def test_missing_dataset_is_404():
    bad = "a" * 32
    assert client.get(f"/api/datasets/{bad}").status_code == 404
    assert client.post("/api/ask", json={"dataset_id": bad, "question": "Show summary"}).status_code == 404


def test_dashboard_assets_load():
    root = client.get("/")
    assert root.status_code == 200
    assert "DataPilot AI" in root.text
    assert client.get("/static/standalone.js").status_code == 200
    assert client.get("/static/styles.css").status_code == 200


def test_automatic_insights_are_deterministic_and_grounded():
    data = demo_dataset()
    assert data["insights"]
    kinds = {item["kind"] for item in data["insights"]}
    assert "quality" in kinds
    assert "ranking" in kinds
    res = client.get(f"/api/datasets/{data['dataset_id']}/insights")
    assert res.status_code == 200
    assert res.json()["items"][0]["kind"] == "quality"


def test_security_headers_and_no_store_on_api():
    res = client.get("/api/health")
    assert res.headers["x-content-type-options"] == "nosniff"
    assert res.headers["x-frame-options"] == "DENY"
    assert res.headers["cache-control"] == "no-store"
    assert "frame-ancestors 'none'" in res.headers["content-security-policy"]


def test_dashboard_serves_same_origin_assets():
    res = client.get("/")
    assert res.status_code == 200
    assert "DataPilot AI" in res.text
    assert client.get("/static/standalone.js").status_code == 200
    assert client.get("/static/styles.css").status_code == 200