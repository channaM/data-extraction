"""Excel service entry point — runs independently of CSV and PDF services."""
import logging
import sys

from etl.pipelines.excel import run

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m services.run_excel <file.xlsx> [sheet_name]")
        sys.exit(1)

    file_path = sys.argv[1]
    sheet_name = sys.argv[2] if len(sys.argv) > 2 else "Data"
    summary = run(file_path, sheet_name)

    print(f"\n=== Excel ETL Complete ===")
    print(f"  Run ID      : {summary['run_id']}")
    print(f"  File        : {summary['file']}")
    print(f"  Sheet       : {summary['sheet']}")
    print(f"  Rows read   : {summary['rows_read']}")
    print(f"  Rows loaded : {summary['rows_loaded']}")
    print(f"  Status      : {summary['status']}")

    if summary["status"] == "failed":
        print(f"  Error       : {summary['error']}")
        sys.exit(1)
