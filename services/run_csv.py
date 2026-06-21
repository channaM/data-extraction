"""CSV service entry point — runs independently of Excel and PDF services."""
import logging
import sys

from etl.pipelines.csv import run

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m services.run_csv <file.csv>")
        sys.exit(1)

    summary = run(sys.argv[1])

    print(f"\n=== CSV ETL Complete ===")
    print(f"  Run ID      : {summary['run_id']}")
    print(f"  File        : {summary['file']}")
    print(f"  Rows read   : {summary['rows_read']}")
    print(f"  Rows loaded : {summary['rows_loaded']}")
    print(f"  Status      : {summary['status']}")

    if summary["status"] == "failed":
        print(f"  Error       : {summary['error']}")
        sys.exit(1)
