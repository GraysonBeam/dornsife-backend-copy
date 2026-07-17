-- Database indexes for repository query paths.
-- Primary keys and unique constraints already create their own indexes.

-- Remove indexes superseded by the current query-specific indexes below.
DROP INDEX IF EXISTS idx_attendance_event_instance_id;
DROP INDEX IF EXISTS idx_attendance_user_id;
DROP INDEX IF EXISTS idx_attendance_event_user;
DROP INDEX IF EXISTS idx_events_type_id;
DROP INDEX IF EXISTS idx_users_race_id;
DROP INDEX IF EXISTS idx_events_name;

-- Supports event attendance lookups ordered by check-in time.
CREATE INDEX IF NOT EXISTS idx_attendance_event_checkin_time
ON attendance(event_instance_id, check_in_time);

-- Supports event date filtering and event listing order.
CREATE INDEX IF NOT EXISTS idx_events_start_datetime
ON events(start_datetime);

-- Supports active account lookup by normalized contact fields.
CREATE INDEX IF NOT EXISTS idx_users_active_email
ON users(email)
WHERE is_active = TRUE;

CREATE INDEX IF NOT EXISTS idx_users_active_phone_number
ON users(phone_number)
WHERE is_active = TRUE;

-- Supports admin user pagination.
CREATE INDEX IF NOT EXISTS idx_users_created_at_desc
ON users(created_at DESC);
