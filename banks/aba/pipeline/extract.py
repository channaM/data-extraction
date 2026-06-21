"""
Extract raw transaction data from any supported source file into a DataFrame.

Handles:
  CSV   — auto-detects delimiter and encoding
  XLS   — legacy Excel (xlrd)
  XLSX  — modern Excel (openpyxl)
  PDF   — extracts tables from all pages using pdfplumber

For Excel/PDF, auto-detects where the column header row is by scanning the
first MAX_HEADER_SCAN_ROWS rows for known keywords (defined in config.py).
"""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

from config import (
    DATE_FORMATS,
    EXCEL_SHEET_NAMES,
    HEADER_MIN_MATCH,
    HEADER_SEARCH_KEYWORDS,
    MAX_HEADER_SCAN_ROWS,
)

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────────────
# Public entry point
# ──────────────────────────────────────────────────────────────────────────────

def extract(file_path: str, file_type: str) -> pd.DataFrame:
    """
    Read source file → raw DataFrame with original column names preserved.
    All rows are returned; the transform stage handles filtering.
    """
    path = Path(file_path)
    logger.info("[extract] Reading '%s' as %s", path.name, file_type)

    if file_type == "csv":
        df = _extract_csv(path)
    elif file_type == "xlsx":
        df = _extract_xlsx(path)
    elif file_type == "xls":
        df = _extract_xls(path)
    elif file_type == "pdf":
        df = _extract_pdf(path)
    else:
        raise ValueError(f"Unsupported file type for extraction: {file_type}")

    if df.empty:
        raise ValueError(
            f"No data rows found in '{path.name}'. "
            "Check that the file contains transactions."
        )

    logger.info("[extract] Read %d rows, %d columns from '%s'",
                len(df), len(df.columns), path.name)
    return df


# ──────────────────────────────────────────────────────────────────────────────
# Format-specific extractors
# ──────────────────────────────────────────────────────────────────────────────

def _extract_csv(path: Path) -> pd.DataFrame:
    encodings = ["utf-8-sig", "utf-8", "cp1252", "latin-1"]
    delimiters = [",", ";", "\t", "|"]

    for enc in encodings:
        for delim in delimiters:
            try:
                df = pd.read_csv(path, encoding=enc, sep=delim,
                                 skip_blank_lines=True, dtype=str)
                if len(df.columns) >= 3:
                    return df.dropna(how="all")
            except Exception:
                continue

    raise ValueError(
        f"Could not parse '{path.name}' as CSV. "
        "Please check the file is not corrupted."
    )


def _extract_xlsx(path: Path) -> pd.DataFrame:
    try:
        xl = pd.ExcelFile(path, engine="openpyxl")
    except Exception as exc:
        raise ValueError(f"Cannot open '{path.name}': {exc}") from exc

    sheet = _pick_sheet(xl.sheet_names)
    logger.info("[extract] Using sheet '%s'", sheet)

    raw = pd.read_excel(path, sheet_name=sheet, header=None,
                        engine="openpyxl", dtype=str)
    return _align_header(raw, path.name)


def _extract_xls(path: Path) -> pd.DataFrame:
    try:
        xl = pd.ExcelFile(path, engine="xlrd")
    except Exception as exc:
        raise ValueError(f"Cannot open '{path.name}': {exc}") from exc

    sheet = _pick_sheet(xl.sheet_names)
    logger.info("[extract] Using sheet '%s'", sheet)

    raw = pd.read_excel(path, sheet_name=sheet, header=None,
                        engine="xlrd", dtype=str)
    return _align_header(raw, path.name)


def _extract_pdf(path: Path) -> pd.DataFrame:
    try:
        import pdfplumber
    except ImportError:
        raise ImportError(
            "pdfplumber is required to process PDF files. "
            "Run: pip install pdfplumber"
        )

    frames: list[pd.DataFrame] = []
    header_cols: list[str] | None = None

    with pdfplumber.open(str(path)) as pdf:
        if not pdf.pages:
            raise ValueError(f"'{path.name}' is an empty PDF.")

        for page_num, page in enumerate(pdf.pages, start=1):
            tables = page.extract_tables()
            if not tables:
                logger.debug("[extract] PDF page %d: no tables found", page_num)
                continue

            for table in tables:
                if not table or not table[0]:
                    continue
                df_page = pd.DataFrame(table[1:], columns=table[0], dtype=object)
                df_page = df_page.astype(str).replace("None", pd.NA)
                df_page = df_page.dropna(how="all")

                if header_cols is None:
                    header_cols = list(df_page.columns)
                    frames.append(df_page)
                else:
                    # Subsequent pages: drop repeated header row if present
                    if list(df_page.columns) == header_cols:
                        frames.append(df_page)
                    else:
                        df_page.columns = header_cols[:len(df_page.columns)]
                        frames.append(df_page)

    if not frames:
        raise ValueError(
            f"No tables found in '{path.name}'. "
            "This PDF may be a scanned image. "
            "Please provide a text-based PDF."
        )

    return pd.concat(frames, ignore_index=True)


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

def _pick_sheet(sheet_names: list[str]) -> str:
    """Return the preferred sheet name, or fall back to the first sheet."""
    for preferred in EXCEL_SHEET_NAMES:
        for name in sheet_names:
            if name.strip().lower() == preferred.lower():
                return name
    return sheet_names[0]


def _align_header(raw: pd.DataFrame, filename: str) -> pd.DataFrame:
    """
    Scan the first MAX_HEADER_SCAN_ROWS rows to find the column header row.
    Uses that row as the DataFrame header and returns everything below it.
    """
    for idx in range(min(MAX_HEADER_SCAN_ROWS, len(raw))):
        row_vals = [str(v).strip().lower() for v in raw.iloc[idx].fillna("")]
        matches = sum(1 for v in row_vals if any(kw in v for kw in HEADER_SEARCH_KEYWORDS))
        if matches >= HEADER_MIN_MATCH:
            headers = [str(v).strip() for v in raw.iloc[idx].fillna("")]
            df = raw.iloc[idx + 1:].copy()
            df.columns = headers
            df = df.dropna(how="all").reset_index(drop=True)
            logger.info("[extract] Header row found at row %d in '%s'", idx + 1, filename)
            return df

    # No header row found — treat row 0 as headers
    logger.warning("[extract] No header row detected in '%s'; using row 0 as headers.", filename)
    df = raw.copy()
    df.columns = [str(v).strip() for v in raw.iloc[0].fillna("")]
    return df.iloc[1:].dropna(how="all").reset_index(drop=True)
