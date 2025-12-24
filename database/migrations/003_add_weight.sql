-- Add weight (span length in days) to historical_events and extraction debug.

ALTER TABLE historical_events
    ADD COLUMN IF NOT EXISTS weight INTEGER;

ALTER TABLE event_date_extraction_debug
    ADD COLUMN IF NOT EXISTS chosen_weight_days INTEGER;
