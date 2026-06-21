"""Extract phase: read CSV, XLS, XLSX, or PDF templates into a DataFrame."""
import logging
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from etl.detect import TemplateInfo, detect

logger = logging.getLogger(__name__)

REQUIRED_COLUMNS = {"name"}
COLUMN_MAP = {
    "id": "external_id",
    "name": "name",
    "category": "category",
    "price": "price",
    "quantity": "quantity",
    "description": "description",
    "date": "record_date",
}


@dataclass
class ExtractionResult:
    df: pd.DataFrame | None
    template_info: TemplateInfo
    resolved_sheet: str     # "N/A" for CSV and PDF
    status: str             # "success" or "failed"
    error: str | None


def extract(file_path: str, sheet_name: str = "Data") -> ExtractionResult:
    """
    Detect the template type and extract it into a DataFrame.

    Always returns an ExtractionResult — callers check .status instead of
    catching exceptions so the template type is always available for logging.
    """
    info = detect(file_path)

    if not info.supported:
        return ExtractionResult(
            df=None,
            template_info=info,
            resolved_sheet="N/A",
            status="failed",
            error=info.reason,
        )

    try:
        if info.file_type == "csv":
            df, resolved = _extract_csv(file_path)
        elif info.file_type in ("xls", "xlsx"):
            df, resolved = _extract_excel(file_path, sheet_name)
        elif info.file_type == "pdf":
            df, resolved = _extract_pdf(file_path)
        else:
            raise ValueError(f"Unhandled file type: {info.file_type}")

        df = _validate_and_clean(df, resolved)

        return ExtractionResult(
            df=df,
            template_info=info,
            resolved_sheet=resolved,
            status="success",
            error=None,
        )

    except Exception as exc:
        logger.exception("Extraction failed for %s: %s", file_path, exc)
        return ExtractionResult(
            df=None,
            template_info=info,
            resolved_sheet="N/A",
            status="failed",
            error=str(exc),
        )


# ---------------------------------------------------------------------------
# Per-format extractors
# ---------------------------------------------------------------------------

def _extract_csv(file_path: str) -> tuple[pd.DataFrame, str]:
    df = pd.read_csv(file_path, dtype=str)
    df.columns = [str(c).strip().lower() for c in df.columns]
    logger.info("CSV: read %d rows from %s", len(df), file_path)
    return df, "N/A"


def _extract_excel(file_path: str, sheet_name: str) -> tuple[pd.DataFrame, str]:
    engine = "xlrd" if Path(file_path).suffix.lower() == ".xls" else "openpyxl"
    xl = pd.ExcelFile(file_path, engine=engine)
    available = xl.sheet_names
    logger.info("Excel sheets found: %s", available)

    resolved = sheet_name if sheet_name in available else available[0]
    if resolved != sheet_name:
        logger.warning("Sheet '%s' not found — using '%s'.", sheet_name, resolved)

    df = xl.parse(resolved, dtype=str)
    df.columns = [str(c).strip().lower() for c in df.columns]
    logger.info("Excel: read %d rows from sheet '%s'.", len(df), resolved)
    return df, resolved


def _extract_pdf(file_path: str) -> tuple[pd.DataFrame, str]:
    try:
        import pdfplumber
    except ImportError as exc:
        raise ImportError(
            "pdfplumber is required for PDF extraction. "
            "Run: pip install pdfplumber"
        ) from exc

    with pdfplumber.open(file_path) as pdf:
        for page_num, page in enumerate(pdf.pages, start=1):
            tables = page.extract_tables()
            if not tables:
                continue

            raw = tables[0]
            if not raw or len(raw) < 2:
                continue

            headers = [str(h).strip().lower() if h else f"col_{i}"
                       for i, h in enumerate(raw[0])]
            rows = raw[1:]
            df = pd.DataFrame(rows, columns=headers, dtype=object)
            df = df.astype(str).replace("None", pd.NA)
            logger.info("PDF: extracted table from page %d (%d rows).", page_num, len(df))
            return df, f"page_{page_num}"

    raise ValueError(
        "No extractable tables found in the PDF. "
        "Ensure the PDF contains a properly formatted data table."
    )


# ---------------------------------------------------------------------------
# Shared validation
# ---------------------------------------------------------------------------

def _validate_and_clean(df: pd.DataFrame, source: str) -> pd.DataFrame:
    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(f"Template missing required columns: {missing} (source: {source})")
    df = df.dropna(how="all")
    logger.info("Validated %d rows from '%s'.", len(df), source)
    return df
