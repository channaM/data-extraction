"""ETL pipeline for Excel (XLS/XLSX) templates — isolated from CSV and PDF services."""
from pathlib import Path

from etl.extractors.excel import extract
from etl.pipelines._base import run_from_result


def run(file_path: str, sheet_name: str = "Data") -> dict:
    return run_from_result(extract(file_path, sheet_name), Path(file_path).name)
