# ETL Manager

A Dockerized ETL pipeline that reads structured data from **CSV, Excel (XLS/XLSX), and PDF** templates, transforms it, and stores it in **PostgreSQL** — with **Redis** caching for run tracking and record lookups. Includes a **PyQt6 desktop UI** for importing files, browsing results, and editing records.

Each template type runs as its **own isolated service**: if the PDF service goes down, CSV and Excel services are unaffected.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Language | Python 3.12 |
| ETL pipeline | pandas · openpyxl · xlrd · pdfplumber · psycopg2 |
| Database | PostgreSQL 16 |
| Cache | Redis 7 |
| Desktop UI | PyQt6 |
| Containers | Docker · Docker Compose |

---

## Project Structure

```
.
├── docker-compose.yml          # Orchestrates postgres, redis, etl services
├── Dockerfile                  # Python 3.12 image for the ETL app
├── requirements.txt            # Python dependencies
├── .env                        # Environment variables (DB credentials, paths)
│
├── main.py                     # CLI entry point — auto-detects file type and routes
├── ui_app.py                   # PyQt6 desktop UI
├── create_sample_template.py   # Helper — generates a sample Excel template
│
├── etl/
│   ├── schema.py               # Shared types: ExtractionResult, COLUMN_MAP
│   ├── detect.py               # Identifies file type before extraction
│   ├── config.py               # Reads DB/Redis settings from .env
│   │
│   ├── extractors/             # Per-template extractors (isolated imports)
│   │   ├── csv.py              # CSV extraction only
│   │   ├── excel.py            # XLS/XLSX extraction only (openpyxl / xlrd)
│   │   └── pdf.py              # PDF extraction only (pdfplumber, lazy import)
│   │
│   ├── pipelines/              # Per-template pipeline entry points
│   │   ├── _base.py            # Shared: transform → load → cache logic
│   │   ├── csv.py              # CSV pipeline
│   │   ├── excel.py            # Excel pipeline
│   │   └── pdf.py              # PDF pipeline
│   │
│   ├── pipeline.py             # Router — dispatches to the right pipeline by extension
│   ├── transform.py            # Phase 2 — validates, casts, normalises rows
│   ├── load.py                 # Phase 3 — upserts records into PostgreSQL
│   └── cache.py                # Redis helpers — run status & record cache
│
├── services/                   # Standalone entry points, one per template type
│   ├── run_csv.py              # Run only the CSV service
│   ├── run_excel.py            # Run only the Excel service
│   └── run_pdf.py              # Run only the PDF service
│
├── db/
│   └── init.sql                # Creates tables, indexes, and triggers on first run
│
└── templates/
    ├── data_template.xlsx      # Sample Excel template
    └── sample_data.csv         # Sample CSV template
```

---

## How It Works

### ETL Flow

```
File input
    │
    ▼
detect.py          — identify file type from extension (.csv / .xls / .xlsx / .pdf)
    │
    ▼
extractors/        — per-template extractor reads the file into a DataFrame
  csv.py           — pd.read_csv
  excel.py         — pd.ExcelFile (openpyxl or xlrd)
  pdf.py           — pdfplumber (lazy import — never loaded by CSV/Excel services)
    │
    ▼
transform.py       — validate required columns, cast types, collect unknown columns → extra JSONB
    │
    ▼
load.py            — upsert into PostgreSQL (records + etl_runs tables)
    │
    ▼
cache.py           — write run status and record lookups to Redis (best-effort)
```

### Service Isolation

Each template type has its own extractor and pipeline module. They share the same PostgreSQL DB and Redis instance, but **run as separate processes** so a failure in one does not affect the others:

```
services/run_csv.py   →  etl/pipelines/csv.py   →  etl/extractors/csv.py
services/run_excel.py →  etl/pipelines/excel.py →  etl/extractors/excel.py
services/run_pdf.py   →  etl/pipelines/pdf.py   →  etl/extractors/pdf.py
                                  │
                          etl/pipelines/_base.py  (shared)
                          etl/transform.py        (shared)
                          etl/load.py             (shared → same PostgreSQL DB)
                          etl/cache.py            (shared → same Redis)
```

---

## Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) ≥ 24
- Python 3.11+ (for running services and the desktop UI locally)

Install Python dependencies:

```bash
pip install -r requirements.txt
# For the desktop UI also:
pip install PyQt6
```

---

## Quick Start

### 1. Configure environment variables

Edit `.env` — the defaults work with Docker Compose as-is:

```env
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=etl_db
POSTGRES_USER=etl_user
POSTGRES_PASSWORD=etl_pass

REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

EXCEL_TEMPLATE_PATH=templates/data_template.xlsx
```

### 2. Start the infrastructure

```bash
docker compose up -d postgres redis
```

PostgreSQL automatically runs `db/init.sql` on first start, creating the `records` and `etl_runs` tables.

### 3. Generate a sample template *(first time only)*

```bash
python create_sample_template.py
# → templates/data_template.xlsx
```

---

## Running the ETL Pipeline

### Option A — Auto-detect (router)

`main.py` and `etl/pipeline.py` detect the file extension and delegate to the correct per-template pipeline automatically:

