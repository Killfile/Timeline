-- Migration: add table for date extraction observability
--
-- Note: `database/init.sql` only runs when the Postgres data volume is first created.
-- For existing volumes, apply this migration manually (or via a future migration runner).

CREATE TABLE IF NOT EXISTS event_date_extraction_debug (
    id SERIAL PRIMARY KEY,
    historical_event_id INTEGER NOT NULL REFERENCES historical_events(id) ON DELETE CASCADE,
    pageid INTEGER,
    title VARCHAR(500),
    category VARCHAR(100),
    wikipedia_url TEXT,

    extraction_method TEXT NOT NULL,
    extracted_year_matches JSONB,
    chosen_start_year INTEGER,
    chosen_is_bc_start BOOLEAN DEFAULT FALSE,
    chosen_end_year INTEGER,
    chosen_is_bc_end BOOLEAN DEFAULT FALSE,

    -- Derived metric aligned with historical_events.weight.
    chosen_weight_days INTEGER,

    extract_snippet TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_event_date_extraction_debug_event_id
    ON event_date_extraction_debug(historical_event_id);
