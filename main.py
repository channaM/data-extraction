"""ETL entry point: reads the Excel template and loads data into PostgreSQL."""
import logging
import sys

from etl.config import Config
from etl.pipeline import run

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

logger = logging.getLogger(__name__)


if __name__ == "__main__":
    file_path = Config.EXCEL_TEMPLATE_PATH
    sheet = "Data"

    logger.info("Starting ETL pipeline for: %s (sheet=%s)", file_path, sheet)
    summary = run(file_path, sheet_name=sheet)

    if summary["status"] == "failed":
        logger.error("ETL failed: %s", summary["error"])
        sys.exit(1)

    print("\n=== ETL Complete ===")
    print(f"  Run ID        : {summary['run_id']}")
    print(f"  File          : {summary['file']}")
    print(f"  Template type : {summary['template_type']}")
    print(f"  Sheet/source  : {summary['sheet']}")
    print(f"  Rows read     : {summary['rows_read']}")
    print(f"  Rows loaded   : {summary['rows_loaded']}")
    print(f"  Status        : {summary['status']}")
    if summary.get("failed_stage"):
        print(f"  Failed stage  : {summary['failed_stage']}")