```bash
# Uses EXCEL_TEMPLATE_PATH from .env
python main.py

# Or pass any supported file directly
python -c "from etl.pipeline import run; print(run('templates/data_template.xlsx'))"
```

### Option B — Per-template services (recommended for production)

Run each template type as its own independent process:

```bash
# CSV service
python -m services.run_csv templates/sample_data.csv

# Excel service (sheet name is optional, defaults to "Data")
python -m services.run_excel templates/data_template.xlsx
python -m services.run_excel templates/data_template.xlsx MySheet

# PDF service
python -m services.run_pdf templates/report.pdf
```

Example output:

```
=== Excel ETL Complete ===
  Run ID      : 1
  File        : data_template.xlsx
  Sheet       : Data
  Rows read   : 6
  Rows loaded : 6
  Status      : success
```

### Option C — Docker (fully containerised)

```bash
docker compose up --build etl
```

---

## Desktop UI

The PyQt6 UI lets you import any supported file type interactively and manage records without the CLI.

```bash
python ui_app.py
```

### Import tab

| Control | Purpose |
|---------|---------|
| Browse… | Pick any `.xlsx` / `.xls` / `.csv` / `.pdf` file |
| Sheet | Sheet name for Excel files (disabled for CSV and PDF) |
| Run ETL | Executes the matching pipeline in a background thread |
| Pipeline Log | Live log output from all ETL phases |
| Run History | Table of every ETL run with row counts and status |

### Records tab

| Control | Purpose |
|---------|---------|
| Search | Filter by name or description |
| Category | Dropdown filter by category |
| Double-click row | Opens the Edit dialog |
| Edit Selected | Same as double-click |
| Save (in dialog) | Writes the updated record back to PostgreSQL |
| Refresh | Reloads records from the database |

---

## Supported Template Formats

### Excel (`.xlsx` / `.xls`)

Place data in a sheet named **`Data`** (or specify a different name via CLI or UI).

### CSV (`.csv`)

Column headers should match the field names below (case-insensitive).

### PDF (`.pdf`)

The extractor reads the **first table found** on the first page that contains one. Headers must match the field names below.

### Expected columns (all formats)

| Column | Type | Required | Notes |
|--------|------|----------|-------|
| `id` | text | No | Upsert key — re-importing the same `id` updates the row |
| `name` | text | **Yes** | Rows without a name are skipped |
| `category` | text | No | Used for filtering in the UI |
| `price` | decimal | No | e.g. `29.99` |
| `quantity` | integer | No | Whole numbers only |
| `description` | text | No | Free text |
| `date` | date | No | `YYYY-MM-DD`, `DD/MM/YYYY`, or `MM/DD/YYYY` |

> **Extra columns** — any column not listed above is preserved automatically in the `extra` JSONB field, with no code changes needed.

---

## Database Schema

All template types share the same PostgreSQL database and tables.

### `records`

| Column | Type | Notes |
|--------|------|-------|
| `id` | serial PK | |
| `external_id` | text UNIQUE | Mapped from the `id` column in the source file |
| `name` | text NOT NULL | |
| `category` | text | |
| `price` | numeric(12,2) | |
| `quantity` | integer | |
| `description` | text | |
| `record_date` | date | |
| `extra` | jsonb | Unknown source columns land here |
| `etl_run_id` | integer FK | References the ETL run that loaded this row |
| `created_at` | timestamptz | Set on insert |
| `updated_at` | timestamptz | Auto-updated on every `UPDATE` via trigger |

### `etl_runs`

| Column | Type | Notes |
|--------|------|-------|
| `id` | serial PK | |
| `file_name` | text | |
| `sheet_name` | text | `N/A` for CSV and PDF |
| `template_type` | text | `csv` · `xls` · `xlsx` · `pdf` |
| `status` | text | `running` · `success` · `failed` |
| `rows_read` | integer | Rows extracted from source |
| `rows_loaded` | integer | Rows successfully upserted |
| `error_msg` | text | Populated on failure |
| `started_at` | timestamptz | |
| `finished_at` | timestamptz | |

---

## Redis Caching

| Key pattern | TTL | Content |
|-------------|-----|---------|
| `etl:run:<id>` | 24 h | Hash: `file`, `sheet`, `status`, `rows_loaded` |
| `etl:record:<external_id>` | 1 h | JSON blob of the record dict |

The pipeline continues normally if Redis is unavailable — caching is best-effort.

---

## Useful Commands

```bash
# Start infrastructure only
docker compose up -d postgres redis

# Run a specific template service locally
python -m services.run_csv path/to/file.csv
python -m services.run_excel path/to/file.xlsx
python -m services.run_pdf path/to/file.pdf

# Tail ETL logs (Docker)
docker compose logs -f etl

# Stop everything and reset the database
docker compose down -v

# Connect to PostgreSQL directly
docker exec -it etl_postgres psql -U etl_user -d etl_db

# Connect to Redis CLI
docker exec -it etl_redis redis-cli

# Check recent ETL runs
docker exec -it etl_postgres psql -U etl_user -d etl_db \
  -c "SELECT id, file_name, template_type, status, rows_loaded, started_at FROM etl_runs ORDER BY id DESC LIMIT 10;"
```
