"""Load phase: upsert records into PostgreSQL and track ETL run metadata."""
import logging
from datetime import datetime, timezone

import psycopg2
import psycopg2.extras

from etl.config import Config

logger = logging.getLogger(__name__)


def _connect():
    return psycopg2.connect(Config.pg_dsn())


def start_run(file_name: str, sheet_name: str, template_type: str = "unknown") -> int:
    """Insert an etl_runs row and return its id."""
    sql = """
        INSERT INTO etl_runs (file_name, sheet_name, template_type, status, started_at)
        VALUES (%s, %s, %s, 'running', %s)
        RETURNING id
    """
    with _connect() as conn, conn.cursor() as cur:
        cur.execute(sql, (file_name, sheet_name, template_type, datetime.now(timezone.utc)))
        run_id = cur.fetchone()[0]
    logger.info("ETL run %d started (type=%s).", run_id, template_type)
    return run_id


def finish_run(run_id: int, status: str, rows_read: int, rows_loaded: int, error: str | None = None) -> None:
    sql = """
        UPDATE etl_runs
        SET status = %s, rows_read = %s, rows_loaded = %s,
            error_msg = %s, finished_at = %s
        WHERE id = %s
    """
    with _connect() as conn, conn.cursor() as cur:
        cur.execute(sql, (status, rows_read, rows_loaded, error, datetime.now(timezone.utc), run_id))
    logger.info("ETL run %d finished with status=%s (%d/%d rows loaded).", run_id, status, rows_loaded, rows_read)


def upsert_records(records: list[dict], run_id: int, batch_size: int = 500) -> int:
    """
    Upsert records in batches; returns total rows affected.

    Conflict on external_id → update all mutable fields.
    Rows without external_id are always inserted (no upsert key).
    """
    if not records:
        return 0

    upsert_sql = """
        INSERT INTO records
            (external_id, name, category, price, quantity, description, record_date, extra, etl_run_id)
        VALUES
            (%(external_id)s, %(name)s, %(category)s, %(price)s, %(quantity)s,
             %(description)s, %(record_date)s, %(extra)s::jsonb, %(etl_run_id)s)
        ON CONFLICT (external_id) DO UPDATE SET
            name        = EXCLUDED.name,
            category    = EXCLUDED.category,
            price       = EXCLUDED.price,
            quantity    = EXCLUDED.quantity,
            description = EXCLUDED.description,
            record_date = EXCLUDED.record_date,
            extra       = EXCLUDED.extra,
            etl_run_id  = EXCLUDED.etl_run_id
    """
    insert_sql = """
        INSERT INTO records
            (name, category, price, quantity, description, record_date, extra, etl_run_id)
        VALUES
            (%(name)s, %(category)s, %(price)s, %(quantity)s,
             %(description)s, %(record_date)s, %(extra)s::jsonb, %(etl_run_id)s)
    """

    total = 0
    with _connect() as conn, conn.cursor() as cur:
        for i in range(0, len(records), batch_size):
            batch = records[i : i + batch_size]
            for rec in batch:
                rec["etl_run_id"] = run_id
                sql = upsert_sql if rec.get("external_id") else insert_sql
                cur.execute(sql, rec)
            total += len(batch)
            logger.debug("Loaded batch %d-%d.", i, i + len(batch))
        conn.commit()

    logger.info("Upserted %d records into PostgreSQL.", total)
    return total
