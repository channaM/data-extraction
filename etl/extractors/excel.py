"""Excel (XLS/XLSX)-only extractor — no CSV or PDF imports."""
import logging
from pathlib import Path

import pandas as pd

from etl.detect import detect
from etl.schema import REQUIRED_COLUMNS, ExtractionResult

logger = logging.getLogger(__name__)


def extract(file_path: str, sheet_name: str = "Data") -> ExtractionResult:
    info = detect(file_path)
    if not info.supported or info.file_type not in ("xls", "xlsx"):
        return ExtractionResult(
            df=None, template_info=info, resolved_sheet="N/A",
            status="failed",
            error=info.reason or f"Expected XLS/XLSX, got '{info.file_type}'",
        )
    try:
        engine = "xlrd" if info.file_type == "xls" else "openpyxl"
        xl = pd.ExcelFile(file_path, engine=engine)
        available = xl.sheet_names
        logger.info("Excel sheets found: %s", available)

        resolved = sheet_name if sheet_name in available else available[0]
        if resolved != sheet_name:
            logger.warning("Sheet '%s' not found — using '%s'.", sheet_name, resolved)

        df = xl.parse(resolved, dtype=str)
        df.columns = [str(c).strip().lower() for c in df.columns]
        logger.info("Excel: read %d rows from sheet '%s'.", len(df), resolved)
        df = _validate(df, resolved)
        return ExtractionResult(
            df=df, template_info=info, resolved_sheet=resolved,
            status="success", error=None,
        )
    except Exception as exc:
        logger.exception("Excel extraction failed for %s: %s", file_path, exc)
        return ExtractionResult(
            df=None, template_info=info, resolved_sheet="N/A",
            status="failed", error=str(exc),
        )


def _validate(df: pd.DataFrame, source: str) -> pd.DataFrame:
    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(f"Template missing required columns: {missing} (sheet: {source})")
    return df.dropna(how="all")
