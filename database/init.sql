-- Initialize TimescaleDB extension
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- Create raw data table for ingestion
CREATE TABLE IF NOT EXISTS raw_events (
    id SERIAL,
    event_time TIMESTAMPTZ NOT NULL,
    event_type VARCHAR(50) NOT NULL,
    event_data JSONB,
    source VARCHAR(100),
    ingested_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (id, event_time)
);

-- Convert to hypertable for time-series optimization
SELECT create_hypertable('raw_events', 'event_time', if_not_exists => TRUE);

-- Create processed data table for ETL output
CREATE TABLE IF NOT EXISTS processed_events (
    id SERIAL,
    event_time TIMESTAMPTZ NOT NULL,
    event_type VARCHAR(50) NOT NULL,
    event_value NUMERIC,
    event_metadata JSONB,
    source VARCHAR(100),
    processed_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (id, event_time)
);

-- Convert to hypertable
SELECT create_hypertable('processed_events', 'event_time', if_not_exists => TRUE);

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_raw_events_type ON raw_events(event_type, event_time DESC);
CREATE INDEX IF NOT EXISTS idx_raw_events_source ON raw_events(source, event_time DESC);
CREATE INDEX IF NOT EXISTS idx_processed_events_type ON processed_events(event_type, event_time DESC);
CREATE INDEX IF NOT EXISTS idx_processed_events_source ON processed_events(source, event_time DESC);

-- Create a view for API consumption
CREATE OR REPLACE VIEW timeline_summary AS
SELECT 
    event_type,
    COUNT(*) as event_count,
    MIN(event_time) as first_event,
    MAX(event_time) as last_event,
    AVG(event_value) as avg_value
FROM processed_events
GROUP BY event_type;
