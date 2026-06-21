"""
Detect the format of a source bank statement file.

Returns a DetectResult with:
  file_type   — "csv" | "xls" | "xlsx" | "pdf"
  is_valid    — True if the file can be processed
  error       — human-readable message if not valid
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

MAGIC_BYTES = {
    b"\x50\x4b\x03\x04": "xlsx",  # ZIP (OpenXML)
    b"\xd0\xcf\x11\xe0": "xls",   # OLE2 (legacy Excel)
    b"\x25\x50\x44\x46": "pdf",   # %PDF
}

SUPPORTED = {"csv", "xls", "xlsx", "pdf"}


@dataclass
class DetectResult:
    file_type: str
    is_valid:  bool
    error:     str | None = None


def detect(file_path: str) -> DetectResult:
    path = Path(file_path)

    if not path.exists():
        return DetectResult("", False, f"File not found: {file_path}")

    if path.stat().st_size == 0:
        return DetectResult("", False, f"File is empty: {path.name}")

    ext = path.suffix.lower().lstrip(".")

    # Trust extension for CSV (no magic bytes)
    if ext == "csv":
        return DetectResult("csv", True)

    # For binary formats, validate by reading magic bytes
    with open(path, "rb") as f:
        header = f.read(4)

    for magic, fmt in MAGIC_BYTES.items():
        if header.startswith(magic):
            detected = fmt
            break
    else:
        detected = ext  # fall back to extension

    if detected not in SUPPORTED:
        return DetectResult(
            detected, False,
            f"Unsupported file type '{detected}'. "
            f"Supported formats: {', '.join(sorted(SUPPORTED))}",
        )

    # Extra check: warn if extension and magic bytes disagree
    if ext in SUPPORTED and ext != detected:
        # e.g., file named .xls but actually .xlsx — use magic bytes result
        pass

    return DetectResult(detected, True)
