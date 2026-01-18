-- Migration 004: Add strategy tracking
-- Create strategies table to track which ingestion strategy generated each event

CREATE TABLE IF NOT EXISTS strategies (
    id SERIAL PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    description TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Add strategy_id to historical_events
ALTER TABLE historical_events
ADD COLUMN IF NOT EXISTS strategy_id INTEGER REFERENCES strategies(id);

-- Create index for efficient querying by strategy
CREATE INDEX IF NOT EXISTS idx_historical_events_strategy_id ON historical_events(strategy_id);

-- Update any existing 'time_periods' to 'list_of_time_periods' for consistency
UPDATE strategies SET name = 'list_of_time_periods' WHERE name = 'time_periods';

-- Insert known strategies
INSERT INTO strategies (name, description) VALUES
    ('list_of_years', 'Extracts events from Wikipedia List of years pages'),
    ('bespoke_events', 'Manually curated events from JSON file'),
    ('list_of_time_periods', 'Extracts events from Wikipedia List of time periods')
ON CONFLICT (name) DO UPDATE SET
    description = EXCLUDED.description;