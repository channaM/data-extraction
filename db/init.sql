-- ETL run tracking
CREATE TABLE IF NOT EXISTS etl_runs (
    id            SERIAL PRIMARY KEY,
    file_name     TEXT NOT NULL,
    sheet_name    TEXT NOT NULL,
    template_type TEXT NOT NULL DEFAULT 'unknown',
    status        TEXT NOT NULL CHECK (status IN ('running', 'success', 'failed')),
    rows_read     INTEGER DEFAULT 0,
    rows_loaded   INTEGER DEFAULT 0,
    error_msg     TEXT,
    started_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    finished_at   TIMESTAMPTZ
);

-- Generic records table populated from the Excel template
CREATE TABLE IF NOT EXISTS records (
    id            SERIAL PRIMARY KEY,
    external_id   TEXT UNIQUE,
    name          TEXT NOT NULL,
    category      TEXT,
    price         NUMERIC(12, 2),
    quantity      INTEGER,
    description   TEXT,
    record_date   DATE,
    extra         JSONB,
    etl_run_id    INTEGER REFERENCES etl_runs(id),
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Keep updated_at current on every update
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_records_updated_at
    BEFORE UPDATE ON records
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE INDEX IF NOT EXISTS idx_records_category    ON records(category);
CREATE INDEX IF NOT EXISTS idx_records_record_date ON records(record_date);
CREATE INDEX IF NOT EXISTS idx_records_etl_run_id  ON records(etl_run_id);

-- Migration: add template_type to existing databases (safe to run multiple times)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'etl_runs' AND column_name = 'template_type'
    ) THEN
        ALTER TABLE etl_runs ADD COLUMN template_type TEXT NOT NULL DEFAULT 'unknown';
    END IF;
END
$$;
