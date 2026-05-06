# URL Shortener Service Design

## Overview

A URL shortener service demonstrating REST API design, PostgreSQL database work, and Redis caching. Built with Python/FastAPI, deployed to Fly.io.

## Tech Stack

- **Framework**: FastAPI
- **Database**: PostgreSQL + SQLAlchemy (async)
- **Cache**: Redis (URL lookups)
- **Auth**: Optional JWT tokens
- **Deploy**: Fly.io

## Architecture

```
┌─────────────────────────────────────────────────┐
│                   FastAPI                       │
│  ┌───────────┐  ┌───────────┐  ┌─────────────┐ │
│  │  Shorten  │  │  Redirect │  │   Stats     │ │
│  │  Endpoint │  │  Endpoint │  │  Endpoint   │ │
└────────┼──────────────┼───────────────┼────────┘
         │              │               │
    ┌────▼────┐    ┌────▼────┐    ┌─────▼─────┐
    │  Write  │    │  Read   │    │   Read    │
    │   DB    │    │  Redis  │◄───│    DB     │
    └────┬────┘    │  Cache  │    └───────────┘
         │         └────┬────┘ miss
    ┌────▼──────────────▼────┐
    │      PostgreSQL        │
    └────────────────────────┘
```

## Data Model

### users
| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PRIMARY KEY |
| email | VARCHAR | UNIQUE, NOT NULL |
| password_hash | VARCHAR | NOT NULL |
| created_at | TIMESTAMP | DEFAULT NOW() |

### urls
| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PRIMARY KEY |
| short_code | VARCHAR(20) | UNIQUE, NOT NULL, INDEX |
| original_url | TEXT | NOT NULL |
| user_id | UUID | NULLABLE, FK → users.id |
| created_at | TIMESTAMP | DEFAULT NOW() |
| expires_at | TIMESTAMP | NULLABLE |
| is_active | BOOLEAN | DEFAULT TRUE |

### clicks
| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PRIMARY KEY |
| url_id | UUID | NOT NULL, FK → urls.id, INDEX |
| clicked_at | TIMESTAMP | DEFAULT NOW(), INDEX |
| referrer | TEXT | NULLABLE |
| user_agent | TEXT | NULLABLE |
| ip_hash | VARCHAR | NULLABLE |

## API Endpoints

### Public
- `POST /api/v1/urls` - Create short URL
- `GET /{short_code}` - Redirect to original URL
- `GET /api/v1/urls/{short_code}/stats` - Get click analytics

### Auth
- `POST /api/v1/auth/register` - Create account
- `POST /api/v1/auth/login` - Get JWT token

### Authenticated
- `GET /api/v1/urls` - List user's URLs
- `DELETE /api/v1/urls/{short_code}` - Deactivate URL
- `PATCH /api/v1/urls/{short_code}` - Update URL

## Caching Strategy

- Key: `url:{short_code}`
- Value: `{"original_url": "...", "is_active": true}`
- TTL: 1 hour
- Invalidate on deactivation/update

## Project Structure

```
url-shortener/
├── app/
│   ├── main.py
│   ├── config.py
│   ├── database.py
│   ├── redis.py
│   ├── models/
│   ├── schemas/
│   ├── routers/
│   ├── services/
│   └── utils/
├── tests/
├── alembic/
├── docker-compose.yml
├── Dockerfile
├── fly.toml
└── requirements.txt
```
