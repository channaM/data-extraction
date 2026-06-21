"""ETL pipeline for CSV templates — isolated from Excel and PDF services."""
from pathlib import Path

from etl.extractors.csv import extract
from etl.pipelines._base import run_from_result


def run(file_path: str) -> dict:
    return run_from_result(extract(file_path), Path(file_path).name)
