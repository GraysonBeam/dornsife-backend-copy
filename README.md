Dornsife Backend Repo

## Setup

### 1. Create a virtual Python environment

```bash
python -m venv venv
```

### 2. Activate the virtual environment

```bash
source ./venv/Scripts/activate
# or
./venv/Scripts/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

Copy the `env.example` file to `.env` and fill in the required values:

```bash
cp env.example .env
```

Required environment variables:

- **DORNSIFE_DATABASE_URL**: PostgreSQL connection string (format: `postgresql://user:password@host:port/database`)
- **VERIFICATION_TTL**: Time-to-live for verification codes in minutes (e.g., `15`)
- **SENDGRID_API_KEY**: Your SendGrid API key for sending emails
- **SENDGRID_FROM_EMAIL**: Email address that will appear as the sender
- **SENDGRID_VERIFICATION_TEMPLATE_ID**: SendGrid template ID for verification emails

### 5. Run the application

```bash
python src/main.py
```

The API will be available at `http://127.0.0.1:8000`

## Development

### Running tests

```bash
pytest
```

### Linting and formatting

```bash
ruff check --fix
ruff format
```