# Marrai Backend

Marrai Backend is the FastAPI service that powers Marrai’s AI visibility and Answer Engine Optimization (AEO) audit system.

It accepts a website URL, crawls pages from the same domain, extracts machine-readable signals, runs deterministic and semantic scoring, and returns a structured audit report for the frontend.

## What is Marrai?

Marrai helps website owners understand whether AI answer engines can understand, retrieve, and cite their website.

Traditional SEO focuses on search rankings. Marrai focuses on answer-engine readability: the signals that help AI systems parse, summarize, compare, and cite a website.

## Features

* FastAPI audit API
* Async website crawling
* Same-domain crawl control
* Up to 20 pages crawled per audit
* Static HTML extraction
* Metadata extraction
* Heading hierarchy extraction
* Schema and structured data checks
* Canonical URL checks
* Internal link analysis
* Content quality scoring
* Technical compliance checks
* Semantic alignment scoring with embeddings
* Background job processing with Celery
* Redis-backed worker queue
* PostgreSQL persistence
* Alembic database migrations
* IP-based rate limiting
* Email notification support
* Docker Compose local development
* GitHub Actions CI/CD-ready structure

## Tech Stack

* Python
* FastAPI
* Uvicorn
* PostgreSQL
* asyncpg
* SQLAlchemy Core
* Alembic
* Redis
* Celery
* httpx
* BeautifulSoup4
* Pydantic
* pydantic-settings
* sentence-transformers
* scikit-learn
* PyTorch CPU
* Docker
* Docker Compose
* pytest

## Project Structure

```txt
marrai-backend/
├── .github/
│   └── workflows/
├── alembic/
├── app/
│   ├── api/
│   ├── core/
│   ├── worker/
│   ├── config.py
│   └── logger.py
├── tests/
├── .env.example
├── Dockerfile
├── docker-compose.yml
├── docker-compose.production.yml
├── alembic.ini
├── main.py
├── requirements.txt
└── README.md
```

## How the Audit Works

```txt
1. User submits a website URL
2. Backend creates an audit job
3. Celery worker picks up the job
4. Crawler discovers same-domain pages
5. Parser extracts metadata, headings, schema, links, and content
6. Deterministic scoring runs across AEO categories
7. Semantic scoring evaluates heading-to-section alignment
8. Final report is saved
9. Frontend polls the job until success or failure
```

## Scoring Categories

Marrai currently evaluates:

### Metadata

Checks title tags, meta descriptions, canonical URLs, and robots signals.

### Content Quality

Checks headings, word count, body text, and content structure.

### Structured Data

Checks schema presence, schema types, and FAQ-style structured data.

### Connectivity

Checks internal links and site crawlability.

### Technical Compliance

Checks image alt text and basic machine-readable hygiene.

### Semantic Clarity

Uses embeddings to compare headings with the content beneath them.

## API Endpoints

### Health Check

```txt
GET /health
```

Example:

```bash
curl http://localhost:8000/health
```

Example response:

```json
{
  "status": "ok",
  "env": "development"
}
```

### Create Audit

```txt
POST /api/v1/audit
```

Request:

```json
{
  "url": "https://example.com",
  "email": "user@example.com"
}
```

`email` may be optional depending on the frontend flow.

Example:

```bash
curl -X POST "http://localhost:8000/api/v1/audit" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com",
    "email": "user@example.com"
  }'
```

Example response:

```json
{
  "job_id": "uuid-string",
  "status": "pending"
}
```

### Get Audit Status / Report

```txt
GET /api/v1/audit/{job_id}
```

Example:

```bash
curl http://localhost:8000/api/v1/audit/<job_id>
```

Possible statuses:

```txt
pending
started
crawling
scoring
success
failure
```

Successful report responses include:

```txt
job_id
url
status
result
error_message
created_at
updated_at
completed_at
```

The `result` object contains:

```txt
overall_score
semantic_score
pages_crawled
findings
recommendations
semantic_findings
semantic_recommendations
pages
semantic_pages
unreachable_pages
crawl_duration_seconds
created_at
```

## Local Development

### 1. Clone the repository

```bash
git clone https://github.com/whyismeleige/marrai-backend.git
cd marrai-backend
```

### 2. Create environment file

```bash
cp .env.example .env.docker
```

Example local values:

```env
APP_ENV=development
LOG_LEVEL=INFO

CRAWL_LIMIT=20
CRAWL_TIMEOUT=10
USER_AGENT=aeo-audit-bot/1.0

DB_HOST=postgres
DB_PORT=5432
DB_NAME=aeo_audit
DB_USER=postgres
DB_PASSWORD=postgres

REDIS_URL=redis://redis:6379/0

EMBEDDING_MODEL=all-MiniLM-L6-v2
WORKER_CONCURRENCY_LIMIT=2
```

### 3. Start services

```bash
docker compose up --build
```

This starts:

```txt
FastAPI API server
Celery worker
PostgreSQL
Redis
Alembic migrator
```

The API should be available at:

```txt
http://localhost:8000
```

### 4. Check health

```bash
curl http://localhost:8000/health
```

## Running Without Docker

Create and activate a virtual environment:

```bash
python -m venv venv
source venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Run the server:

```bash
uvicorn main:app --reload
```

This mode requires PostgreSQL and Redis to already be running and reachable from your environment variables.

## Database Migrations

Run migrations with Alembic:

```bash
alembic upgrade head
```

Create a new migration:

```bash
alembic revision -m "describe change"
```

## Testing

Run tests:

```bash
pytest -v
```

## Environment Variables

Common variables:

```txt
APP_ENV
LOG_LEVEL
CRAWL_LIMIT
CRAWL_TIMEOUT
USER_AGENT
DB_HOST
DB_PORT
DB_NAME
DB_USER
DB_PASSWORD
REDIS_URL
EMBEDDING_MODEL
WORKER_CONCURRENCY_LIMIT
```

Production deployments may also require email, CORS, domain, and deployment-specific secrets.

## Frontend Connection

The frontend repository is:

```txt
https://github.com/whyismeleige/marrai-web
```

The frontend calls the backend through Next.js proxy routes.

Expected production API URL:

```txt
https://api.marrai.tech
```

Expected local API URL:

```txt
http://localhost:8000
```

## Development Workflow

Recommended branch flow:

```txt
main = stable deployable backend
feature branches = individual backend changes
```

Example:

```bash
git checkout -b feat/improve-semantic-scoring
pytest -v
git add .
git commit -m "feat(scoring): improve semantic alignment checks"
git push origin feat/improve-semantic-scoring
```

Then open a pull request into `main`.

## Notes

This backend is part of the Marrai MVP. The current goal is to provide a reliable free AEO audit flow that can crawl a site, score it, and return a practical report for frontend users.
