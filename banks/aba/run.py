"""
ABA Bank ETL Engine — main entry point.

Usage:
    python run.py <source_file_path>  [--output-dir <path>]  [--no-db]

Arguments:
    source_file_path        Path to the ABA bank statement (CSV/XLS/XLSX/PDF)
    --output-dir <path>     Override the default output directory (default: ./output)
    --no-db                 Skip SQLite loading (export Excel only)

Output:
    Prints a JSON object to stdout with the run summary.
    Exit code 0 = success, 1 = failure.

This script is designed to be called programmatically by a GUI or launcher.
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path


# ── Ensure the engine root is on the import path ──────────────────────────────
ENGINE_ROOT = Path(__file__).parent
sys.path.insert(0, str(ENGINE_ROOT))

from pipeline.detect    import detect
from pipeline.extract   import extract
from pipeline.transform import dominant_year_month, split_by_currency, transform
from pipeline.export    import export as export_xlsx
from db.sqlite_loader   import load as db_load


# ── Logging setup ─────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.StreamHandler(sys.stderr)],
)
logger = logging.getLogger("aba_etl")


# ──────────────────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────────────────

def run(source_file: str, output_dir: str = "output", skip_db: bool = False) -> dict:
    """
    Full ETL pipeline for one ABA source file.

    Returns a summary dict (also printed as JSON to stdout).
    """
    source_path = Path(source_file).resolve()
    summary: dict = {
        "status":       "success",
        "bank":         "aba",
        "source_file":  source_path.name,
        "file_type":    None,
        "rows_read":    0,
        "rows_exported": 0,
        "rows_loaded_db": 0,
        "output_files": [],
        "year":         None,
        "month":        None,
        "currencies":   [],
        "error":        None,
    }

    # ── 1. Detect ──────────────────────────────────────────────────────────
    logger.info("=== ABA ETL  |  %s ===", source_path.name)
    detect_result = detect(str(source_path))

    if not detect_result.is_valid:
        summary["status"] = "failed"
        summary["error"]  = detect_result.error
        return summary

    summary["file_type"] = detect_result.file_type
    logger.info("Detected format: %s", detect_result.file_type)

    # ── 2. Extract ─────────────────────────────────────────────────────────
    try:
        df = extract(str(source_path), detect_result.file_type)
        summary["rows_read"] = len(df)
    except Exception as exc:
        summary["status"] = "failed"
        summary["error"]  = f"Extract failed: {exc}"
        logger.exception("Extract error")
        return summary

    # ── 3. Transform ───────────────────────────────────────────────────────
    try:
        records = transform(df, str(source_path))
    except Exception as exc:
        summary["status"] = "failed"
        summary["error"]  = f"Transform failed: {exc}"
        logger.exception("Transform error")
        return summary

    if not records:
        summary["status"] = "failed"
        summary["error"]  = "No valid transaction records found after transform."
        return summary

    # ── 4. Determine year / month ──────────────────────────────────────────
    year, month = dominant_year_month(records)
    if not (year and month):
        summary["status"] = "failed"
        summary["error"]  = "Could not determine year/month from transaction dates."
        return summary

    summary["year"]  = year
    summary["month"] = month

    # ── 5. Split by currency and export ───────────────────────────────────
    groups = split_by_currency(records)
    summary["currencies"] = list(groups.keys())

    for currency, ccy_records in groups.items():
        try:
            out_path = export_xlsx(ccy_records, currency, year, month, output_dir)
            summary["output_files"].append(str(out_path))
            summary["rows_exported"] += len(ccy_records)
            logger.info("Exported %d rows → %s", len(ccy_records), out_path)
        except Exception as exc:
            logger.exception("Export failed for currency %s", currency)
            summary["status"] = "partial"
            summary["error"]  = f"Export failed ({currency}): {exc}"

    # ── 6. Load into SQLite ────────────────────────────────────────────────
    if not skip_db:
        try:
            rows_loaded = db_load(
                records,
                source_file=source_path.name,
                rows_read=summary["rows_read"],
                status=summary["status"],
            )
            summary["rows_loaded_db"] = rows_loaded
        except Exception as exc:
            logger.warning("SQLite load failed (non-fatal): %s", exc)
            summary["rows_loaded_db"] = 0

    logger.info(
        "Done: %d read, %d exported, %d loaded to DB  |  Status: %s",
        summary["rows_read"], summary["rows_exported"],
        summary["rows_loaded_db"], summary["status"],
    )
    return summary


# ──────────────────────────────────────────────────────────────────────────────
# CLI entry point
# ──────────────────────────────────────────────────────────────────────────────

def _parse_args(argv: list[str]) -> tuple[str, str, bool]:
    if len(argv) < 2:
        print("Usage: python run.py <source_file> [--output-dir <path>] [--no-db]",
              file=sys.stderr)
        sys.exit(1)

    source_file = argv[1]
    output_dir  = "output"
    skip_db     = False

    i = 2
    while i < len(argv):
        if argv[i] == "--output-dir" and i + 1 < len(argv):
            output_dir = argv[i + 1]
            i += 2
        elif argv[i] == "--no-db":
            skip_db = True
            i += 1
        else:
            i += 1

    return source_file, output_dir, skip_db


if __name__ == "__main__":
    source, out_dir, no_db = _parse_args(sys.argv)

    result = run(source, output_dir=out_dir, skip_db=no_db)

    # Print JSON to stdout so the GUI can read it
    print(json.dumps(result, indent=2, default=str))

    sys.exit(0 if result["status"] in ("success", "partial") else 1)
