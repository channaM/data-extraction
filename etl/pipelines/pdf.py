"""ETL pipeline for PDF templates — isolated from CSV and Excel services."""
from pathlib import Path

from etl.extractors.pdf import extract
from etl.pipelines._base import run_from_result


def run(file_path: str) -> dict:
    return run_from_result(extract(file_path), Path(file_path).name)
