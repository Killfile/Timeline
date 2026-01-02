-- Create table for historical events from Wikipedia
CREATE TABLE IF NOT EXISTS historical_events (
    id SERIAL PRIMARY KEY,
    event_key TEXT UNIQUE NOT NULL, -- Deterministic hash for enrichment association
    title VARCHAR(500) NOT NULL,
    description TEXT,
    start_year INTEGER,
    start_month INTEGER,
    start_day INTEGER,
    end_year INTEGER,
    end_month INTEGER,
    end_day INTEGER,
    is_bc_start BOOLEAN DEFAULT FALSE,
    is_bc_end BOOLEAN DEFAULT FALSE,
    -- Derived metric: approximate span length in days.
    -- We treat 1 year as 365 days for now.
    weight INTEGER,
    -- Precision of the date (1.0 = exact, 0.5 = approximate, etc.)
    precision NUMERIC(10, 2),
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
    chosen_start_month INTEGER,
    chosen_start_day INTEGER,
    chosen_is_bc_start BOOLEAN DEFAULT FALSE,
    chosen_end_year INTEGER,
    chosen_end_month INTEGER,
    chosen_end_day INTEGER,
    chosen_is_bc_end BOOLEAN DEFAULT FALSE,

    -- Derived metric aligned with historical_events.weight.
    chosen_weight_days INTEGER,
    
    -- Precision of the span (1.0 = exact, 0.5 = approximate, etc.)
    chosen_precision NUMERIC(10, 2),

    extract_snippet TEXT,
    span_match_notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_event_date_extraction_debug_event_id
    ON event_date_extraction_debug(historical_event_id);

-- Create indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_historical_events_event_key ON historical_events(event_key);
CREATE INDEX IF NOT EXISTS idx_historical_events_start_year ON historical_events(start_year);
CREATE INDEX IF NOT EXISTS idx_historical_events_end_year ON historical_events(end_year);
CREATE INDEX IF NOT EXISTS idx_historical_events_category ON historical_events(category);
CREATE INDEX IF NOT EXISTS idx_historical_events_date_range ON historical_events(start_year, end_year);

-- Create full-text search index
CREATE INDEX IF NOT EXISTS idx_historical_events_search ON historical_events USING gin(to_tsvector('english', title || ' ' || COALESCE(description, '')));

-- Event enrichments table (second-order data that survives reimports)
-- Stores enrichment data tied to event_key rather than event id
CREATE TABLE IF NOT EXISTS event_enrichments (
    event_key TEXT PRIMARY KEY REFERENCES historical_events(event_key) ON DELETE CASCADE,
    interest_count INTEGER DEFAULT 0,
    last_enriched_at TIMESTAMPTZ DEFAULT NOW()
);

-- Event categories table (supports multiple categories per event)
-- Second-order data that survives reimports
-- Tracks both Wikipedia-native and LLM-assigned categories
CREATE TABLE IF NOT EXISTS event_categories (
    event_key TEXT REFERENCES historical_events(event_key) ON DELETE CASCADE,
    category TEXT NOT NULL,
    llm_source TEXT,  -- NULL for Wikipedia, 'gpt-4o-mini' etc for LLM
    confidence FLOAT,  -- NULL for Wikipedia, 0.0-1.0 for LLM
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (event_key, category, COALESCE(llm_source, ''))
);

CREATE INDEX IF NOT EXISTS idx_event_categories_category ON event_categories(category);
CREATE INDEX IF NOT EXISTS idx_event_categories_llm_source ON event_categories(llm_source);

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
