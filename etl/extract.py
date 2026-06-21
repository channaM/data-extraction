"""Extract phase — delegates to per-template extractors.

Re-exports ExtractionResult, COLUMN_MAP, and REQUIRED_COLUMNS from etl.schema
so any existing code that imports them from here continues to work.
"""
import logging
from pathlib import Path

from etl.detect import detect
from etl.schema import COLUMN_MAP, REQUIRED_COLUMNS, ExtractionResult  # noqa: F401

logger = logging.getLogger(__name__)


def extract(file_path: str, sheet_name: str = "Data") -> ExtractionResult:
    """Detect file type and delegate to the matching per-template extractor."""
    ext = Path(file_path).suffix.lower()

    if ext == ".csv":
        from etl.extractors.csv import extract as _extract
        return _extract(file_path)
    elif ext in (".xls", ".xlsx"):
        from etl.extractors.excel import extract as _extract
        return _extract(file_path, sheet_name)
    elif ext == ".pdf":
        from etl.extractors.pdf import extract as _extract
        return _extract(file_path)
    else:
        info = detect(file_path)
        return ExtractionResult(
            df=None, template_info=info, resolved_sheet="N/A",
            status="failed", error=info.reason,
        )
