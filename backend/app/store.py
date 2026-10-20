"""Validated local CSV storage for DataPilot AI."""
from __future__ import annotations

from io import BytesIO, StringIO
import csv
from pathlib import Path
from uuid import uuid4
import os
import pandas as pd

MAX_BYTES = int(os.getenv("MAX_UPLOAD_BYTES", "5000000"))
MAX_ROWS = int(os.getenv("MAX_ROWS", "50000"))
MAX_COLUMNS = int(os.getenv("MAX_COLUMNS", "80"))
DATA_DIR = Path(os.getenv("DATA_DIR", Path(__file__).resolve().parents[1] / "data"))


class DatasetError(ValueError):
    pass


def validate_dataset_id(dataset_id: str) -> str:
    dataset_id = str(dataset_id).strip().lower()
    if len(dataset_id) != 32 or any(ch not in "0123456789abcdef" for ch in dataset_id):
        raise FileNotFoundError("Dataset not found")
    return dataset_id


def validate_frame(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        raise DatasetError("CSV must contain at least one data row.")
    if len(df) > MAX_ROWS:
        raise DatasetError(f"CSV has too many rows. Maximum is {MAX_ROWS:,}.")
    if len(df.columns) > MAX_COLUMNS:
        raise DatasetError(f"CSV has too many columns. Maximum is {MAX_COLUMNS}.")
    if any(not str(name).strip() for name in df.columns):
        raise DatasetError("Column headers cannot be blank.")
    if df.columns.duplicated().any():
        raise DatasetError("Duplicate column headers are not supported.")

    cleaned = df.copy()
    cleaned.columns = [str(c).strip() for c in cleaned.columns]
    if len(set(cleaned.columns)) != len(cleaned.columns):
        raise DatasetError("Column headers must be unique after trimming spaces.")

    # Completely empty columns rarely help analysis and can create confusing types.
    empty_cols = [c for c in cleaned.columns if cleaned[c].isna().all()]
    if len(empty_cols) == len(cleaned.columns):
        raise DatasetError("CSV cannot contain only empty columns.")
    return cleaned


def parse_csv(raw: bytes) -> pd.DataFrame:
    if not raw:
        raise DatasetError("CSV file is empty.")
    if len(raw) > MAX_BYTES:
        raise DatasetError(f"CSV is too large. Maximum size is {MAX_BYTES / 1_000_000:.1f} MB.")
    try:
        text = raw.decode("utf-8-sig")
        header = next(csv.reader(StringIO(text)))
        cleaned_header = [str(value).strip() for value in header]
        if not cleaned_header or any(not value for value in cleaned_header):
            raise DatasetError("Column headers cannot be blank.")
        if len(set(cleaned_header)) != len(cleaned_header):
            raise DatasetError("Duplicate column headers are not supported.")
        df = pd.read_csv(BytesIO(raw), encoding="utf-8-sig", low_memory=False)
    except DatasetError:
        raise
    except (UnicodeError, ValueError, StopIteration, csv.Error, pd.errors.ParserError, pd.errors.EmptyDataError) as exc:
        raise DatasetError("Could not parse CSV. Save it as UTF-8 CSV and try again.") from exc
    return validate_frame(df)


def save_frame(df: pd.DataFrame) -> str:
    df = validate_frame(df)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    dataset_id = uuid4().hex
    df.to_csv(DATA_DIR / f"{dataset_id}.csv", index=False)
    return dataset_id


def read_frame(dataset_id: str) -> pd.DataFrame:
    dataset_id = validate_dataset_id(dataset_id)
    path = DATA_DIR / f"{dataset_id}.csv"
    if not path.is_file():
        raise FileNotFoundError("Dataset not found")
    try:
        return validate_frame(pd.read_csv(path, low_memory=False))
    except (ValueError, pd.errors.ParserError, pd.errors.EmptyDataError) as exc:
        raise DatasetError("Stored dataset could not be read.") from exc


def delete_frame(dataset_id: str) -> bool:
    dataset_id = validate_dataset_id(dataset_id)
    path = DATA_DIR / f"{dataset_id}.csv"
    if not path.exists():
        return False
    path.unlink()
    return True