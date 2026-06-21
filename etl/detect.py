"""Template detection: identify file type before extraction is attempted."""
from dataclasses import dataclass
from pathlib import Path

SUPPORTED_EXTENSIONS = {".csv", ".xls", ".xlsx", ".pdf"}


@dataclass
class TemplateInfo:
    file_type: str      # "csv", "xls", "xlsx", "pdf", or "unknown"
    supported: bool
    reason: str | None  # populated only when supported is False


def detect(file_path: str) -> TemplateInfo:
    """Return TemplateInfo describing the file type and whether extraction is supported."""
    path = Path(file_path)
    if not path.exists():
        return TemplateInfo(
            file_type="unknown",
            supported=False,
            reason=f"File not found: {file_path}",
        )

    ext = path.suffix.lower()
    file_type = ext.lstrip(".") or "unknown"

    if ext not in SUPPORTED_EXTENSIONS:
        supported_list = ", ".join(sorted(SUPPORTED_EXTENSIONS))
        return TemplateInfo(
            file_type=file_type,
            supported=False,
            reason=(
                f"Unsupported file type '{ext or '(no extension)'}'. "
                f"Supported: {supported_list}"
            ),
        )

    return TemplateInfo(file_type=file_type, supported=True, reason=None)
