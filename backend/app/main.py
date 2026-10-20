"""DataPilot AI API — portfolio-grade local-first edition."""
from __future__ import annotations

import os
import re
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, PlainTextResponse
from starlette.requests import Request
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import repository, store
from .agent import ask
from .analytics import create_report, profile
from .insights import automatic_insights
from .sample import sample_sales

load_dotenv()

APP_VERSION = "1.1.0"
app = FastAPI(
    title="DataPilot AI API",
    version=APP_VERSION,
    description="Evidence-first CSV analytics with deterministic tools and an optional LLM agent.",
)

origins = [
    value.strip()
    for value in os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",")
    if value.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Content-Type"],
)


class AskRequest(BaseModel):
    dataset_id: str = Field(min_length=32, max_length=32)
    question: str = Field(min_length=3, max_length=1000)


def _dataset_or_404(dataset_id: str):
    try:
        return store.read_frame(dataset_id)
    except (FileNotFoundError, store.DatasetError):
        raise HTTPException(status_code=404, detail="Dataset not found")


def _metadata(dataset_id: str) -> dict:
    meta = repository.get_dataset(dataset_id)
    if meta:
        return meta
    return {"filename": "uploaded_dataset.csv", "source": "upload"}


def _profile_payload(df, dataset_id: str, filename: str, source: str) -> dict:
    payload = profile(df, dataset_id, filename, source=source)
    payload["insights"] = automatic_insights(df)
    return payload


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; "
        "connect-src 'self'; object-src 'none'; base-uri 'self'; frame-ancestors 'none'"
    )
    if request.url.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store"
    return response


@app.get("/api/health")
def health():
    ai_configured = bool(os.getenv("OPENAI_API_KEY", "").strip())
    return {
        "status": "ok",
        "version": APP_VERSION,
        "analysis_mode": "openai-tools-with-local-fallback" if ai_configured else "local-rules",
        "ai_configured": ai_configured,
        "max_upload_mb": round(store.MAX_BYTES / 1_000_000, 1),
        "max_rows": store.MAX_ROWS,
        "max_columns": store.MAX_COLUMNS,
    }


@app.post("/api/demo")
def demo():
    df = sample_sales()
    dataset_id = store.save_frame(df)
    filename = "sample_sales_2026.csv"
    repository.save_dataset(dataset_id, filename, "demo", len(df), len(df.columns))
    return _profile_payload(df, dataset_id, filename, source="demo")


@app.post("/api/upload")
async def upload(file: UploadFile = File(...)):
    filename = Path(file.filename or "").name.strip()
    if not filename:
        raise HTTPException(status_code=400, detail="Choose a CSV file to upload.")
    if not filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only .csv files are supported.")
    try:
        raw = await file.read(store.MAX_BYTES + 1)
        df = store.parse_csv(raw)
        dataset_id = store.save_frame(df)
        repository.save_dataset(dataset_id, filename, "upload", len(df), len(df.columns))
    except store.DatasetError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    finally:
        await file.close()
    return _profile_payload(df, dataset_id, filename, source="upload")


@app.get("/api/datasets/{dataset_id}")
def dataset(dataset_id: str):
    df = _dataset_or_404(dataset_id)
    meta = _metadata(dataset_id)
    return _profile_payload(df, dataset_id, meta["filename"], source=meta.get("source", "upload"))


@app.delete("/api/datasets/{dataset_id}")
def delete_dataset(dataset_id: str):
    try:
        deleted = store.delete_frame(dataset_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Dataset not found")
    if not deleted:
        raise HTTPException(status_code=404, detail="Dataset not found")
    repository.delete_dataset(dataset_id)
    return {"deleted": True, "dataset_id": dataset_id}


@app.get("/api/datasets/{dataset_id}/insights")
def insights(dataset_id: str):
    df = _dataset_or_404(dataset_id)
    return {"items": automatic_insights(df)}


@app.post("/api/ask")
def analyze(request: AskRequest):
    df = _dataset_or_404(request.dataset_id)
    result = ask(df, request.question.strip())
    repository.record_analysis(request.dataset_id, request.question.strip(), result)
    return result


@app.get("/api/datasets/{dataset_id}/history")
def history(dataset_id: str, limit: int = Query(default=30, ge=1, le=100)):
    _dataset_or_404(dataset_id)
    return {"items": repository.list_history(dataset_id, limit=limit)}


@app.delete("/api/datasets/{dataset_id}/history")
def clear_history(dataset_id: str):
    _dataset_or_404(dataset_id)
    repository.clear_history(dataset_id)
    return {"cleared": True, "dataset_id": dataset_id}


@app.get("/api/datasets/{dataset_id}/report", response_class=PlainTextResponse)
def report(dataset_id: str):
    df = _dataset_or_404(dataset_id)
    meta = _metadata(dataset_id)
    recent = repository.list_history(dataset_id, limit=10)
    body = create_report(df, meta["filename"], analyses=recent)
    raw_stem = Path(meta["filename"]).stem[:60] or "dataset"
    safe_stem = re.sub(r"[^A-Za-z0-9._-]+", "-", raw_stem).strip("-.") or "dataset"
    return PlainTextResponse(
        body,
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="datapilot-{safe_stem}-report.md"'},
    )


STATIC_DIR = Path(__file__).resolve().parent / "static"
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.api_route("/", methods=["GET", "HEAD"], include_in_schema=False)
def dashboard():
    return FileResponse(STATIC_DIR / "index.html")