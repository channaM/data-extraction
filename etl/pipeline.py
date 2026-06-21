"""ETL pipeline router — dispatches to the per-template pipeline based on file extension.

Each template pipeline is imported lazily so a broken dependency (e.g. pdfplumber)
only fails the PDF service, not CSV or Excel.
"""
import logging
from pathlib import Path

from etl.detect import detect

logger = logging.getLogger(__name__)

_EXT_TO_TEMPLATE = {
    ".csv":  "csv",
    ".xls":  "excel",
    ".xlsx": "excel",
    ".pdf":  "pdf",
}


def run(file_path: str, sheet_name: str = "Data") -> dict:
    ext = Path(file_path).suffix.lower()
    template = _EXT_TO_TEMPLATE.get(ext)

    if template == "csv":
        from etl.pipelines.csv import run as _run
        return _run(file_path)
    elif template == "excel":
        from etl.pipelines.excel import run as _run
        return _run(file_path, sheet_name)
    elif template == "pdf":
        from etl.pipelines.pdf import run as _run
        return _run(file_path)
    else:
        info = detect(file_path)
        return {
            "run_id": None, "file": Path(file_path).name,
            "template_type": info.file_type, "sheet": "N/A",
            "rows_read": 0, "rows_loaded": 0, "status": "failed",
            "failed_stage": "detect",
            "error": info.reason or f"Unsupported file type: '{ext}'",
        }
