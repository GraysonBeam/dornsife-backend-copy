--Author: Sue Wu
--Description: user table and lookup table for the races

--Ethnicity lookup table
DROP TABLE IF EXISTS race_lookup CASCADE;
CREATE TABLE race_lookup(
    race_id SERIAL PRIMARY KEY,
    description TEXT NOT NULL
);

--inserting all the data for the lookup ethnicity table
INSERT INTO race_lookup(description) VALUES
    ('White'),
    ('Black or African American'),
    ('American Indian or Alaska Native'),
    ('Native Hawaiian Or Pacific Islander'),
    ('Asian'),
    ('Hispanic or Latino'),
    ('Other');

--User table
DROP TABLE IF EXISTS users CASCADE;
CREATE TABLE users(
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    first_name TEXT,
    last_name TEXT,
    email TEXT,
    phone_number TEXT,
    date_of_birth DATE,
    zip_code TEXT,
    address TEXT,
    race_id INT NOT NULL REFERENCES Race_Lookup(race_id),
    qr_token TEXT UNIQUE NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    parent_id UUID NULL REFERENCES users(id),

    created_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ
);

-- Function to set timestamps on INSERT
CREATE OR REPLACE FUNCTION set_user_timestamps_on_insert()
RETURNS TRIGGER AS $$
BEGIN
    NEW.created_at = NOW();
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Function to set timestamp on UPDATE
CREATE OR REPLACE FUNCTION set_user_timestamp_on_update()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger for INSERT (auto-sets both timestamps)
CREATE TRIGGER before_user_insert
BEFORE INSERT ON users
FOR EACH ROW
EXECUTE FUNCTION set_user_timestamps_on_insert();

-- Trigger for UPDATE (auto-updates updated_at)
CREATE TRIGGER before_user_update
BEFORE UPDATE ON users
FOR EACH ROW
EXECUTE FUNCTION set_user_timestamp_on_update();

--Testing 
/*
Insert a user
INSERT INTO users (first_name, last_name, email) 
VALUES ('Test', 'User', 'test@email.com');

-- Check if timestamps worked
SELECT * FROM users;

-- Update the user's email
UPDATE users SET first_name = 'Jane' WHERE id = 1;
SELECT id, first_name, email, created_at, updated_at FROM users;
*/
