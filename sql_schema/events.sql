CREATE TABLE eventtypes (
    id SERIAL PRIMARY KEY,
    type VARCHAR NOT NULL
);

CREATE TABLE events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR NOT NULL,
    description VARCHAR,
    start_datetime TIMESTAMPTZ NOT NULL,
    end_datetime TIMESTAMPTZ NOT NULL,
    location VARCHAR,
    type_id INTEGER NOT NULL REFERENCES eventtypes(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_events_start_datetime ON events(start_datetime);

-- Create trigger to auto-update updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_events_updated_at BEFORE UPDATE ON Events
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
