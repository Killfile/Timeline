BEGIN;
ALTER TABLE historical_events DROP CONSTRAINT IF EXISTS uq_historical_events_identity;
ALTER TABLE historical_events ADD CONSTRAINT uq_historical_events_identity UNIQUE (title, start_year, end_year, is_bc_start, is_bc_end, wikipedia_url);
COMMIT;
