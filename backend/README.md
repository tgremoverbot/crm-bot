# arabic-contact-bot — backend

FastAPI backend for the Arabic Teacher Telegram CRM. Handles the Telegram
webhook, admin REST API, async SQLAlchemy ORM models, Alembic migrations,
and a database-backed scheduler — no Redis or Celery required.

## Stack

- Python 3.12+
- FastAPI + uvicorn
- Pydantic v2 + pydantic-settings
- SQLAlchemy 2.x async + asyncpg (Postgres) / aiosqlite (tests)
- Alembic
- pytest + httpx (ASGI transport) + aiosqlite
- python-json-logger

## Local setup

```powershell
cd backend
py -3.13 -m venv .venv          # or py -3.12 if available
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
copy .env.example .env
# Edit .env and set DATABASE_URL (see "Database" section below)
```

## Run the dev server

```powershell
uvicorn app.main:app --reload --port 8080
```

```powershell
curl http://localhost:8080/health      # {"status":"ok"}
curl http://localhost:8080/api/version
```

`/docs` and `/redoc` are available unless `ENV=production`.

## Tests

Tests run against an **in-memory SQLite database** — no Postgres or Supabase
account required.

```powershell
pytest
```

## Database

### Production: Supabase

The production database is hosted on **Supabase PostgreSQL**. Cloud Run
scales horizontally, so the backend connects through **Supabase Supavisor**
in **transaction-pooler mode** (port 6543).

**How to get the connection string:**

1. Open your Supabase project → **Settings** → **Database**.
2. Scroll to **Connection string** → choose **Transaction pooler** (port 6543).
3. Click the **URI** tab. You will see something like:
   ```
   postgresql://postgres.PROJECT_REF:PASSWORD@aws-0-REGION.pooler.supabase.com:6543/postgres
   ```
4. Replace `postgresql://` with `postgresql+asyncpg://` and paste it as `DATABASE_URL` in your `.env` or Cloud Run secret.

> **Never** use the Supabase `anon` key or `service_role` key for the database
> connection. Use only the Postgres password shown in the connection string.

### Running migrations against Supabase

```powershell
# With DATABASE_URL set in .env pointing to your Supabase project:
alembic upgrade head
```

Alembic reads `DATABASE_URL` from the same `Settings` class as the app, so
no extra configuration is needed.

### Local Postgres (optional)

If you prefer a local Postgres instead of Supabase during development:

```powershell
# docker-compose or local install
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/arabic_bot
alembic upgrade head
uvicorn app.main:app --reload
```

## Configuration

All settings come from environment variables (`.env` or Cloud Run env/secrets).

| Var | Purpose | Default |
|---|---|---|
| `ENV` | `development` / `staging` / `production` / `test` | `development` |
| `LOG_LEVEL` | Python log level | `INFO` |
| `APP_VERSION` | Reported by `/api/version` | `0.1.0` |
| `HOST` / `PORT` | Bind address. Cloud Run sets `PORT` automatically. | `0.0.0.0` / `8080` |
| `DATABASE_URL` | Supabase transaction-pooler URL (`postgresql+asyncpg://...`) | local default |
| `DB_ECHO` | Log all SQL statements | `false` |
| `DB_POOL_SIZE` | SQLAlchemy pool size per Cloud Run instance | `2` |
| `DB_MAX_OVERFLOW` | Additional connections above pool_size | `3` |
| `DB_POOL_PRE_PING` | Test connections before use | `true` |
| `DB_POOL_RECYCLE` | Recycle connections after N seconds (< Supabase idle timeout) | `1800` |
| `FRONTEND_ORIGIN` | Comma-separated CORS allowlist | `http://localhost:5173` |

> `DATABASE_URL` must **never** be exposed to the frontend. The frontend talks
> to the backend API only.

## Docker

```powershell
docker build -t arabic-contact-bot-backend:dev .
docker run --rm -p 8080:8080 --env-file .env arabic-contact-bot-backend:dev
```

The container runs as a non-root user and respects the `$PORT` env var set by
Cloud Run.

## Layout

```
backend/
├── app/
│   ├── main.py              # FastAPI app factory + lifespan
│   ├── config.py            # Pydantic settings (all env vars)
│   ├── logging.py           # JSON logging + request_id context var
│   ├── middleware.py        # RequestIdMiddleware
│   ├── db/
│   │   ├── base.py          # DeclarativeBase + naming convention
│   │   └── session.py       # Async engine, session factory, get_db dep
│   ├── models/              # SQLAlchemy ORM models
│   ├── repositories/        # DB query functions (no business logic)
│   └── api/routers/
│       ├── health.py        # GET /health
│       └── version.py       # GET /api/version
├── alembic/                 # Alembic migrations
│   └── versions/
│       └── 20260518_0001_initial_schema.py
├── tests/
│   ├── conftest.py          # sqlite in-memory fixtures
│   ├── test_health.py
│   ├── test_version.py
│   ├── test_config.py
│   ├── test_models.py
│   └── test_repositories.py
├── Dockerfile
├── pyproject.toml
└── .env.example
```
