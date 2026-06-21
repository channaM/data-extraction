"""CSV-only extractor — no Excel or PDF imports."""
import logging

import pandas as pd

from etl.detect import detect
from etl.schema import REQUIRED_COLUMNS, ExtractionResult

logger = logging.getLogger(__name__)


def extract(file_path: str) -> ExtractionResult:
    info = detect(file_path)
    if not info.supported or info.file_type != "csv":
        return ExtractionResult(
            df=None, template_info=info, resolved_sheet="N/A",
            status="failed",
            error=info.reason or f"Expected CSV, got '{info.file_type}'",
        )
    try:
        df = pd.read_csv(file_path, dtype=str)
        df.columns = [str(c).strip().lower() for c in df.columns]
        logger.info("CSV: read %d rows from %s", len(df), file_path)
        df = _validate(df)
        return ExtractionResult(
            df=df, template_info=info, resolved_sheet="N/A",
            status="success", error=None,
        )
    except Exception as exc:
        logger.exception("CSV extraction failed for %s: %s", file_path, exc)
        return ExtractionResult(
            df=None, template_info=info, resolved_sheet="N/A",
            status="failed", error=str(exc),
        )


def _validate(df: pd.DataFrame) -> pd.DataFrame:
    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(f"Template missing required columns: {missing}")
    return df.dropna(how="all")
