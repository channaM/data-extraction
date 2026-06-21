"""Shared types and column constants used across all per-template extractors."""
from dataclasses import dataclass

import pandas as pd

from etl.detect import TemplateInfo

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
    resolved_sheet: str
    status: str
    error: str | None
