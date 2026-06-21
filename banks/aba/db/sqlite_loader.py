"""
Load standard records into the local SQLite database.

Database file: database/bank_statements.db (relative to engine root)

Strategy: INSERT OR IGNORE — re-processing the same file never creates duplicates.
The unique constraint is on (bank_name, transaction_date, reference_id, debit_amount, credit_amount).
"""

from __future__ import annotations

import logging
import sqlite3
from datetime import date
from decimal import Decimal
from pathlib import Path

logger = logging.getLogger(__name__)

DB_PATH = Path(__file__).parent.parent / "database" / "bank_statements.db"

CREATE_TRANSACTIONS = """
CREATE TABLE IF NOT EXISTS transactions (
    id               INTEGER  PRIMARY KEY AUTOINCREMENT,
    bank_name        TEXT     NOT NULL,
    transaction_date TEXT     NOT NULL,
    value_date       TEXT,
    account_number   TEXT,
    reference_id     TEXT,
    description      TEXT,
    debit_amount     REAL,
    credit_amount    REAL,
    balance          REAL,
    currency         TEXT     NOT NULL,
    source_file      TEXT,
    extra_data       TEXT,
    imported_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(bank_name, transaction_date, reference_id, debit_amount, credit_amount)
);
"""

CREATE_IMPORT_RUNS = """
CREATE TABLE IF NOT EXISTS import_runs (
    id           INTEGER  PRIMARY KEY AUTOINCREMENT,
    bank_name    TEXT,
    source_file  TEXT,
    rows_read    INTEGER,
    rows_loaded  INTEGER,
    status       TEXT,
    error        TEXT,
    run_at       DATETIME DEFAULT CURRENT_TIMESTAMP
);
"""

INSERT_TRANSACTION = """
INSERT OR IGNORE INTO transactions
    (bank_name, transaction_date, value_date, account_number, reference_id,
     description, debit_amount, credit_amount, balance, currency, source_file, extra_data)
VALUES
    (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
"""

INSERT_RUN = """
INSERT INTO import_runs (bank_name, source_file, rows_read, rows_loaded, status, error)
VALUES (?, ?, ?, ?, ?, ?)
"""


def load(records: list[dict], source_file: str,
         rows_read: int, status: str = "success", error: str | None = None) -> int:
    """
    Insert records into SQLite. Returns the number of rows actually inserted.
    Logs an import run regardless of success or failure.
    """
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(str(DB_PATH)) as conn:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute(CREATE_TRANSACTIONS)
        conn.execute(CREATE_IMPORT_RUNS)

        rows_loaded = 0
        if records:
            params = [_to_row(r) for r in records]
            cursor = conn.executemany(INSERT_TRANSACTION, params)
            rows_loaded = cursor.rowcount if cursor.rowcount >= 0 else 0

        conn.execute(INSERT_RUN, (
            records[0]["bank_name"] if records else "aba",
            source_file,
            rows_read,
            rows_loaded,
            status,
            error,
        ))
        conn.commit()

    logger.info("[sqlite] %d/%d rows inserted into '%s'.", rows_loaded, rows_read, DB_PATH)
    return rows_loaded


def _to_row(r: dict) -> tuple:
    def _d(val) -> str | None:
        if isinstance(val, date):
            return val.isoformat()
        return val

    def _f(val) -> float | None:
        if isinstance(val, Decimal):
            return float(val)
        return val

    return (
        r.get("bank_name"),
        _d(r.get("transaction_date")),
        _d(r.get("value_date")),
        r.get("account_number"),
        r.get("reference_id"),
        r.get("description"),
        _f(r.get("debit_amount")),
        _f(r.get("credit_amount")),
        _f(r.get("balance")),
        r.get("currency"),
        r.get("source_file"),
        r.get("extra_data"),
    )
