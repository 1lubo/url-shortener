# URL Shortener

A URL shortening service demonstrating REST API design, PostgreSQL database work, and Redis caching.

> 🤖 Vibecoded with [Claude Opus 4.5](https://www.anthropic.com/claude) via [Augment Code](https://www.augmentcode.com/)

## Features

- **URL Shortening** - Create short URLs with custom aliases or auto-generated codes
- **Click Analytics** - Track clicks with timestamps, referrers, and user agents
- **Redis Caching** - Fast redirects with cached URL lookups
- **Optional Auth** - JWT authentication for managing your links
- **REST API** - Clean API design with OpenAPI documentation

## Tech Stack

| Component | Technology |
|-----------|------------|
| Framework | FastAPI |
| Database | PostgreSQL + SQLAlchemy (async) |
| Cache | Redis |
| Auth | JWT (python-jose + bcrypt) |
| Migrations | Alembic |
| Testing | pytest + httpx |
| Deploy | Docker, Fly.io |

## Quick Start

### With Docker (recommended)

```bash
# Start PostgreSQL and Redis
docker-compose up -d db redis

# Run migrations
docker-compose run --rm app alembic upgrade head

# Start the app
docker-compose up app

# API docs at http://localhost:8000/docs
```

### Local Development

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

# Install dependencies
pip install -r requirements.txt

# Set up environment
cp .env.example .env
# Edit .env with your database and Redis URLs

# Run migrations
alembic upgrade head

# Start the server
uvicorn app.main:app --reload
```

## API Endpoints

### Public

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/urls` | Create short URL |
| `GET` | `/{short_code}` | Redirect to original URL |
| `GET` | `/api/v1/urls/{short_code}/stats` | Get click statistics |

### Authentication

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/auth/register` | Create account |
| `POST` | `/api/v1/auth/login` | Get JWT token |

### Authenticated

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/urls` | List your URLs |
| `PATCH` | `/api/v1/urls/{short_code}` | Update URL |
| `DELETE` | `/api/v1/urls/{short_code}` | Deactivate URL |

## Example Usage

```bash
# Create a short URL (no auth required)
curl -X POST http://localhost:8000/api/v1/urls \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com/very/long/path"}'

# Response:
# {"short_code": "abc123", "short_url": "http://localhost:8000/abc123", ...}

# Create with custom alias
curl -X POST http://localhost:8000/api/v1/urls \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com", "custom_alias": "my-link"}'
```

## Running Tests

```bash
# Install test dependencies
pip install -r requirements.txt

# Run tests
pytest tests/ -v
```

## Deployment (Fly.io)

```bash
# Install flyctl and login
fly auth login

# Launch app (first time)
fly launch

# Create PostgreSQL database
fly postgres create

# Create Redis (via Upstash)
fly redis create

# Set secrets
fly secrets set JWT_SECRET_KEY=your-secret-key
fly secrets set DATABASE_URL=your-postgres-url
fly secrets set REDIS_URL=your-redis-url

# Deploy
fly deploy
```

## Project Structure

```
url-shortener/
├── app/
│   ├── main.py           # FastAPI application
│   ├── config.py         # Settings
│   ├── database.py       # SQLAlchemy setup
│   ├── redis.py          # Redis client
│   ├── models/           # SQLAlchemy models
│   ├── schemas/          # Pydantic schemas
│   ├── routers/          # API routes
│   ├── services/         # Business logic
│   └── utils/            # Helpers
├── tests/                # Test suite
├── alembic/              # Database migrations
├── docker-compose.yml
├── Dockerfile
└── fly.toml
```

## License

MIT License (MIT)
