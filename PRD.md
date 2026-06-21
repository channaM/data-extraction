# Bank Statement ETL Engine — Product Requirements Document

**Document ID:** BSE-PRD-001  
**Version:** 1.0  
**Date:** 2026-06-21  
**Status:** Active — Living Document  
**Owner:** channa.meng  

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Project Vision and Goals](#2-project-vision-and-goals)
3. [Core Design Principles](#3-core-design-principles)
4. [System Architecture Overview](#4-system-architecture-overview)
5. [Folder Structure](#5-folder-structure)
6. [Single Launcher — launcher.bat](#6-single-launcher--launcherbat)
7. [Per-Bank Standalone Engine](#7-per-bank-standalone-engine)
8. [ETL Pipeline — Extract Transform Load](#8-etl-pipeline--extract-transform-load)
9. [Supported Source File Formats](#9-supported-source-file-formats)
10. [Standard Output Schema](#10-standard-output-schema)
11. [Output File and Folder Convention](#11-output-file-and-folder-convention)
12. [GUI Specification — PyQt6](#12-gui-specification--pyqt6)
13. [Database Strategy](#13-database-strategy)
14. [Bank ABA — Proof of Concept](#14-bank-aba--proof-of-concept)
15. [Scalability Plan — Up to 200 Banks](#15-scalability-plan--up-to-200-banks)
16. [Development Roadmap](#16-development-roadmap)
17. [Glossary](#17-glossary)

---

## 1. Executive Summary

This document defines the complete product requirements for the **Bank Statement ETL Engine** — a professional, standalone Python-based system that reads bank statement files in any format (CSV, XLS, XLSX, PDF), normalizes them into a clean standard structure, and produces organized Excel output files grouped by bank, year, month, and currency.

The system is designed to be:
- **Operated by a single double-click** of one `.bat` file
- **Extended bank by bank** without modifying any existing code
- **Upgraded with a GUI** built in PyQt6 for professional user experience
- **Connected to a database** starting with SQLite and migrating to PostgreSQL

The first bank integrated is **ABA Bank** as the proof of concept. Up to **200 banks** will be added over time following the exact same pattern.

---

## 2. Project Vision and Goals

### Vision
One professional desktop application that any user — from an absolute beginner to a power user — can open, select a bank, drop a statement file, and receive a clean, organized Excel output in seconds. No command line. No configuration. No manual column mapping at runtime.

### Goals

| # | Goal | Priority |
|---|------|----------|
| G1 | Process any bank statement format (CSV / XLS / XLSX / PDF) into clean XLSX | Must Have |
| G2 | Single `.bat` launcher — one click opens everything | Must Have |
| G3 | Each bank engine is fully standalone with its own venv | Must Have |
| G4 | Auto-detect year, month, currency from the data — no manual input | Must Have |
| G5 | Output folder auto-created: `output/aba/2025/202501/USD/` | Must Have |
| G6 | Professional PyQt6 GUI — colorful, beginner-friendly | Must Have |
| G7 | SQLite database to store all processed transactions | Must Have |
| G8 | Proof of concept with ABA Bank only first | Must Have |
| G9 | Architecture supports adding up to 200 banks without refactoring | Must Have |
| G10 | Future migration to PostgreSQL via Docker | Should Have |

---

## 3. Core Design Principles

These principles must never be violated when building or extending the system.

### P1 — One Bank, One Engine, One Venv
Every bank has its own isolated Python virtual environment. Bank A's dependencies never affect Bank B. If one bank needs a special library version, it does not break any other bank.

### P2 — Single Entry Point for the User
The user only ever sees and clicks ONE file: `launcher.bat`. That file launches the GUI. The GUI handles everything else. The user never types a command, never selects a venv, never knows which Python is running.

### P3 — Auto-Detect, Never Ask
The engine must figure out the year, month, and currency by reading the transactions. The user must never be asked "what currency is this?" or "what month is this for?". The data tells us.

### P4 — Source Format is the Bank's Problem, Not the User's
Whether ABA sends a PDF or a CSV this month, the engine handles it silently. The user just drops the file. The engine detects the format automatically.

### P5 — Output is Always Clean XLSX
No matter what format comes in, what comes out is always a clean, formatted `.xlsx` Excel file. Professional column headers, proper date formats, readable amounts — ready to open in Excel or Google Sheets immediately.

### P6 — Logic Stays Separate from Interface
The ETL pipeline code (extract, transform, export) must never know about the GUI. The GUI calls the pipeline. This separation means PyQt6 can be added, changed, or replaced without touching any ETL code.

### P7 — Each Bank is a Blueprint Copy
Adding Bank #50 means: copy the `aba/` folder structure, rename it, fill in the column mapping. Nothing else changes. The pattern is identical for every bank.

---

## 4. System Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                        USER                                  │
│                  double-clicks launcher.bat                  │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                   launcher.bat                               │
│   Detects Python, activates GUI venv, launches gui/main.py  │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                  PyQt6 GUI  (gui/)                           │
│  - Bank selector                                             │
│  - File browser / drag-and-drop                              │
│  - Progress display                                          │
│  - Results table                                             │
│  - Output folder opener                                      │
└──────────────────────────┬──────────────────────────────────┘
                           │  calls via subprocess
                           ▼
┌─────────────────────────────────────────────────────────────┐
│             Per-Bank Standalone Engine                       │
│                                                              │
│   banks/aba/run.py   ←──── called with source file path     │
│        │                                                     │
│        ├── extract.py   (reads CSV / XLS / XLSX / PDF)      │
│        ├── transform.py (maps columns → standard schema)     │
│        └── export.py   (writes clean .xlsx output)          │
│                                                              │
│   banks/bankb/run.py  (future)                              │
│   banks/bankc/run.py  (future)                              │
│   ...                                                        │
└──────────────────────────┬──────────────────────────────────┘
                           │ writes to
                           ▼
┌─────────────────────────────────────────────────────────────┐
│   output/aba/2025/202501/USD/aba_202501_USD.xlsx            │
│   output/aba/2025/202502/USD/aba_202502_USD.xlsx            │
│   output/aba/2025/202501/KHR/aba_202501_KHR.xlsx            │
│   ...                                                        │
└──────────────────────────┬──────────────────────────────────┘
                           │ loaded into
                           ▼
┌─────────────────────────────────────────────────────────────┐
│   SQLite Database  (Phase 1)                                 │
│   PostgreSQL via Docker  (Phase 2)                           │
└─────────────────────────────────────────────────────────────┘
```

---

## 5. Folder Structure

```
project-root/
│
├── launcher.bat                  ← THE ONLY FILE THE USER CLICKS
│
├── gui/                          ← Shared PyQt6 GUI application
│   ├── venv/                     ← GUI's own virtual environment
│   ├── requirements.txt          ← PyQt6 + dependencies for GUI only
│   ├── main.py                   ← Entry point launched by launcher.bat
│   ├── windows/
│   │   ├── main_window.py
│   │   ├── progress_dialog.py
│   │   └── results_window.py
│   ├── widgets/
│   │   ├── bank_selector.py
│   │   ├── file_drop_zone.py
│   │   └── transaction_table.py
│   └── assets/
│       ├── icons/
│       └── styles/
│           └── theme.qss         ← PyQt6 stylesheet (colors, fonts)
│
├── banks/
│   │
│   ├── aba/                      ← ABA Bank — fully standalone engine
│   │   ├── venv/                 ← ABA's own virtual environment (.gitignored)
│   │   ├── requirements.txt      ← ABA's own dependencies
│   │   ├── setup.bat             ← Creates ABA venv and installs deps
│   │   ├── run.py                ← Entry point: called by GUI via subprocess
│   │   ├── config.py             ← ABA column mappings + bank metadata
│   │   ├── pipeline/
│   │   │   ├── __init__.py
│   │   │   ├── detect.py         ← Detects file format (csv/xls/xlsx/pdf)
│   │   │   ├── extract.py        ← Reads source file into DataFrame
│   │   │   ├── transform.py      ← Maps ABA columns → standard schema
│   │   │   └── export.py         ← Writes clean .xlsx output file
│   │   └── db/
│   │       └── sqlite_loader.py  ← Loads records into SQLite
│   │
│   ├── bankb/                    ← Future: Bank B (same structure as aba/)
│   └── bankc/                    ← Future: Bank C (same structure as aba/)
│
├── downloads/
│   ├── aba/                      ← Drop ABA source files here
│   ├── bankb/                    ← Drop Bank B source files here (future)
│   └── bankc/                    ← Drop Bank C source files here (future)
│
├── output/
│   └── aba/
│       └── 2025/
│           ├── 202501/
│           │   ├── USD/
│           │   │   └── aba_202501_USD.xlsx
│           │   └── KHR/
│           │       └── aba_202501_KHR.xlsx
│           └── 202502/
│               └── USD/
│                   └── aba_202502_USD.xlsx
│
├── database/
│   └── bank_statements.db        ← SQLite database file
│
└── PRD.md                        ← This document
```

---

## 6. Single Launcher — launcher.bat

### Purpose
One file. One double-click. Everything starts.

### Behavior
```
launcher.bat
  1. Check if Python 3.10+ is installed on this machine
  2. If gui/venv does not exist → run gui/setup.bat to create it
  3. For each bank in banks/ → if banks/{name}/venv does not exist → run banks/{name}/setup.bat
  4. Launch gui/main.py using gui/venv/Scripts/python.exe
  5. GUI takes over from here
```

### Why Not One .bat Per Bank?
One `.bat` per bank means:
- Users must know which bank to click
- Adding a new bank means creating a new `.bat` and telling users about it
- 200 banks = 200 `.bat` files the user must manage

One `.bat` for everything means:
- User clicks once
- GUI shows all available banks
- Selecting a bank in the GUI calls that bank's engine programmatically
- Adding a new bank is invisible to the user — it just appears in the dropdown

---

## 7. Per-Bank Standalone Engine

### What "Standalone" Means
Each bank engine in `banks/{name}/` must be able to run **completely independently** of everything else:
- Its own `requirements.txt`
- Its own `venv/` created by its own `setup.bat`
- No imports from other banks' folders
- No dependency on any `shared/` folder at the root level

### Why This Matters
- Bank A might need `pdfplumber==0.11` but Bank B might need `pdfplumber==0.12`
- Bank C might not need PDF support at all
- A bug in Bank A's dependencies never breaks Bank B
- Each bank can be handed to a different developer or contractor and tested in isolation
- Future PyQt6 GUI can call each bank as a subprocess — no import conflicts

### How the GUI Calls a Bank Engine
```python
# Inside gui/main.py — how GUI triggers a bank's ETL
import subprocess

bank_python = f"banks/{selected_bank}/venv/Scripts/python.exe"
bank_runner = f"banks/{selected_bank}/run.py"
source_file  = "/path/to/dropped/file.csv"

result = subprocess.run(
    [bank_python, bank_runner, source_file],
    capture_output=True,
    text=True
)
# result.stdout contains JSON summary of the run
```

### run.py Contract
Every bank's `run.py` must:
1. Accept a source file path as the first command-line argument
2. Accept an optional `--output-dir` argument (defaults to `../../output/{bank_name}/`)
3. Print a JSON object to stdout upon completion with the following fields:
```json
{
  "status": "success",
  "bank": "aba",
  "source_file": "statement_jan2025.pdf",
  "rows_read": 145,
  "rows_exported": 145,
  "output_file": "output/aba/2025/202501/USD/aba_202501_USD.xlsx",
  "year": 2025,
  "month": 1,
  "currency": "USD",
  "error": null
}
```
4. Exit with code `0` on success, `1` on failure

---

## 8. ETL Pipeline — Extract Transform Load

### Overview
```
Source File
    │
    ▼
[DETECT]      → identify format: csv / xls / xlsx / pdf
    │
    ▼
[EXTRACT]     → read file into a raw DataFrame (all columns, all rows)
    │
    ▼
[TRANSFORM]   → map bank-specific columns → standard schema
               → cast dates, amounts, currencies to correct types
               → detect dominant year / month / currency
               → skip invalid rows with a warning
    │
    ▼
[EXPORT]      → create output folder: output/{bank}/{year}/{YYYYMM}/{CCY}/
               → write clean .xlsx with formatted table
               → return output file path
    │
    ▼
[LOAD — optional] → insert/upsert records into SQLite
```

### DETECT Stage
- Reads the file extension: `.csv`, `.xls`, `.xlsx`, `.pdf`
- Validates the file is not empty, not corrupt, not password-protected
- Returns: `file_type`, `is_valid`, `error_message`

### EXTRACT Stage
- **CSV**: `pandas.read_csv()` with auto-detection of delimiter and encoding
- **XLS**: `xlrd` library for legacy Excel format
- **XLSX**: `openpyxl` via `pandas.read_excel()`
- **PDF**: `pdfplumber` to extract tables from each page, concatenate pages
- Returns: raw `pd.DataFrame` with original column names preserved

### TRANSFORM Stage
Each bank's `config.py` defines a `COLUMN_MAP` dictionary:
```python
# banks/aba/config.py example
COLUMN_MAP = {
    "Tran Date":     "transaction_date",   # ABA's actual column → standard name
    "Narration":     "description",
    "Debit":         "debit_amount",
    "Credit":        "credit_amount",
    "Balance":       "balance",
    "Ref No":        "reference_id",
    "CCY":           "currency",
    "Account No":    "account_number",
}
```
Transform rules:
- Dates → `datetime.date` objects (try multiple formats)
- Amounts → `Decimal` (remove commas, handle parentheses for negatives)
- Currency → uppercase 3-letter code (e.g. `USD`, `KHR`)
- Empty rows → skipped with log warning
- Unknown columns → preserved in `extra_data` field as JSON

### EXPORT Stage
- Creates output directory: `output/{bank}/{year}/{YYYYMM}/{currency}/`
- Filename: `{bank}_{YYYYMM}_{currency}.xlsx`
- Excel formatting applied:
  - Row 1: bold header with colored background
  - Column widths auto-fitted
  - Date column: formatted as `DD/MM/YYYY`
  - Amount columns: formatted as `#,##0.00`
  - Alternating row colors for readability
  - Freeze top row
  - Table style applied

---

## 9. Supported Source File Formats

| Format | Extension | Library | Notes |
|--------|-----------|---------|-------|
| Comma Separated Values | `.csv` | `pandas` | Auto-detect delimiter and encoding |
| Legacy Excel | `.xls` | `xlrd` | Excel 97-2003 format |
| Modern Excel | `.xlsx` | `openpyxl` | Excel 2007 and later |
| PDF | `.pdf` | `pdfplumber` | Extracts tables from all pages |

### Format Detection Rules
1. Check file extension first
2. If extension is `.xls` but file is actually `.xlsx` (common rename issue) → detect by reading magic bytes
3. If PDF has no extractable tables → raise a clear error: "This PDF does not contain readable tables. Please provide a text-based PDF, not a scanned image."
4. If CSV has no headers → raise a clear error: "CSV file must have column headers in the first row."

---

## 10. Standard Output Schema

Every bank, regardless of its source format, produces records with this schema:

| Field | Type | Description | Required |
|-------|------|-------------|----------|
| `transaction_date` | `date` | Date the transaction occurred | Yes |
| `account_number` | `str` | Bank account number | No |
| `account_name` | `str` | Account holder name | No |
| `reference_id` | `str` | Bank's own transaction reference | No |
| `description` | `str` | Narration / transaction description | No |
| `debit_amount` | `Decimal` | Money going out (positive number) | No |
| `credit_amount` | `Decimal` | Money coming in (positive number) | No |
| `balance` | `Decimal` | Running balance after transaction | No |
| `currency` | `str` | 3-letter currency code (USD, KHR) | Yes |
| `bank_name` | `str` | Bank identifier (e.g. `aba`) | Yes |
| `source_file` | `str` | Original filename that was processed | Yes |

### Amount Convention
- Debit (money out) and credit (money in) are always stored as **positive numbers** in separate columns
- If the source bank uses a single `amount` column with positive/negative values, the transform stage splits them into `debit_amount` and `credit_amount`

---

## 11. Output File and Folder Convention

### Folder Path
```
output/
  {bank_name}/
    {year}/
      {year}{month_2digits}/
        {CURRENCY}/
          {bank_name}_{year}{month_2digits}_{CURRENCY}.xlsx
```

### Real Examples
```
output/aba/2025/202501/USD/aba_202501_USD.xlsx
output/aba/2025/202501/KHR/aba_202501_KHR.xlsx
output/aba/2025/202502/USD/aba_202502_USD.xlsx
output/aba/2024/202412/USD/aba_202412_USD.xlsx
```

### Multi-Currency Files
If a single source file contains transactions in both USD and KHR:
- The engine splits them by currency
- Produces two separate output files — one per currency
- Each goes into its own currency subfolder

### Auto-Detection Logic
The engine determines `{year}`, `{month}`, and `{CURRENCY}` from the data:
1. Count all unique `(year, month)` pairs from `transaction_date`
2. Use the most frequent pair as the canonical year/month
3. Count all unique `currency` values
4. If one currency: use it
5. If multiple currencies: split into separate files per currency

---

## 12. GUI Specification — PyQt6

### Design Philosophy
- Any user — from an absolute beginner to a power user — must be able to use this without reading any instructions
- Color scheme: dark professional theme with bank-brand accent colors
- Every action has a clear visual result (progress bars, status icons, success messages)
- Never show a command line window to the user

### Main Window Layout
```
┌─────────────────────────────────────────────────────────────┐
│  🏦  Bank Statement ETL Engine            [─] [□] [✕]      │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  SELECT BANK:  [▼ ABA Bank              ]                   │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                                                     │   │
│  │        Drag & Drop your statement file here         │   │
│  │                                                     │   │
│  │    or  [ Browse File ]                              │   │
│  │                                                     │   │
│  │    Supported: .csv  .xls  .xlsx  .pdf               │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  [ Process Statement ]                                      │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│  RESULTS                                                    │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Date       │ Description    │ Debit  │ Credit │ Bal  │   │
│  │ 01/01/2025 │ Transfer In    │        │ 500.00 │ ...  │   │
│  │ 02/01/2025 │ ATM Withdrawal │ 100.00 │        │ ...  │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  ✅ 145 transactions exported                               │
│  📁 [ Open Output Folder ]                                  │
└─────────────────────────────────────────────────────────────┘
```

### Color Theme
| Element | Color |
|---------|-------|
| Window background | `#1a1a2e` (dark navy) |
| Panel background | `#16213e` |
| Accent / buttons | `#0f3460` → hover `#e94560` |
| Success indicators | `#00b894` (green) |
| Error indicators | `#e17055` (orange-red) |
| Table header | `#0f3460` |
| Table row even | `#16213e` |
| Table row odd | `#1a1a2e` |
| Text primary | `#ffffff` |
| Text secondary | `#a0aec0` |

### Key Interactions
1. **Bank Selector**: Dropdown auto-populated from `banks/` folder — any new bank added to the folder appears here automatically
2. **File Drop Zone**: Drag a file onto the zone OR click Browse — both work
3. **Process Button**: Disabled until a bank is selected and a file is chosen. Shows a spinner while running.
4. **Progress**: Real-time progress shown while processing (Extracting... Transforming... Exporting...)
5. **Results Table**: Shows all exported transactions in a scrollable table
6. **Open Output Folder**: One click opens the exact output folder in Windows Explorer / macOS Finder
7. **Error Display**: If something goes wrong, a friendly message in red explains what happened (not a stack trace)

---

## 13. Database Strategy

### Phase 1 — SQLite (Current)

SQLite is a single-file database. No server needed. No installation. Perfect for a standalone desktop application.

**Database file location:** `database/bank_statements.db`

**Main table schema:**
```sql
CREATE TABLE IF NOT EXISTS transactions (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    bank_name        TEXT    NOT NULL,
    account_number   TEXT,
    account_name     TEXT,
    transaction_date DATE    NOT NULL,
    reference_id     TEXT,
    description      TEXT,
    debit_amount     REAL,
    credit_amount    REAL,
    balance          REAL,
    currency         TEXT    NOT NULL,
    source_file      TEXT,
    imported_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(bank_name, transaction_date, reference_id, debit_amount, credit_amount)
);

CREATE TABLE IF NOT EXISTS import_runs (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    bank_name    TEXT,
    source_file  TEXT,
    rows_read    INTEGER,
    rows_loaded  INTEGER,
    status       TEXT,
    error        TEXT,
    run_at       DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

**Upsert strategy:** `INSERT OR IGNORE` — re-processing the same file never creates duplicates.

### Phase 2 — PostgreSQL via Docker (Future)

When ready to move to PostgreSQL:
1. Spin up a Docker container: `docker-compose up -d postgres`
2. Point the engine to PostgreSQL via environment variable: `DB_TYPE=postgres`
3. All `sqlite_loader.py` files get a parallel `postgres_loader.py`
4. The ETL pipeline code does not change — only the loader is swapped

**Migration is additive, not destructive.** SQLite remains available. PostgreSQL is an upgrade option.

---

## 14. Bank ABA — Proof of Concept

### Bank Profile
| Property | Value |
|----------|-------|
| Bank Name | ABA Bank |
| Country | Cambodia |
| Engine ID | `aba` |
| Source Folder | `downloads/aba/` |
| Output Folder | `output/aba/` |
| Common Currencies | USD, KHR |
| Status | Phase 1 — Active Development |

### What Needs to Be Confirmed Before Building
Before writing the ABA engine, the following must be confirmed by reviewing an actual ABA bank statement:

1. **Exact column headers** as they appear in the source file
2. **File format** that ABA currently provides (CSV, XLSX, PDF, or multiple)
3. **Date format** used in the statement (e.g., `01/01/2025` or `2025-01-01`)
4. **Amount format**: single column with +/- signs, or separate Debit/Credit columns
5. **Row to start reading from**: does the file have header/summary rows before the data?
6. **Multi-sheet**: if XLSX, which sheet contains the transaction data?
7. **Multi-page**: if PDF, does the header repeat on every page?

### ABA Engine Checklist
- [ ] Confirm source format and column headers with sample file
- [ ] Create `banks/aba/config.py` with confirmed `COLUMN_MAP`
- [ ] Implement `banks/aba/pipeline/extract.py`
- [ ] Implement `banks/aba/pipeline/transform.py`
- [ ] Implement `banks/aba/pipeline/export.py`
- [ ] Implement `banks/aba/pipeline/detect.py`
- [ ] Implement `banks/aba/db/sqlite_loader.py`
- [ ] Implement `banks/aba/run.py` (entry point)
- [ ] Create `banks/aba/requirements.txt`
- [ ] Create `banks/aba/setup.bat`
- [ ] Test with real ABA statement files
- [ ] Validate output Excel matches expected format
- [ ] Validate SQLite records match source data

---

## 15. Scalability Plan — Up to 200 Banks

### How to Add a New Bank (Any Future Bank)

**Step 1 — Create the bank folder**
```
banks/
  newbank/
    requirements.txt   ← copy from aba/, adjust if needed
    setup.bat          ← copy from aba/, change bank name
    run.py             ← copy from aba/, change bank name
    config.py          ← EDIT THIS: put the new bank's column mappings
    pipeline/          ← copy from aba/ — no changes needed
    db/                ← copy from aba/ — no changes needed
```

**Step 2 — Fill in config.py**
```python
BANK_NAME = "newbank"

COLUMN_MAP = {
    "TransDate":      "transaction_date",   # new bank's headers
    "Details":        "description",
    "DR":             "debit_amount",
    "CR":             "credit_amount",
    "Runbal":         "balance",
    "Ref":            "reference_id",
    "Currency":       "currency",
    "AcctNo":         "account_number",
}
```

**Step 3 — Create the downloads folder**
```
downloads/newbank/     ← create this folder
```

**Step 4 — Done.**  
The GUI auto-discovers the new bank. The user sees it in the dropdown immediately. No code changes anywhere else.

### What Never Changes When Adding Banks
- `launcher.bat` — no changes
- `gui/` — no changes (auto-discovers banks)
- Other banks' engines — no changes
- Database schema — no changes
- Output folder structure pattern — no changes

---

## 16. Development Roadmap

### Phase 1 — Foundation (Current Sprint)
- [ ] Finalize this PRD
- [ ] Confirm ABA Bank source format
- [ ] Build ABA standalone engine (no GUI yet)
- [ ] Test ABA engine with real files
- [ ] Validate output Excel quality
- [ ] Implement SQLite loader
- [ ] Create `launcher.bat` (CLI mode first)

### Phase 2 — GUI
- [ ] Set up `gui/` folder with its own venv
- [ ] Build PyQt6 main window
- [ ] Implement bank selector (auto-discovers banks/)
- [ ] Implement file drop zone
- [ ] Wire GUI → subprocess → bank engine
- [ ] Display results table
- [ ] Apply color theme
- [ ] Test on Windows (primary) and macOS

### Phase 3 — Polish and Production
- [ ] Error handling in GUI (friendly messages)
- [ ] Progress bar with real-time updates
- [ ] Open output folder button
- [ ] Application icon
- [ ] Installer / packaged executable (PyInstaller)

### Phase 4 — Database and Second Bank
- [ ] Validate SQLite integration end-to-end
- [ ] Add second bank to prove the pattern works
- [ ] Begin PostgreSQL / Docker planning

### Phase 5 — Scale
- [ ] Add banks 3 through N following the established pattern
- [ ] PostgreSQL migration when volume justifies it
- [ ] Reporting features in GUI (summary by month, by currency)

---

## 17. Glossary

| Term | Definition |
|------|------------|
| ETL | Extract, Transform, Load — the three-stage data processing pipeline |
| Source File | The raw bank statement file as received from the bank (any format) |
| Standard Schema | The fixed set of column names that every bank's output conforms to |
| COLUMN_MAP | A dictionary in each bank's config.py that maps the bank's column names to standard names |
| Venv | Python virtual environment — an isolated folder of Python + packages for one bank |
| XLSX | Microsoft Excel Open XML format — the output format for all processed statements |
| KHR | Cambodian Riel — the local currency of Cambodia |
| USD | United States Dollar |
| SQLite | A lightweight, serverless, file-based SQL database |
| PostgreSQL | A full-featured SQL database server, run in Docker for this project |
| PyQt6 | A Python library for building professional desktop GUI applications |
| subprocess | A Python mechanism to run one Python program from inside another |
| Upsert | Insert a record if it does not exist; skip if it already exists |
| Dominant Year/Month | The most frequent year+month combination found in the transaction dates |
| Drop Zone | The area in the GUI where you can drag and drop a file to process it |
| launcher.bat | The single Windows batch file that the user double-clicks to start the application |

---

*This document is the authoritative reference for all design and implementation decisions. When in doubt about any aspect of the system, refer to this document. When a decision is made that contradicts or extends this document, update this document first.*

**Last Updated:** 2026-06-21  
**Next Review:** When ABA Bank engine is complete and validated
