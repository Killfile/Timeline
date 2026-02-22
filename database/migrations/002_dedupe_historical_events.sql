-- Defense-in-depth: prevent exact duplicate events.
--
-- We consider an event duplicate if (title, start_year, end_year, is_bc_start, is_bc_end) matches.
-- This helps when multiple list-of-years pages reuse the same bullet list.

DO $$
BEGIN
    -- Prefer a named UNIQUE CONSTRAINT so application code can use:
    --   ON CONFLICT ON CONSTRAINT uq_historical_events_identity
    -- This is more robust than listing columns in the ON CONFLICT target.
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'uq_historical_events_identity'
    ) THEN
        ALTER TABLE historical_events
            ADD CONSTRAINT uq_historical_events_identity
            UNIQUE (title, start_year, end_year, is_bc_start, is_bc_end, wikipedia_url);
    END IF;
END $$;
