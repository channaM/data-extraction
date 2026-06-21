"""
Transform a raw DataFrame into a list of standard records.

Standard record fields:
  transaction_date  date
  value_date        date | None
  account_number    str  | None
  reference_id      str  | None
  description       str  | None
  debit_amount      Decimal | None   (positive — money OUT)
  credit_amount     Decimal | None   (positive — money IN)
  balance           Decimal | None
  currency          str              (3-letter ISO code, e.g. USD)
  bank_name         str              ("aba")
  source_file       str

Rows that are missing both transaction_date and any amount are skipped.
"""

from __future__ import annotations

import json
import logging
import re
from collections import Counter
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

import pandas as pd

from config import BANK_NAME, COLUMN_MAP, DATE_FORMATS

logger = logging.getLogger(__name__)

_CLEAN_RE = re.compile(r"[^\d.\-]")   # strip commas, spaces, currency symbols


def transform(df: pd.DataFrame, source_file: str) -> list[dict]:
    """Map raw DataFrame → list of standard record dicts."""
    df = df.copy()
    df.columns = [str(c).strip().lower() for c in df.columns]

    col_map = {k.lower(): v for k, v in COLUMN_MAP.items()}

    records: list[dict] = []
    skipped = 0

    for idx, row in df.iterrows():
        mapped: dict[str, str | None]  = {}
        extra:  dict[str, str]         = {}

        for col in df.columns:
            raw_val = row[col]
            val     = str(raw_val).strip() if raw_val is not None else ""
            val     = None if val in ("", "nan", "NaN", "None", "<NA>", "nat", "NaT") else val

            std_field = col_map.get(col)
            if std_field:
                # Prefer the first match (don't overwrite with a duplicate synonym)
                if std_field not in mapped:
                    mapped[std_field] = val
            elif val is not None:
                extra[col] = val

        txn_date  = _to_date(mapped.get("transaction_date"))
        debit     = _to_decimal(mapped.get("debit_amount"))
        credit    = _to_decimal(mapped.get("credit_amount"))
        balance   = _to_decimal(mapped.get("balance"))

        # Skip rows with no date AND no amounts (likely blank or summary rows)
        if txn_date is None and debit is None and credit is None:
            logger.debug("[transform] Row %d skipped — no date or amounts.", idx)
            skipped += 1
            continue

        currency = _infer_currency(mapped, extra)

        record = {
            "bank_name":        BANK_NAME,
            "transaction_date": txn_date,
            "value_date":       _to_date(mapped.get("value_date")),
            "account_number":   _clean_str(mapped.get("account_number")),
            "reference_id":     _clean_str(mapped.get("reference_id")),
            "description":      _clean_str(mapped.get("description")),
            "debit_amount":     debit,
            "credit_amount":    credit,
            "balance":          balance,
            "currency":         currency,
            "source_file":      Path(source_file).name,
            "extra_data":       json.dumps(extra) if extra else None,
        }
        records.append(record)

    logger.info("[transform] %d records, %d skipped from '%s'.",
                len(records), skipped, source_file)
    return records


def dominant_year_month(records: list[dict]) -> tuple[int | None, int | None]:
    pairs = [
        (r["transaction_date"].year, r["transaction_date"].month)
        for r in records
        if isinstance(r.get("transaction_date"), date)
    ]
    if not pairs:
        return None, None
    (year, month), _ = Counter(pairs).most_common(1)[0]
    return year, month


def split_by_currency(records: list[dict]) -> dict[str, list[dict]]:
    """Group records by currency. Each group produces one output file."""
    groups: dict[str, list[dict]] = {}
    for r in records:
        ccy = r.get("currency") or "UNKNOWN"
        groups.setdefault(ccy, []).append(r)
    return groups


# ──────────────────────────────────────────────────────────────────────────────
# Type helpers
# ──────────────────────────────────────────────────────────────────────────────

def _to_date(value: str | None) -> date | None:
    if not value:
        return None
    v = value.strip()
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(v, fmt).date()
        except ValueError:
            continue
    # Try pandas as a last resort
    try:
        return pd.to_datetime(v, dayfirst=True).date()
    except Exception:
        return None


def _to_decimal(value: str | None) -> Decimal | None:
    if not value:
        return None
    # Remove parentheses used for negatives in some bank formats, e.g. (100.00)
    negative = value.strip().startswith("(") and value.strip().endswith(")")
    cleaned  = _CLEAN_RE.sub("", value.strip().strip("()"))
    if not cleaned or cleaned == ".":
        return None
    try:
        result = Decimal(cleaned)
        return -result if negative else result
    except InvalidOperation:
        return None


def _clean_str(value: str | None) -> str | None:
    if not value:
        return None
    v = value.strip()
    return v if v else None


def _infer_currency(mapped: dict, extra: dict) -> str:
    """Try to determine the currency from the column names or values."""
    # Check if any mapped column key contained the currency (e.g. "debit (usd)")
    for col_name in mapped:
        upper = col_name.upper()
        for ccy in ("USD", "KHR", "EUR", "SGD", "THB"):
            if ccy in upper:
                return ccy

    # Check extra fields for a "currency" or "ccy" key
    for key, val in extra.items():
        if key.lower() in ("currency", "ccy", "curr"):
            return val.strip().upper()[:3]

    # Default for ABA Bank Cambodia
    return "USD"
