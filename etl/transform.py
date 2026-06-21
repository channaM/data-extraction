"""Transform phase: validate, cast, and normalize raw rows into DB-ready records."""
import json
import logging
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

import pandas as pd

from etl.extract import COLUMN_MAP

logger = logging.getLogger(__name__)

KNOWN_COLUMNS = set(COLUMN_MAP.keys())


def _to_decimal(value: str | None) -> Decimal | None:
    if value is None or str(value).strip() in ("", "nan", "NaN"):
        return None
    try:
        return Decimal(str(value).replace(",", "").strip())
    except InvalidOperation:
        return None


def _to_int(value: str | None) -> int | None:
    if value is None or str(value).strip() in ("", "nan", "NaN"):
        return None
    try:
        return int(float(str(value).strip()))
    except (ValueError, TypeError):
        return None


def _to_date(value: str | None) -> date | None:
    if value is None or str(value).strip() in ("", "nan", "NaN"):
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(str(value).strip(), fmt).date()
        except ValueError:
            continue
    return None


def transform(df: pd.DataFrame) -> list[dict]:
    """
    Convert a raw DataFrame into a list of clean record dicts ready for DB insert.

    Unknown columns are collected into the `extra` JSONB field.
    Invalid rows are skipped with a warning.
    """
    known_cols = {c for c in df.columns if c in KNOWN_COLUMNS}
    extra_cols = [c for c in df.columns if c not in KNOWN_COLUMNS]

    records: list[dict] = []
    skipped = 0

    for idx, row in df.iterrows():
        name = str(row.get("name", "")).strip()
        if not name or name.lower() == "nan":
            logger.warning("Row %d skipped: missing required 'name' field.", idx)
            skipped += 1
            continue

        extra = {}
        for col in extra_cols:
            val = row.get(col)
            if val is not None and str(val).strip() not in ("", "nan", "NaN"):
                extra[col] = str(val).strip()

        record = {
            "external_id": str(row.get("id", "")).strip() or None,
            "name": name,
            "category": str(row.get("category", "")).strip() or None,
            "price": _to_decimal(row.get("price")),
            "quantity": _to_int(row.get("quantity")),
            "description": str(row.get("description", "")).strip() or None,
            "record_date": _to_date(row.get("date")),
            "extra": json.dumps(extra) if extra else None,
        }
        records.append(record)

    logger.info("Transform complete: %d valid records, %d skipped.", len(records), skipped)
    return records
