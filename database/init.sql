-- Create table for historical events from Wikipedia
CREATE TABLE IF NOT EXISTS historical_events (
    id SERIAL PRIMARY KEY,
    title VARCHAR(500) NOT NULL,
    description TEXT,
    start_year INTEGER,
    end_year INTEGER,
    is_bc_start BOOLEAN DEFAULT FALSE,
    is_bc_end BOOLEAN DEFAULT FALSE,
    -- Derived metric: approximate span length in days.
    -- We treat 1 year as 365 days for now.
    weight INTEGER,
    category VARCHAR(100),
    wikipedia_url TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Defense-in-depth: prevent exact duplicate events.
-- Application code uses: ON CONFLICT ON CONSTRAINT uq_historical_events_identity
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'uq_historical_events_identity'
    ) THEN
        ALTER TABLE historical_events
            ADD CONSTRAINT uq_historical_events_identity
            UNIQUE (title, start_year, end_year, is_bc_start, is_bc_end);
    END IF;
END $$;

-- Observability table: store how we extracted/decided dates for an event
-- This helps debug obvious mistakes (e.g., picking unrelated years in the intro text).
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

-- Create indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_historical_events_start_year ON historical_events(start_year);
CREATE INDEX IF NOT EXISTS idx_historical_events_end_year ON historical_events(end_year);
CREATE INDEX IF NOT EXISTS idx_historical_events_category ON historical_events(category);
CREATE INDEX IF NOT EXISTS idx_historical_events_date_range ON historical_events(start_year, end_year);

-- Create full-text search index
CREATE INDEX IF NOT EXISTS idx_historical_events_search ON historical_events USING gin(to_tsvector('english', title || ' ' || COALESCE(description, '')));

-- Create function to convert year to timeline position (handling BC dates)
CREATE OR REPLACE FUNCTION get_timeline_position(year INTEGER, is_bc BOOLEAN)
RETURNS INTEGER AS $$
BEGIN
    IF is_bc THEN
        RETURN -year;
    ELSE
        RETURN year;
    END IF;
END;
$$ LANGUAGE plpgsql IMMUTABLE;
