-- Function for updating the UPDATED_AT column
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TABLE CheckInMethodTypes (
	checkInId SERIAL PRIMARY KEY,
	methodType VARCHAR NOT NULL UNIQUE
);

CREATE TABLE Attendance (
	ID UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    check_in_time TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

	-- Foreign Keys
	user_id UUID REFERENCES users(id) ON DELETE SET NULL,
	event_instance_id UUID NOT NULL REFERENCES events(id) ON DELETE CASCADE,
	check_in_method_id INTEGER NOT NULL REFERENCES CheckInMethodTypes(checkInId),

	-- Audit Columns
    CREATED_AT TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UPDATED_AT TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

	-- Guarantee unique rows by combining User + Event
	UNIQUE (user_id, event_instance_id)
);

-- Create trigger to auto update UPDATED_AT column
CREATE TRIGGER trigger_update_timestamp
BEFORE UPDATE ON Attendance
FOR EACH ROW
WHEN (OLD.* IS DISTINCT FROM NEW.*)
EXECUTE FUNCTION update_updated_at_column();

INSERT INTO CheckInMethodTypes (methodType) VALUES ('QR code'), ('manual');
