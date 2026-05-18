# arabic-contact-bot — backend

FastAPI backend for the Arabic Teacher Telegram CRM. Phase 1 ships only the
HTTP skeleton: app factory, settings, structured logging, async SQLAlchemy
engine, Alembic config, `/health` and `/api/version` endpoints, and pytest.

The Telegram bot and admin API land in later phases.

## Stack

- Python 3.12
- FastAPI + uvicorn
- Pydantic v2 + pydantic-settings
- SQLAlchemy 2.x async + asyncpg
- Alembic
- pytest + httpx (ASGI transport)
- python-json-logger

## Local setup

```powershell
cd backend
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
copy .env.example .env
```

## Run the dev server

```powershell
uvicorn app.main:app --reload --port 8080
```

Sanity check:

```powershell
curl http://localhost:8080/health
curl http://localhost:8080/api/version
```

`/docs` and `/redoc` are enabled unless `ENV=production`.

## Tests

```powershell
pytest
```

The tests use `httpx.ASGITransport`, so no real HTTP server or database is
needed for Phase 1.

## Database migrations

The DB engine is wired up but no models or migrations are defined yet (Phase 2).
Once models exist, generate and apply migrations with:

```powershell
alembic revision --autogenerate -m "create initial schema"
alembic upgrade head
```

`alembic/env.py` reads `DATABASE_URL` via the same `Settings` class as the app.

## Configuration

All settings come from environment variables (see `.env.example`).

| Var | Purpose | Default |
|---|---|---|
| `ENV` | `development` / `staging` / `production` / `test`. Controls doc exposure. | `development` |
| `LOG_LEVEL` | Python log level. | `INFO` |
| `APP_VERSION` | Reported by `/api/version`. | `0.1.0` |
| `HOST` / `PORT` | Bind address. Cloud Run overrides `PORT`. | `0.0.0.0` / `8080` |
| `DATABASE_URL` | Async SQLAlchemy URL (`postgresql+asyncpg://...`). | local default |
| `DB_ECHO` | Echo SQL statements. | `false` |
| `FRONTEND_ORIGIN` | Comma-separated CORS allowlist. | `http://localhost:5173` |

## Docker

```powershell
docker build -t arabic-contact-bot-backend:dev .
docker run --rm -p 8080:8080 --env-file .env arabic-contact-bot-backend:dev
```

The container runs as a non-root user and respects the `$PORT` env var, so the
same image deploys to Cloud Run without changes.

## Layout

```
backend/
├── app/
│   ├── main.py              # FastAPI app factory + lifespan
│   ├── config.py            # Pydantic settings
│   ├── logging.py           # JSON logging + request_id context
│   ├── middleware.py        # RequestIdMiddleware
│   ├── db/
│   │   ├── base.py          # Declarative base + naming convention
│   │   └── session.py       # Async engine + session dependency
│   └── api/routers/
│       ├── health.py        # GET /health
│       └── version.py       # GET /api/version
├── alembic/                 # migrations (empty for now)
├── tests/                   # pytest suite
├── Dockerfile
├── pyproject.toml
└── .env.example
```
