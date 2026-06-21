# ETL Manager

A Dockerized ETL pipeline that reads structured data from Excel templates, transforms it, and stores it in **PostgreSQL** — with **Redis** caching for run tracking and record lookups. Includes a **PyQt6 desktop UI** for importing files, browsing results, and editing records.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Language | Python 3.12 |
| ETL pipeline | pandas · openpyxl · psycopg2 |
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
├── main.py                     # CLI entry point — runs the ETL pipeline once
├── ui_app.py                   # PyQt6 desktop UI
├── create_sample_template.py   # Helper — generates a sample Excel template
│
├── etl/
│   ├── config.py               # Reads settings from .env
│   ├── extract.py              # Phase 1 — reads Excel with pandas/openpyxl
│   ├── transform.py            # Phase 2 — validates, casts, normalises rows
│   ├── load.py                 # Phase 3 — upserts records into PostgreSQL
│   ├── cache.py                # Redis helpers — run status & record cache
│   └── pipeline.py             # Orchestrates extract → transform → load
│
├── db/
│   └── init.sql                # Creates tables, indexes, and triggers on first run
│
└── templates/
    └── data_template.xlsx      # Sample Excel template (edit or replace this)
```

---

## Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) ≥ 24
- Python 3.11+ (for the desktop UI only)
- pip packages for the UI:

```bash
pip install PyQt6 psycopg2-binary pandas openpyxl python-dotenv
```

---

## Quick Start

### 1. Clone / open the project

```bash
cd demo
```

### 2. Configure environment variables

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

### 3. Start the infrastructure

```bash
docker compose up -d postgres redis
```

PostgreSQL automatically runs `db/init.sql` on first start, creating the `records` and `etl_runs` tables.

### 4. Generate a sample Excel template *(first time only)*

```bash
python create_sample_template.py
# → templates/data_template.xlsx
```

---

## Running the ETL Pipeline

### Option A — Docker (fully containerised)

```bash
# Runs one ETL pass against templates/data_template.xlsx
docker compose up --build etl
```

### Option B — CLI (local Python)

```bash
python main.py
```

Output:

```
=== ETL Complete ===
  Run ID      : 1
  File        : data_template.xlsx
  Sheet       : Data
  Rows read   : 6
  Rows loaded : 6
  Status      : success
```

---

## Desktop UI

The PyQt6 UI lets you import files interactively and manage records without touching the CLI.

```bash
python ui_app.py
```

### Import tab

| Control | Purpose |
|---------|---------|
| Browse… | Pick any `.xlsx` / `.xls` file |
| Sheet | Name of the sheet to read (default: `Data`) |
| Run ETL | Executes the pipeline in a background thread |
| Pipeline Log | Live log output from all ETL phases |
| Run History | Table of every ETL run with row counts and status |

### Records tab

| Control | Purpose |
|---------|---------|
| Search | Filter by name or description (press Enter or click Search) |
| Category | Dropdown filter by category |
| Double-click row | Opens the Edit dialog |
| Edit Selected | Same as double-click |
| Save (in dialog) | Writes the updated record back to PostgreSQL |
| Refresh | Reloads records from the database |

---

## Excel Template Format

Place your data in a sheet named **`Data`** (or specify a different name in the UI).

| Column | Type | Required | Notes |
|--------|------|----------|-------|
| `id` | text | No | Used as the upsert key — re-importing the same `id` updates the row |
| `name` | **text** | **Yes** | Rows without a name are skipped |
| `category` | text | No | Used for filtering in the UI |
| `price` | decimal | No | e.g. `29.99` |
| `quantity` | integer | No | Whole numbers only |
| `description` | text | No | Free text |
| `date` | date | No | `YYYY-MM-DD` or `DD/MM/YYYY` |

> **Extra columns** — any column not listed above is preserved automatically in the `extra` JSONB field in PostgreSQL.

---

## Database Schema

### `records`

| Column | Type | Notes |
|--------|------|-------|
| `id` | serial PK | |
| `external_id` | text UNIQUE | Mapped from the `id` column in Excel |
| `name` | text NOT NULL | |
| `category` | text | |
| `price` | numeric(12,2) | |
| `quantity` | integer | |
| `description` | text | |
| `record_date` | date | |
| `extra` | jsonb | All unknown Excel columns land here |
| `etl_run_id` | integer FK | References the ETL run that loaded this row |
| `created_at` | timestamptz | Set on insert |
| `updated_at` | timestamptz | Auto-updated on every `UPDATE` via trigger |

### `etl_runs`

| Column | Type | Notes |
|--------|------|-------|
| `id` | serial PK | |
| `file_name` | text | |
| `sheet_name` | text | |
| `status` | text | `running` · `success` · `failed` |
| `rows_read` | integer | Rows extracted from Excel |
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

## Extending the Template

1. **Add a new column** to your Excel sheet — it will be stored in `extra` JSONB automatically, with no code changes needed.
2. **Promote a column to a dedicated DB field** — add it to `db/init.sql`, handle it in `etl/transform.py`, and add it to the `INSERT`/`UPDATE` in `etl/load.py`.
3. **Support multiple sheets** — call `pipeline.run(file, sheet_name="Sheet2")` for each sheet, or loop over sheet names via `pd.ExcelFile(path).sheet_names`.

---

## Useful Commands

```bash
# Start all services
docker compose up -d

# Tail ETL logs
docker compose logs -f etl

# Stop everything and remove volumes (resets the database)
docker compose down -v

# Connect to PostgreSQL directly
docker exec -it etl_postgres psql -U etl_user -d etl_db

# Connect to Redis CLI
docker exec -it etl_redis redis-cli
```
# data-extraction
# data-extraction
# data-extraction
