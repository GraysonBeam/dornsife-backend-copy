# Local Development Guide

This is a development guide for running and testing the dornsife backend API locally. We use Docker Compose to provide a local PostgreSQL database without deploying to Render or messing with a shared database. The backend API runs directly on your local machine without Docker. This is done because in production we do not reference a Docker file. For directly interacting with your local database I recommend using PGAdmin. The information about the connection is in this file.

---

## Second-time+ running

Ensure .env file is present and aligned with all keys in env.example

Start the local database

```bash
docker compose up -d
```

Run the backend

```bash
uvicorn src.main:app --host 127.0.0.1 --port 8000 --reload
```

Docs available at `http://127.0.0.1:8000/docs`

Stop the API Press `Ctrl+C` in the terminal where uvicorn is running.

Stop the database container (data is preserved):
```bash
docker compose down
```

Stop the database and delete all data (full reset):
```bash
docker compose down -v
```

---

## Pre-flight checks

Before starting, confirm Docker is installed and the Docker daemon is running:

If Docker is not installed you can install it here https://www.docker.com/products/docker-desktop/

```bash
docker --version
docker compose version
docker ps
```

If `docker ps` returns an error, start Docker Desktop and try again.

---

## First-time setup

**Step 1 — Copy the environment file**

cp env.example .env

The `.env` file is loaded automatically by the app at startup. Do not worry about SendGrid variables at this time.

**Step 2 — Start the local database**

```bash
docker compose up -d
```

**Step 3 — Create the tables**

Run from the repo root, after the database container is healthy. Order matters (`users` → `pending_registration` → `events` → `create_attendance_table`).

**PowerShell (Windows)**

```powershell
Get-Content -Raw .\sql_schema\users.sql | docker exec -i dornsife-postgres psql -U user -d dornsife_db
Get-Content -Raw .\sql_schema\pending_registration.sql | docker exec -i dornsife-postgres psql -U user -d dornsife_db
Get-Content -Raw .\sql_schema\events.sql | docker exec -i dornsife-postgres psql -U user -d dornsife_db
Get-Content -Raw .\sql_schema\create_attendance_table.sql | docker exec -i dornsife-postgres psql -U user -d dornsife_db
```

**Bash (macOS, Linux, Git Bash)**

```bash
docker exec -i dornsife-postgres psql -U user -d dornsife_db < sql_schema/users.sql
docker exec -i dornsife-postgres psql -U user -d dornsife_db < sql_schema/pending_registration.sql
docker exec -i dornsife-postgres psql -U user -d dornsife_db < sql_schema/events.sql
docker exec -i dornsife-postgres psql -U user -d dornsife_db < sql_schema/create_attendance_table.sql
```

**Step 4 — Run the backend**

Run from the repo root:

```bash
uvicorn src.main:app --host 127.0.0.1 --port 8000 --reload
```

The API will be available at `http://127.0.0.1:8000`.

You can visit `http://127.0.0.1:8000/docs` to see all API endpoints and interact with them there. This will interact with your local Postgres DB.

We are using uvicorn rather than running the python file directly as that is how Render will launch the application.

---

## Verifying the database is ready

```bash
docker compose ps
```

You should see `dornsife-postgres` with status `running (healthy)`. If it shows `starting`, wait a few seconds and run the command again.

---

## How the API connects to the database

`DORNSIFE_DATABASE_URL` in your `.env` file points to:

```
postgresql://user:password@localhost:5433/dornsife_db
```

- Docker maps host port `5433` to the container's Postgres port `5432`
- We changed the port to specifically avoid collisions

---

## Stopping and resetting

**Stop the API:** Press `Ctrl+C` in the terminal where uvicorn is running. The API runs on your host machine, not in Docker, so `docker compose down` does not affect it.

**Stop the database container** (data is preserved):
```bash
docker compose down
```

**Stop the database and delete all data** (full reset):
```bash
docker compose down -v
```

---