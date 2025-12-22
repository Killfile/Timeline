-- Create table for historical events from Wikipedia
CREATE TABLE IF NOT EXISTS historical_events (
    id SERIAL PRIMARY KEY,
    title VARCHAR(500) NOT NULL,
    description TEXT,
    start_date DATE,
    end_date DATE,
    start_year INTEGER,
    end_year INTEGER,
    is_bc_start BOOLEAN DEFAULT FALSE,
    is_bc_end BOOLEAN DEFAULT FALSE,
    category VARCHAR(100),
    wikipedia_url TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

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
