"""Shared post-extraction pipeline logic (transform → load → cache)."""
import logging

from etl import cache, load
from etl.schema import ExtractionResult
from etl.transform import transform

logger = logging.getLogger(__name__)


def run_from_result(result: ExtractionResult, file_name: str) -> dict:
    template_type = result.template_info.file_type
    run_id = load.start_run(file_name, result.resolved_sheet, template_type)

    try:
        cache.cache_run_start(run_id, file_name, result.resolved_sheet)
    except Exception as exc:
        logger.warning("Redis unavailable, continuing without cache: %s", exc)

    rows_read = rows_loaded = 0
    status = "success"
    failed_stage: str | None = None
    error_msg: str | None = None

    try:
        if result.status == "failed":
            failed_stage = "extract"
            raise ValueError(result.error)

        rows_read = len(result.df)
        records = transform(result.df)
        rows_loaded = load.upsert_records(records, run_id)

        try:
            for rec in records:
                if rec.get("external_id"):
                    cache.cache_record(rec["external_id"], rec)
        except Exception as exc:
            logger.warning("Failed to cache records: %s", exc)

    except Exception as exc:
        status = "failed"
        error_msg = str(exc)
        if failed_stage is None:
            failed_stage = "transform_or_load"
        logger.exception("Pipeline failed at stage=%s: %s", failed_stage, exc)

    finally:
        load.finish_run(run_id, status, rows_read, rows_loaded, error_msg)
        try:
            cache.cache_run_finish(run_id, status, rows_loaded)
        except Exception:
            pass

    summary = {
        "run_id": run_id, "file": file_name, "template_type": template_type,
        "sheet": result.resolved_sheet, "rows_read": rows_read,
        "rows_loaded": rows_loaded, "status": status,
        "failed_stage": failed_stage, "error": error_msg,
    }
    logger.info("Pipeline summary: %s", summary)
    return summary
