"""PDF-only extractor — pdfplumber is imported lazily so a missing install
only breaks this service, never CSV or Excel services."""
import logging

import pandas as pd

from etl.detect import detect
from etl.schema import REQUIRED_COLUMNS, ExtractionResult

logger = logging.getLogger(__name__)


def extract(file_path: str) -> ExtractionResult:
    info = detect(file_path)
    if not info.supported or info.file_type != "pdf":
        return ExtractionResult(
            df=None, template_info=info, resolved_sheet="N/A",
            status="failed",
            error=info.reason or f"Expected PDF, got '{info.file_type}'",
        )
    try:
        df, resolved = _read_pdf(file_path)
        df = _validate(df, resolved)
        return ExtractionResult(
            df=df, template_info=info, resolved_sheet=resolved,
            status="success", error=None,
        )
    except Exception as exc:
        logger.exception("PDF extraction failed for %s: %s", file_path, exc)
        return ExtractionResult(
            df=None, template_info=info, resolved_sheet="N/A",
            status="failed", error=str(exc),
        )


def _read_pdf(file_path: str) -> tuple[pd.DataFrame, str]:
    try:
        import pdfplumber
    except ImportError as exc:
        raise ImportError(
            "pdfplumber is required for PDF extraction. Run: pip install pdfplumber"
        ) from exc

    with pdfplumber.open(file_path) as pdf:
        for page_num, page in enumerate(pdf.pages, start=1):
            tables = page.extract_tables()
            if not tables:
                continue
            raw = tables[0]
            if not raw or len(raw) < 2:
                continue
            headers = [
                str(h).strip().lower() if h else f"col_{i}"
                for i, h in enumerate(raw[0])
            ]
            df = pd.DataFrame(raw[1:], columns=headers, dtype=object)
            df = df.astype(str).replace("None", pd.NA)
            logger.info("PDF: extracted table from page %d (%d rows).", page_num, len(df))
            return df, f"page_{page_num}"

    raise ValueError(
        "No extractable tables found in the PDF. "
        "Ensure the PDF contains a properly formatted data table."
    )


def _validate(df: pd.DataFrame, source: str) -> pd.DataFrame:
    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(f"Template missing required columns: {missing} (source: {source})")
    return df.dropna(how="all")
